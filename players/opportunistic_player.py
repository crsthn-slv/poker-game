from pypokerengine.players import BasePokerPlayer
import random
from .memory_manager import UnifiedMemoryManager
from .hand_utils import evaluate_hand_strength

class OpportunisticPlayer(BasePokerPlayer):
    """Combina Smart (contexto) + Aggressive (oportunidades). Identifica oportunidades e ataca agressivamente. Usa sistema de memória unificado."""
    
    def __init__(self, memory_file="opportunistic_player_memory.json"):
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.25,  # Alto blefe inicial
            default_aggression=0.65,  # Alta agressão inicial
            default_tightness=25  # Menos seletivo (oportunista)
        )
        self.memory = self.memory_manager.get_memory()
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.initial_stack = None
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Analisa oportunidades
        opportunity = self._identify_opportunity(round_state)
        
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        should_bluff = self._should_bluff_with_opportunity(opportunity)
        
        if should_bluff:
            action, amount = self._bluff_action(valid_actions, round_state, opportunity)
        else:
            action, amount = self._normal_action(valid_actions, hand_strength, round_state, opportunity)
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            street = round_state.get('street', 'preflop')
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
        
        return action, amount
    
    def _identify_opportunity(self, round_state):
        """Identifica oportunidades de ataque."""
        pot_size = round_state['pot']['main']['amount']
        active_players = len([s for s in round_state['seats'] if s['state'] == 'participating'])
        street = round_state['street']
        
        opportunity_score = 0
        
        # Poucos jogadores = oportunidade
        if active_players <= 2:
            opportunity_score += 30
        
        # Pot pequeno = oportunidade de blefe
        if pot_size < 50:
            opportunity_score += 20
        
        # Street inicial = mais oportunidades
        if street == 'preflop' or street == 'flop':
            opportunity_score += 15
        
        return {
            'score': opportunity_score,
            'pot_size': pot_size,
            'active_players': active_players,
            'street': street
        }
    
    def _should_bluff_with_opportunity(self, opportunity):
        """Decide blefe baseado em oportunidades."""
        # Ajusta probabilidade baseado em oportunidade
        adjusted_prob = self.bluff_probability * (1 + opportunity['score'] / 100)
        return random.random() < min(0.50, adjusted_prob)
    
    def _bluff_action(self, valid_actions, round_state, opportunity):
        """Blefe agressivo quando há oportunidade."""
        # Se oportunidade alta, ataca agressivamente
        if opportunity['score'] > 40 and valid_actions[2]['amount']['min'] != -1:
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, min(max_amount, min_amount + 30))
            return raise_action['action'], amount
        else:
            return valid_actions[1]['action'], valid_actions[1]['amount']
    
    def _normal_action(self, valid_actions, hand_strength, round_state, opportunity):
        """Ação normal considerando oportunidades."""
        # Mão muito forte: sempre ataca
        if hand_strength >= 55:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, min(max_amount, min_amount + int(30 * self.aggression_level)))
                return raise_action['action'], amount
        
        # Mão forte + oportunidade: ataca
        if hand_strength >= 40 and opportunity['score'] > 30:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                return raise_action['action'], raise_action['amount']['min']
        
        # Mão forte: call
        if hand_strength >= 30:
            return valid_actions[1]['action'], valid_actions[1]['amount']
        
        # Mão fraca: fold (a menos que oportunidade muito alta)
        if opportunity['score'] > 50:
            return valid_actions[1]['action'], valid_actions[1]['amount']
        
        return valid_actions[0]['action'], valid_actions[0]['amount']
    
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
            from .cards_registry import store_player_cards
            from .hand_utils import normalize_hole_cards
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
        """Aprende padrões de oportunidades."""
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Aprende quando oportunidades funcionam
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= 10:
            recent_rounds = round_history[-10:]
            win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
            
            # Se está ganhando, aumenta agressão e blefe
            if win_rate > 0.5:
                self.memory['aggression_level'] = min(0.85, self.memory['aggression_level'] + 0.08)
                self.memory['bluff_probability'] = min(0.40, self.memory['bluff_probability'] * 1.1)
            # Se está perdendo, reduz
            elif win_rate < 0.3:
                self.memory['aggression_level'] = max(0.45, self.memory['aggression_level'] - 0.10)
                self.memory['bluff_probability'] = max(0.15, self.memory['bluff_probability'] * 0.9)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        self.aggression_level = self.memory['aggression_level']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Salva memória após ajustes
        self.memory_manager.save()

