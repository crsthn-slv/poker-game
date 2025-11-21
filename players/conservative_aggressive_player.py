from pypokerengine.players import BasePokerPlayer
import random
import json
import os
from .memory_utils import get_memory_path

class ConservativeAggressivePlayer(BasePokerPlayer):
    """Combina Tight (conservador) + Aggressive (agressão seletiva). Conservador no início, agressivo quando ganha. Com memória persistente."""
    
    def __init__(self, memory_file="conservative_aggressive_player_memory.json"):
        self.memory_file = get_memory_path(memory_file)
        self.bluff_probability = 0.05  # Começa muito conservador (5%)
        
        # Começa conservador, fica agressivo quando ganha
        self.tightness_threshold = 35  # Muito seletivo inicialmente
        self.aggression_level = 0.40   # Baixa agressão inicial
        self.conservative_mode = True   # Modo conservador ativo
        
        # Sistema de aprendizado
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
    
    def _normal_action(self, valid_actions, hand_strength, round_state):
        """Ação baseada no modo (conservador ou agressivo)."""
        # Mão muito forte: sempre raise
        if hand_strength >= 55:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, min(max_amount, min_amount + int(25 * self.aggression_level)))
                return raise_action['action'], amount
        
        # Mão forte: depende do modo
        if hand_strength >= self.tightness_threshold:
            if not self.conservative_mode and self.aggression_level > 0.6:
                # Modo agressivo: pode fazer raise
                if valid_actions[2]['amount']['min'] != -1:
                    return valid_actions[2]['action'], valid_actions[2]['amount']['min']
            
            # Sempre faz call se passou do threshold
            return valid_actions[1]['action'], valid_actions[1]['amount']
        
        # Mão fraca: fold
        return valid_actions[0]['action'], valid_actions[0]['amount']
    
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
        """Aprendizado: conservador no início, agressivo quando ganha."""
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
        if len(self.round_results) > 20:
            self.round_results = self.round_results[-20:]
        
        # Aprendizado: muda de conservador para agressivo quando ganha
        if len(self.round_results) >= 5:
            win_rate = sum(1 for r in self.round_results if r['won']) / len(self.round_results)
            
            # Se está ganhando bem, muda para modo agressivo
            if win_rate > 0.6:
                self.conservative_mode = False
                self.aggression_level = min(0.80, self.aggression_level + 0.10)
                self.bluff_probability = min(0.25, self.bluff_probability * 1.2)
                self.tightness_threshold = max(25, self.tightness_threshold - 5)
            # Se está perdendo, volta para modo conservador
            elif win_rate < 0.3:
                self.conservative_mode = True
                self.aggression_level = max(0.30, self.aggression_level - 0.10)
                self.bluff_probability = max(0.03, self.bluff_probability * 0.8)
                self.tightness_threshold = min(40, self.tightness_threshold + 5)
        
        # Salva memória após ajustes
        self.save_memory()
    
    def save_memory(self):
        """Salva memória aprendida em arquivo."""
        memory = {
            'bluff_probability': self.bluff_probability,
            'tightness_threshold': self.tightness_threshold,
            'aggression_level': self.aggression_level,
            'conservative_mode': self.conservative_mode,
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
                
                self.bluff_probability = memory.get('bluff_probability', 0.05)
                self.tightness_threshold = memory.get('tightness_threshold', 35)
                self.aggression_level = memory.get('aggression_level', 0.40)
                self.conservative_mode = memory.get('conservative_mode', True)
                self.total_rounds = memory.get('total_rounds', 0)
                self.wins = memory.get('wins', 0)
            except Exception as e:
                pass  # Silencioso

