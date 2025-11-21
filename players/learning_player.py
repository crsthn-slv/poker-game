from pypokerengine.players import BasePokerPlayer
import random
import json
import os
from .memory_utils import get_memory_path

class LearningPlayer(BasePokerPlayer):
    """IA que aprende e se adapta baseado no histórico de jogos."""
    
    def __init__(self, learning_rate=0.1, memory_file="learning_player_memory.json"):
        # Parâmetros de aprendizado
        self.learning_rate = learning_rate
        self.memory_file = get_memory_path(memory_file)
        
        # Histórico de ações dos oponentes
        self.opponent_history = {}  # {uuid: {'actions': [], 'patterns': {}}}
        
        # Resultados das rodadas
        self.round_results = []  # Lista de resultados das rodadas
        
        # Estratégia adaptativa
        self.bluff_probability = 0.20  # Probabilidade inicial de blefe
        self.aggression_level = 0.50   # Nível de agressão (0-1)
        self.tightness = 0.50          # Seletividade (0-1)
        
        # Estatísticas
        self.total_rounds = 0
        self.wins = 0
        self.total_profit = 0
        self.initial_stack = None
        
        # Carrega memória anterior se existir
        self.load_memory()
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Analisa oponentes antes de decidir
        self._analyze_opponents(round_state)
        
        # Avalia força da mão
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        
        # Decide se deve blefar baseado no aprendizado
        should_bluff = self._should_bluff_with_learning(round_state)
        
        if should_bluff:
            return self._bluff_action(valid_actions, round_state)
        else:
            return self._normal_action_with_learning(valid_actions, hand_strength, round_state)
    
    def _should_bluff_with_learning(self, round_state):
        """Decide se deve blefar considerando o aprendizado."""
        base_probability = self.bluff_probability
        
        # Ajusta baseado nos oponentes
        active_opponents = [s for s in round_state['seats'] 
                           if s['uuid'] != self.uuid and s['state'] == 'participating']
        
        # Se oponentes são muito agressivos, blefa menos
        avg_opponent_aggression = self._get_avg_opponent_aggression(active_opponents)
        if avg_opponent_aggression > 0.7:
            base_probability *= 0.7  # Reduz blefe
        
        # Se está perdendo muito, blefa menos
        if self.total_rounds > 5:
            win_rate = self.wins / self.total_rounds if self.total_rounds > 0 else 0
            if win_rate < 0.2:
                base_probability *= 0.5  # Reduz blefe se está perdendo muito
        
        return random.random() < base_probability
    
    def _get_avg_opponent_aggression(self, active_opponents):
        """Calcula agressão média dos oponentes."""
        if not active_opponents:
            return 0.5
        
        aggressions = []
        for opp in active_opponents:
            opp_uuid = opp['uuid']
            if opp_uuid in self.opponent_history:
                patterns = self.opponent_history[opp_uuid].get('patterns', {})
                aggression = patterns.get('aggression', 0.5)
                aggressions.append(aggression)
        
        return sum(aggressions) / len(aggressions) if aggressions else 0.5
    
    def _normal_action_with_learning(self, valid_actions, hand_strength, round_state):
        """Ação normal considerando aprendizado."""
        # Ajusta threshold baseado no aprendizado
        # Se está ganhando, pode ser mais seletivo
        # Se está perdendo, precisa ser mais agressivo
        
        if self.total_rounds > 5:
            win_rate = self.wins / self.total_rounds if self.total_rounds > 0 else 0
            if win_rate > 0.5:
                # Está ganhando: pode ser mais conservador
                threshold_multiplier = 1.2
            else:
                # Está perdendo: precisa ser mais agressivo
                threshold_multiplier = 0.8
        else:
            threshold_multiplier = 1.0
        
        adjusted_strength = hand_strength * threshold_multiplier
        
        # Mão muito forte: raise
        if adjusted_strength >= 60:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                return raise_action['action'], raise_action['amount']['min']
        
        # Mão forte: call ou raise moderado
        if adjusted_strength >= 40:
            if self.aggression_level > 0.6 and valid_actions[2]['amount']['min'] != -1:
                return valid_actions[2]['action'], valid_actions[2]['amount']['min']
            else:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # Mão média: depende do aprendizado
        if adjusted_strength >= 25:
            # Se oponentes são conservadores, pode blefar mais
            avg_aggression = self._get_avg_opponent_aggression(
                [s for s in round_state['seats'] if s['uuid'] != self.uuid and s['state'] == 'participating']
            )
            if avg_aggression < 0.4:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
            else:
                fold_action = valid_actions[0]
                return fold_action['action'], fold_action['amount']
        
        # Mão fraca: fold
        fold_action = valid_actions[0]
        return fold_action['action'], fold_action['amount']
    
    def _bluff_action(self, valid_actions, round_state):
        """Executa blefe considerando aprendizado."""
        context = self._analyze_table_context(round_state)
        
        # Ajusta blefe baseado no aprendizado
        if self.total_rounds > 5:
            recent_results = self.round_results[-5:] if len(self.round_results) >= 5 else self.round_results
            recent_wins = sum(1 for r in recent_results if r.get('won', False))
            
            # Se blefes recentes funcionaram, continua
            if recent_wins > 2:
                bluff_aggressive = True
            else:
                bluff_aggressive = False
        else:
            bluff_aggressive = random.random() < 0.5
        
        if bluff_aggressive and valid_actions[2]['amount']['min'] != -1:
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, min(max_amount, min_amount + 20))
            return raise_action['action'], amount
        else:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _analyze_opponents(self, round_state):
        """Analisa padrões dos oponentes."""
        for seat in round_state['seats']:
            if seat['uuid'] != self.uuid:
                opp_uuid = seat['uuid']
                if opp_uuid not in self.opponent_history:
                    self.opponent_history[opp_uuid] = {
                        'actions': [],
                        'patterns': {
                            'aggression': 0.5,
                            'tightness': 0.5,
                            'bluff_frequency': 0.2,
                            'fold_frequency': 0.3
                        }
                    }
    
    def receive_game_update_message(self, action, round_state):
        """Registra ações dos oponentes para aprendizado."""
        # A estrutura pode variar, tenta diferentes formatos
        player_uuid = action.get('uuid') or action.get('player_uuid')
        if not player_uuid:
            # Se não encontrar uuid na ação, tenta no round_state
            # ou simplesmente ignora se não conseguir identificar
            return
        
        if player_uuid != self.uuid:
            if player_uuid not in self.opponent_history:
                self.opponent_history[player_uuid] = {
                    'actions': [],
                    'patterns': {
                        'aggression': 0.5,
                        'tightness': 0.5,
                        'bluff_frequency': 0.2,
                        'fold_frequency': 0.3
                    }
                }
            
            # Registra ação
            self.opponent_history[player_uuid]['actions'].append({
                'action': action['action'],
                'amount': action.get('amount', 0),
                'street': round_state.get('street', 'preflop')
            })
            
            # Mantém apenas últimas 50 ações
            if len(self.opponent_history[player_uuid]['actions']) > 50:
                self.opponent_history[player_uuid]['actions'] = \
                    self.opponent_history[player_uuid]['actions'][-50:]
            
            # Atualiza padrões periodicamente
            if len(self.opponent_history[player_uuid]['actions']) > 10:
                self._update_opponent_patterns(player_uuid)
    
    def _update_opponent_patterns(self, opp_uuid):
        """Atualiza padrões de um oponente baseado no histórico."""
        actions = self.opponent_history[opp_uuid]['actions']
        
        if not actions:
            return
        
        # Calcula frequências
        total_actions = len(actions)
        raise_count = sum(1 for a in actions if a['action'] == 'raise')
        fold_count = sum(1 for a in actions if a['action'] == 'fold')
        
        # Atualiza padrões com learning rate
        old_aggression = self.opponent_history[opp_uuid]['patterns']['aggression']
        new_aggression = raise_count / total_actions if total_actions > 0 else 0.5
        self.opponent_history[opp_uuid]['patterns']['aggression'] = \
            old_aggression * (1 - self.learning_rate) + new_aggression * self.learning_rate
        
        old_fold_freq = self.opponent_history[opp_uuid]['patterns']['fold_frequency']
        new_fold_freq = fold_count / total_actions if total_actions > 0 else 0.3
        self.opponent_history[opp_uuid]['patterns']['fold_frequency'] = \
            old_fold_freq * (1 - self.learning_rate) + new_fold_freq * self.learning_rate
        
        # Tightness: quanto mais fold, mais tight
        old_tightness = self.opponent_history[opp_uuid]['patterns']['tightness']
        new_tightness = fold_count / total_actions if total_actions > 0 else 0.5
        self.opponent_history[opp_uuid]['patterns']['tightness'] = \
            old_tightness * (1 - self.learning_rate) + new_tightness * self.learning_rate
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprende com o resultado da rodada."""
        self.total_rounds += 1
        
        # Verifica se ganhou
        won = any(w['uuid'] == self.uuid for w in winners)
        if won:
            self.wins += 1
        
        # Calcula lucro/prejuízo
        my_seat = next((s for s in round_state['seats'] if s['uuid'] == self.uuid), None)
        if my_seat:
            current_stack = my_seat['stack']
            if self.initial_stack is None:
                self.initial_stack = current_stack
            
            stack_change = current_stack - self.initial_stack
            if not self.round_results:
                self.total_profit = stack_change
            else:
                self.total_profit = stack_change
        
        # Registra resultado
        self.round_results.append({
            'won': won,
            'round': self.total_rounds,
            'stack': my_seat['stack'] if my_seat else 0
        })
        
        # Mantém apenas últimas 20 rodadas
        if len(self.round_results) > 20:
            self.round_results = self.round_results[-20:]
        
        # Ajusta estratégia baseado nos resultados
        if self.total_rounds > 5:
            self._adapt_strategy()
    
    def _adapt_strategy(self):
        """Adapta estratégia baseado no aprendizado."""
        if len(self.round_results) < 5:
            return
        
        # Analisa performance recente
        recent_results = self.round_results[-10:] if len(self.round_results) >= 10 else self.round_results
        recent_wins = sum(1 for r in recent_results if r.get('won', False))
        win_rate = recent_wins / len(recent_results) if recent_results else 0
        
        # Ajusta probabilidade de blefe
        if win_rate > 0.6:
            # Está ganhando: pode blefar mais
            self.bluff_probability = min(0.35, self.bluff_probability * 1.1)
        elif win_rate < 0.3:
            # Está perdendo: blefa menos
            self.bluff_probability = max(0.05, self.bluff_probability * 0.9)
        
        # Ajusta agressão
        if win_rate > 0.5:
            # Está ganhando: mantém ou aumenta agressão
            self.aggression_level = min(0.8, self.aggression_level + 0.05)
        else:
            # Está perdendo: pode precisar ser mais conservador
            self.aggression_level = max(0.2, self.aggression_level - 0.05)
        
        # Ajusta tightness
        if win_rate < 0.3:
            # Está perdendo: precisa ser mais seletivo
            self.tightness = min(0.8, self.tightness + 0.1)
        else:
            # Está ganhando: pode jogar mais mãos
            self.tightness = max(0.2, self.tightness - 0.05)
    
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
    
    def _analyze_table_context(self, round_state):
        """Analisa contexto da mesa."""
        pot_size = round_state['pot']['main']['amount']
        active_players = len([s for s in round_state['seats'] if s['state'] == 'participating'])
        street = round_state['street']
        
        return {
            'pot_size': pot_size,
            'active_players': active_players,
            'street': street
        }
    
    def save_memory(self):
        """Salva memória aprendida em arquivo."""
        memory = {
            'opponent_history': self.opponent_history,
            'bluff_probability': self.bluff_probability,
            'aggression_level': self.aggression_level,
            'tightness': self.tightness,
            'total_rounds': self.total_rounds,
            'wins': self.wins,
            'total_profit': self.total_profit
        }
        
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar memória: {e}")
    
    def load_memory(self):
        """Carrega memória aprendida de arquivo."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    memory = json.load(f)
                
                self.opponent_history = memory.get('opponent_history', {})
                self.bluff_probability = memory.get('bluff_probability', 0.20)
                self.aggression_level = memory.get('aggression_level', 0.50)
                self.tightness = memory.get('tightness', 0.50)
                self.total_rounds = memory.get('total_rounds', 0)
                self.wins = memory.get('wins', 0)
                self.total_profit = memory.get('total_profit', 0)
            except Exception as e:
                print(f"Erro ao carregar memória: {e}")
    
    def receive_game_start_message(self, game_info):
        """Inicializa stack inicial."""
        # Encontra nosso stack inicial
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

