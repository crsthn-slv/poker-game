from pypokerengine.players import BasePokerPlayer
import random
from .memory_utils import get_memory_path
from .hand_utils import evaluate_hand_strength, get_rank_value
from .constants import (
    BLUFF_PROBABILITY_TIGHT, TIGHTNESS_THRESHOLD_DEFAULT,
    HAND_STRENGTH_VERY_STRONG, HAND_STRENGTH_STRONG
)
from .error_handling import safe_memory_save, safe_memory_load

class TightPlayer(BasePokerPlayer):
    """Jogador conservador que joga apenas com mãos fortes. Blefa raramente (8%). Aprendizado conservador básico com memória persistente."""
    
    def __init__(self, memory_file="tight_player_memory.json"):
        self.memory_file = get_memory_path(memory_file)
        self.bluff_probability = BLUFF_PROBABILITY_TIGHT
        self.bluff_call_ratio = 0.70  # 70% CALL / 30% RAISE quando blefar
        
        # Sistema de aprendizado conservador (básico)
        self.round_results = []  # Histórico simples (últimas 10 rodadas)
        self.consecutive_losses = 0
        self.tightness_threshold = TIGHTNESS_THRESHOLD_DEFAULT
        self.total_rounds = 0
        self.wins = 0
        
        # Carrega memória anterior se existir
        self.load_memory()
    
    def declare_action(self, valid_actions, hole_card, round_state):
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        should_bluff = self._should_bluff()
        
        if should_bluff:
            return self._bluff_action(valid_actions, round_state)
        else:
            return self._normal_action(valid_actions, hand_strength, round_state)
    
    def _should_bluff(self):
        """Decide se deve blefar baseado na probabilidade configurada."""
        return random.random() < self.bluff_probability
    
    def _bluff_action(self, valid_actions, round_state):
        """Executa blefe: escolhe CALL ou RAISE baseado no contexto da mesa."""
        context = self._analyze_table_context(round_state)
        
        # Blefe mais sutil em pot pequeno
        if context['pot_size'] < 50:
            # Pot pequeno: mais chance de RAISE
            bluff_choice = random.random() < 0.40  # 40% RAISE, 60% CALL
        else:
            # Pot grande: mais chance de CALL (blefe mais conservador)
            bluff_choice = random.random() < 0.20  # 20% RAISE, 80% CALL
        
        if bluff_choice and valid_actions[2]['amount']['min'] != -1:
            # Faz RAISE
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(min_amount, min(max_amount, min_amount + 20))
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
    
    def _evaluate_hand_strength(self, hole_card, round_state=None):
        """Avalia a força das cartas usando utilitário compartilhado."""
        community_cards = round_state.get('community_card', []) if round_state else None
        return evaluate_hand_strength(hole_card, community_cards)
    
    def _normal_action(self, valid_actions, hand_strength, round_state):
        """Ação normal baseada na força das cartas (ajustada pelo aprendizado)."""
        # Ajusta threshold baseado no aprendizado conservador
        adjusted_threshold = self.tightness_threshold
        
        # Mão muito forte: tenta fazer raise
        if hand_strength >= HAND_STRENGTH_STRONG:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                return raise_action['action'], raise_action['amount']['min']
        
        # Mão forte: faz call (threshold ajustado pelo aprendizado)
        if hand_strength >= adjusted_threshold:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
        
        # Mão fraca: faz fold
        fold_action = valid_actions[0]
        return fold_action['action'], fold_action['amount']
    
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
        pass
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprendizado conservador: ajusta apenas quando perde muito."""
        self.total_rounds += 1
        
        # Verifica se ganhou
        won = any(w['uuid'] == self.uuid for w in winners)
        if won:
            self.wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        # Registra resultado (mantém apenas últimas 10)
        self.round_results.append({'won': won, 'round': self.total_rounds})
        if len(self.round_results) > 10:
            self.round_results = self.round_results[-10:]
        
        # Aprendizado conservador: só ajusta quando win rate < 30% OU 3+ perdas seguidas
        if len(self.round_results) >= 5:
            win_rate = sum(1 for r in self.round_results if r['won']) / len(self.round_results)
            
            # Aumenta seletividade quando win rate < 30% (threshold mais alto)
            if win_rate < 0.30:
                self.tightness_threshold = min(35, self.tightness_threshold + 5)
            
            # Reduz blefe quando perde 3+ rodadas seguidas
            if self.consecutive_losses >= 3:
                self.bluff_probability = max(0.02, self.bluff_probability * 0.7)
        
        # Salva memória após ajustes
        self.save_memory()
    
    def save_memory(self):
        """Salva memória aprendida em arquivo com tratamento de erros melhorado."""
        memory = {
            'bluff_probability': self.bluff_probability,
            'tightness_threshold': self.tightness_threshold,
            'total_rounds': self.total_rounds,
            'wins': self.wins,
            'consecutive_losses': self.consecutive_losses
        }
        
        safe_memory_save(self.memory_file, memory)
    
    def load_memory(self):
        """Carrega memória aprendida de arquivo com tratamento de erros melhorado."""
        default_memory = {
            'bluff_probability': BLUFF_PROBABILITY_TIGHT,
            'tightness_threshold': TIGHTNESS_THRESHOLD_DEFAULT,
            'total_rounds': 0,
            'wins': 0,
            'consecutive_losses': 0
        }
        
        memory = safe_memory_load(self.memory_file, default_memory)
        
        self.bluff_probability = memory.get('bluff_probability', BLUFF_PROBABILITY_TIGHT)
        self.tightness_threshold = memory.get('tightness_threshold', TIGHTNESS_THRESHOLD_DEFAULT)
        self.total_rounds = memory.get('total_rounds', 0)
        self.wins = memory.get('wins', 0)
        self.consecutive_losses = memory.get('consecutive_losses', 0)

