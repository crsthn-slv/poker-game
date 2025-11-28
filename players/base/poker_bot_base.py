"""
Classe base para TODOS os bots.
Contém TODA a lógica compartilhada.
Subclasses apenas injetam configuração.
"""
from abc import ABC
import random
import os
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

    return _RANDOM_SEED

# Debug mode global
_DEBUG_MODE = False

def set_debug_mode(enabled: bool):
    """Habilita/desabilita modo debug global."""
    global _DEBUG_MODE
    _DEBUG_MODE = enabled

def get_debug_mode() -> bool:
    """Retorna estado do modo debug."""
    return _DEBUG_MODE


class PokerBotBase(BasePokerPlayer, ABC):
    """
    Classe base para TODOS os bots.
    Contém TODA a lógica compartilhada.
    Subclasses apenas injetam configuração.
    """
    
    @property
    def debug_mode(self) -> bool:
        """Retorna se modo debug está ativo."""
        return _DEBUG_MODE
    
    def _log_debug(self, message: str):
        """Helper para logar mensagens de debug se o modo estiver ativo."""
        if self.debug_mode:
            print(f"[DEBUG] [{self.config.name}] {message}")

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
        self.position = "Unknown" # Posição na mesa
        
        # NOVO: Estado interno para round count
        self.current_round_count = 0
        
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
        Define UUID do bot conforme atribuído pelo PyPokerEngine.
        
        Mantemos o _fixed_uuid para persistência de memória, mas usamos
        o uuid do engine para identificar o bot no estado do jogo.
        """
        if self._is_debug_mode():
            print(f"[DEBUG] set_uuid called for {self.config.name}: {uuid}")
        self.uuid = uuid
    
    def _load_parameters_from_memory(self):
        """Carrega parâmetros globais da memória."""
        # Usa parâmetros globais
        self.bluff_probability = self.memory.get('bluff_probability', self.config.default_bluff)
        self.aggression_level = self.memory.get('aggression_level', self.config.default_aggression)
        self.tightness_threshold = self.memory.get('tightness_threshold', self.config.default_tightness)
    
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

    def _determine_position(self, round_state):
        """
        Determina a posição do bot na mesa.
        
        Posições (em ordem de ação pré-flop):
        - SB (Small Blind)
        - BB (Big Blind)
        - UTG (Under the Gun - primeiro a falar)
        - MP (Middle Position)
        - CO (Cutoff)
        - BTN (Button - Dealer)
        """
        try:
            my_uuid = self.uuid
            dealer_btn = round_state['dealer_btn']
            seats = round_state['seats']
            active_players = [s for s in seats if s['state'] == 'participating']
            num_players = len(active_players)
            
            # Encontra índice do dealer e do bot na lista de ativos
            # Nota: seats é a lista completa, precisamos filtrar apenas os ativos para determinar ordem relativa
            
            # Mapeia uuid para índice na lista de ativos
            my_index = -1
            dealer_index = -1
            
            for i, player in enumerate(active_players):
                if player['uuid'] == my_uuid:
                    my_index = i
                
                # O dealer_btn é o índice na lista COMPLETA de seats
                # Precisamos achar quem é o dealer na lista de ATIVOS
                # O dealer real é seats[dealer_btn]
                dealer_uuid = seats[dealer_btn]['uuid']
                if player['uuid'] == dealer_uuid:
                    dealer_index = i
            
            # Fallback: se não achou por UUID, tenta por nome
            if my_index == -1:
                my_name = self.config.name
                for i, player in enumerate(active_players):
                    if player['name'] == my_name:
                        my_index = i
                        # Atualiza UUID se encontrou por nome
                        if self.uuid != player['uuid']:
                            self._log_debug(f"UUID Mismatch fixed by Name: {self.uuid} -> {player['uuid']}")
                            self.uuid = player['uuid']
                        break

            if my_index == -1 or dealer_index == -1:
                if self.debug_mode:
                    active_uuids = [p['uuid'] for p in active_players]
                    active_names = [p['name'] for p in active_players]
                    dealer_uuid = seats[dealer_btn]['uuid']
                    self._log_debug(f"Position Unknown Debug:")
                    self._log_debug(f"  My UUID: {my_uuid} | My Name: {self.config.name}")
                    self._log_debug(f"  Dealer UUID: {dealer_uuid} (Index {dealer_btn})")
                    self._log_debug(f"  Active UUIDs: {active_uuids}")
                    self._log_debug(f"  Active Names: {active_names}")
                    self._log_debug(f"  My Index: {my_index}, Dealer Index: {dealer_index}")
                return "Unknown"
                
            # Calcula distância do dealer (sentido horário)
            # 0 = Dealer (BTN)
            # 1 = SB
            # 2 = BB
            # 3 = UTG
            # ...
            distance_from_dealer = (my_index - dealer_index) % num_players
            
            if num_players == 2:
                # Heads-up: Dealer é SB (age primeiro pré-flop), Outro é BB
                if distance_from_dealer == 0:
                    return "SB" # Dealer age como SB no HU
                return "BB"
            
            if distance_from_dealer == 0:
                return "BTN"
            elif distance_from_dealer == 1:
                return "SB"
            elif distance_from_dealer == 2:
                return "BB"
            elif distance_from_dealer == 3:
                return "UTG"
            elif distance_from_dealer == num_players - 1:
                return "CO" # Cutoff (antes do botão)
            else:
                return "MP" # Middle Position
                
        except Exception as e:
            self._log_debug(f"Error determining position: {e}")
            return "Unknown"
        
        if my_index == -1 or dealer_index == -1:
            if self.debug_mode:
                active_uuids = [p['uuid'] for p in active_players]
                dealer_uuid = seats[dealer_btn]['uuid']
                self._log_debug(f"Position Unknown Debug:")
                self._log_debug(f"  My UUID: {my_uuid}")
                self._log_debug(f"  Dealer UUID: {dealer_uuid} (Index {dealer_btn})")
                self._log_debug(f"  Active UUIDs: {active_uuids}")
                self._log_debug(f"  My Index: {my_index}, Dealer Index: {dealer_index}")
            return "Unknown"
    
    def declare_action(self, valid_actions, hole_card, round_state):
        """
        Lógica UNIVERSAL de decisão.
        ZERO lógica específica de bot aqui.
        """
        # MELHORIA #5: Extrair partes críticas de declare_action
        # 1. Garante UUID e identifica oponentes
        self._ensure_uuid_and_identify_opponents(round_state)
        
        # 1.1 Determina Posição
        self.position = self._determine_position(round_state)
        
        # 2. Coleta métricas e contexto
        metrics = self._collect_decision_metrics(hole_card, round_state)
        
        # 3. Atualiza estado interno (stack e SPR) - MELHORIA #4
        self._update_internal_state(round_state)
        
        # 4. Decide ação
        action, amount = self._make_decision(
            valid_actions, round_state, metrics
        )
        
        # 5. Debug: mostra cartas e decisão
        self._debug_show_cards_and_decision(hole_card, round_state, action, amount, metrics)
        
        # 6. Registra ação
        self._record_action(action, amount, metrics, round_state)
        
        self._log_debug(f"DECISION: {action.upper()} amount={amount}")
        self._log_debug("-" * 40)
        
        return action, amount
    
    def _ensure_uuid_and_identify_opponents(self, round_state):
        """MELHORIA #5: Garante UUID e identifica oponentes."""
        # NOTA: Removemos a sobrescrita de self.uuid com self._fixed_uuid
        # O self.uuid deve ser o fornecido pelo engine (via set_uuid)
        # para que o bot possa ser encontrado na lista de seats.
        
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
    
    def _collect_decision_metrics(self, hole_card, round_state):
        """MELHORIA #5: Coleta métricas e contexto para decisão."""
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
        
        # Atualiza valores da memória (usa parâmetros globais)
        self._load_parameters_from_memory()
        
        if self.debug_mode:
            hole_card_str = str(hole_card) if hole_card else "None"
            
            self._log_debug(f"START TURN - {round_state.get('street', 'preflop').upper()}")
            self._log_debug(f"Cards: {hole_card_str} | Pos: {self.position} | Stack: {self.current_stack}")
            hand_str = f"{hand_strength:.1f}" if hand_strength is not None else "N/A"
            spr_str = f"{self.current_spr:.2f}" if self.current_spr is not None else "N/A"
            self._log_debug(f"Hand Strength: {hand_str} | SPR: {spr_str}")

        return {
            'current_actions': current_actions,
            'hand_strength': hand_strength,
            'bluff_analysis': bluff_analysis,
            'hole_card': hole_card
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
        
        if should_bluff:
            self._log_debug("STRATEGY: BLUFFING")
        else:
            self._log_debug("STRATEGY: NORMAL PLAY")

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
            # "Panic Rule": Se houver 3 ou mais raises (3-bet+), NUNCA blefe
            if current_actions.raise_count >= 3:
                self._log_debug(f"Bluff Rejected: Panic Rule (Raises={current_actions.raise_count})")
                return False
            if current_actions.raise_count >= (2 * raise_sensitivity):
                self._log_debug(f"Bluff Rejected: High Sensitivity (Raises={current_actions.raise_count})")
                return False
        
        # MELHORIA: Não blefa se blefou muito recentemente (evita padrão previsível)
        if len(self.recent_bluffs) >= 2:
            # Se blefou nas últimas 2 vezes, reduz chance de blefe
            recent_bluff_count = sum(1 for b in self.recent_bluffs[-2:] if b is not None)
            if recent_bluff_count >= 2:
                # Reduz probabilidade em 50% se blefou muito recentemente
                adjusted_bluff_prob = self.bluff_probability * 0.5
                roll = random.random()
                success = roll < adjusted_bluff_prob
                self._log_debug(f"Bluff Check (Recent Penalty): Prob={adjusted_bluff_prob:.2f} Roll={roll:.2f} -> {success}")
                return success
        
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
        
        # NOVO: Ajuste baseado em posição
        position_bluff_adjustment = 0.0
        if self.position in ["BTN", "CO"]:
            # Posição tardia: aumenta probabilidade de blefe
            position_bluff_adjustment = self.config.position_bluff_late_bonus
        elif self.position in ["UTG", "MP"]:
            # Posição inicial: reduz probabilidade de blefe
            position_bluff_adjustment = -self.config.position_bluff_early_penalty
        
        adjusted_prob += position_bluff_adjustment
        
        # Limita entre 0 e 1
        adjusted_prob = min(1.0, max(0.0, adjusted_prob))
        
        roll = random.random()
        success = roll < adjusted_prob
        
        if position_bluff_adjustment != 0 and self.debug_mode:
            self._log_debug(f"Bluff Check: Base={self.bluff_probability:.2f} StreetMult={street_multiplier:.1f} PosAdj={position_bluff_adjustment:+.2f} FinalProb={adjusted_prob:.2f} Roll={roll:.2f} -> {success}")
        else:
            self._log_debug(f"Bluff Check: Base={self.bluff_probability:.2f} StreetMult={street_multiplier:.1f} FinalProb={adjusted_prob:.2f} Roll={roll:.2f} -> {success}")
        return success
    
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
            round_count = getattr(self, 'current_round_count', 0)
            amount = self.sizing_calculator.calculate_bet_size(
                min_amount, max_amount, round_state, 
                hand_strength=0,  # Mão fraca para blefe
                my_stack=my_stack,
                strong_hand_threshold=self.config.strong_hand_threshold,
                raise_threshold=self.config.raise_threshold,
                round_count=round_count
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
        
        CORREÇÃO CRÍTICA: Diferencia métricas Preflop (Equity 0-100, Maior é Melhor)
        de Postflop (PokerKit Score 0-7462, Menor é Melhor).
        """
        street = round_state.get('street', 'preflop')
        is_preflop = (street == 'preflop')
        
        # ============================================================
        # FASE 1: DECISÃO (fold/call/raise) - SEM CALCULAR SIZING
        # ============================================================
        
        # 1. Verifica detecção de blefe
        if bluff_analysis and bluff_analysis.should_call_bluff:
            # Nota: bluff_detection_threshold é base 0-100.
            # Se for pós-flop, precisaria converter, mas por enquanto mantemos simples
            # ou assumimos que bluff_detection só funciona bem preflop/flop cedo
            if is_preflop and hand_strength >= self.config.bluff_detection_threshold:
                call_action = valid_actions[1]
                return call_action['action'], call_action['amount']
        
        # 2. Calcula thresholds
        # PREFLOP: Higher is Better
        fold_threshold_preflop = self.config.fold_threshold_base
        
        # POSTFLOP: Lower is Better (Score)
        fold_threshold_postflop = self.config.fold_threshold_score
        
        # MELHORIA: Avalia Potencial (Draws)
        # Se tiver draw forte, melhora o score (diminui valor) para evitar fold
        potential_bonus = 0
        if not is_preflop:
            from utils.hand_utils import evaluate_hand_potential
            community_cards = round_state.get('community_card', [])
            # Fix: Retrieve hole_card from metrics
            my_hole_card = metrics.get('hole_card', []) if metrics else []
            potential_bonus = evaluate_hand_potential(my_hole_card, community_cards)
            
            if potential_bonus > 0:
                # Aplica bônus ao score (Score efetivo = Score real - Bonus)
                # Ex: High Card (6000) - Flush Draw (2000) = 4000 (Equivalente a Pair)
                # Isso faz o bot tratar o draw como uma mão feita de força média
                hand_strength -= potential_bonus
                if self.debug_mode:
                    self._log_debug(f"Potential Bonus: -{potential_bonus} (Draw) -> Effective Score: {hand_strength}")
        
        # Ajustes por Raises (Apenas Preflop por enquanto para simplificar, ou inverte lógica para postflop)
        if current_actions:
            if current_actions.has_raises:
                adjustment = (
                    self.config.raise_threshold_adjustment_base +
                    (current_actions.raise_count * self.config.raise_threshold_adjustment_per_raise)
                )
                if is_preflop:
                    fold_threshold_preflop += adjustment
                else:
                    # Postflop: precisa de mão MELHOR (score MENOR)
                    fold_threshold_postflop -= (adjustment * 200) # 200 pontos de score ~ um rank
            elif current_actions.last_action == 'raise':
                adjustment = self.config.raise_threshold_adjustment_base
                if is_preflop:
                    fold_threshold_preflop += adjustment
                else:
                    fold_threshold_postflop -= (adjustment * 200)
        
        # 3. Ajuste por número de jogadores (Preflop)
        active_players = len([
            s for s in round_state.get('seats', []) 
            if s.get('state') == 'participating'
        ])
        
        if is_preflop and active_players >= 6:
            fold_threshold_preflop += (active_players - 5) * 2
        
        # 4. Ajuste por Posição
        position_adjustment = self._get_position_adjustment()
        if is_preflop:
            fold_threshold_preflop += position_adjustment
        else:
            # Postflop: posição ajuda, aceita mão um pouco pior (score maior)
            # position_adjustment negativo = bom (BTN).
            # Se BTN (-8), queremos aceitar mão pior -> Aumentar threshold score
            fold_threshold_postflop -= (position_adjustment * 100)
            
        if self.debug_mode:
            if is_preflop:
                self._log_debug(f"Threshold Adj: Pos={position_adjustment} -> Preflop Threshold: {fold_threshold_preflop}")
            else:
                self._log_debug(f"Threshold Adj: Pos={position_adjustment} -> Postflop Threshold: {fold_threshold_postflop}")

        # 5. Pot Odds (Pós-flop)
        pot_size = round_state.get('pot', {}).get('main', {}).get('amount', 0)
        call_amount = valid_actions[1]['amount'] if len(valid_actions) > 1 else 0
        
        if not is_preflop and call_amount > 0:
            pot_odds_ratio = pot_size / call_amount
            if pot_odds_ratio > 5.0:
                # Aceita mão pior (aumenta threshold score)
                fold_threshold_postflop += 500 
                self._log_debug(f"Pot Odds (Ratio {pot_odds_ratio:.1f}): Relaxing threshold by +500")
        
        # 6. DECISÃO FINAL
        
        # 6.1 FOLD CHECK
        should_fold = False
        if is_preflop:
            # MELHORIA: Ajuste dinâmico por custo do call (Universal Fix)
            # Se call for barato (ou grátis), reduz threshold proporcionalmente.
            # Call = 0 (Check) -> Factor 0 -> Threshold 0 -> Nunca folda (Check grátis)
            # Call = SB -> Factor 0.5 -> Threshold 50% -> Joga mais solto
            # Call >= BB -> Factor 1.0 -> Threshold 100% -> Jogo normal
            
            call_amount = valid_actions[1]['amount'] if len(valid_actions) > 1 else 0
            big_blind = round_state['small_blind_amount'] * 2
            
            # Calcula custo REAL do call (subtraindo o que já colocou)
            # PyPokerEngine: call_amount é o valor TOTAL para igualar a aposta
            call_cost = call_amount
            
            if self.position == 'BB':
                call_cost -= big_blind
            elif self.position == 'SB':
                call_cost -= round_state['small_blind_amount']
            
            # Garante que não seja negativo (ex: se houve raise e já pagou mais? improvável no preflop inicial)
            call_cost = max(0, call_cost)
            
            # Evita divisão por zero se BB for 0 (improvável, mas seguro)
            if big_blind > 0:
                call_cost_factor = min(1.0, call_cost / big_blind)
            else:
                call_cost_factor = 1.0
                
            effective_threshold = fold_threshold_preflop * call_cost_factor
            
            if self.debug_mode:
                 self._log_debug(f"Preflop Calc: Base={fold_threshold_preflop} Cost={call_cost} (Amt={call_amount}) Factor={call_cost_factor:.2f} -> Eff={effective_threshold:.1f}")

            # Preflop: Se força < threshold efetivo -> Fold
            if hand_strength < effective_threshold:
                should_fold = True
                reason = f"Preflop Strength {hand_strength:.1f} < {effective_threshold:.1f} (Base {fold_threshold_preflop})"
        else:
            # Postflop: Se score > threshold -> Fold (Score alto = mão ruim)
            if hand_strength > fold_threshold_postflop:
                should_fold = True
                reason = f"Postflop Score {hand_strength:.0f} > {fold_threshold_postflop}"
        
        if should_fold:
            self._log_debug(f"Action: FOLD ({reason})")
            fold_action = valid_actions[0]
            return fold_action['action'], fold_action['amount']
            
        # 6.2 RAISE CHECK (Strong Hand)
        is_raise_available = self.sizing_calculator.is_raise_available(valid_actions)
        is_strong_hand = False
        
        if is_preflop:
            if hand_strength >= self.config.strong_hand_threshold:
                is_strong_hand = True
        else:
            # Postflop: Score < Strong Threshold (Score baixo = mão forte)
            if hand_strength <= self.config.strong_hand_threshold_score:
                is_strong_hand = True
                
        if is_strong_hand and is_raise_available:
            self.aggressive_line_started = True
            
            # Calcula Sizing
            raise_action = valid_actions[2]
            min_amount = raise_action['amount']['min']
            max_amount = raise_action['amount']['max']
            my_stack = self._get_my_stack(round_state)
            self.current_stack = my_stack
            round_count = getattr(self, 'current_round_count', 0)
            
            # Nota: Passamos hand_strength direto. O SizingCalculator precisa saber lidar?
            # O SizingCalculator usa select_sizing_category que compara com thresholds.
            # Precisamos garantir que ele use os thresholds corretos lá também.
            # Por enquanto, vamos confiar que ele usa os defaults ou passar thresholds explícitos.
            # MELHORIA: Passar thresholds corretos para o calculator
            
            strong_thresh = self.config.strong_hand_threshold if is_preflop else self.config.strong_hand_threshold_score
            raise_thresh = self.config.raise_threshold if is_preflop else self.config.raise_threshold_score
            
            # Hack: SizingCalculator espera "Higher is Better" para categorizar 'large', 'medium'.
            # Se for postflop (Lower is Better), precisamos inverter ou adaptar o calculator.
            # Para não quebrar o calculator agora, vamos fazer um "proxy" de força para o calculator se for postflop.
            # Se score baixo (bom), queremos que pareça alto (bom).
            # Score 0 (Royal) -> 100
            # Score 7462 (High Card) -> 0
            # Proxy = 100 * (1 - score/7462)
            
            calc_strength = hand_strength
            calc_strong_thresh = strong_thresh
            calc_raise_thresh = raise_thresh
            
            if not is_preflop:
                # Inverte para o calculator entender (0-100)
                calc_strength = max(0, 100 * (1 - (hand_strength / 7500)))
                # Ajusta thresholds para escala 0-100 também
                # Strong score 2000 -> 100 * (1 - 2000/7500) = 73
                calc_strong_thresh = max(0, 100 * (1 - (self.config.strong_hand_threshold_score / 7500)))
                # Raise score 3000 -> 100 * (1 - 3000/7500) = 60
                calc_raise_thresh = max(0, 100 * (1 - (self.config.raise_threshold_score / 7500)))
            
            amount = self.sizing_calculator.calculate_bet_size(
                min_amount, max_amount, round_state, calc_strength,
                my_stack=my_stack,
                strong_hand_threshold=calc_strong_thresh,
                raise_threshold=calc_raise_thresh,
                round_count=round_count
            )
            
            self._log_debug(f"Action: RAISE (Strong Hand) Strength={hand_strength} Amount={amount}")
            return raise_action['action'], amount

        # 6.3 PANIC RULE (Muitos raises)
        panic_threshold = getattr(self.config, 'raise_count_panic_threshold', 3)
        if current_actions and current_actions.raise_count >= panic_threshold:
            # Só paga se estiver perto do strong
            is_near_strong = False
            if is_preflop:
                if hand_strength >= (self.config.strong_hand_threshold - 10):
                    is_near_strong = True
            else:
                if hand_strength <= (self.config.strong_hand_threshold_score + 1000):
                    is_near_strong = True
            
            if is_near_strong:
                 call_action = valid_actions[1]
                 self._log_debug(f"PANIC CALL: Raises={current_actions.raise_count}")
                 return call_action['action'], call_action['amount']
            else:
                 fold_action = valid_actions[0]
                 self._log_debug(f"PANIC FOLD: Raises={current_actions.raise_count}")
                 return fold_action['action'], fold_action['amount']

        # 6.4 AGGRESSIVE PLAY (Mão média/boa + Agressividade)
        # Se mão é melhor que fold threshold e temos agressividade, podemos dar raise
        
        # Verifica se mão é "jogável" (já passou pelo fold check, então é)
        # Mas para raise, queremos algo melhor que apenas "não fold"
        
        can_raise_value = False
        if is_preflop:
            if hand_strength >= self.config.raise_threshold:
                can_raise_value = True
        else:
            if hand_strength <= self.config.raise_threshold_score:
                can_raise_value = True
        
        if can_raise_value and is_raise_available:
            adjusted_aggression = self.aggression_level
            if current_actions and current_actions.raise_count >= 1:
                adjusted_aggression *= 0.5 # Reduz muito agressão se já houve raise
            
            if adjusted_aggression > self.config.default_aggression:
                 # Calcula Sizing (mesma lógica de proxy)
                raise_action = valid_actions[2]
                min_amount = raise_action['amount']['min']
                max_amount = raise_action['amount']['max']
                my_stack = self._get_my_stack(round_state)
                self.current_stack = my_stack
                round_count = getattr(self, 'current_round_count', 0)
                
                calc_strength = hand_strength
                calc_strong_thresh = self.config.strong_hand_threshold if is_preflop else 73 # aprox
                calc_raise_thresh = self.config.raise_threshold if is_preflop else 60 # aprox
                
                if not is_preflop:
                    calc_strength = max(0, 100 * (1 - (hand_strength / 7500)))
                
                amount = self.sizing_calculator.calculate_bet_size(
                    min_amount, max_amount, round_state, calc_strength,
                    my_stack=my_stack,
                    strong_hand_threshold=calc_strong_thresh,
                    raise_threshold=calc_raise_thresh,
                    round_count=round_count
                )
                self._log_debug(f"Action: RAISE (Aggressive) Strength={hand_strength} Amount={amount}")
                return raise_action['action'], amount

        # 6.5 CALL (Default)
        self._log_debug(f"Action: CALL (Default)")
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
    
    def _get_position_adjustment(self) -> int:
        """
        Retorna ajuste de threshold baseado na posição na mesa.
        
        Posições tardias (BTN, CO) retornam valores negativos (joga mais mãos).
        Posições iniciais (UTG) retornam valores positivos (joga menos mãos).
        
        Returns:
            int: Ajuste a ser adicionado ao fold_threshold
        """
        if self.position == "BTN":
            return self.config.position_btn_adjustment
        elif self.position == "CO":
            return self.config.position_co_adjustment
        elif self.position == "MP":
            return self.config.position_mp_adjustment
        elif self.position == "UTG":
            return self.config.position_utg_adjustment
        elif self.position == "BB":
            return self.config.position_bb_adjustment
        elif self.position == "SB":
            return self.config.position_sb_adjustment
        else:
            # Unknown position: sem ajuste
            return 0
    
    def _evaluate_hand_strength(self, hole_card, round_state=None):
        """Avalia força usando utilitário compartilhado"""
        from utils.hand_utils import evaluate_hand_strength
        community_cards = round_state.get('community_card', []) if round_state else None
        return evaluate_hand_strength(hole_card, community_cards)
    
    def _is_debug_mode(self) -> bool:
        """Verifica se modo debug está ativado"""
        log_level = os.environ.get('POKER_PLAYER_LOG_LEVEL', 'WARNING').upper()
        return log_level == 'DEBUG'
    
    def _debug_show_cards_and_decision(self, hole_card, round_state, action, amount, metrics):
        """Mostra cartas e decisão do bot em modo debug"""
        if not self._is_debug_mode():
            return
        
        from utils.hand_utils import normalize_hole_cards
        hole_cards = normalize_hole_cards(hole_card)
        hand_strength = metrics.get('hand_strength', 0)
        street = round_state.get('street', 'preflop')
        community_cards = round_state.get('community_card', [])
        
        # Formata cartas
        cards_str = ' '.join(hole_cards) if hole_cards else 'N/A'
        community_str = ' '.join(community_cards) if community_cards else 'Nenhuma'
        
        # Formata ação
        action_str = f"{action.upper()}"
        if action == 'raise':
            action_str += f" {amount}"
        elif action == 'call':
            action_str += f" {amount}"
        
        print(f"🎴 [DEBUG] {self.config.name} | Round {self.memory.get('total_rounds', 0) + 1} | {street.upper()}")
        print(f"   Cartas: {cards_str} | Força: {hand_strength}")
        print(f"   Comunitárias: {community_str}")
        print(f"   Decisão: {action_str}")
        
        # Mostra contexto adicional
        current_actions = metrics.get('current_actions')
        if current_actions:
            if current_actions.has_raises:
                print(f"   ⚠️  Raises na mesa: {current_actions.raise_count}")
        
        bluff_analysis = metrics.get('bluff_analysis')
        if bluff_analysis and bluff_analysis.possible_bluff_probability > 0.3:
            print(f"   🎭 Possível blefe detectado: {bluff_analysis.possible_bluff_probability:.1%}")
        
        print()  # Linha em branco para separar
    
    def _debug_show_all_cards(self, round_count):
        """Mostra cartas de todos os bots em modo debug"""
        if not self._is_debug_mode():
            return
        
        from utils.cards_registry import get_all_cards
        from utils.uuid_utils import get_bot_class_uuid_from_name
        
        all_cards = get_all_cards()
        if not all_cards:
            return
        
        print(f"🎴 [DEBUG] Round {round_count} - Cartas de todos os bots:")
        
        # Tenta obter nomes dos bots pelos UUIDs
        for uuid, cards in all_cards.items():
            # Tenta encontrar nome do bot pelo UUID
            bot_name = None
            # Verifica se é o próprio bot
            if hasattr(self, 'uuid') and self.uuid == uuid:
                bot_name = self.config.name
            else:
                # Tenta mapear UUID para nome conhecido
                from utils.uuid_utils import get_all_known_bot_names
                for known_name in get_all_known_bot_names():
                    known_uuid = get_bot_class_uuid_from_name(known_name)
                    if known_uuid == uuid:
                        bot_name = known_name
                        break
            
            if not bot_name:
                bot_name = f"Bot-{uuid[:8]}"
            
            cards_str = ' '.join(cards) if cards else 'N/A'
            print(f"   {bot_name}: {cards_str}")
        print()  # Linha em branco para separar
    
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
    
    def _adjust_threshold_for_risk_simple(self, fold_threshold, round_state, valid_actions):
        """
        Ajusta threshold por risco de forma simplificada (2 níveis).
        
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
        
        # Calcula % do stack
        stack_ratio = call_amount / my_stack
        
        # Sistema simplificado: 2 níveis
        # Baixo risco (< 20%): pode jogar mais mãos
        # Alto risco (>= 20%): precisa de mão mais forte
        if stack_ratio < 0.20:
            # Baixo risco: reduz threshold em 2 pontos
            threshold_adjustment = -2
        else:
            # Alto risco: aumenta threshold em 2 pontos
            threshold_adjustment = 2
        
        # Aplica ajuste
        adjusted_threshold = fold_threshold + threshold_adjustment
        
        # Limites de segurança
        max_threshold = self.config.fold_threshold_base + 15
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
        # NOVO: Atualiza round count
        self.current_round_count = round_count
        
        if round_count % 5 == 0:
            self.memory_manager.save()
        
        # Armazena cartas no registry
        if hole_card and hasattr(self, 'uuid') and self.uuid:
            from utils.cards_registry import store_player_cards
            from utils.hand_utils import normalize_hole_cards
            hole_cards = normalize_hole_cards(hole_card)
            if hole_cards:
                # Tenta obter o nome do bot dos seats primeiro (nome do jogo, ex: "King")
                # Se não encontrar, usa o nome da configuração (ex: "CFR")
                bot_name = self.config.name
                if seats:
                    for seat in seats:
                        if isinstance(seat, dict):
                            seat_uuid = seat.get('uuid', '')
                            # Verifica se o UUID do seat corresponde ao nosso UUID fixo
                            if seat_uuid == self.uuid or seat_uuid == getattr(self, '_fixed_uuid', None):
                                seat_name = seat.get('name', '')
                                if seat_name:
                                    bot_name = seat_name
                                    break
                
                store_player_cards(self.uuid, hole_cards, bot_name)
        
        # Debug: mostra cartas de todos os bots no início do round
        self._debug_show_all_cards(round_count)
    
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
