from pypokerengine.players import BasePokerPlayer
import random
import json
import os
from .memory_utils import get_memory_path

class SmartPlayer(BasePokerPlayer):
    """Jogador inteligente que ajusta estratégia dinamicamente. Blefe base 15%, ajusta conforme performance. Com memória persistente."""
    
    def __init__(self, memory_file="smart_player_memory.json"):
        self.memory_file = get_memory_path(memory_file)
        self.base_bluff_probability = 0.15  # 15% base
        self.current_bluff_probability = 0.15
        self.initial_stack = None
        self.current_stack = None
        self.wins = 0
        self.rounds_played = 0
        
        # Sistema de aprendizado avançado
        self.round_results = []  # Histórico detalhado (50 rodadas)
        self.street_performance = {
            'preflop': {'wins': 0, 'total': 0},
            'flop': {'wins': 0, 'total': 0},
            'turn': {'wins': 0, 'total': 0},
            'river': {'wins': 0, 'total': 0}
        }
        self.bluff_success_rate = {'successful': 0, 'total': 0}
        self.pot_size_strategy = {}  # Estratégia por tamanho de pot
        self.current_street = 'preflop'
        self.last_bluff_round = None
        
        # Carrega memória anterior se existir
        self.load_memory()
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Atualiza stack atual
        self._update_stack(round_state)
        
        # Ajusta probabilidade de blefe baseado na performance
        self._adjust_bluff_probability()
        
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        should_bluff = self._should_bluff()
        
        if should_bluff:
            return self._bluff_action(valid_actions, round_state)
        else:
            return self._normal_action(valid_actions, hand_strength, round_state)
    
    def _should_bluff(self):
        """Decide se deve blefar baseado na probabilidade ajustada dinamicamente."""
        result = random.random() < self.current_bluff_probability
        if result:
            self.last_bluff_round = self.rounds_played
        return result
    
    def _adjust_bluff_probability(self):
        """Ajusta probabilidade de blefe baseado na performance."""
        if self.initial_stack is None or self.current_stack is None:
            return
        
        # Calcula performance (stack atual vs inicial)
        if self.initial_stack > 0:
            performance_ratio = self.current_stack / self.initial_stack
            
            # Se está ganhando (stack > inicial), blefa mais
            if performance_ratio > 1.2:
                self.current_bluff_probability = self.base_bluff_probability * 1.5  # Aumenta 50%
            elif performance_ratio > 1.0:
                self.current_bluff_probability = self.base_bluff_probability * 1.2  # Aumenta 20%
            # Se está perdendo (stack < inicial), blefa menos
            elif performance_ratio < 0.8:
                self.current_bluff_probability = self.base_bluff_probability * 0.5  # Reduz 50%
            elif performance_ratio < 1.0:
                self.current_bluff_probability = self.base_bluff_probability * 0.8  # Reduz 20%
            else:
                self.current_bluff_probability = self.base_bluff_probability
    
    def _update_stack(self, round_state):
        """Atualiza informações do stack."""
        for seat in round_state['seats']:
            if seat['uuid'] == self.uuid:
                if self.initial_stack is None:
                    self.initial_stack = seat['stack']
                self.current_stack = seat['stack']
                break
    
    def _bluff_action(self, valid_actions, round_state):
        """Executa blefe inteligente baseado no contexto."""
        context = self._analyze_table_context(round_state)
        
        # Análise sofisticada: pot grande = CALL, pot pequeno = RAISE
        if context['pot_size'] > 100:
            # Pot grande: 60% CALL (blefe mais conservador)
            bluff_choice = random.random() < 0.40  # 40% RAISE
        else:
            # Pot pequeno: 70% RAISE (blefe mais agressivo)
            bluff_choice = random.random() < 0.70
        
        # Considera número de jogadores
        if context['active_players'] <= 2:
            # Poucos jogadores: mais agressivo
            bluff_choice = bluff_choice or random.random() < 0.20
        
        if bluff_choice and valid_actions[2]['amount']['min'] != -1:
            # Faz RAISE
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            # Raise moderado
            amount = random.randint(min_amount, min(max_amount, min_amount + 25))
            return raise_action['action'], amount
        else:
            # Faz CALL
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _analyze_table_context(self, round_state):
        """Análise sofisticada do contexto da mesa."""
        pot_size = round_state['pot']['main']['amount']
        active_players = len([s for s in round_state['seats'] if s['state'] == 'participating'])
        street = round_state['street']
        
        # Calcula stack médio dos outros jogadores
        other_stacks = [s['stack'] for s in round_state['seats'] if s['uuid'] != self.uuid and s['state'] == 'participating']
        avg_stack = sum(other_stacks) / len(other_stacks) if other_stacks else 100
        
        return {
            'pot_size': pot_size,
            'active_players': active_players,
            'street': street,
            'avg_stack': avg_stack
        }
    
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
            base_strength = 50 + rank_value
            
            # Verifica se forma trinca ou melhor com comunitárias
            if community_cards:
                all_ranks = card_ranks + [c[1] for c in community_cards]
                rank_counts = {}
                for rank in all_ranks:
                    rank_counts[rank] = rank_counts.get(rank, 0) + 1
                
                # Trinca
                if max(rank_counts.values()) >= 3:
                    return 80
                # Dois pares
                pairs = [count for count in rank_counts.values() if count >= 2]
                if len(pairs) >= 2:
                    return 70
            
            return base_strength
        
        # Cartas altas
        high_cards = ['A', 'K', 'Q', 'J']
        has_high = any(rank in high_cards for rank in card_ranks)
        
        if has_high:
            # Duas cartas altas
            if all(rank in high_cards for rank in card_ranks):
                return 45
            # Uma carta alta
            return 30
        
        # Mesmo naipe (possibilidade de flush)
        if card_suits[0] == card_suits[1]:
            if community_cards:
                same_suit_community = [c for c in community_cards if c[0] == card_suits[0]]
                if len(same_suit_community) >= 3:
                    return 60  # Flush possível
            return 20
        
        # Cartas baixas
        return 10
    
    def _get_rank_value(self, rank):
        """Retorna valor numérico do rank."""
        rank_map = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }
        return rank_map.get(rank, 0)
    
    def _normal_action(self, valid_actions, hand_strength, round_state):
        """Ação normal baseada na força da mão e contexto."""
        context = self._analyze_table_context(round_state)
        
        # Mão muito forte: raise agressivo
        if hand_strength >= 70:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                amount = random.randint(min_amount, min(max_amount, min_amount + 30))
                return raise_action['action'], amount
        
        # Mão forte: raise moderado ou call
        if hand_strength >= 50:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1 and context['pot_size'] < 80:
                return raise_action['action'], raise_action['amount']['min']
            else:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # Mão média: call se pot pequeno, fold se pot grande
        if hand_strength >= 25:
            if context['pot_size'] < 50:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
            else:
                fold_action = valid_actions[0]
                return fold_action['action'], fold_action['amount']
        
        # Mão fraca: fold
        fold_action = valid_actions[0]
        return fold_action['action'], fold_action['amount']
    
    def receive_game_start_message(self, game_info):
        # Inicializa stack inicial
        # game_info['seats'] é uma lista de players
        seats = game_info.get('seats', [])
        if isinstance(seats, list):
            for player in seats:
                if player.get('uuid') == self.uuid:
                    self.initial_stack = player.get('stack', 100)
                    self.current_stack = player.get('stack', 100)
                    break
        elif isinstance(seats, dict) and 'players' in seats:
            for player in seats['players']:
                if player.get('uuid') == self.uuid:
                    self.initial_stack = player.get('stack', 100)
                    self.current_stack = player.get('stack', 100)
                    break
    
    def receive_round_start_message(self, round_count, hole_card, seats):
        """Salva memória periodicamente e armazena cartas no registry."""
        if round_count % 5 == 0:
            self.save_memory()
        # Armazena cartas no registry global para exibição no final do round
        if hole_card and hasattr(self, 'uuid') and self.uuid:
            from .cards_registry import store_player_cards
            from .hand_utils import normalize_hole_cards
            hole_cards = normalize_hole_cards(hole_card)
            if hole_cards:
                store_player_cards(self.uuid, hole_cards)
    
    def receive_street_start_message(self, street, round_state):
        """Registra mudança de street para aprendizado."""
        self.current_street = street
    
    def receive_game_update_message(self, action, round_state):
        pass
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprendizado avançado: análise multi-dimensional."""
        self.rounds_played += 1
        
        # Verifica se ganhou
        won = any(w['uuid'] == self.uuid for w in winners)
        if won:
            self.wins += 1
        
        # Atualiza performance por street
        self.street_performance[self.current_street]['total'] += 1
        if won:
            self.street_performance[self.current_street]['wins'] += 1
        
        # Analisa sucesso de blefes
        if self.last_bluff_round == self.rounds_played - 1:
            self.bluff_success_rate['total'] += 1
            if won:
                self.bluff_success_rate['successful'] += 1
        
        # Registra resultado detalhado (mantém 50 rodadas)
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        self.round_results.append({
            'won': won,
            'round': self.rounds_played,
            'street': self.current_street,
            'pot_size': pot_size,
            'stack': self.current_stack if self.current_stack else 100
        })
        if len(self.round_results) > 50:
            self.round_results = self.round_results[-50:]
        
        # Aprendizado avançado: ajusta estratégia baseado em múltiplos fatores
        if len(self.round_results) >= 10:
            self._advanced_learning()
    
    def _advanced_learning(self):
        """Aprendizado avançado multi-dimensional."""
        # 1. Ajusta blefe baseado em sucesso
        if self.bluff_success_rate['total'] > 5:
            success_rate = self.bluff_success_rate['successful'] / self.bluff_success_rate['total']
            if success_rate > 0.6:
                # Blefes funcionando: aumenta probabilidade
                self.base_bluff_probability = min(0.25, self.base_bluff_probability * 1.1)
            elif success_rate < 0.3:
                # Blefes não funcionando: reduz
                self.base_bluff_probability = max(0.05, self.base_bluff_probability * 0.9)
        
        # 2. Ajusta estratégia por street
        for street, perf in self.street_performance.items():
            if perf['total'] > 5:
                win_rate = perf['wins'] / perf['total']
                # Se está perdendo muito em uma street específica, ajusta
                if win_rate < 0.2:
                    # Reduz agressão nessa street
                    pass  # Pode ser implementado ajuste específico
        
        # 3. Ajusta baseado em pot size
        recent_results = self.round_results[-20:] if len(self.round_results) >= 20 else self.round_results
        for result in recent_results:
            pot_size = result['pot_size']
            pot_category = 'small' if pot_size < 50 else 'medium' if pot_size < 150 else 'large'
            
            if pot_category not in self.pot_size_strategy:
                self.pot_size_strategy[pot_category] = {'wins': 0, 'total': 0}
            
            self.pot_size_strategy[pot_category]['total'] += 1
            if result['won']:
                self.pot_size_strategy[pot_category]['wins'] += 1
        
        # Salva memória após aprendizado
        self.save_memory()
    
    def save_memory(self):
        """Salva memória aprendida em arquivo."""
        memory = {
            'base_bluff_probability': self.base_bluff_probability,
            'current_bluff_probability': self.current_bluff_probability,
            'rounds_played': self.rounds_played,
            'wins': self.wins,
            'street_performance': self.street_performance,
            'bluff_success_rate': self.bluff_success_rate,
            'pot_size_strategy': self.pot_size_strategy
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
                
                self.base_bluff_probability = memory.get('base_bluff_probability', 0.15)
                self.current_bluff_probability = memory.get('current_bluff_probability', 0.15)
                self.rounds_played = memory.get('rounds_played', 0)
                self.wins = memory.get('wins', 0)
                self.street_performance = memory.get('street_performance', {
                    'preflop': {'wins': 0, 'total': 0},
                    'flop': {'wins': 0, 'total': 0},
                    'turn': {'wins': 0, 'total': 0},
                    'river': {'wins': 0, 'total': 0}
                })
                self.bluff_success_rate = memory.get('bluff_success_rate', {'successful': 0, 'total': 0})
                self.pot_size_strategy = memory.get('pot_size_strategy', {})
            except Exception as e:
                pass  # Silencioso

