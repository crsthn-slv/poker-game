from pypokerengine.players import BasePokerPlayer
import random
from utils.memory_manager import UnifiedMemoryManager
from utils.hand_utils import evaluate_hand_strength
from utils.action_analyzer import analyze_current_round_actions, analyze_possible_bluff
from utils.constants import (
    BLUFF_PROBABILITY_TIGHT, TIGHTNESS_THRESHOLD_DEFAULT,
    HAND_STRENGTH_VERY_STRONG, HAND_STRENGTH_STRONG
)

class TightPlayer(BasePokerPlayer):
    """Jogador conservador que joga apenas com mãos fortes. Blefa raramente (8%). Aprendizado conservador básico com memória persistente."""
    
    def __init__(self, memory_file="tight_player_memory.json"):
        # Inicializa gerenciador de memória unificada
        self.memory_manager = UnifiedMemoryManager(
            memory_file,
            default_bluff=0.15,  # Nivelado: ligeiramente abaixo da média
            default_aggression=0.54,  # Nivelado: ligeiramente abaixo da média
            default_tightness=29  # Nivelado: ligeiramente acima da média
        )
        self.memory = self.memory_manager.get_memory()
        self.bluff_probability = self.memory['bluff_probability']
        self.tightness_threshold = self.memory['tightness_threshold']
        self.bluff_call_ratio = 0.70  # 70% CALL / 30% RAISE quando blefar
        self.consecutive_losses = 0
        self.initial_stack = None
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        # NOVO: Analisa ações do round atual
        current_actions = analyze_current_round_actions(round_state, self.uuid) if hasattr(self, 'uuid') and self.uuid else None
        
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        
        # NOVO: Analisa possível blefe dos oponentes
        bluff_analysis = None
        if hasattr(self, 'uuid') and self.uuid:
            bluff_analysis = analyze_possible_bluff(
                round_state, self.uuid, hand_strength, self.memory_manager
            )
        
        should_bluff = self._should_bluff()
        
        # Atualiza valores da memória
        self.bluff_probability = self.memory['bluff_probability']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # NOVO: Ajusta blefe baseado em ações atuais
        if current_actions and current_actions['has_raises']:
            should_bluff = False  # Não blefa se alguém fez raise
        
        if should_bluff:
            action, amount = self._bluff_action(valid_actions, round_state)
        else:
            action, amount = self._normal_action(valid_actions, hand_strength, round_state, current_actions, bluff_analysis)
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            street = round_state.get('street', 'preflop')
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
        
        return action, amount
    
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
    
    def _normal_action(self, valid_actions, hand_strength, round_state, current_actions=None, bluff_analysis=None):
        """Ação normal baseada na força das cartas (ajustada pelo aprendizado e ações atuais)."""
        # Ajusta threshold baseado no aprendizado conservador
        adjusted_threshold = self.tightness_threshold
        
        # NOVO: Ajusta threshold baseado em ações do round atual
        if current_actions:
            if current_actions['has_raises']:
                # Se alguém fez raise, fica mais seletivo (conservador)
                adjusted_threshold += 8 + (current_actions['raise_count'] * 3)
            elif current_actions['last_action'] == 'raise':
                # Se última ação foi raise, aumenta threshold
                adjusted_threshold += 5
        
        # NOVO: Campo passivo reduz threshold (TightPlayer fica um pouco menos conservador)
        if current_actions and current_actions.get('is_passive', False):
            passive_score = current_actions.get('passive_opportunity_score', 0.0)
            # Reduz threshold moderadamente (TightPlayer é conservador)
            adjusted_threshold = max(28, adjusted_threshold - int(passive_score * 3))
        
        # Mão muito forte: tenta fazer raise
        if hand_strength >= HAND_STRENGTH_STRONG:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                return raise_action['action'], raise_action['amount']['min']
        
        # NOVO: Com campo passivo, TightPlayer pode fazer raise com mão forte
        if current_actions and current_actions.get('is_passive', False):
            passive_score = current_actions.get('passive_opportunity_score', 0.0)
            if hand_strength >= 45 and passive_score > 0.6:
                raise_action = valid_actions[2]
                if raise_action['amount']['min'] != -1:
                    return raise_action['action'], raise_action['amount']['min']
        
        # NOVO: Se análise indica possível blefe e deve pagar, considera call mesmo com mão média
        if bluff_analysis and bluff_analysis['should_call_bluff']:
            if hand_strength >= 32:  # Tight: paga blefe com mão razoável (mais seletivo)
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # Mão forte: faz call (threshold ajustado pelo aprendizado)
        if hand_strength >= adjusted_threshold:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
        
        # Mão fraca: fold apenas se for MUITO fraca (reduzido de threshold direto)
        # Antes: foldava se < threshold. Agora: folda apenas se < threshold - 5
        if hand_strength < (adjusted_threshold - 5):
            fold_action = valid_actions[0]
            return fold_action['action'], fold_action['amount']
        
        # Mão média-fraca: call (não desiste tão fácil)
        call_action = valid_actions[1]
        return call_action['action'], call_action['amount']
    
    def receive_game_start_message(self, game_info):
        """Inicializa stack inicial."""
        seats = game_info.get('seats', [])
        if isinstance(seats, list):
            for player in seats:
                if player.get('uuid') == self.uuid:
                    self.initial_stack = player.get('stack', 100)
                    if not hasattr(self.memory_manager, 'initial_stack'):
                        self.memory_manager.initial_stack = self.initial_stack
                    break
    
    def receive_round_start_message(self, round_count, hole_card, seats):
        """Salva memória periodicamente e armazena cartas no registry."""
        if round_count % 5 == 0:
            self.memory_manager.save()
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
        """Registra ações dos oponentes."""
        player_uuid = action.get('uuid') or action.get('player_uuid')
        if player_uuid and player_uuid != self.uuid:
            self.memory_manager.record_opponent_action(player_uuid, action, round_state)
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprendizado conservador: ajusta apenas quando perde muito."""
        # Processa resultado usando gerenciador de memória
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(winners, hand_info, round_state, self.uuid)
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Verifica se ganhou
        won = any(
            (w.get('uuid') if isinstance(w, dict) else getattr(w, 'uuid', None)) == self.uuid
            for w in winners
        )
        
        if won:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        # Aprendizado conservador: só ajusta quando win rate < 30% OU 3+ perdas seguidas
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= 5:
            recent_rounds = round_history[-10:] if len(round_history) >= 10 else round_history
            win_rate = sum(1 for r in recent_rounds if r['final_result']['won']) / len(recent_rounds)
            
            # Aumenta seletividade quando win rate < 30% (evolução lenta)
            if win_rate < 0.30:
                self.memory['tightness_threshold'] = min(35, self.memory['tightness_threshold'] + 1)
            
            # Reduz blefe quando perde 3+ rodadas seguidas (evolução muito lenta)
            if self.consecutive_losses >= 3:
                self.memory['bluff_probability'] = max(0.10, self.memory['bluff_probability'] * 0.999)
        
        # Atualiza valores locais
        self.bluff_probability = self.memory['bluff_probability']
        self.tightness_threshold = self.memory['tightness_threshold']
        
        # Salva memória após ajustes
        self.memory_manager.save()

