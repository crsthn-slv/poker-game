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
    
    # Thresholds de decisão
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
    bluff_raise_prob_few_players: float = 0.80  # Prob de raise no blefe com poucos jogadores
    bluff_raise_prob_many_players: float = 0.50  # Prob de raise no blefe com muitos jogadores
    
    # Ajustes de threshold baseados em ações
    raise_threshold_adjustment_base: int = 3  # Ajuste base quando há raise
    raise_threshold_adjustment_per_raise: int = 2  # Ajuste por cada raise adicional
    
    # Ajustes de threshold para campo passivo
    passive_threshold_reduction_factor: float = 4.0  # Fator de redução de threshold em campo passivo
    passive_threshold_min: int = 20  # Threshold mínimo em campo passivo

