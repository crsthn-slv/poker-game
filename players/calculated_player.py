from pypokerengine.players import BasePokerPlayer
import random
from utils.memory_manager import UnifiedMemoryManager
from utils.hand_utils import evaluate_hand_strength
from utils.action_analyzer import analyze_current_round_actions

class CalculatedPlayer(BasePokerPlayer):
    """Jogador que calcula bem as probabilidades antes de agir. Analítico mas não extremo. Usa sistema de memória unificado."""
    
    def __init__(self, memory_file="calculated_player_memory.json"):
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.14,  # Calculado
            default_aggression=0.54,  # Moderado-alto
            default_tightness=27  # Médio
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
        
        # Calcula contexto antes de decidir
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        active_players = len([
            s for s in round_state.get('seats', [])
            if isinstance(s, dict) and s.get('state') == 'participating'
        ])
        street = round_state.get('street', 'preflop')
        
        # Decisão calculada baseada em múltiplos fatores
        should_bluff = self._calculate_bluff_probability(pot_size, active_players, street, hand_strength)
        
        # NOVO: Ajusta blefe baseado em ações atuais
        if current_actions and current_actions['has_raises'] and current_actions['raise_count'] >= 2:
            should_bluff = False  # Não blefa se muito agressão
        
        if should_bluff:
            action, amount = self._bluff_action(valid_actions, round_state)
        else:
            action, amount = self._normal_action(valid_actions, hand_strength, round_state, pot_size, active_players, current_actions)
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
        
        return action, amount
    
    def _calculate_bluff_probability(self, pot_size, active_players, street, hand_strength):
        """Calcula probabilidade de blefe baseado em múltiplos fatores."""
        base_prob = self.bluff_probability
        
        # Ajusta baseado em contexto
        if pot_size < 40 and active_players <= 2:
            base_prob *= 1.2  # Pot pequeno, poucos jogadores
        elif pot_size > 100:
            base_prob *= 0.8  # Pot grande, mais cauteloso
        
        if street in ['preflop', 'flop']:
            base_prob *= 1.1  # Streets iniciais, mais oportunidades
        
        # Reduz blefe se mão muito fraca
        if hand_strength < 15:
            base_prob *= 0.7
        
        return random.random() < min(0.22, base_prob)
    
    def _bluff_action(self, valid_actions, round_state):
        """Blefe calculado: balanceado."""
        if valid_actions[2]['amount']['min'] != -1 and random.random() < 0.45:
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, min(max_amount, min_amount + 16))
            return raise_action['action'], amount
        else:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _normal_action(self, valid_actions, hand_strength, round_state, pot_size, active_players, current_actions=None):
        """Ação calculada: baseada em análise e ações atuais."""
        adjusted_threshold = self.tightness_threshold
        
        # NOVO: Ajusta threshold baseado em ações do round atual
        if current_actions:
            if current_actions['has_raises']:
                adjusted_threshold += 5 + (current_actions['raise_count'] * 2)
            elif current_actions['last_action'] == 'raise':
                adjusted_threshold += 3
        
        # Mão muito forte: raise calculado
        if hand_strength >= 52:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                # Calcula valor baseado em agressão
                amount = random.randint(min_amount, min(max_amount, min_amount + int(18 * self.aggression_level)))
                return raise_action['action'], amount
        
        # Mão forte: call ou raise pequeno
        if hand_strength >= adjusted_threshold:
            if self.aggression_level > 0.54 and valid_actions[2]['amount']['min'] != -1:
                return valid_actions[2]['action'], valid_actions[2]['amount']['min']
            else:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # Mão fraca: fold apenas se for MUITO fraca
        if hand_strength < (adjusted_threshold - 7):
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
        """Aprendizado calculado: ajusta baseado em análise de resultados."""
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Aprendizado calculado: análise de performance
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= 10:
            recent_rounds = round_history[-10:]
            win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
            
            # Ajustes calculados baseados em win rate
            if win_rate > 0.60:
                self.memory['aggression_level'] = min(0.68, self.memory['aggression_level'] * 1.004)
                self.memory['bluff_probability'] = min(0.19, self.memory['bluff_probability'] * 1.004)
            elif win_rate < 0.32:
                self.memory['tightness_threshold'] = min(30, self.memory['tightness_threshold'] + 1)
                self.memory['aggression_level'] = max(0.45, self.memory['aggression_level'] * 0.996)
                self.memory['bluff_probability'] = max(0.11, self.memory['bluff_probability'] * 0.996)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Salva memória após ajustes
        self.memory_manager.save()

