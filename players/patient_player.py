from pypokerengine.players import BasePokerPlayer
import random
from utils.memory_manager import UnifiedMemoryManager
from utils.hand_utils import evaluate_hand_strength
from utils.action_analyzer import analyze_current_round_actions

class PatientPlayer(BasePokerPlayer):
    """Jogador paciente que espera boas oportunidades antes de agir. Usa sistema de memória unificado."""
    
    def __init__(self, memory_file="patient_player_memory.json"):
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.13,  # Baixo, espera oportunidades
            default_aggression=0.50,  # Moderado
            default_tightness=28  # Seletivo, paciente
        )
        self.memory = self.memory_manager.get_memory()
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.initial_stack = None
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # NOVO: Analisa ações do round atual
        current_actions = analyze_current_round_actions(round_state, self.uuid) if hasattr(self, "uuid") and self.uuid else None
        
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Analisa contexto antes de decidir
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        active_players = len([
            s for s in round_state.get('seats', [])
            if isinstance(s, dict) and s.get('state') == 'participating'
        ])
        
        # Só blefa em situações favoráveis
        should_bluff = self._should_bluff_with_context(pot_size, active_players)
        
        # NOVO: Ajusta blefe baseado em ações atuais
        if current_actions and current_actions['has_raises'] and current_actions['raise_count'] >= 2:
            should_bluff = False  # Não blefa se muito agressão
        
        if should_bluff:
            action, amount = self._bluff_action(valid_actions, round_state)
        else:
            action, amount = self._normal_action(valid_actions, hand_strength, round_state, pot_size, active_players, current_actions)
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            street = round_state.get('street', 'preflop')
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
        
        return action, amount
    
    def _should_bluff_with_context(self, pot_size, active_players):
        """Decide blefe baseado em contexto - paciente."""
        base_prob = self.bluff_probability
        # Aumenta chance de blefe se pot pequeno e poucos jogadores
        if pot_size < 50 and active_players <= 3:
            base_prob *= 1.3
        return random.random() < min(0.20, base_prob)
    
    def _bluff_action(self, valid_actions, round_state):
        """Blefe paciente: prefere call."""
        if valid_actions[2]['amount']['min'] != -1 and random.random() < 0.4:
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, min(max_amount, min_amount + 12))
            return raise_action['action'], amount
        else:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _normal_action(self, valid_actions, hand_strength, round_state, pot_size, active_players, current_actions=None):
        """Ação paciente: espera mãos fortes, considerando ações atuais."""
        adjusted_threshold = self.tightness_threshold
        
        # NOVO: Ajusta threshold baseado em ações do round atual
        if current_actions:
            if current_actions['has_raises']:
                adjusted_threshold += 6 + (current_actions['raise_count'] * 2)
            elif current_actions['last_action'] == 'raise':
                adjusted_threshold += 4
        
        # Mão muito forte: raise paciente
        if hand_strength >= 55:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, min(max_amount, min_amount + 16))
                return raise_action['action'], amount
        
        # Mão forte: call (paciente)
        if hand_strength >= adjusted_threshold:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
        
        # Mão fraca: fold apenas se for MUITO fraca
        if hand_strength < (adjusted_threshold - 5):
            fold_action = valid_actions[0]
            return fold_action['action'], fold_action['amount']
        
        # Mão média-fraca: call (não desiste tão fácil)
        call_action = valid_actions[1]
        return call_action['action'], call_action['amount']
    
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
        """Aprendizado paciente: ajusta muito lentamente."""
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Aprendizado paciente: ajustes muito lentos
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= 20:
            recent_rounds = round_history[-20:]
            win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
            
            # Ajustes muito graduais
            if win_rate > 0.62:
                self.memory['bluff_probability'] = min(0.18, self.memory['bluff_probability'] * 1.001)
                self.memory['aggression_level'] = min(0.58, self.memory['aggression_level'] * 1.001)
            elif win_rate < 0.28:
                self.memory['tightness_threshold'] = min(31, self.memory['tightness_threshold'] + 1)
                self.memory['bluff_probability'] = max(0.09, self.memory['bluff_probability'] * 0.999)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Salva memória após ajustes
        self.memory_manager.save()

