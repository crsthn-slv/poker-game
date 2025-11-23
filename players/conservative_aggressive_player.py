from pypokerengine.players import BasePokerPlayer
import random
from utils.memory_manager import UnifiedMemoryManager
from utils.hand_utils import evaluate_hand_strength
from utils.action_analyzer import analyze_current_round_actions

class ConservativeAggressivePlayer(BasePokerPlayer):
    """Combina Tight (conservador) + Aggressive (agressão seletiva). Conservador no início, agressivo quando ganha. Usa sistema de memória unificado."""
    
    def __init__(self, memory_file="conservative_aggressive_player_memory.json"):
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.05,  # Muito conservador inicialmente
            default_aggression=0.40,  # Baixa agressão inicial
            default_tightness=35  # Muito seletivo inicialmente
        )
        self.memory = self.memory_manager.get_memory()
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.conservative_mode = self.memory.get('conservative_mode', True)  # Modo conservador ativo
        self.initial_stack = None
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        # NOVO: Analisa ações do round atual
        current_actions = analyze_current_round_actions(round_state, self.uuid) if hasattr(self, 'uuid') and self.uuid else None
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.conservative_mode = self.memory.get('conservative_mode', True)
        
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        should_bluff = self._should_bluff()
        
        # NOVO: Ajusta blefe baseado em ações atuais (conservador fica mais conservador)
        if current_actions and current_actions['has_raises']:
            should_bluff = False  # Não blefa se alguém fez raise
        
        if should_bluff:
            action, amount = self._bluff_action(valid_actions, round_state)
        else:
            action, amount = self._normal_action(valid_actions, hand_strength, round_state, current_actions)
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            street = round_state.get('street', 'preflop')
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
        
        return action, amount
    
    def _should_bluff(self):
        """Blefe muito raro em modo conservador."""
        return random.random() < self.bluff_probability
    
    def _bluff_action(self, valid_actions, round_state):
        """Blefe conservador ou agressivo dependendo do modo."""
        if self.conservative_mode:
            # Modo conservador: apenas call
            return valid_actions[1]['action'], valid_actions[1]['amount']
        else:
            # Modo agressivo: pode fazer raise
            if valid_actions[2]['amount']['min'] != -1 and random.random() < 0.6:
                raise_action = valid_actions[2]
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, min(max_amount, min_amount + 25))
                return raise_action['action'], amount
            else:
                return valid_actions[1]['action'], valid_actions[1]['amount']
    
    def _normal_action(self, valid_actions, hand_strength, round_state, current_actions=None):
        """Ação baseada no modo (conservador ou agressivo) e ações atuais."""
        # NOVO: Ajusta threshold baseado em ações do round atual
        adjusted_threshold = self.tightness_threshold
        if current_actions:
            if current_actions['has_raises']:
                # Conservador fica ainda mais conservador
                adjusted_threshold += 8 + (current_actions['raise_count'] * 3)
            elif current_actions['last_action'] == 'raise':
                adjusted_threshold += 5
        
        # Mão muito forte: sempre raise
        if hand_strength >= 55:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, min(max_amount, min_amount + int(25 * self.aggression_level)))
                return raise_action['action'], amount
        
        # Mão forte: depende do modo
        if hand_strength >= adjusted_threshold:
            if not self.conservative_mode and self.aggression_level > 0.6:
                # Modo agressivo: pode fazer raise
                if valid_actions[2]['amount']['min'] != -1:
                    return valid_actions[2]['action'], valid_actions[2]['amount']['min']
            
            # Sempre faz call se passou do threshold
            return valid_actions[1]['action'], valid_actions[1]['amount']
        
        # Mão fraca: fold apenas se for MUITO fraca
        if hand_strength < (self.tightness_threshold - 5):
            return valid_actions[0]['action'], valid_actions[0]['amount']
        
        # Mão média-fraca: call (não desiste tão fácil)
        return valid_actions[1]['action'], valid_actions[1]['amount']
    
    def _evaluate_hand_strength(self, hole_card, round_state=None):
        """Avalia força da mão usando utilitário compartilhado."""
        community_cards = round_state.get('community_card', []) if round_state else None
        return evaluate_hand_strength(hole_card, community_cards)
    
    def receive_game_start_message(self, game_info):
        """Inicializa stack."""
        seats = game_info.get('seats', [])
        if isinstance(seats, list):
            for player in seats:
                if player.get('uuid') == self.uuid:
                    self.initial_stack = player.get('stack', 100)
                    if not hasattr(self.memory_manager, 'initial_stack'):
                        self.memory_manager.initial_stack = self.initial_stack
                    break
    
    def receive_round_start_message(self, round_count, hole_card, seats):
        """Salva memória periodicamente."""
        if round_count % 5 == 0:
            self.memory_manager.save()
        # Armazena cartas no registry global para exibição no final do round
        if hole_card and hasattr(self, 'uuid') and self.uuid:
            from utils.cards_registry import store_player_cards
            from utils.hand_utils import normalize_hole_cards
            hole_cards = normalize_hole_cards(hole_card)
            if hole_cards:
                store_player_cards(self.uuid, hole_cards)
    
    def receive_street_start_message(self, street, round_state):
        pass
    
    def receive_game_update_message(self, action, round_state):
        """Registra ações dos oponentes."""
        player_uuid = action.get('uuid') or action.get('player_uuid')
        if player_uuid and player_uuid != self.uuid:
            self.memory_manager.record_opponent_action(player_uuid, action, round_state)
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprendizado: conservador no início, agressivo quando ganha."""
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Aprendizado: muda de conservador para agressivo quando ganha
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= 5:
            recent_rounds = round_history[-5:]
            win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
            
            # Se está ganhando bem, muda para modo agressivo
            if win_rate > 0.6:
                self.memory['conservative_mode'] = False
                self.memory['aggression_level'] = min(0.80, self.memory['aggression_level'] + 0.10)
                self.memory['bluff_probability'] = min(0.25, self.memory['bluff_probability'] * 1.2)
                self.memory['tightness_threshold'] = max(25, self.memory['tightness_threshold'] - 5)
            # Se está perdendo, volta para modo conservador
            elif win_rate < 0.3:
                self.memory['conservative_mode'] = True
                self.memory['aggression_level'] = max(0.30, self.memory['aggression_level'] - 0.10)
                self.memory['bluff_probability'] = max(0.03, self.memory['bluff_probability'] * 0.8)
                self.memory['tightness_threshold'] = min(40, self.memory['tightness_threshold'] + 5)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.conservative_mode = self.memory.get('conservative_mode', True)
        
        # Salva memória após ajustes
        self.memory_manager.save()

