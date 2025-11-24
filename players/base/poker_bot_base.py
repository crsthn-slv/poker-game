"""
Classe base para TODOS os bots.
Contém TODA a lógica compartilhada.
Subclasses apenas injetam configuração.
"""
from abc import ABC
import random
from typing import Optional
from pypokerengine.players import BasePokerPlayer
from utils.memory_manager import UnifiedMemoryManager
from utils.action_analyzer import analyze_current_round_actions, analyze_possible_bluff
from utils.action_dataclasses import CurrentActions, BluffAnalysis
from utils.bet_sizing import BetSizingCalculator
from .bot_config import BotConfig

# Seed global opcional para debugging (MELHORIA #3)
_RANDOM_SEED: Optional[int] = None

def set_random_seed(seed: Optional[int] = None):
    """
    Define seed opcional para random (para debugging).
    
    Permite reproduzir cenários, isolar bugs, comparar versões de bots.
    
    Args:
        seed: Seed para random (None para desabilitar)
    """
    global _RANDOM_SEED
    _RANDOM_SEED = seed
    if seed is not None:
        random.seed(seed)

def get_random_seed() -> Optional[int]:
    """Retorna seed atual (se configurado)."""
    return _RANDOM_SEED


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
        
        # Estado interno (MELHORIA #4: atualização interna de stack e SPR)
        self.initial_stack = None
        self.current_stack = None
        self.current_spr = None  # SPR atualizado internamente
        
        # MELHORIA: Memória de curto prazo (últimas 5 ações)
        self.recent_actions = []  # Últimas 5 ações: [{'action': str, 'hand_strength': int, 'street': str}, ...]
        self.recent_bluffs = []  # Últimos 3 blefes: [{'round': int, 'street': str}, ...]
        
        # Inicializa calculadora de sizing (MELHORIA #11)
        self.sizing_calculator = BetSizingCalculator(config)
        
        # Gera UUID fixo baseado na classe imediatamente
        from utils.uuid_utils import get_bot_class_uuid
        self._fixed_uuid = get_bot_class_uuid(self)
        # Define UUID fixo imediatamente (PyPokerEngine pode não chamar set_uuid)
        self.uuid = self._fixed_uuid
        
        # Aplica seed se configurado (MELHORIA #3)
        if _RANDOM_SEED is not None:
            random.seed(_RANDOM_SEED)
    
    def set_uuid(self, uuid):
        """
        Define UUID fixo baseado na classe do bot.
        Ignora o UUID do PyPokerEngine e usa UUID determinístico baseado na classe.
        Isso garante que o mesmo tipo de bot sempre tenha o mesmo UUID.
        """
        # Sempre usa UUID fixo, ignorando o UUID do PyPokerEngine
        self.uuid = self._fixed_uuid
    
    def _load_parameters_from_memory(self, opponent_uuid: Optional[str] = None):
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
    
    def _get_position(self, round_state) -> str:
        """
        MELHORIA: Identifica posição na mesa baseado na ordem de ação.
        
        Posição é fundamental no poker:
        - Early: Primeiros a agir (precisa de mãos mais fortes)
        - Middle: Meio da mesa (jogo balanceado)
        - Late: Últimos a agir (pode jogar mais mãos, tem vantagem informacional)
        - Blinds: Nas blinds (situação especial)
        
        Args:
            round_state: Estado do round
            
        Returns:
            str: 'early', 'middle', 'late', ou 'blinds'
        """
        if not hasattr(self, 'uuid') or not self.uuid:
            return 'middle'  # Fallback
        
        seats = round_state.get('seats', [])
        if not seats:
            return 'middle'
        
        # Identifica jogadores ativos (participating)
        active_seats = [s for s in seats if isinstance(s, dict) and s.get('state') == 'participating']
        if len(active_seats) < 2:
            return 'middle'
        
        # Encontra índice do bot
        my_index = None
        for i, seat in enumerate(active_seats):
            if seat.get('uuid') == self.uuid:
                my_index = i
                break
        
        if my_index is None:
            return 'middle'
        
        total_players = len(active_seats)
        
        # Determina posição baseado na ordem
        # Early: primeiro terço
        # Middle: segundo terço
        # Late: último terço
        if total_players <= 2:
            # Heads-up: posição é relativa
            return 'late' if my_index == 1 else 'early'
        elif total_players == 3:
            # 3 jogadores: early (0), middle (1), late (2)
            if my_index == 0:
                return 'early'
            elif my_index == 1:
                return 'middle'
            else:
                return 'late'
        else:
            # 4+ jogadores: divide em terços
            early_cutoff = total_players // 3
            late_start = (total_players * 2) // 3
            
            if my_index < early_cutoff:
                return 'early'
            elif my_index >= late_start:
                return 'late'
            else:
                return 'middle'
    
    def _adjust_for_position(self, fold_threshold: int, position: str) -> int:
        """
        MELHORIA: Ajusta threshold baseado em posição na mesa.
        
        Método virtual que pode ser sobrescrito por subclasses para personalizar
        ajustes de posição baseados na personalidade do bot.
        
        Args:
            fold_threshold: Threshold atual
            position: Posição na mesa ('early', 'middle', 'late', 'blinds')
            
        Returns:
            int: Threshold ajustado
        """
        if position == 'late':
            # Late position: pode jogar mais mãos (reduz threshold em 2-3 pontos)
            return fold_threshold - 3
        elif position == 'early':
            # Early position: precisa de mãos mais fortes (aumenta threshold em 2-3 pontos)
            return fold_threshold + 3
        elif position == 'middle':
            # Middle position: ajuste mínimo
            return fold_threshold + 1
        else:  # blinds
            # Blinds: situação especial, ajuste conservador
            return fold_threshold + 2
    
    def _update_recent_memory(self, action: str, hand_strength: int, street: str, was_bluff: bool):
        """
        MELHORIA: Atualiza memória de curto prazo com última ação.
        
        Mantém histórico das últimas 5 ações para evitar inconsistências.
        
        Args:
            action: Ação realizada ('fold', 'call', 'raise')
            hand_strength: Força da mão
            street: Street atual ('preflop', 'flop', 'turn', 'river')
            was_bluff: Se a ação foi um blefe
        """
        current_round = self.memory.get('total_rounds', 0)
        
        # Adiciona ação recente
        self.recent_actions.append({
            'action': action,
            'hand_strength': hand_strength,
            'street': street,
            'round': current_round,
            'was_bluff': was_bluff
        })
        
        # Mantém apenas últimas 5 ações
        if len(self.recent_actions) > 5:
            self.recent_actions.pop(0)
        
        # Atualiza histórico de blefes
        if was_bluff:
            self.recent_bluffs.append({
                'round': current_round,
                'street': street
            })
            # Mantém apenas últimos 3 blefes
            if len(self.recent_bluffs) > 3:
                self.recent_bluffs.pop(0)
    
    def _get_primary_opponent_uuid(self, round_state) -> Optional[str]:
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
        # MELHORIA #5: Extrair partes críticas de declare_action
        # 1. Garante UUID e identifica oponentes
        self._ensure_uuid_and_identify_opponents(round_state)
        
        # 2. Coleta métricas e contexto
        metrics = self._collect_decision_metrics(hole_card, round_state)
        
        # 3. Atualiza estado interno (stack e SPR) - MELHORIA #4
        self._update_internal_state(round_state)
        
        # 4. Decide ação
        action, amount = self._make_decision(
            valid_actions, round_state, metrics
        )
        
        # 5. Registra ação
        self._record_action(action, amount, metrics, round_state)
        
        return action, amount
    
    def _ensure_uuid_and_identify_opponents(self, round_state):
        """MELHORIA #5: Garante UUID e identifica oponentes."""
        # Garante que UUID fixo seja mantido (PyPokerEngine pode ter sobrescrito)
        if hasattr(self, '_fixed_uuid') and self._fixed_uuid:
            self.uuid = self._fixed_uuid
        
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
    
    def _collect_decision_metrics(self, hole_card, round_state):
        """MELHORIA #5: Coleta métricas e contexto para decisão."""
        # Identifica oponente principal para usar parâmetros específicos
        primary_opponent_uuid = self._get_primary_opponent_uuid(round_state)
        
        # MELHORIA: Identifica posição na mesa
        position = self._get_position(round_state)
        
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
        if primary_opponent_uuid:
            self._load_parameters_from_memory(primary_opponent_uuid)
        else:
            self._load_parameters_from_memory()
        
        return {
            'current_actions': current_actions,
            'hand_strength': hand_strength,
            'bluff_analysis': bluff_analysis,
            'primary_opponent_uuid': primary_opponent_uuid,
            'position': position  # MELHORIA: Adiciona posição
        }
    
    def _update_internal_state(self, round_state):
        """MELHORIA #4: Actualização interna de stack e SPR."""
        my_stack = self._get_my_stack(round_state)
        self.current_stack = my_stack
        
        # Calcula e armazena SPR internamente
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        self.current_spr = self.sizing_calculator.calculate_spr(my_stack, pot_size)
    
    def _make_decision(self, valid_actions, round_state, metrics):
        """MELHORIA #5: Toma decisão baseada em métricas."""
        current_actions = metrics['current_actions']
        hand_strength = metrics['hand_strength']
        bluff_analysis = metrics['bluff_analysis']
        
        # Decide blefe (passa round_state para análise contextual)
        should_bluff = self._should_bluff(current_actions, round_state)
        
        # Escolhe ação
        if should_bluff:
            return self._bluff_action(valid_actions, round_state)
        else:
            return self._normal_action(
                valid_actions, hand_strength, round_state,
                current_actions, bluff_analysis, metrics
            )
    
    def _record_action(self, action, amount, metrics, round_state):
        """MELHORIA #5: Registra ação na memória."""
        if hasattr(self, 'uuid') and self.uuid:
            street = round_state.get('street', 'preflop')
            hand_strength = metrics['hand_strength']
            current_actions = metrics['current_actions']
            
            # Determina se foi blefe (passa round_state para análise contextual)
            should_bluff = self._should_bluff(current_actions, round_state)
            
            # MELHORIA: Atualiza memória de curto prazo
            self._update_recent_memory(action, hand_strength, street, should_bluff)
            
            self.memory_manager.record_my_action(
                street, action, amount, hand_strength, round_state, should_bluff
            )
    
    def _should_bluff(self, current_actions: Optional[CurrentActions], round_state=None) -> bool:
        """
        MELHORIA: Decide blefe baseado em config, contexto E histórico recente.
        
        Sistema melhorado que considera:
        - Probabilidade base de blefe
        - Contexto atual (raises, agressão)
        - Histórico recente (não blefar muito seguido)
        - Street atual (blefes mais efetivos em streets específicas)
        """
        # Não blefa se muita agressão
        if current_actions and current_actions.has_raises:
            raise_sensitivity = self.config.raise_count_sensitivity
            if current_actions.raise_count >= (2 * raise_sensitivity):
                return False
        
        # MELHORIA: Não blefa se blefou muito recentemente (evita padrão previsível)
        if len(self.recent_bluffs) >= 2:
            # Se blefou nas últimas 2 vezes, reduz chance de blefe
            recent_bluff_count = sum(1 for b in self.recent_bluffs[-2:] if b is not None)
            if recent_bluff_count >= 2:
                # Reduz probabilidade em 50% se blefou muito recentemente
                adjusted_bluff_prob = self.bluff_probability * 0.5
                return random.random() < adjusted_bluff_prob
        
        # MELHORIA: Ajusta probabilidade baseado na street
        street = round_state.get('street', 'preflop') if round_state else 'preflop'
        street_multiplier = 1.0
        
        if street == 'preflop':
            # Preflop: blefes são menos efetivos (muitas mãos ainda podem melhorar)
            street_multiplier = 0.8
        elif street == 'flop':
            # Flop: blefes são mais efetivos (continuidade)
            street_multiplier = 1.1
        elif street == 'turn':
            # Turn: blefes são efetivos (poucas cartas restantes)
            street_multiplier = 1.2
        elif street == 'river':
            # River: blefes são muito efetivos (última chance)
            street_multiplier = 1.3
        
        adjusted_prob = self.bluff_probability * street_multiplier
        # Limita entre 0 e 1
        adjusted_prob = min(1.0, max(0.0, adjusted_prob))
        
        return random.random() < adjusted_prob
    
    def _bluff_action(self, valid_actions, round_state):
        """
        Executa blefe baseado em config.
        
        Usa novo sistema de sizing para blefes (sizing "small").
        """
        context = self._analyze_table_context(round_state)
        
        # MELHORIA #2: Verificação explícita de raise disponível
        if not self.sizing_calculator.is_raise_available(valid_actions):
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
        
        # Calcula probabilidade de raise no blefe baseado em número de jogadores
        if context['active_players'] <= 2:
            raise_prob = self.config.bluff_raise_prob_few_players
        else:
            raise_prob = self.config.bluff_raise_prob_many_players
        
        if random.random() < raise_prob:
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            
            # Atualiza stack interno antes de calcular sizing (MELHORIA #4)
            my_stack = self._get_my_stack(round_state)
            self.current_stack = my_stack
            
            # Usa módulo de sizing dedicado (MELHORIA #11)
            # Blefes usam sizing "small" (mão fraca = hand_strength=0)
            amount = self.sizing_calculator.calculate_bet_size(
                min_amount, max_amount, round_state, 
                hand_strength=0,  # Mão fraca para blefe
                my_stack=my_stack,
                strong_hand_threshold=self.config.strong_hand_threshold,
                raise_threshold=self.config.raise_threshold
            )
            return raise_action['action'], amount
        else:
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
    
    def _normal_action(self, valid_actions, hand_strength, round_state,
                       current_actions: Optional[CurrentActions] = None, 
                       bluff_analysis: Optional[BluffAnalysis] = None,
                       metrics: Optional[dict] = None):
        """
        Ação normal baseada em config.
        
        SEPARAÇÃO EXPLÍCITA: Decisão (fold/call/raise) é calculada ANTES do sizing.
        Sizing só é calculado se decisão for RAISE.
        """
        
        # ============================================================
        # FASE 1: DECISÃO (fold/call/raise) - SEM CALCULAR SIZING
        # ============================================================
        
        # 1. Verifica detecção de blefe
        if bluff_analysis and bluff_analysis.should_call_bluff:
            if hand_strength >= self.config.bluff_detection_threshold:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # 2. Calcula threshold base (fold_threshold_base + ajustes por raises)
        fold_threshold = self.config.fold_threshold_base
        if current_actions:
            if current_actions.has_raises:
                fold_threshold += (
                    self.config.raise_threshold_adjustment_base +
                    (current_actions.raise_count * self.config.raise_threshold_adjustment_per_raise)
                )
            elif current_actions.last_action == 'raise':
                fold_threshold += self.config.raise_threshold_adjustment_base
        
        # MELHORIA: Ajusta threshold por posição na mesa
        position = metrics.get('position', 'middle') if metrics else 'middle'
        fold_threshold = self._adjust_for_position(fold_threshold, position)
        
        # 3. MELHORIA SIMPLIFICADA: Ajusta threshold por risco e multiway (sistema simplificado)
        fold_threshold = self._adjust_threshold_for_risk_and_multiway_simple(
            fold_threshold, round_state, valid_actions
        )
        
        # 4. Considera pot odds (já existente)
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        call_amount = valid_actions[1]['amount'] if len(valid_actions) > 1 else 0
        
        if call_amount > 0:
            pot_odds_ratio = pot_size / call_amount if call_amount > 0 else 0
            if pot_odds_ratio > 5.0:
                fold_threshold = max(fold_threshold - 5, self.config.fold_threshold_base - 10)
            elif pot_odds_ratio > 3.0:
                fold_threshold = max(fold_threshold - 3, self.config.fold_threshold_base - 8)
        
        # 5. Considera análise de blefe (módulo separado, não misturado)
        # (já considerado no passo 1)
        
        # 6. Decide ação: FOLD / CALL / RAISE (SEM CALCULAR SIZING)
        
        # 6.1. Mão muito fraca: FOLD
        if hand_strength < fold_threshold:
            fold_action = valid_actions[0]
            return fold_action['action'], fold_action['amount']
        
        # MELHORIA #2: Verificação explícita de raise disponível
        is_raise_available = self.sizing_calculator.is_raise_available(valid_actions)
        
        # 6.2. Mão muito forte: RAISE (sizing será calculado depois)
        if hand_strength >= self.config.strong_hand_threshold:
            if is_raise_available:
                raise_action = valid_actions[2]
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                
                # Atualiza stack interno antes de calcular sizing (MELHORIA #4)
                my_stack = self._get_my_stack(round_state)
                self.current_stack = my_stack
                
                # FASE 2: Calcula sizing apenas se decisão for RAISE (MELHORIA #11)
                amount = self.sizing_calculator.calculate_bet_size(
                    min_amount, max_amount, round_state, hand_strength,
                    my_stack=my_stack,
                    strong_hand_threshold=self.config.strong_hand_threshold,
                    raise_threshold=self.config.raise_threshold
                )
                return raise_action['action'], amount
        
        # 6.3. Campo passivo: pode fazer raise com mão média
        if current_actions and current_actions.is_passive:
            passive_score = current_actions.passive_opportunity_score
            if (hand_strength >= self.config.passive_raise_threshold and
                passive_score > self.config.passive_raise_score_threshold and
                is_raise_available):
                # FASE 2: Calcula sizing apenas se decisão for RAISE
                raise_action = valid_actions[2]
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                
                # Atualiza stack interno antes de calcular sizing (MELHORIA #4)
                my_stack = self._get_my_stack(round_state)
                self.current_stack = my_stack
                
                amount = self.sizing_calculator.calculate_bet_size(
                    min_amount, max_amount, round_state, hand_strength,
                    my_stack=my_stack,
                    strong_hand_threshold=self.config.strong_hand_threshold,
                    raise_threshold=self.config.raise_threshold
                )
                return raise_action['action'], amount
        
        # 6.4. Mão forte: decide call ou raise baseado em agressão
        adjusted_aggression = self.aggression_level
        
        # Reduz agressão se muitos raises
        if current_actions and current_actions.raise_count >= 2:
            adjusted_aggression *= self.config.raise_count_aggression_reduction
        
        # Aumenta agressão se campo passivo
        if current_actions and current_actions.is_passive:
            passive_score = current_actions.passive_opportunity_score
            adjusted_aggression = min(
                0.95,
                adjusted_aggression + (passive_score * self.config.passive_aggression_boost)
            )
        
        # Compara força da mão com threshold ajustado
        if hand_strength >= fold_threshold:
            # Decide raise se agressão alta
            if adjusted_aggression > self.config.default_aggression:
                if is_raise_available:
                    # FASE 2: Calcula sizing apenas se decisão for RAISE
                    raise_action = valid_actions[2]
                    min_amount = raise_action['amount']['min']
                    max_amount = raise_action['amount']['max']
                    
                    # Atualiza stack interno antes de calcular sizing (MELHORIA #4)
                    my_stack = self._get_my_stack(round_state)
                    self.current_stack = my_stack
                    
                    amount = self.sizing_calculator.calculate_bet_size(
                        min_amount, max_amount, round_state, hand_strength,
                        my_stack=my_stack,
                        strong_hand_threshold=self.config.strong_hand_threshold,
                        raise_threshold=self.config.raise_threshold
                    )
                    return raise_action['action'], amount
            
            # Senão, CALL
            call_action = valid_actions[1]
            return call_action['action'], call_action['amount']
        
        # 6.5. Hook para lógica especial de bot: força raise em certas condições
        # Método virtual que pode ser sobrescrito por subclasses
        if self._should_force_raise(hand_strength, fold_threshold, round_state):
            if is_raise_available:
                # FASE 2: Calcula sizing apenas se decisão for RAISE
                raise_action = valid_actions[2]
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                
                # Atualiza stack interno antes de calcular sizing (MELHORIA #4)
                my_stack = self._get_my_stack(round_state)
                self.current_stack = my_stack
                
                amount = self.sizing_calculator.calculate_bet_size(
                    min_amount, max_amount, round_state, hand_strength,
                    my_stack=my_stack,
                    strong_hand_threshold=self.config.strong_hand_threshold,
                    raise_threshold=self.config.raise_threshold
                )
                return raise_action['action'], amount
        
        # 6.6. Mão média: CALL
        call_action = valid_actions[1]
        return call_action['action'], call_action['amount']
    
    def _should_force_raise(self, hand_strength: int, fold_threshold: int, round_state) -> bool:
        """
        Hook virtual: determina se deve forçar raise mesmo com mão média.
        
        Método que pode ser sobrescrito por subclasses para implementar
        lógica especial de decisão (ex: bot agressivo sempre tenta raise).
        
        Args:
            hand_strength: Força da mão atual
            fold_threshold: Threshold atual para fold
            round_state: Estado do round
            
        Returns:
            bool: True se deve forçar raise, False caso contrário
        """
        # Implementação padrão: não força raise
        return False
    
    def _evaluate_hand_strength(self, hole_card, round_state=None):
        """Avalia força usando utilitário compartilhado"""
        from utils.hand_utils import evaluate_hand_strength
        community_cards = round_state.get('community_card', []) if round_state else None
        return evaluate_hand_strength(hole_card, community_cards)
    
    # ============================================================
    # Sistema de Decisão e Bet Sizing Contextual
    # ============================================================
    
    def _get_my_stack(self, round_state):
        """Retorna stack atual do bot"""
        if hasattr(self, 'uuid') and self.uuid:
            for seat in round_state.get('seats', []):
                if seat.get('uuid') == self.uuid:
                    return seat.get('stack', 1000)
        return 1000  # Fallback
    
    def _calculate_spr(self, round_state):
        """
        Calcula Stack-to-Pot Ratio (SPR).
        
        SPR = stack_efetivo / pote_atual
        
        SPR é fundamental no poker:
        - SPR baixo (< 3): Situação de all-in, decisões binárias
        - SPR médio (3-10): Jogo post-flop normal
        - SPR alto (> 10): Muito espaço para manobra
        
        Returns:
            float: SPR atual
        """
        my_stack = self._get_my_stack(round_state)
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        return self.sizing_calculator.calculate_spr(my_stack, pot_size)
    
    def _calculate_risk_index(self, round_state, valid_actions):
        """
        Calcula índice de risco baseado em stack efetivo e pote.
        
        Risk Index representa o impacto da aposta:
        - % do stack efetivo que precisa pagar (peso 70%)
        - % do pote que precisa pagar (peso 30%)
        
        Returns:
            float: Índice de risco entre 0.0 (baixo) e 2.0+ (muito alto)
        """
        my_stack = self._get_my_stack(round_state)
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        
        # Obtém call_amount
        call_amount = 0
        if valid_actions and len(valid_actions) > 1:
            call_action = valid_actions[1]
            call_amount = call_action.get('amount', 0)
        
        if call_amount == 0 or my_stack == 0 or pot_size == 0:
            return 0.0  # Sem risco se não há aposta
        
        # Calcula razões
        stack_ratio = call_amount / my_stack if my_stack > 0 else 0
        pot_ratio = call_amount / pot_size if pot_size > 0 else 0
        
        # Risk index unificado (contínuo e previsível)
        risk = (stack_ratio * 0.7) + (pot_ratio * 0.3)
        
        return risk
    
    def _count_active_players(self, round_state):
        """
        Conta jogadores ativos no pote (multiway).
        
        Returns:
            int: Número de jogadores ativos (mínimo 2)
        """
        active_count = 0
        for seat in round_state.get('seats', []):
            if seat.get('stack', 0) > 0:
                active_count += 1
        return max(2, active_count)  # Mínimo 2 (heads-up)
    
    def _get_risk_sensitivity(self):
        """
        Retorna sensibilidade ao risco baseada na personalidade.
        
        Método virtual que pode ser sobrescrito por subclasses para personalizar
        sensibilidade ao risco. Implementação padrão retorna 1.0 (balanced).
        
        Herdabilidade: personalidade afeta apenas sensibilidade, nunca regras base.
        
        Returns:
            float: Multiplicador de sensibilidade (0.7 a 1.5)
        """
        # Implementação padrão: balanced
        return 1.0
    
    def _adjust_threshold_for_risk_and_multiway_simple(self, fold_threshold, round_state, valid_actions):
        """
        MELHORIA SIMPLIFICADA: Ajusta threshold de forma mais simples e previsível.
        
        Sistema simplificado com snapshot único ao invés de múltiplos ajustes incrementais:
        - Calcula % do stack uma vez
        - Aplica ajuste único baseado em 3 níveis claros
        - Multiway: ajuste simples e direto
        
        Args:
            fold_threshold: Threshold atual para fold
            round_state: Estado do round
            valid_actions: Ações válidas (para obter call_amount)
        
        Returns:
            int: Threshold ajustado para fold
        """
        my_stack = self._get_my_stack(round_state)
        
        # Obtém call_amount
        call_amount = 0
        if valid_actions and len(valid_actions) > 1:
            call_action = valid_actions[1]
            call_amount = call_action.get('amount', 0)
        
        if call_amount == 0 or my_stack == 0:
            # Sem aposta: retorna threshold original
            return fold_threshold
        
        # Calcula % do stack (snapshot único)
        stack_ratio = call_amount / my_stack
        
        # Sensibilidade por personalidade
        sensitivity = self._get_risk_sensitivity()
        
        # SISTEMA SIMPLIFICADO: 3 níveis claros
        # Baixo risco (< 10%): pode jogar mais mãos
        # Médio risco (10-30%): ajuste mínimo
        # Alto risco (> 30%): precisa de mão mais forte
        if stack_ratio < 0.10:
            # Baixo risco: reduz threshold em 2 pontos
            threshold_adjustment = -2
        elif stack_ratio < 0.30:
            # Médio risco: ajuste mínimo (+1 ponto)
            threshold_adjustment = 1
        else:
            # Alto risco: aumenta threshold em 4 pontos
            threshold_adjustment = 4
        
        # Aplica sensibilidade de personalidade
        threshold_adjustment = int(threshold_adjustment * sensitivity)
        
        # Ajuste multiway: simples e direto
        active_players = self._count_active_players(round_state)
        if active_players > 2 and stack_ratio >= 0.10:
            # Multiway com aposta média/alta: +1 ponto por jogador extra
            multiway_adjustment = (active_players - 2) * 1
            threshold_adjustment += multiway_adjustment
        
        # Aplica ajuste
        adjusted_threshold = fold_threshold + threshold_adjustment
        
        # Limites de segurança (mantém consistência)
        max_threshold = self.config.fold_threshold_base + 15  # Reduzido de 25
        min_threshold = max(5, self.config.fold_threshold_base - 5)
        
        return max(min_threshold, min(adjusted_threshold, max_threshold))
    
    
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

