from pypokerengine.players import BasePokerPlayer
import random
import json
import os
from .memory_utils import get_memory_path

class OpportunisticPlayer(BasePokerPlayer):
    """Combina Smart (contexto) + Aggressive (oportunidades). Identifica oportunidades e ataca agressivamente. Com memória persistente."""
    
    def __init__(self, memory_file="opportunistic_player_memory.json"):
        self.memory_file = get_memory_path(memory_file)
        self.bluff_probability = 0.25  # 25% inicial
        
        # Análise de oportunidades
        self.opportunity_patterns = {}  # Padrões de quando atacar
        self.aggression_level = 0.65
        
        # Sistema de aprendizado avançado
        self.round_results = []
        self.total_rounds = 0
        self.wins = 0
        self.initial_stack = None
        self.current_stack = None
        
        # Carrega memória anterior se existir
        self.load_memory()
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Analisa oportunidades
        opportunity = self._identify_opportunity(round_state)
        
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        should_bluff = self._should_bluff_with_opportunity(opportunity)
        
        if should_bluff:
            return self._bluff_action(valid_actions, round_state, opportunity)
        else:
            return self._normal_action(valid_actions, hand_strength, round_state, opportunity)
    
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
    
    def _evaluate_hand_strength(self, hole_card, round_state):
        """Avalia força da mão."""
        if not hole_card or len(hole_card) < 2:
            return 0
        
        card_ranks = [card[1] for card in hole_card]
        card_suits = [card[0] for card in hole_card]
        community_cards = round_state.get('community_card', [])
        
        # Par nas mãos
        if card_ranks[0] == card_ranks[1]:
            rank_value = self._get_rank_value(card_ranks[0])
            return 50 + rank_value
        
        # Cartas altas
        high_cards = ['A', 'K', 'Q', 'J']
        has_high = any(rank in high_cards for rank in card_ranks)
        
        if has_high:
            if all(rank in high_cards for rank in card_ranks):
                return 45
            return 30
        
        # Mesmo naipe
        if card_suits[0] == card_suits[1]:
            return 20
        
        return 10
    
    def _get_rank_value(self, rank):
        """Retorna valor numérico do rank."""
        rank_map = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }
        return rank_map.get(rank, 0)
    
    def receive_game_start_message(self, game_info):
        """Inicializa stack."""
        seats = game_info.get('seats', [])
        if isinstance(seats, list):
            for player in seats:
                if player.get('uuid') == self.uuid:
                    self.initial_stack = player.get('stack', 100)
                    break
    
    def receive_round_start_message(self, round_count, hole_card, seats):
        """Salva memória periodicamente."""
        if round_count % 5 == 0:
            self.save_memory()
    
    def receive_street_start_message(self, street, round_state):
        pass
    
    def receive_game_update_message(self, action, round_state):
        pass
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprende padrões de oportunidades."""
        self.total_rounds += 1
        
        # Atualiza stack
        for seat in round_state['seats']:
            if seat['uuid'] == self.uuid:
                if self.initial_stack is None:
                    self.initial_stack = seat['stack']
                self.current_stack = seat['stack']
                break
        
        # Verifica se ganhou
        won = any(w['uuid'] == self.uuid for w in winners)
        if won:
            self.wins += 1
        
        # Registra resultado
        self.round_results.append({
            'won': won,
            'round': self.total_rounds,
            'stack': self.current_stack if self.current_stack else 100
        })
        if len(self.round_results) > 25:
            self.round_results = self.round_results[-25:]
        
        # Aprende quando oportunidades funcionam
        if len(self.round_results) >= 10:
            win_rate = sum(1 for r in self.round_results if r['won']) / len(self.round_results)
            
            # Se está ganhando, aumenta agressão e blefe
            if win_rate > 0.5:
                self.aggression_level = min(0.85, self.aggression_level + 0.08)
                self.bluff_probability = min(0.40, self.bluff_probability * 1.1)
            # Se está perdendo, reduz
            elif win_rate < 0.3:
                self.aggression_level = max(0.45, self.aggression_level - 0.10)
                self.bluff_probability = max(0.15, self.bluff_probability * 0.9)
        
        # Salva memória após ajustes
        self.save_memory()
    
    def save_memory(self):
        """Salva memória aprendida em arquivo."""
        memory = {
            'bluff_probability': self.bluff_probability,
            'aggression_level': self.aggression_level,
            'total_rounds': self.total_rounds,
            'wins': self.wins
        }
        
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            pass  # Silencioso
    
    def load_memory(self):
        """Carrega memória aprendida de arquivo."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    memory = json.load(f)
                
                self.bluff_probability = memory.get('bluff_probability', 0.25)
                self.aggression_level = memory.get('aggression_level', 0.65)
                self.total_rounds = memory.get('total_rounds', 0)
                self.wins = memory.get('wins', 0)
            except Exception as e:
                pass  # Silencioso

