from pypokerengine.players import BasePokerPlayer
import random
import json
import os
from .memory_utils import get_memory_path

class AdaptivePlayer(BasePokerPlayer):
    """Combina Smart (análise) + Random (exploração). Aprendizado avançado com exploração vs exploração. Com memória persistente."""
    
    def __init__(self, memory_file="adaptive_player_memory.json"):
        self.memory_file = get_memory_path(memory_file)
        self.bluff_probability = 0.20  # 20% inicial
        
        # Sistema de exploração vs exploração
        self.epsilon = 0.15  # 15% de exploração (escolhe aleatoriamente)
        self.exploration_decay = 0.99  # Reduz exploração com o tempo
        
        # Análise sofisticada como Smart
        self.round_results = []
        self.street_performance = {
            'preflop': {'wins': 0, 'total': 0},
            'flop': {'wins': 0, 'total': 0},
            'turn': {'wins': 0, 'total': 0},
            'river': {'wins': 0, 'total': 0}
        }
        self.strategy_success = {}  # Rastreia sucesso de estratégias
        
        self.total_rounds = 0
        self.wins = 0
        self.initial_stack = None
        self.current_stack = None
        self.current_street = 'preflop'
        
        # Carrega memória anterior se existir
        self.load_memory()
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Exploração: escolhe aleatoriamente
        if random.random() < self.epsilon:
            return self._explore_action(valid_actions)
        
        # Exploração: usa análise
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        should_bluff = self._should_bluff_with_analysis(round_state)
        
        if should_bluff:
            return self._bluff_action(valid_actions, round_state)
        else:
            return self._normal_action(valid_actions, hand_strength, round_state)
    
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
        # Analisa performance na street atual
        street_perf = self.street_performance.get(self.current_street, {'wins': 0, 'total': 0})
        if street_perf['total'] > 5:
            street_win_rate = street_perf['wins'] / street_perf['total']
            # Ajusta probabilidade baseado em performance na street
            adjusted_prob = self.bluff_probability * (1 + (street_win_rate - 0.5))
            return random.random() < adjusted_prob
        
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
        
        # Mão média: depende da análise
        if hand_strength >= 25:
            return valid_actions[1]['action'], valid_actions[1]['amount']
        
        # Mão fraca: fold
        return valid_actions[0]['action'], valid_actions[0]['amount']
    
    def _evaluate_hand_strength(self, hole_card, round_state):
        """Avalia força da mão considerando cartas comunitárias."""
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
        """Registra mudança de street."""
        self.current_street = street
    
    def receive_game_update_message(self, action, round_state):
        pass
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprendizado avançado com exploração vs exploração."""
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
        
        # Atualiza performance por street
        self.street_performance[self.current_street]['total'] += 1
        if won:
            self.street_performance[self.current_street]['wins'] += 1
        
        # Registra resultado
        self.round_results.append({
            'won': won,
            'round': self.total_rounds,
            'street': self.current_street
        })
        if len(self.round_results) > 30:
            self.round_results = self.round_results[-30:]
        
        # Reduz exploração com o tempo
        self.epsilon = max(0.05, self.epsilon * self.exploration_decay)
        
        # Ajusta estratégia baseado em resultados
        if len(self.round_results) >= 10:
            win_rate = sum(1 for r in self.round_results if r['won']) / len(self.round_results)
            
            if win_rate > 0.6:
                self.bluff_probability = min(0.30, self.bluff_probability * 1.05)
            elif win_rate < 0.3:
                self.bluff_probability = max(0.10, self.bluff_probability * 0.95)
        
        # Salva memória após ajustes
        self.save_memory()
    
    def save_memory(self):
        """Salva memória aprendida em arquivo."""
        memory = {
            'bluff_probability': self.bluff_probability,
            'epsilon': self.epsilon,
            'street_performance': self.street_performance,
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
                
                self.bluff_probability = memory.get('bluff_probability', 0.20)
                self.epsilon = memory.get('epsilon', 0.15)
                self.street_performance = memory.get('street_performance', {
                    'preflop': {'wins': 0, 'total': 0},
                    'flop': {'wins': 0, 'total': 0},
                    'turn': {'wins': 0, 'total': 0},
                    'river': {'wins': 0, 'total': 0}
                })
                self.total_rounds = memory.get('total_rounds', 0)
                self.wins = memory.get('wins', 0)
            except Exception as e:
                pass  # Silencioso

