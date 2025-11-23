from pypokerengine.players import BasePokerPlayer
import random
from utils.memory_manager import UnifiedMemoryManager
from utils.hand_utils import evaluate_hand_strength

class AdaptivePlayer(BasePokerPlayer):
    """Combina Smart (análise) + Random (exploração). Usa sistema de memória unificado."""
    
    def __init__(self, memory_file="adaptive_player_memory.json"):
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.17,  # Nivelado: média
            default_aggression=0.56,  # Nivelado: ligeiramente acima da média
            default_tightness=27  # Nivelado: média
        )
        self.memory = self.memory_manager.get_memory()
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Sistema de exploração vs exploração (reduzido)
        self.epsilon = 0.10  # 10% de exploração (reduzido de 15%)
        self.exploration_decay = 0.999  # Reduz exploração muito lentamente
        self.initial_stack = None
        self.current_street = 'preflop'
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Avalia força da mão
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        
        # Exploração: escolhe aleatoriamente (reduzido)
        if random.random() < self.epsilon:
            action, amount = self._explore_action(valid_actions)
            should_bluff = False
        else:
            # Exploração: usa análise
            should_bluff = self._should_bluff_with_analysis(round_state)
            
            if should_bluff:
                action, amount = self._bluff_action(valid_actions, round_state)
            else:
                action, amount = self._normal_action(valid_actions, hand_strength, round_state)
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            street = round_state.get('street', 'preflop')
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
        
        return action, amount
    
    def _explore_action(self, valid_actions):
        """Exploração: escolhe ação aleatória para aprender."""
        action_choice = random.choice(['fold', 'call', 'raise'])
        
        if action_choice == 'fold':
            return valid_actions[0]['action'], valid_actions[0]['amount']
        elif action_choice == 'call':
            return valid_actions[1]['action'], valid_actions[1]['amount']
        else:
            if valid_actions[2]['amount']['min'] != -1:
                min_amount = valid_actions[2]['amount']['min']
                max_amount = valid_actions[2]['amount']['max']
                amount = random.randint(min_amount, max_amount)
                return valid_actions[2]['action'], amount
            else:
                return valid_actions[1]['action'], valid_actions[1]['amount']
    
    def _should_bluff_with_analysis(self, round_state):
        """Decide blefe baseado em análise."""
        return random.random() < self.bluff_probability
    
    def _bluff_action(self, valid_actions, round_state):
        """Blefe baseado em análise."""
        if valid_actions[2]['amount']['min'] != -1 and random.random() < 0.6:
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, min(max_amount, min_amount + 20))
            return raise_action['action'], amount
        else:
            return valid_actions[1]['action'], valid_actions[1]['amount']
    
    def _normal_action(self, valid_actions, hand_strength, round_state):
        """Ação baseada em análise."""
        adjusted_threshold = self.tightness_threshold
        
        # Mão muito forte: raise
        if hand_strength >= 60:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                return raise_action['action'], raise_action['amount']['min']
        
        # Mão forte: call ou raise moderado
        if hand_strength >= 40:
            if random.random() < 0.4:
                raise_action = valid_actions[2]
                if raise_action['amount']['min'] != -1:
                    return raise_action['action'], raise_action['amount']['min']
            else:
                return valid_actions[1]['action'], valid_actions[1]['amount']
        
        # Mão média: depende do threshold
        if hand_strength >= adjusted_threshold:
            return valid_actions[1]['action'], valid_actions[1]['amount']
        
        # Mão fraca: fold
        return valid_actions[0]['action'], valid_actions[0]['amount']
    
    def _evaluate_hand_strength(self, hole_card, round_state):
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
        """Registra mudança de street."""
        self.current_street = street
    
    def receive_game_update_message(self, action, round_state):
        """Registra ações dos oponentes."""
        player_uuid = action.get('uuid') or action.get('player_uuid')
        if player_uuid and player_uuid != self.uuid:
            self.memory_manager.record_opponent_action(player_uuid, action, round_state)
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprendizado avançado com exploração vs exploração (evolução lenta)."""
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Reduz exploração muito lentamente
        self.epsilon = max(0.05, self.epsilon * self.exploration_decay)
        
        # Aprendizado lento e sutil: ajusta baseado em win rate recente
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= 10:
            recent_rounds = round_history[-10:]
            win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
            
            # Evolução muito lenta: ajustes de 0.1% por vez
            if win_rate > 0.6:
                self.memory['bluff_probability'] = min(0.20, self.memory['bluff_probability'] * 1.001)
            elif win_rate < 0.3:
                self.memory['bluff_probability'] = max(0.12, self.memory['bluff_probability'] * 0.999)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Salva memória após ajustes
        self.memory_manager.save()
