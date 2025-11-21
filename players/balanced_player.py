from pypokerengine.players import BasePokerPlayer
import random
import json
import os
from .memory_utils import get_memory_path

class BalancedPlayer(BasePokerPlayer):
    """Combina Tight (seletividade) + Aggressive (agressão moderada). Aprendizado intermediário com memória persistente."""
    
    def __init__(self, memory_file="balanced_player_memory.json"):
        self.memory_file = get_memory_path(memory_file)
        self.bluff_probability = 0.15  # 15% de chance de blefar (moderado)
        
        # Combina características: seletivo como Tight, mas agressivo quando joga
        self.tightness_threshold = 30  # Mais seletivo que Aggressive, menos que Tight
        self.aggression_level = 0.60   # Mais agressivo que Tight, menos que Aggressive
        
        # Sistema de aprendizado intermediário
        self.round_results = []
        self.total_rounds = 0
        self.wins = 0
        self.initial_stack = None
        self.current_stack = None
        
        # Carrega memória anterior se existir
        self.load_memory()
    
    def declare_action(self, valid_actions, hole_card, round_state):
        hand_strength = self._evaluate_hand_strength(hole_card)
        should_bluff = self._should_bluff()
        
        if should_bluff:
            return self._bluff_action(valid_actions, round_state)
        else:
            return self._normal_action(valid_actions, hand_strength, round_state)
    
    def _should_bluff(self):
        """Decide se deve blefar baseado na probabilidade ajustada."""
        return random.random() < self.bluff_probability
    
    def _bluff_action(self, valid_actions, round_state):
        """Blefe moderado."""
        if valid_actions[2]['amount']['min'] != -1 and random.random() < 0.5:
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, min(max_amount, min_amount + 15))
            return raise_action['action'], amount
        else:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _normal_action(self, valid_actions, hand_strength, round_state):
        """Ação balanceada: seletivo mas agressivo quando joga."""
        # Mão muito forte: raise agressivo
        if hand_strength >= 50:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, min(max_amount, min_amount + int(20 * self.aggression_level)))
                return raise_action['action'], amount
        
        # Mão forte: call ou raise moderado (baseado em threshold)
        if hand_strength >= self.tightness_threshold:
            if self.aggression_level > 0.6 and valid_actions[2]['amount']['min'] != -1:
                return valid_actions[2]['action'], valid_actions[2]['amount']['min']
            else:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # Mão fraca: fold
        fold_action = valid_actions[0]
        return fold_action['action'], fold_action['amount']
    
    def _evaluate_hand_strength(self, hole_card):
        """Avalia força da mão."""
        if not hole_card or len(hole_card) < 2:
            return 0
        
        card_ranks = [card[1] for card in hole_card]
        card_suits = [card[0] for card in hole_card]
        
        # Par
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
        """Aprendizado intermediário: ajusta baseado em win rate."""
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
        self.round_results.append({'won': won, 'round': self.total_rounds})
        if len(self.round_results) > 15:
            self.round_results = self.round_results[-15:]
        
        # Aprendizado intermediário: ajusta baseado em win rate
        if len(self.round_results) >= 5:
            win_rate = sum(1 for r in self.round_results if r['won']) / len(self.round_results)
            
            # Se está ganhando, pode ser mais agressivo
            if win_rate > 0.5:
                self.aggression_level = min(0.75, self.aggression_level + 0.05)
                self.bluff_probability = min(0.25, self.bluff_probability * 1.05)
            # Se está perdendo, precisa ser mais conservador
            elif win_rate < 0.3:
                self.tightness_threshold = min(40, self.tightness_threshold + 3)
                self.aggression_level = max(0.45, self.aggression_level - 0.05)
                self.bluff_probability = max(0.08, self.bluff_probability * 0.95)
        
        # Salva memória após ajustes
        self.save_memory()
    
    def save_memory(self):
        """Salva memória aprendida em arquivo."""
        memory = {
            'bluff_probability': self.bluff_probability,
            'tightness_threshold': self.tightness_threshold,
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
                
                self.bluff_probability = memory.get('bluff_probability', 0.15)
                self.tightness_threshold = memory.get('tightness_threshold', 30)
                self.aggression_level = memory.get('aggression_level', 0.60)
                self.total_rounds = memory.get('total_rounds', 0)
                self.wins = memory.get('wins', 0)
            except Exception as e:
                pass  # Silencioso

