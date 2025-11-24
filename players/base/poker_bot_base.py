"""
Classe base para TODOS os bots.
Contém TODA a lógica compartilhada.
Subclasses apenas injetam configuração.
"""
from abc import ABC
import random
from pypokerengine.players import BasePokerPlayer
from utils.memory_manager import UnifiedMemoryManager
from utils.action_analyzer import analyze_current_round_actions, analyze_possible_bluff
from .bot_config import BotConfig


class PokerBotBase(BasePokerPlayer, ABC):
    """
    Classe base para TODOS os bots.
    Contém TODA a lógica compartilhada.
    Subclasses apenas injetam configuração.
    """
    
    def __init__(self, config: BotConfig):
        """ÚNICA forma de criar um bot: com configuração"""
        self.config = config
        
        # Inicializa memória (lógica compartilhada)
        self.memory_manager = UnifiedMemoryManager(
            config.memory_file,
            config.default_bluff,
            config.default_aggression,
            config.default_tightness,
            config.name  # Passa nome do bot para pré-registrar todos os outros bots
        )
        self.memory = self.memory_manager.get_memory()
        
        # Carrega parâmetros da memória
        self._load_parameters_from_memory()
        
        # Estado interno
        self.initial_stack = None
        self.current_stack = None
        
        # Gera UUID fixo baseado na classe imediatamente
        from utils.uuid_utils import get_bot_class_uuid
        self._fixed_uuid = get_bot_class_uuid(self)
        # Define UUID fixo imediatamente (PyPokerEngine pode não chamar set_uuid)
        self.uuid = self._fixed_uuid
    
    def set_uuid(self, uuid):
        """
        Define UUID fixo baseado na classe do bot.
        Ignora o UUID do PyPokerEngine e usa UUID determinístico baseado na classe.
        Isso garante que o mesmo tipo de bot sempre tenha o mesmo UUID.
        """
        # Sempre usa UUID fixo, ignorando o UUID do PyPokerEngine
        self.uuid = self._fixed_uuid
    
    def _load_parameters_from_memory(self, opponent_uuid: str = None):
        """Carrega parâmetros da memória, opcionalmente específicos para um oponente.
        
        Args:
            opponent_uuid: UUID do oponente para usar parâmetros específicos (opcional)
        """
        # Se tem oponente específico e ele está na memória, usa parâmetros específicos
        if opponent_uuid and opponent_uuid in self.memory.get('opponents', {}):
            opp = self.memory['opponents'][opponent_uuid]
            # Usa parâmetros específicos do oponente, com fallback para globais
            self.bluff_probability = opp.get('bluff_probability', 
                self.memory.get('bluff_probability', self.config.default_bluff))
            self.aggression_level = opp.get('aggression_level',
                self.memory.get('aggression_level', self.config.default_aggression))
            self.tightness_threshold = opp.get('tightness_threshold',
                self.memory.get('tightness_threshold', self.config.default_tightness))
        else:
            # Usa parâmetros globais
            self.bluff_probability = self.memory.get('bluff_probability', self.config.default_bluff)
            self.aggression_level = self.memory.get('aggression_level', self.config.default_aggression)
            self.tightness_threshold = self.memory.get('tightness_threshold', self.config.default_tightness)
    
    def _get_primary_opponent_uuid(self, round_state) -> str:
        """Identifica o oponente principal no round (o que mais interagiu).
        
        Args:
            round_state: Estado do round
            
        Returns:
            UUID do oponente principal ou None
        """
        if not hasattr(self, 'uuid') or not self.uuid:
            return None
        
        from utils.uuid_utils import get_bot_class_uuid_from_name
        
        seats = round_state.get('seats', [])
        my_seat = next((s for s in seats if isinstance(s, dict) and s.get('uuid') == self.uuid), None)
        my_name = my_seat.get('name', 'Unknown') if my_seat else None
        my_uuid_fixed = get_bot_class_uuid_from_name(my_name) if my_name else self.uuid
        
        # Identifica oponentes ativos
        active_opponents = []
        for seat in seats:
            if isinstance(seat, dict):
                opp_uuid_from_seat = seat.get('uuid')
                if opp_uuid_from_seat and opp_uuid_from_seat != self.uuid:
                    opp_name = seat.get('name', 'Unknown')
                    opp_uuid_fixed = get_bot_class_uuid_from_name(opp_name)
                    opp_uuid = opp_uuid_fixed if opp_uuid_fixed else opp_uuid_from_seat
                    
                    if opp_uuid != my_uuid_fixed and seat.get('state') == 'participating':
                        active_opponents.append(opp_uuid)
        
        # Se tem apenas um oponente, usa ele
        if len(active_opponents) == 1:
            return active_opponents[0]
        
        # Se tem múltiplos oponentes, escolhe o que tem mais rounds jogados juntos
        if len(active_opponents) > 1:
            best_opp = None
            max_rounds = 0
            for opp_uuid in active_opponents:
                if opp_uuid in self.memory.get('opponents', {}):
                    rounds = self.memory['opponents'][opp_uuid].get('total_rounds_against', 0)
                    if rounds > max_rounds:
                        max_rounds = rounds
                        best_opp = opp_uuid
            return best_opp if best_opp else active_opponents[0]
        
        return None
    
    def declare_action(self, valid_actions, hole_card, round_state):
        """
        Lógica UNIVERSAL de decisão.
        ZERO lógica específica de bot aqui.
        """
        # Garante que UUID fixo seja mantido (PyPokerEngine pode ter sobrescrito)
        if hasattr(self, '_fixed_uuid') and self._fixed_uuid:
            self.uuid = self._fixed_uuid
        
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
        
        # Identifica oponente principal para usar parâmetros específicos
        primary_opponent_uuid = self._get_primary_opponent_uuid(round_state)
        
        # Analisa contexto
        current_actions = analyze_current_round_actions(
            round_state, self.uuid
        ) if hasattr(self, 'uuid') and self.uuid else None
        
        # Avalia mão
        hand_strength = self._evaluate_hand_strength(hole_card, round_state)
        
        # Análise de blefe dos oponentes
        bluff_analysis = None
        if hasattr(self, 'uuid') and self.uuid:
            bluff_analysis = analyze_possible_bluff(
                round_state, self.uuid, hand_strength, self.memory_manager
            )
        
        # Atualiza valores da memória (usa parâmetros específicos do oponente se disponível)
        self._load_parameters_from_memory(primary_opponent_uuid)
        
        # Decide blefe
        should_bluff = self._should_bluff(current_actions)
        
        # Escolhe ação
        if should_bluff:
            action, amount = self._bluff_action(valid_actions, round_state)
        else:
            action, amount = self._normal_action(
                valid_actions, hand_strength, round_state,
                current_actions, bluff_analysis
            )
        
        # Registra ação
        if hasattr(self, 'uuid') and self.uuid:
            street = round_state.get('street', 'preflop')
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
        
        return action, amount
    
    def _should_bluff(self, current_actions) -> bool:
        """Decide blefe baseado em config E contexto"""
        # Não blefa se muita agressão
        if current_actions and current_actions.get('has_raises'):
            raise_sensitivity = self.config.raise_count_sensitivity
            if current_actions['raise_count'] >= (2 * raise_sensitivity):
                return False
        
        return random.random() < self.bluff_probability
    
    def _bluff_action(self, valid_actions, round_state):
        """Executa blefe baseado em config"""
        context = self._analyze_table_context(round_state)
        
        # Calcula probabilidade de raise no blefe baseado em número de jogadores
        if context['active_players'] <= 2:
            raise_prob = self.config.bluff_raise_prob_few_players
        else:
            raise_prob = self.config.bluff_raise_prob_many_players
        
        if random.random() < raise_prob and valid_actions[2]['amount']['min'] != -1:
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            amount = random.randint(
                min_amount,
                min(max_amount, min_amount + self.config.raise_multiplier_min)
            )
            return raise_action['action'], amount
        else:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _normal_action(self, valid_actions, hand_strength, round_state,
                       current_actions=None, bluff_analysis=None):
        """Ação normal baseada em config"""
        
        # 1. Verifica detecção de blefe
        if bluff_analysis and bluff_analysis['should_call_bluff']:
            if hand_strength >= self.config.bluff_detection_threshold:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # 2. Ajusta threshold baseado em ações
        adjusted_threshold = self.tightness_threshold
        if current_actions:
            if current_actions.get('has_raises'):
                adjusted_threshold += (
                    self.config.raise_threshold_adjustment_base +
                    (current_actions['raise_count'] * self.config.raise_threshold_adjustment_per_raise)
                )
            elif current_actions.get('last_action') == 'raise':
                adjusted_threshold += self.config.raise_threshold_adjustment_base
        
        # 3. Ajusta agressão
        adjusted_aggression = self.aggression_level
        
        # Reduz agressão se muitos raises
        if current_actions and current_actions.get('raise_count', 0) >= 2:
            adjusted_aggression *= self.config.raise_count_aggression_reduction
        
        # Aumenta agressão se campo passivo
        if current_actions and current_actions.get('is_passive', False):
            passive_score = current_actions.get('passive_opportunity_score', 0.0)
            adjusted_aggression = min(
                0.95,
                adjusted_aggression + (passive_score * self.config.passive_aggression_boost)
            )
            # Reduz threshold quando campo passivo
            adjusted_threshold = max(
                self.config.passive_threshold_min,
                adjusted_threshold - int(passive_score * self.config.passive_threshold_reduction_factor)
            )
        
        # 4. Mão muito forte: raise
        if hand_strength >= self.config.strong_hand_threshold:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                # Calcula amount baseado em agressão ajustada
                multiplier = int(self.config.raise_multiplier_max * adjusted_aggression)
                amount = random.randint(
                    min_amount,
                    min(max_amount, min_amount + multiplier)
                )
                return raise_action['action'], amount
        
        # 5. Campo passivo: pode fazer raise com mão média
        if current_actions and current_actions.get('is_passive', False):
            passive_score = current_actions.get('passive_opportunity_score', 0.0)
            if (hand_strength >= self.config.passive_raise_threshold and
                passive_score > self.config.passive_raise_score_threshold and
                valid_actions[2]['amount']['min'] != -1):
                return valid_actions[2]['action'], valid_actions[2]['amount']['min']
        
        # 6. Mão forte: call ou raise baseado em agressão
        if hand_strength >= adjusted_threshold:
            if adjusted_aggression > self.config.default_aggression:
                if valid_actions[2]['amount']['min'] != -1:
                    return valid_actions[2]['action'], valid_actions[2]['amount']['min']
            
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
        
        # 7. Para Aggressive: sempre tenta raise se possível (lógica especial)
        if self.config.name == "Aggressive" and hand_strength >= self.config.fold_threshold_base:
            raise_action = valid_actions[2]
            if raise_action['amount']['min'] != -1:
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                # Se tem mão forte, raise maior
                if hand_strength >= 30:
                    raise_multiplier = 15 + int(adjusted_aggression * 20)
                    amount = random.randint(min_amount, min(max_amount, min_amount + raise_multiplier))
                else:
                    # Ainda faz raise, mas menor se agressão foi reduzida
                    if adjusted_aggression > 0.5:
                        amount = min_amount
                    else:
                        # Se agressão muito baixa, pode fazer call
                        call_action = valid_actions[1]
                        return call_action['action'], call_action['amount']
                return raise_action['action'], amount
        
        # 8. Mão fraca: fold se muito fraca
        # Para aggressive: fold_threshold_base já é usado diretamente
        # Para cautious: usa adjusted_threshold - 4 (mais tolerante)
        # Para outros: usa adjusted_threshold - 8 (padrão)
        if self.config.name == "Aggressive":
            fold_threshold = self.config.fold_threshold_base
            if current_actions and current_actions.get('has_raises'):
                fold_threshold += (
                    self.config.raise_threshold_adjustment_base +
                    (current_actions['raise_count'] * self.config.raise_threshold_adjustment_per_raise)
                )
        elif self.config.name == "Cautious":
            fold_threshold = adjusted_threshold - 4  # Cautious é mais tolerante
        else:
            fold_threshold = adjusted_threshold - 8  # Ajuste padrão para outros bots
        
        if hand_strength < fold_threshold:
            fold_action = valid_actions[0]
            return fold_action['action'], fold_action['amount']
        
        # 9. Mão média: call
        call_action = valid_actions[1]
        return call_action['action'], call_action['amount']
    
    def _evaluate_hand_strength(self, hole_card, round_state=None):
        """Avalia força usando utilitário compartilhado"""
        from utils.hand_utils import evaluate_hand_strength
        community_cards = round_state.get('community_card', []) if round_state else None
        return evaluate_hand_strength(hole_card, community_cards)
    
    def _analyze_table_context(self, round_state):
        """Analisa contexto da mesa"""
        pot_size = round_state['pot']['main']['amount']
        active_players = len([
            s for s in round_state['seats'] 
            if s['state'] == 'participating'
        ])
        street = round_state['street']
        
        return {
            'pot_size': pot_size,
            'active_players': active_players,
            'street': street
        }
    
    # ============================================================
    # Métodos receive_* (lógica compartilhada)
    # ============================================================
    
    def receive_game_start_message(self, game_info):
        """Inicializa stack"""
        # Garante que UUID fixo seja mantido (PyPokerEngine pode ter sobrescrito)
        if hasattr(self, '_fixed_uuid') and self._fixed_uuid:
            self.uuid = self._fixed_uuid
        
        seats = game_info.get('seats', [])
        if isinstance(seats, list):
            for player in seats:
                if player.get('uuid') == self.uuid:
                    self.initial_stack = player.get('stack', 100)
                    self.memory_manager.initial_stack = self.initial_stack
                    break
    
    def receive_round_start_message(self, round_count, hole_card, seats):
        """Salva memória periodicamente"""
        if round_count % 5 == 0:
            self.memory_manager.save()
        
        # Armazena cartas no registry
        if hole_card and hasattr(self, 'uuid') and self.uuid:
            from utils.cards_registry import store_player_cards
            from utils.hand_utils import normalize_hole_cards
            hole_cards = normalize_hole_cards(hole_card)
            if hole_cards:
                store_player_cards(self.uuid, hole_cards)
    
    def receive_street_start_message(self, street, round_state):
        """Hook para futuras extensões"""
        pass
    
    def receive_game_update_message(self, action, round_state):
        """Registra ações dos oponentes"""
        player_uuid = action.get('uuid') or action.get('player_uuid')
        if player_uuid and player_uuid != self.uuid:
            self.memory_manager.record_opponent_action(player_uuid, action, round_state)
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        """Aprendizado baseado em config"""
        # Processa resultado
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.process_round_result(
                winners, hand_info, round_state, self.uuid
            )
        
        # Atualiza stack
        for seat in round_state['seats']:
            if seat['uuid'] == self.uuid:
                if self.initial_stack is None:
                    self.initial_stack = seat['stack']
                    self.memory_manager.initial_stack = self.initial_stack
                self.current_stack = seat['stack']
                break
        
        # Atualiza valores locais
        self.memory = self.memory_manager.get_memory()
        self.total_rounds = self.memory['total_rounds']
        self.wins = self.memory['wins']
        
        # Aprendizado gradual
        round_history = self.memory.get('round_history', [])
        if len(round_history) >= self.config.rounds_before_learning:
            recent_rounds = round_history[-self.config.rounds_before_learning:]
            win_rate = sum(
                1 for r in recent_rounds if r['final_result']['won']
            ) / len(recent_rounds)
            
            learning_factor = 1 + self.config.learning_speed
            
            if win_rate > self.config.win_rate_threshold_high:
                self.memory['aggression_level'] = min(
                    0.75, self.memory['aggression_level'] * learning_factor
                )
                self.memory['bluff_probability'] = min(
                    0.22, self.memory['bluff_probability'] * learning_factor
                )
            elif win_rate < self.config.win_rate_threshold_low:
                self.memory['tightness_threshold'] = min(
                    35, self.memory['tightness_threshold'] + 1
                )
                self.memory['aggression_level'] = max(
                    0.35, self.memory['aggression_level'] / learning_factor
                )
                self.memory['bluff_probability'] = max(
                    0.10, self.memory['bluff_probability'] / learning_factor
                )
        
        # Ajuste baseado em stack (para alguns bots)
        if self.initial_stack and self.current_stack:
            stack_ratio = self.current_stack / self.initial_stack
            if stack_ratio < 0.7:
                # Stack baixo: reduz agressão
                self.memory['aggression_level'] = max(
                    0.40, self.memory['aggression_level'] * 0.999
                )
        
        # Atualiza valores locais
        self._load_parameters_from_memory()
        
        # Salva memória
        self.memory_manager.save()

