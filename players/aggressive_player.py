from pypokerengine.players import BasePokerPlayer
import random
import json
import os
from .memory_utils import get_memory_path

class AggressivePlayer(BasePokerPlayer):
    """Jogador agressivo que joga muitas mãos e blefa frequentemente (35%). Aprendizado agressivo intermediário com memória persistente."""
    
    def __init__(self, memory_file="aggressive_player_memory.json"):
        self.memory_file = get_memory_path(memory_file)
        self.bluff_probability = 0.35  # 35% de chance de blefar
        self.bluff_call_ratio = 0.40  # 40% CALL / 60% RAISE quando blefar
        
        # Sistema de aprendizado agressivo (intermediário)
        self.round_results = []  # Histórico de 20 rodadas
        self.aggression_level = 0.70  # Nível de agressão (0-1)
        self.opponent_bluff_patterns = {}  # Padrões de blefe dos oponentes
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
        """Decide se deve blefar baseado na probabilidade configurada."""
        return random.random() < self.bluff_probability
    
    def _bluff_action(self, valid_actions, round_state):
        """Executa blefe agressivo: prefere RAISE."""
        context = self._analyze_table_context(round_state)
        
        # Blefe mais agressivo quando há poucos jogadores ativos
        if context['active_players'] <= 2:
            # Poucos jogadores: mais RAISE (80%)
            bluff_choice = random.random() < 0.80
        else:
            # Muitos jogadores: ainda prefere RAISE (50%)
            bluff_choice = random.random() < 0.50
        
        if bluff_choice and valid_actions[2]['amount']['min'] != -1:
            # Faz RAISE agressivo
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            # Raise mais alto que o mínimo
            amount = random.randint(min_amount, min(max_amount, min_amount + 30))
            return raise_action['action'], amount
        else:
            # Faz CALL
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _analyze_table_context(self, round_state):
        """Analisa o contexto da mesa."""
        pot_size = round_state['pot']['main']['amount']
        active_players = len([s for s in round_state['seats'] if s['state'] == 'participating'])
        street = round_state['street']
        
        return {
            'pot_size': pot_size,
            'active_players': active_players,
            'street': street
        }
    
    def _evaluate_hand_strength(self, hole_card):
        """Avalia a força das cartas (mais permissivo que TightPlayer)."""
        if not hole_card or len(hole_card) < 2:
            return 0
        
        card_ranks = [card[1] for card in hole_card]
        card_suits = [card[0] for card in hole_card]
        
        # Par
        if card_ranks[0] == card_ranks[1]:
            return 40
        
        # Qualquer carta alta
        high_cards = ['A', 'K', 'Q', 'J', 'T']
        if any(rank in high_cards for rank in card_ranks):
            return 30
        
        # Mesmo naipe
        if card_suits[0] == card_suits[1]:
            return 20
        
        # Qualquer coisa
        return 10
    
    def _normal_action(self, valid_actions, hand_strength, round_state):
        """Ação normal: ajusta agressão baseado no aprendizado."""
        # Ajusta agressão baseado no aprendizado
        adjusted_aggression = self.aggression_level
        
        # Sempre tenta fazer raise se possível (ajustado pelo aprendizado)
        raise_action = valid_actions[2]
        if raise_action['amount']['min'] != -1:
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            
            # Se tem mão forte, raise maior
            if hand_strength >= 30:
                # Ajusta baseado no nível de agressão aprendido
                raise_multiplier = 15 + (adjusted_aggression * 20)
                amount = random.randint(min_amount, min(max_amount, min_amount + int(raise_multiplier)))
            else:
                # Ainda faz raise, mas menor se agressão foi reduzida
                if adjusted_aggression > 0.5:
                    amount = min_amount
                else:
                    # Se agressão muito baixa, pode fazer call
                    call_action = valid_actions[1]
                    return call_action['action'], call_action['amount']
            return raise_action['action'], amount
        
        # Se não pode fazer raise, faz call
        call_action = valid_actions[1]
        return call_action['action'], call_action['amount']
    
    def receive_game_start_message(self, game_info):
        pass
    
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
        pass
    
    def receive_game_update_message(self, action, round_state):
        """Aprende padrões de blefe dos oponentes."""
        player_uuid = action.get('uuid') or action.get('player_uuid')
        if not player_uuid or player_uuid == self.uuid:
            return
        
        # Analisa se oponente está blefando (raise com mão fraca aparente)
        if action.get('action') == 'raise':
            if player_uuid not in self.opponent_bluff_patterns:
                self.opponent_bluff_patterns[player_uuid] = {'bluff_count': 0, 'total_raises': 0}
            
            self.opponent_bluff_patterns[player_uuid]['total_raises'] += 1
            # Se raise em pot pequeno ou com poucos jogadores, pode ser blefe
            pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
            if pot_size < 50:
                self.opponent_bluff_patterns[player_uuid]['bluff_count'] += 1
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprendizado agressivo: ajusta rapidamente baseado em resultados."""
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
        
        # Registra resultado (mantém apenas últimas 20)
        self.round_results.append({
            'won': won,
            'round': self.total_rounds,
            'stack': self.current_stack if self.current_stack else 100
        })
        if len(self.round_results) > 20:
            self.round_results = self.round_results[-20:]
        
        # Aprendizado agressivo: ajusta rapidamente
        if len(self.round_results) >= 5:
            recent_results = self.round_results[-10:] if len(self.round_results) >= 10 else self.round_results
            win_rate = sum(1 for r in recent_results if r['won']) / len(recent_results)
            
            # Aumenta agressão quando ganha
            if win_rate > 0.6:
                self.aggression_level = min(0.90, self.aggression_level + 0.10)
                self.bluff_probability = min(0.45, self.bluff_probability * 1.1)
            # Reduz agressão quando perde muito
            elif win_rate < 0.3:
                self.aggression_level = max(0.30, self.aggression_level - 0.15)
                self.bluff_probability = max(0.20, self.bluff_probability * 0.9)
            
            # Ajusta baseado em stack
            if self.initial_stack and self.current_stack:
                stack_ratio = self.current_stack / self.initial_stack
                if stack_ratio < 0.7:
                    # Stack baixo: reduz agressão
                    self.aggression_level = max(0.40, self.aggression_level - 0.10)
        
        # Salva memória após ajustes
        self.save_memory()
    
    def save_memory(self):
        """Salva memória aprendida em arquivo."""
        memory = {
            'bluff_probability': self.bluff_probability,
            'aggression_level': self.aggression_level,
            'total_rounds': self.total_rounds,
            'wins': self.wins,
            'opponent_bluff_patterns': self.opponent_bluff_patterns
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
                
                self.bluff_probability = memory.get('bluff_probability', 0.35)
                self.aggression_level = memory.get('aggression_level', 0.70)
                self.total_rounds = memory.get('total_rounds', 0)
                self.wins = memory.get('wins', 0)
                self.opponent_bluff_patterns = memory.get('opponent_bluff_patterns', {})
            except Exception as e:
                pass  # Silencioso
    
    def receive_game_start_message(self, game_info):
        """Inicializa stack."""
        seats = game_info.get('seats', [])
        if isinstance(seats, list):
            for player in seats:
                if player.get('uuid') == self.uuid:
                    self.initial_stack = player.get('stack', 100)
                    break

