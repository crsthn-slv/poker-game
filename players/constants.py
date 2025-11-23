"""
Constantes compartilhadas para players.
Substitui magic numbers por constantes nomeadas.
"""
from enum import Enum

# Probabilidades de blefe padrão
BLUFF_PROBABILITY_TIGHT = 0.08
BLUFF_PROBABILITY_AGGRESSIVE = 0.35
BLUFF_PROBABILITY_RANDOM = 0.25
BLUFF_PROBABILITY_SMART = 0.15
BLUFF_PROBABILITY_BALANCED = 0.15
BLUFF_PROBABILITY_ADAPTIVE = 0.20
BLUFF_PROBABILITY_LEARNING = 0.20

# Thresholds de força de mão
HAND_STRENGTH_VERY_STRONG = 70
HAND_STRENGTH_STRONG = 50
HAND_STRENGTH_MEDIUM = 25
HAND_STRENGTH_WEAK = 10

# Thresholds de tightness
TIGHTNESS_THRESHOLD_DEFAULT = 25
TIGHTNESS_THRESHOLD_CONSERVATIVE = 30
TIGHTNESS_THRESHOLD_AGGRESSIVE = 20

# Níveis de agressão
AGGRESSION_LEVEL_LOW = 0.3
AGGRESSION_LEVEL_MEDIUM = 0.5
AGGRESSION_LEVEL_HIGH = 0.7
AGGRESSION_LEVEL_VERY_HIGH = 0.85

# Valores de stack
STACK_INITIAL = 100
STACK_LOW_THRESHOLD = 0.7  # 70% do stack inicial
STACK_HIGH_THRESHOLD = 1.2  # 120% do stack inicial

# Tamanhos de pot
POT_SIZE_SMALL = 50
POT_SIZE_MEDIUM = 100
POT_SIZE_LARGE = 150

# Taxas de aprendizado
LEARNING_RATE_DEFAULT = 0.1
LEARNING_RATE_CONSERVATIVE = 0.05
LEARNING_RATE_AGGRESSIVE = 0.15

# Histórico de rodadas (quantas manter)
HISTORY_SIZE_SHORT = 10
HISTORY_SIZE_MEDIUM = 20
HISTORY_SIZE_LONG = 50

# Cartas altas
HIGH_CARDS = ['A', 'K', 'Q', 'J']

# ============================================================================
# Constantes do PokerKit - Score Ranges
# ============================================================================
# PokerKit usa scores de 0-7462, onde menor score = melhor mão
# Nota: O código inverte o score do PokerKit para manter compatibilidade
#       (PokerKit: maior = melhor, nosso código: menor = melhor)

# Score máximo do PokerKit
POKERKIT_MAX_SCORE = 7462
POKERKIT_MIN_SCORE = 0

# Thresholds de Score por Tipo de Mão (menor = melhor)
# Esses valores são usados para mapear score → nome da mão
HAND_SCORE_ROYAL_FLUSH_MAX = 1
HAND_SCORE_STRAIGHT_FLUSH_MAX = 10
HAND_SCORE_FOUR_OF_A_KIND_MAX = 166
HAND_SCORE_FULL_HOUSE_MAX = 322
HAND_SCORE_FLUSH_MAX = 1599
HAND_SCORE_STRAIGHT_MAX = 1609
HAND_SCORE_THREE_OF_A_KIND_MAX = 2467
HAND_SCORE_TWO_PAIR_MAX = 3325
HAND_SCORE_ONE_PAIR_MAX = 6185
HAND_SCORE_HIGH_CARD_MAX = POKERKIT_MAX_SCORE

# Thresholds de Nível de Força da Mão (para classificação semântica)
HAND_STRENGTH_EXCELLENT_MAX = 166  # Royal Flush até Four of a Kind
HAND_STRENGTH_GOOD_MAX = 2467      # Full House até Three of a Kind
HAND_STRENGTH_FAIR_MAX = 3325      # Flush até Two Pair
# HAND_STRENGTH_POOR = acima de 3325 (One Pair ou High Card)

# Número mínimo de cartas comunitárias para avaliação completa com PokerKit
MIN_COMMUNITY_CARDS_FOR_POKERKIT = 3

# Número total de cartas comunitárias no poker
TOTAL_COMMUNITY_CARDS = 5

# Número de simulações Monte Carlo
MONTE_CARLO_DEFAULT_SIMULATIONS = 1000


# ============================================================================
# Enums para Tipos de Mão e Níveis de Força
# ============================================================================

class HandType(Enum):
    """Enum para tipos de mão de poker."""
    ROYAL_FLUSH = "Royal Flush"
    STRAIGHT_FLUSH = "Straight Flush"
    FOUR_OF_A_KIND = "Four of a Kind"
    FULL_HOUSE = "Full House"
    FLUSH = "Flush"
    STRAIGHT = "Straight"
    THREE_OF_A_KIND = "Three of a Kind"
    TWO_PAIR = "Two Pair"
    ONE_PAIR = "One Pair"
    HIGH_CARD = "High Card"


class HandStrengthLevel(Enum):
    """Enum para níveis semânticos de força da mão."""
    EXCELLENT = "Excellent"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"

