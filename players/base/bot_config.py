"""
Configuração de bot usando dataclass.
ZERO lógica aqui - apenas dados.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class BotConfig:
    """Configuração completa de um bot - ZERO lógica aqui"""
    
    # Identificação
    name: str
    memory_file: str
    
    # Parâmetros de personalidade (valores padrão)
    default_bluff: float
    default_aggression: float
    default_tightness: int
    
    # Thresholds de decisão (Heurística Pré-Flop: 0-100% Equidade, MAIOR é melhor)
    # Ajustado para Equidade Real:
    # 50% = Média (ex: Q8o)
    # 60% = Bom (ex: KJs)
    # 70% = Muito Bom (ex: TT)
    # 80% = Premium (ex: QQ+)
    fold_threshold_base: int
    raise_threshold: int
    strong_hand_threshold: int
    
    # Fatores de ajuste para raises
    raise_multiplier_min: int
    raise_multiplier_max: int
    
    # Comportamento de blefe
    bluff_call_ratio: float  # Probabilidade de fazer call vs raise no blefe
    
    # Comportamento em contextos específicos
    passive_aggression_boost: float  # Quanto aumenta agressão quando campo passivo
    raise_count_sensitivity: float  # Sensibilidade a raises (multiplicador)
    bluff_detection_threshold: int  # Threshold para pagar blefe detectado
    
    # --- CAMPOS COM VALORES DEFAULT (Devem vir por último) ---
    
    # Thresholds de decisão (PokerKit Score Pós-Flop: 0-7462, MENOR é melhor)
    # Valores padrão conservadores (ajustáveis por bot)
    # 6000 ~ One Pair baixo
    # 3000 ~ Two Pair
    # 1000 ~ Flush/Full House
    fold_threshold_score: int = 6000  # Fold se score > 6000 (One Pair muito fraco ou pior)
    raise_threshold_score: int = 4800  # Raise se score < 4800 (Top Pair ou melhor)
    strong_hand_threshold_score: int = 2800  # Mão muito forte se score < 2800 (Two Pair forte ou melhor)
    
    # Ajustes de agressão baseados em contexto
    raise_count_aggression_reduction: float = 0.9  # Reduz agressão quando muitos raises
    passive_raise_threshold: int = 20  # Threshold para raise em campo passivo
    passive_raise_score_threshold: float = 0.4  # Score mínimo para raise passivo
    
    # Aprendizado
    learning_speed: float = 0.001  # Velocidade de aprendizado (0.001 = lento, 0.01 = rápido)
    win_rate_threshold_high: float = 0.60  # Win rate alto para aumentar agressão
    win_rate_threshold_low: float = 0.30  # Win rate baixo para reduzir agressão
    rounds_before_learning: int = 10  # Rodadas mínimas antes de aprender
    
    # Comportamento de blefe baseado em contexto
    bluff_raise_prob_few_players: float = 0.60  # Prob de raise no blefe com poucos jogadores (Reduzido de 0.80)
    bluff_raise_prob_many_players: float = 0.40  # Prob de raise no blefe com muitos jogadores (Reduzido de 0.50)
    
    # Ajustes de threshold baseados em ações
    raise_threshold_adjustment_base: int = 2  # Ajuste base quando há raise
    raise_threshold_adjustment_per_raise: int = 1  # Ajuste por cada raise adicional
    
    # Ajustes de threshold para campo passivo
    passive_threshold_reduction_factor: float = 4.0  # Fator de redução de threshold em campo passivo
    passive_threshold_min: int = 20  # Threshold mínimo em campo passivo
    
    # Panic Rule
    raise_count_panic_threshold: int = 3  # Número de raises para ativar "Panic Rule" (foldar se não tiver mão forte)
    
    # Position-based adjustments
    position_btn_adjustment: int = -8  # Button: joga mais solto (threshold menor)
    position_co_adjustment: int = -5   # Cutoff: joga solto
    position_mp_adjustment: int = 0    # Middle Position: neutro
    position_utg_adjustment: int = 5   # Under the Gun: joga apertado (threshold maior)
    position_bb_adjustment: int = -3   # Big Blind: já investiu, defende mais
    position_sb_adjustment: int = 2    # Small Blind: má posição pós-flop
    position_bluff_late_bonus: float = 0.20      # Bonus de blefe em posição tardia (BTN/CO)
    position_bluff_early_penalty: float = 0.10   # Penalidade de blefe em posição inicial (UTG/MP)

    # ============================================================
    # EQUITY BASED DECISIONS (New)
    # ============================================================
    
    # Minimum equity to justify a CALL (overrides Score-based fold)
    # 0.25 = 25% equity required to call
    min_equity_call: float = 0.25
    
    # Equity to consider a value RAISE
    # 0.60 = 60% equity required to raise for value
    strong_equity_raise: float = 0.60

