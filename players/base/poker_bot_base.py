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
from utils.win_probability_calculator import calculate_win_probability_for_player
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
        
        # Gera UUID fixo baseado na classe - sempre determinístico
        from utils.uuid_utils import get_bot_class_uuid
        self.uuid = get_bot_class_uuid(self)
        
        # Aplica seed se configurado (MELHORIA #3)
        if _RANDOM_SEED is not None:
            random.seed(_RANDOM_SEED)
    
    def set_uuid(self, uuid):
        """
        PyPokerEngine tenta atribuir UUID variável, mas sempre sobrescrevemos com UUID fixo.
        Isso garante que o mesmo tipo de bot sempre tenha o mesmo UUID.
        """
        from utils.uuid_utils import get_bot_class_uuid
        fixed_uuid = get_bot_class_uuid(self)
        if self._is_debug_mode():
            print(f"[DEBUG] set_uuid called for {self.config.name}: PyPokerEngine={uuid} -> Fixed={fixed_uuid}")
        # SEMPRE usa UUID fixo, ignorando o UUID do engine
        self.uuid = fixed_uuid
    
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
            dealer_btn = round_state['dealer_btn']
            seats = round_state['seats']
            
            # CORREÇÃO: Primeiro encontra o bot por NOME (mais confiável que UUID)
            my_seat = None
            my_name = self.config.name
            
            for seat in seats:
                if seat.get('name') == my_name:
                    my_seat = seat
                    # Atualiza UUID se necessário (corrige mismatch)
                    seat_uuid = seat.get('uuid')
                    if seat_uuid and self.uuid != seat_uuid:
                        if self.debug_mode:
                            self._log_debug(f"UUID updated from {self.uuid} to {seat_uuid}")
                        self.uuid = seat_uuid
                    break
            
            if not my_seat:
                # Fallback: tenta por UUID
                for seat in seats:
                    if seat.get('uuid') == self.uuid:
                        my_seat = seat
                        break
            
            if not my_seat:
                if self.debug_mode:
                    self._log_debug(f"Could not find seat for {my_name} (UUID: {self.uuid})")
                return "Unknown"
            
            # Filtra apenas jogadores ativos para calcular posições relativas
            active_players = [s for s in seats if s['state'] == 'participating']
            num_active = len(active_players)
            
            if num_active == 0:
                return "Unknown"
            
            # CORREÇÃO: Encontra índices na lista de ATIVOS (não na lista completa)
            my_index = -1
            dealer_index = -1
            
            # O dealer é sempre seats[dealer_btn], mesmo se fez fold
            dealer_seat = seats[dealer_btn]
            dealer_uuid = dealer_seat.get('uuid')
            
            for i, player in enumerate(active_players):
                player_uuid = player.get('uuid')
                
                # Encontra meu índice
                if player_uuid == self.uuid or player.get('name') == my_name:
                    my_index = i
                
                # Encontra índice do dealer (se ainda estiver ativo)
                if player_uuid == dealer_uuid:
                    dealer_index = i
            
            # Se o dealer fez fold, precisa calcular a posição de forma diferente
            # Nesse caso, usamos a lista completa de seats para determinar a ordem
            if dealer_index == -1:
                # Dealer fez fold - calcula posição baseado na ordem dos seats
                # Encontra índice do dealer na lista completa
                dealer_seat_index = dealer_btn
                my_seat_index = -1
                
                for i, seat in enumerate(seats):
                    if seat.get('uuid') == self.uuid or seat.get('name') == my_name:
                        my_seat_index = i
                        break
                
                if my_seat_index == -1:
                    return "Unknown"
                
                # Calcula distância do dealer na lista completa
                total_seats = len(seats)
                distance = (my_seat_index - dealer_seat_index) % total_seats
                
                # Mapeia para posição baseado no número de jogadores ATIVOS
                if num_active == 2:
                    # Heads-up
                    if distance == 0:
                        return "SB"
                    return "BB"
                
                # Mapeia distância para posição
                if distance == 0:
                    return "BTN"
                elif distance == 1:
                    return "SB"
                elif distance == 2:
                    return "BB"
                elif distance == 3:
                    return "UTG"
                elif distance >= total_seats - 1:
                    return "CO"
                else:
                    return "MP"
            
            # Dealer ainda está ativo - usa cálculo normal
            if my_index == -1:
                if self.debug_mode:
                    self._log_debug(f"Could not find my index in active players")
                return "Unknown"
            
            # Calcula distância do dealer (sentido horário)
            distance_from_dealer = (my_index - dealer_index) % num_active
            
            if num_active == 2:
                # Heads-up: Dealer é SB (age primeiro pré-flop), Outro é BB
                if distance_from_dealer == 0:
                    return "SB"
                return "BB"
            
            if distance_from_dealer == 0:
                return "BTN"
            elif distance_from_dealer == 1:
                return "SB"
            elif distance_from_dealer == 2:
                return "BB"
            elif distance_from_dealer == 3:
                return "UTG"
            elif distance_from_dealer == num_active - 1:
                return "CO"
            else:
                return "MP"
                
        except Exception as e:
            self._log_debug(f"Error determining position: {e}")
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
        
        # 1.2 CORREÇÃO: Armazena cartas do bot no registry para showdown
        if hole_card and len(hole_card) >= 2:
            from utils.cards_registry import store_player_cards
            from utils.hand_utils import normalize_hole_cards
            from utils.uuid_utils import get_bot_class_uuid
            
            normalized_cards = normalize_hole_cards(hole_card)
            if normalized_cards:
                # Registra com UUID atual (PyPokerEngine) para uso interno (win prob)
                store_player_cards(self.uuid, normalized_cards, self.config.name)
                
                # Registra TAMBÉM com UUID fixo para o GameHistory
                fixed_uuid = get_bot_class_uuid(self)
                if fixed_uuid and fixed_uuid != self.uuid:
                    store_player_cards(fixed_uuid, normalized_cards, self.config.name)
        
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
        # UUID é sempre fixo, não precisa de mapeamento
        # Identifica oponentes
        if hasattr(self, 'uuid') and self.uuid:
            self.memory_manager.identify_opponents(round_state, self.uuid)
    
    def _calculate_equity(self, hole_card, round_state) -> float:
        """
        Calcula a equidade (probabilidade de vitória) usando simulação Monte Carlo.
        Retorna float entre 0.0 e 1.0.
        """
        # Limita simulações para performance (500 é suficiente para decisão rápida)
        # O humano usa ~2000, mas bots precisam ser mais rápidos
        NUM_SIMULATIONS = 500
        
        try:
            # UUID é sempre fixo, usa diretamente
            equity = calculate_win_probability_for_player(
                player_uuid=self.uuid,
                round_state=round_state,
                num_simulations=NUM_SIMULATIONS,
                return_confidence=False
            )
            return equity if equity is not None else 0.0
        except Exception as e:
            if self.debug_mode:
                print(f"[BOT DEBUG] Error calculating equity: {e}")
            return 0.0

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
        
        # Calcula Equity (Win Probability)
        equity = 0.0
        # Só calcula equity se tiver cartas comunitárias (pós-flop) ou se for preflop (já tem tabela)
        if round_state['street'] != 'preflop':
             equity = self._calculate_equity(hole_card, round_state)
        else:
             # Preflop: hand_strength já é equity (0-100), converte para 0-1
             equity = hand_strength / 100.0
        
        # Armazena equity atual para uso em bluff check
        self.current_equity = equity
        
        if self.debug_mode:
            hole_card_str = str(hole_card) if hole_card else "None"
            
            self._log_debug(f"START TURN - {round_state.get('street', 'preflop').upper()}")
            self._log_debug(f"Cards: {hole_card_str} | Pos: {self.position} | Stack: {self.current_stack}")
            hand_str = f"{hand_strength:.1f}" if hand_strength is not None else "N/A"
            spr_str = f"{self.current_spr:.2f}" if self.current_spr is not None else "N/A"
            self._log_debug(f"Hand Strength: {hand_str} | SPR: {spr_str}")
            print(f"[BOT DEBUG] {self.config.name} - Strength: {hand_strength}, Equity: {equity:.2f}")

        return {
            'current_actions': current_actions,
            'hand_strength': hand_strength,
            'equity': equity,
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
        - Board texture (blefes menos efetivos em boards pareados)
        - Equity mínima (nunca blefar com equity muito baixa)
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
        
        # NOVO: Ajuste baseado em board texture (pós-flop)
        board_texture_adjustment = 0.0
        if round_state and street != 'preflop':
            from utils.hand_utils import get_community_cards, analyze_board_texture
            community_cards = get_community_cards(round_state)
            
            if community_cards and len(community_cards) >= 3:
                board_texture = analyze_board_texture(community_cards)
                
                # Board pareado: blefes são MENOS efetivos
                # Todos têm pelo menos um par, então é mais difícil fazer fold
                if board_texture['has_trips']:
                    # Trips no board: reduz MUITO a probabilidade de blefe
                    board_texture_adjustment = -0.15  # -15%
                    if self.debug_mode:
                        self._log_debug(f"Board Texture: Trips detected ({board_texture['trips_rank']}) -> Bluff -15%")
                        
                elif board_texture['has_pair']:
                    # Par no board: reduz probabilidade de blefe
                    board_texture_adjustment = -0.10  # -10%
                    if self.debug_mode:
                        self._log_debug(f"Board Texture: Pair detected ({board_texture['pair_rank']}) -> Bluff -10%")
                
                # Board com muitas cartas altas: blefes são menos efetivos
                # (oponentes provavelmente conectaram)
                elif board_texture['num_high_cards'] >= 3:
                    board_texture_adjustment = -0.05  # -5%
                    if self.debug_mode:
                        self._log_debug(f"Board Texture: Many high cards ({board_texture['num_high_cards']}) -> Bluff -5%")
        
        adjusted_prob += board_texture_adjustment
        
        # NOVO: Ajuste baseado em posição (REDUZIDO para ser menos agressivo)
        position_bluff_adjustment = 0.0
        if self.position in ["BTN", "CO"]:
            # Posição tardia: aumenta probabilidade de blefe (REDUZIDO de 0.20 para 0.10)
            position_bluff_adjustment = 0.10  # Antes era self.config.position_bluff_late_bonus (0.20)
        elif self.position in ["UTG", "MP"]:
            # Posição inicial: reduz probabilidade de blefe
            position_bluff_adjustment = -self.config.position_bluff_early_penalty
        
        adjusted_prob += position_bluff_adjustment
        
        # NOVO: Ajuste baseado em número de jogadores ativos
        # Quanto mais jogadores, menos efetivo é o blefe
        if round_state:
            active_players = len([
                s for s in round_state.get('seats', []) 
                if s.get('state') == 'participating'
            ])
            if active_players >= 4:
                # 4+ jogadores: reduz blefe em 5%
                adjusted_prob -= 0.05
                if self.debug_mode:
                    self._log_debug(f"Many players ({active_players}) -> Bluff -5%")
        
        # Limita entre 0 e 1
        adjusted_prob = min(1.0, max(0.0, adjusted_prob))
        
        roll = random.random()
        success = roll < adjusted_prob
        
        # CRÍTICO: NUNCA blefar com equity muito baixa (<15%)
        # Isso evita blefes suicidas em situações sem chance de vitória
        if success and hasattr(self, 'current_equity'):
            if self.current_equity is not None and self.current_equity < 0.15:
                if self.debug_mode:
                    self._log_debug(f"Bluff REJECTED: Equity too low ({self.current_equity:.2f} < 0.15)")
                return False
        
        # Log detalhado
        if self.debug_mode:
            log_parts = [f"Base={self.bluff_probability:.2f}"]
            log_parts.append(f"StreetMult={street_multiplier:.1f}")
            if board_texture_adjustment != 0:
                log_parts.append(f"BoardAdj={board_texture_adjustment:+.2f}")
            if position_bluff_adjustment != 0:
                log_parts.append(f"PosAdj={position_bluff_adjustment:+.2f}")
            log_parts.append(f"FinalProb={adjusted_prob:.2f}")
            log_parts.append(f"Roll={roll:.2f} -> {success}")
            self._log_debug(f"Bluff Check: {' '.join(log_parts)}")
        
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
            
            # TOURNAMENT STAGE LOGIC
            stage = self._get_tournament_stage(round_state)
            
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
            
            # SAFETY CAP: In DEEP stage, never go All-In on a bluff
            # unless the pot is already huge (SPR < 1)
            if stage == "DEEP":
                pot_size = context['pot_size']
                if amount >= my_stack and self.current_spr > 1.0:
                    # Cap raise to Pot Size or 1.5x Pot, but keep it valid
                    safe_amount = int(pot_size * 1.5)
                    amount = max(min_amount, min(safe_amount, max_amount))
                    # If safe amount is still all-in (short stack logic applied to deep?), clamp it
                    if amount >= my_stack:
                         # If we can't make a safe raise, just call
                         call_action = valid_actions[1]
                         self._log_debug(f"Bluff Raise rejected (DEEP STAGE SAFETY): {amount} is All-In")
                         return call_action['action'], call_action['amount']
                    
                    self._log_debug(f"Bluff Raise Capped (DEEP STAGE): {amount}")
            
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
        raise_count = 0
        if current_actions:
            raise_count = current_actions.raise_count
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

        # 4. Ajuste por Custo do Call (Pot Odds Implícito) - PREFLOP
        # Se o call for caro (muitos BBs), precisamos de uma mão muito melhor
        cost_penalty = 0.0
        if is_preflop:
            call_action = valid_actions[1] if len(valid_actions) > 1 else {'amount': 0}
            call_amount = call_action.get('amount', 0)
            bb = round_state['small_blind_amount'] * 2
            
            if bb > 0 and call_amount > 0:
                call_cost_bb = call_amount / bb
                
                # Se custar mais que 1 BB (ou seja, houve raise)
                if call_cost_bb > 1.0:
                    # Penalidade: 5 pontos de threshold por BB extra
                    # Ex: Raise para 3BB (custo 3) -> (3-1)*5 = +10 no threshold
                    # Ex: Raise para 5BB (custo 5) -> (5-1)*5 = +20 no threshold
                    cost_penalty = (call_cost_bb - 1.0) * 5.0
                    
                    # Cap na penalidade para não quebrar o jogo (max +40)
                    cost_penalty = min(40.0, cost_penalty)
                    
                    fold_threshold_preflop += cost_penalty
                    
                    if self.debug_mode:
                        self._log_debug(f"High Call Cost ({call_cost_bb:.1f} BB) -> Threshold +{cost_penalty:.1f}")
        
        # NOVO: Ajuste por Board Texture (Pós-flop)
        # Quando o board tem pares/trips, TODOS os jogadores têm pelo menos essa mão
        # Portanto, precisamos de uma mão MELHOR para continuar
        board_texture_threshold_adjustment = 0
        if not is_preflop:
            from utils.hand_utils import get_community_cards, analyze_board_texture
            community_cards = get_community_cards(round_state)
            
            if community_cards and len(community_cards) >= 3:
                board_texture = analyze_board_texture(community_cards)
                
                # Board com trips: TODOS têm trips, só kickers importam
                # Precisamos de mão MUITO melhor (score MENOR)
                if board_texture['has_trips']:
                    # Reduz threshold em 1500 pontos (exige mão ~1 rank melhor)
                    board_texture_threshold_adjustment = -1500
                    if self.debug_mode:
                        self._log_debug(f"Board Texture: Trips ({board_texture['trips_rank']}) -> Threshold -1500 (need better hand)")
                
                # Board com par: TODOS têm pelo menos um par
                # Precisamos de mão melhor (score MENOR)
                elif board_texture['has_pair']:
                    # Reduz threshold em 800 pontos
                    board_texture_threshold_adjustment = -800
                    if self.debug_mode:
                        self._log_debug(f"Board Texture: Pair ({board_texture['pair_rank']}) -> Threshold -800 (need better hand)")
                
                # Aplica ajuste ao threshold pós-flop
                fold_threshold_postflop += board_texture_threshold_adjustment
        
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
        call_action_data = valid_actions[1] if len(valid_actions) > 1 else {'action': 'call', 'amount': 0}
        call_amount = call_action_data['amount']
        
        pot_odds = 0.0
        if not is_preflop and call_amount > 0:
            if call_amount > 0:
                pot_odds = pot_size / call_amount
            
            if pot_odds > 5.0:
                # Boas odds: Aceita mão pior (aumenta threshold score)
                fold_threshold_postflop += 500 
                self._log_debug(f"Good Pot Odds (Ratio {pot_odds:.1f}): Relaxing threshold by +500")
            elif pot_odds < 2.0:
                # Más odds: Exige mão melhor (diminui threshold score)
                # Se tiver que pagar muito para ganhar pouco, só paga com mão feita
                fold_threshold_postflop -= 500
                self._log_debug(f"Bad Pot Odds (Ratio {pot_odds:.1f}): Tightening threshold by -500")
        
        # 6. DECISION LOGIC
        # ============================================================
        
        # Extrai equity das métricas
        equity = metrics.get('equity', 0.0)
        
        # 6.1 FOLD CHECK
        should_fold = False
        fold_reason = ""
        
        if is_preflop:
            # Preflop logic (unchanged for now, relies on hand_strength/equity table)
            # Calculate effective threshold considering position
            effective_threshold = fold_threshold_preflop + position_adjustment
            
            # Adjust for raises (tighten up if raised)
            if raise_count > 0:
                effective_threshold += (self.config.raise_threshold_adjustment_base + 
                                      (raise_count - 1) * self.config.raise_threshold_adjustment_per_raise)
            
            # Call amount relative to big blind (pot odds proxy)
            bb = round_state['small_blind_amount'] * 2
            call_cost_bb = call_amount / bb if bb > 0 else 0
            
            # If it's cheap to call (< 1 BB) and we have decent equity, loosen threshold
            if call_cost_bb < 1.0:
                effective_threshold *= 0.8
            
            if hand_strength < effective_threshold:
                should_fold = True
                fold_reason = f"Preflop Strength {hand_strength:.1f} < {effective_threshold:.1f}"

        else:
            # Postflop: Score based (Lower is Better)
            # But now with EQUITY OVERRIDE!
            
            # Base check: Score > Threshold -> Fold candidate
            if call_amount > 0 and hand_strength > fold_threshold_postflop:
                should_fold = True
                fold_reason = f"Score {hand_strength} > {fold_threshold_postflop}"
                
                # EQUITY OVERRIDE: If we have good equity, DON'T FOLD!
                # This handles Draws (Flush/Straight) and Live Cards
                if equity >= self.config.min_equity_call:
                    should_fold = False
                    if self.debug_mode:
                        print(f"[BOT STRATEGY] {self.config.name} SAVED by Equity! Score bad ({hand_strength}) but Equity {equity:.2f} >= {self.config.min_equity_call}")
            
            # Pot Odds Check (if we were going to fold)
            if should_fold and pot_odds > 0:
                # Basic pot odds: required equity = call / (pot + call)
                required_equity = call_amount / (round_state['pot']['main']['amount'] + call_amount)
                
                # If our equity is better than pot odds, CALL
                if equity > required_equity:
                    should_fold = False
                    fold_reason = ""
                    if self.debug_mode:
                        print(f"[BOT STRATEGY] {self.config.name} SAVED by Pot Odds! Equity {equity:.2f} > Required {required_equity:.2f}")

        # Execute Fold if still true
        if should_fold and call_amount > 0:
            self._log_debug(f"Action: FOLD ({fold_reason})")
            return 'fold', 0
            
        # 6.2 RAISE CHECK
        is_raise_available = self.sizing_calculator.is_raise_available(valid_actions)
        is_strong_hand = False
        
        if is_preflop:
            # Aplica penalidade de custo também para raise/strong thresholds
            # Se custa caro ver o flop, a barra para "mão forte" sobe
            adjusted_strong_threshold = self.config.strong_hand_threshold + cost_penalty
            
            if hand_strength >= adjusted_strong_threshold:
                is_strong_hand = True
                if self.debug_mode and cost_penalty > 0:
                     self._log_debug(f"Strong Hand Check: {hand_strength} >= {adjusted_strong_threshold} (Adj +{cost_penalty:.1f})")
        else:
            # Postflop: Score < Strong Threshold (Score baixo = mão forte)
            if hand_strength <= self.config.strong_hand_threshold_score:
                is_strong_hand = True
            # EQUITY STRONG: If equity is massive (e.g. > 75%), it's a strong hand
            elif equity >= (self.config.strong_equity_raise + 0.15):
                is_strong_hand = True
                if self.debug_mode:
                    self._log_debug(f"Equity Strong Hand: {equity:.2f}")
                
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
                # 6.3 PANIC RULE (Muitos raises)
        panic_threshold = getattr(self.config, 'raise_count_panic_threshold', 3)
        if current_actions and current_actions.raise_count >= panic_threshold:
            # Só paga se estiver perto do strong
            is_near_strong = False
            if is_preflop:
                # REMOVIDO BUFFER: Antes era (strong - 10), agora é strong puro
                # Ex: Precisa de 50+ (QQ+), não 40+ (88+)
                if hand_strength >= self.config.strong_hand_threshold:
                    is_near_strong = True
                    if self.debug_mode:
                         self._log_debug(f"Panic Check Preflop: {hand_strength} >= {self.config.strong_hand_threshold} -> PASS")
                elif self.debug_mode:
                     self._log_debug(f"Panic Check Preflop: {hand_strength} < {self.config.strong_hand_threshold} -> FAIL")
            else:
                # REMOVIDO BUFFER: Antes era (strong + 1000), agora é strong puro
                # Ex: Precisa de Score <= 2800 (Two Pair+), não <= 3800 (One Pair)
                if hand_strength <= self.config.strong_hand_threshold_score:
                    is_near_strong = True
                    if self.debug_mode:
                         self._log_debug(f"Panic Check Postflop: {hand_strength} <= {self.config.strong_hand_threshold_score} -> PASS")
                elif self.debug_mode:
                     self._log_debug(f"Panic Check Postflop: {hand_strength} > {self.config.strong_hand_threshold_score} -> FAIL")
            
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
            # Aplica penalidade de custo também para raise threshold
            adjusted_raise_threshold = self.config.raise_threshold + cost_penalty
            if hand_strength >= adjusted_raise_threshold:
                can_raise_value = True
        else:
            if hand_strength <= self.config.raise_threshold_score:
                can_raise_value = True
            # EQUITY RAISE: If we have high equity, we can raise for value
            elif equity >= self.config.strong_equity_raise:
                can_raise_value = True
                if self.debug_mode:
                    self._log_debug(f"Equity Raise Triggered: {equity:.2f} >= {self.config.strong_equity_raise}")
        
        if can_raise_value and is_raise_available:
            adjusted_aggression = self.aggression_level
            if current_actions and current_actions.raise_count >= 1:
                adjusted_aggression *= 0.8 # Reduz agressão se já houve raise
            
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
                
                # SAFETY CAP (Normal Play): In DEEP stage, be careful with All-Ins
                stage = self._get_tournament_stage(round_state)
                if stage == "DEEP" and amount >= my_stack:
                    # Only All-In if hand is PREMIUM (Score < 2000 or Equity > 80%)
                    is_premium = False
                    if is_preflop:
                        if hand_strength >= 80: is_premium = True
                    else:
                        if hand_strength <= 2000: is_premium = True
                        if metrics.get('equity', 0) > 0.80: is_premium = True
                    
                    if not is_premium:
                        # Cap raise to 1.5x Pot
                        pot_size = round_state['pot']['main']['amount']
                        safe_amount = int(pot_size * 1.5)
                        amount = max(min_amount, min(safe_amount, max_amount))
                        if amount >= my_stack:
                            # If still all-in, just call
                            self._log_debug(f"Aggressive All-In rejected (DEEP STAGE): Hand not premium enough")
                            call_action = valid_actions[1]
                            return call_action['action'], call_action['amount']
                        self._log_debug(f"Aggressive Raise Capped (DEEP STAGE): {amount}")

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

    def _get_tournament_stage(self, round_state):
        """
        Determina o estágio do torneio baseado em Stack efetivo (BBs).
        
        Stages:
        - DEEP (> 50 BB): Jogo profundo, early game. Evitar all-ins especulativos.
        - NORMAL (20-50 BB): Jogo padrão.
        - SHORT (< 20 BB): Jogo curto, push/fold começa a ser relevante.
        - CRITICAL (< 10 BB): Modo sobrevivência/desespero.
        """
        my_stack = self._get_my_stack(round_state)
        bb = round_state['small_blind_amount'] * 2
        if bb == 0: return "NORMAL"
        
        bbs = my_stack / bb
        
        if bbs > 50:
            return "DEEP"
        elif bbs >= 20:
            return "NORMAL"
        elif bbs >= 10:
            return "SHORT"
        else:
            return "CRITICAL"
    
    # ============================================================
    # Métodos receive_* (lógica compartilhada)
    # ============================================================
    
    def receive_game_start_message(self, game_info):
        """Inicializa stack"""
        # Garante que UUID fixo seja mantido (PyPokerEngine pode ter sobrescrito)
        # UUID é sempre fixo, não precisa de verificação
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
                            # UUID é sempre fixo, comparação direta
                            if seat_uuid == self.uuid:
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
