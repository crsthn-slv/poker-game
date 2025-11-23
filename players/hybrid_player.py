from pypokerengine.players import BasePokerPlayer
import random
import json
import os
from utils.memory_utils import get_memory_path
from utils.action_analyzer import analyze_current_round_actions

class HybridPlayer(BasePokerPlayer):
    """Combina todas as abordagens. Alterna entre estratégias baseado em contexto. Mais versátil e adaptável. Com memória persistente."""
    
    def __init__(self, memory_file="hybrid_player_memory.json"):
        self.memory_file = get_memory_path(memory_file)
        
        # Múltiplas estratégias
        self.strategies = {
            'tight': {'bluff_prob': 0.08, 'threshold': 30, 'aggression': 0.40},
            'aggressive': {'bluff_prob': 0.35, 'threshold': 20, 'aggression': 0.75},
            'balanced': {'bluff_prob': 0.15, 'threshold': 25, 'aggression': 0.60},
            'smart': {'bluff_prob': 0.20, 'threshold': 28, 'aggression': 0.55}
        }
        
        self.current_strategy = 'balanced'  # Estratégia inicial
        self.strategy_performance = {s: {'wins': 0, 'total': 0} for s in self.strategies.keys()}
        
        # Sistema de aprendizado avançado
        self.round_results = []
        self.total_rounds = 0
        self.wins = 0
        self.initial_stack = None
        self.current_stack = None
        self.context_history = []  # Histórico de contextos e estratégias usadas
        
        # Carrega memória anterior se existir
        self.load_memory()
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # NOVO: Analisa ações do round atual
        current_actions = analyze_current_round_actions(round_state, self.uuid) if hasattr(self, 'uuid') and self.uuid else None
        
        # Analisa contexto e escolhe melhor estratégia
        context = self._analyze_context(round_state)
        self._select_strategy(context)
        
        # Usa estratégia atual
        strategy = self.strategies[self.current_strategy]
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        
        should_bluff = random.random() < strategy['bluff_prob']
        
        # NOVO: Ajusta blefe baseado em ações atuais
        if current_actions and current_actions['has_raises'] and current_actions['raise_count'] >= 2:
            should_bluff = False  # Não blefa se muito agressão
        
        if should_bluff:
            return self._bluff_action(valid_actions, round_state, strategy)
        else:
            return self._normal_action(valid_actions, hand_strength, round_state, strategy, current_actions)
    
    def _analyze_context(self, round_state):
        """Analisa contexto da mesa."""
        pot_size = round_state['pot']['main']['amount']
        active_players = len([s for s in round_state['seats'] if s['state'] == 'participating'])
        street = round_state['street']
        
        # Calcula stack ratio
        my_seat = next((s for s in round_state['seats'] if s['uuid'] == self.uuid), None)
        stack_ratio = 1.0
        if my_seat and self.initial_stack:
            stack_ratio = my_seat['stack'] / self.initial_stack
        
        return {
            'pot_size': pot_size,
            'active_players': active_players,
            'street': street,
            'stack_ratio': stack_ratio
        }
    
    def _select_strategy(self, context):
        """Seleciona melhor estratégia baseado em contexto e aprendizado."""
        # Se tem dados suficientes, escolhe baseado em performance
        if self.total_rounds > 10:
            # Encontra estratégia com melhor win rate
            best_strategy = max(self.strategy_performance.items(), 
                              key=lambda x: x[1]['wins'] / x[1]['total'] if x[1]['total'] > 0 else 0)
            
            # Se uma estratégia está claramente melhor, usa ela
            if best_strategy[1]['total'] > 5:
                best_wr = best_strategy[1]['wins'] / best_strategy[1]['total']
                current_wr = self.strategy_performance[self.current_strategy]['wins'] / \
                            self.strategy_performance[self.current_strategy]['total'] \
                            if self.strategy_performance[self.current_strategy]['total'] > 0 else 0
                
                if best_wr > current_wr + 0.15:
                    self.current_strategy = best_strategy[0]
        
        # Ajusta estratégia baseado em contexto
        if context['active_players'] <= 2:
            # Poucos jogadores: mais agressivo
            if context['stack_ratio'] > 1.2:
                self.current_strategy = 'aggressive'
        elif context['pot_size'] > 100:
            # Pot grande: mais conservador
            self.current_strategy = 'tight'
        elif context['stack_ratio'] < 0.7:
            # Stack baixo: precisa ser mais seletivo
            self.current_strategy = 'tight'
    
    def _bluff_action(self, valid_actions, round_state, strategy):
        """Blefe baseado na estratégia atual."""
        if valid_actions[2]['amount']['min'] != -1:
            if strategy['aggression'] > 0.6:
                raise_action = valid_actions[2]
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, min(max_amount, min_amount + 20))
                return raise_action['action'], amount
        
        return valid_actions[1]['action'], valid_actions[1]['amount']
    
    def _normal_action(self, valid_actions, hand_strength, round_state, strategy, current_actions=None):
        """Ação baseada na estratégia atual e ações atuais."""
        threshold = strategy['threshold']
        aggression = strategy['aggression']
        
        # NOVO: Ajusta threshold baseado em ações do round atual
        if current_actions:
            if current_actions['has_raises']:
                threshold += 5 + (current_actions['raise_count'] * 2)
            elif current_actions['last_action'] == 'raise':
                threshold += 3
        
        # Mão muito forte: sempre raise
        if hand_strength >= 55:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, min(max_amount, min_amount + int(25 * aggression)))
                return raise_action['action'], amount
        
        # Mão forte: depende da estratégia
        if hand_strength >= threshold:
            if aggression > 0.65 and valid_actions[2]['amount']['min'] != -1:
                return valid_actions[2]['action'], valid_actions[2]['amount']['min']
            else:
                return valid_actions[1]['action'], valid_actions[1]['amount']
        
        # Mão fraca: fold apenas se for MUITO fraca
        if hand_strength < (threshold - 8):
            return valid_actions[0]['action'], valid_actions[0]['amount']
        
        # Mão média-fraca: call (não desiste tão fácil)
        return valid_actions[1]['action'], valid_actions[1]['amount']
    
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
        pass
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprende qual estratégia funciona melhor."""
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
        
        # Atualiza performance da estratégia atual
        self.strategy_performance[self.current_strategy]['total'] += 1
        if won:
            self.strategy_performance[self.current_strategy]['wins'] += 1
        
        # Registra resultado
        self.round_results.append({
            'won': won,
            'round': self.total_rounds,
            'strategy': self.current_strategy,
            'stack': self.current_stack if self.current_stack else 100
        })
        if len(self.round_results) > 40:
            self.round_results = self.round_results[-40:]
        
        # Ajusta estratégias baseado em aprendizado
        if self.total_rounds > 15:
            for strategy_name, perf in self.strategy_performance.items():
                if perf['total'] > 5:
                    win_rate = perf['wins'] / perf['total']
                    strategy = self.strategies[strategy_name]
                    
                    # Ajusta parâmetros da estratégia baseado em performance
                    if win_rate > 0.6:
                        strategy['bluff_prob'] = min(0.40, strategy['bluff_prob'] * 1.05)
                        strategy['aggression'] = min(0.85, strategy['aggression'] + 0.03)
                    elif win_rate < 0.3:
                        strategy['bluff_prob'] = max(0.05, strategy['bluff_prob'] * 0.95)
                        strategy['aggression'] = max(0.30, strategy['aggression'] - 0.03)
        
        # Salva memória após ajustes
        self.save_memory()
    
    def save_memory(self):
        """Salva memória aprendida em arquivo."""
        memory = {
            'strategies': self.strategies,
            'current_strategy': self.current_strategy,
            'strategy_performance': self.strategy_performance,
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
                
                self.strategies = memory.get('strategies', self.strategies)
                self.current_strategy = memory.get('current_strategy', 'balanced')
                self.strategy_performance = memory.get('strategy_performance', 
                    {s: {'wins': 0, 'total': 0} for s in self.strategies.keys()})
                self.total_rounds = memory.get('total_rounds', 0)
                self.wins = memory.get('wins', 0)
            except Exception as e:
                pass  # Silencioso

