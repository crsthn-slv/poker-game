"""
Jogador que aprende e adapta estratégia continuamente.
Toda lógica está em PokerBotBase.
"""
from players.base.poker_bot_base import PokerBotBase
from players.base.bot_config import BotConfig


def _create_config(memory_file: str = "learning_player_memory.json") -> BotConfig:
    """Cria configuração para jogador que aprende e adapta estratégia continuamente."""
    return BotConfig(
        # Identificação do bot
        name="Learning",  # Nome do bot (string)
        memory_file=memory_file,  # Arquivo de memória (string, ex: "bot_memory.json")
        
        
        # PARÂMETROS DE PERSONALIDADE BASE
        # ============================================================
        # Probabilidade inicial de blefe (0.0 = nunca blefa, 1.0 = sempre blefa)
        # Mínimo: 0.0 | Máximo: 1.0 | Típico: 0.10-0.25
        default_bluff=0.17,
        # Nível inicial de agressão (0.0 = passivo, 1.0 = muito agressivo)
        # Mínimo: 0.0 | Máximo: 1.0 | Típico: 0.40-0.65
        # Controla frequência de raises vs calls
        default_aggression=0.55,
        # Threshold inicial de seletividade (quanto maior, mais seletivo)
        # Mínimo: 15 | Máximo: 50 | Típico: 20-35
        # Mão precisa ter força >= este valor para não foldar
        default_tightness=28,
        # ============================================================
        # THRESHOLDS DE DECISÃO
        # ============================================================
        # Threshold base para foldar (força mínima para não foldar)
        # Mínimo: 10 | Máximo: 35 | Típico: 15-30
        # Mão com força < este valor = fold
        fold_threshold_base=20,
        # Threshold mínimo para considerar fazer raise
        # Mínimo: 20 | Máximo: 40 | Típico: 25-35
        # Mão precisa ter força >= este valor para considerar raise
        raise_threshold=28,
        # Threshold para mão muito forte (sempre faz raise)
        # Mínimo: 30 | Máximo: 60 | Típico: 30-55
        # Mão com força >= este valor = raise garantido
        strong_hand_threshold=50,
        # ============================================================
        # AJUSTES DE VALOR DE RAISE
        # ============================================================
        # Multiplicador mínimo para calcular valor do raise
        # Mínimo: 10 | Máximo: 30 | Típico: 15-25
        # Usado para calcular: min_amount + (random entre min e max)
        raise_multiplier_min=15,
        # Multiplicador máximo para calcular valor do raise
        # Mínimo: 15 | Máximo: 35 | Típico: 20-30
        # Usado para calcular: min_amount + (random entre min e max)
        raise_multiplier_max=20,
        # ============================================================
        # COMPORTAMENTO DE BLEFE
        # ============================================================
        # Probabilidade de fazer call vs raise quando blefa
        # Mínimo: 0.0 (sempre raise) | Máximo: 1.0 (sempre call) | Típico: 0.30-0.70
        bluff_call_ratio=0.5,
        # Probabilidade de raise no blefe com poucos jogadores (≤2)
        # Mínimo: 0.0 | Máximo: 1.0 | Típico: 0.50-0.80
        # Com poucos jogadores, blefe com raise é mais efetivo
        bluff_raise_prob_few_players=0.5,
        # Probabilidade de raise no blefe com muitos jogadores (>2)
        # Mínimo: 0.0 | Máximo: 1.0 | Típico: 0.30-0.50
        # Com muitos jogadores, blefe com call é mais seguro
        bluff_raise_prob_many_players=0.5,
        # ============================================================
        # REAÇÃO A AÇÕES DOS OPONENTES
        # ============================================================
        # Sensibilidade a raises dos oponentes (multiplicador)
        # Mínimo: 1.0 | Máximo: 5.0 | Típico: 2.0-3.0
        # Quanto maior, mais conservador fica quando há raises
        raise_count_sensitivity=2.0,
        # Ajuste base do threshold quando detecta raise
        # Mínimo: 3 | Máximo: 10 | Típico: 3-8
        # Quantos pontos adiciona ao threshold quando há 1 raise
        raise_threshold_adjustment_base=5,
        # Ajuste adicional por cada raise extra
        # Mínimo: 1 | Máximo: 5 | Típico: 2-3
        # Quantos pontos adiciona ao threshold por cada raise adicional
        raise_threshold_adjustment_per_raise=2,
        # ============================================================
        # DETECÇÃO E PAGAMENTO DE BLEFE
        # ============================================================
        # Threshold para pagar blefe detectado dos oponentes
        # Mínimo: 20 | Máximo: 35 | Típico: 22-32
        # Mão precisa ter força >= este valor para pagar possível blefe
        # Conservadores: 28-32 | Agressivos: 22-24 | Balanceados: 25-28
        bluff_detection_threshold=26,
        # ============================================================
        # COMPORTAMENTO EM CAMPO PASSIVO
        # ============================================================
        # Quanto aumenta agressão quando campo está passivo (só calls)
        # Mínimo: 0.0 | Máximo: 0.50 | Típico: 0.10-0.35
        # Multiplicado pelo passive_opportunity_score
        passive_aggression_boost=0.15,
        # Fator de redução do threshold em campo passivo
        # Mínimo: 2.0 | Máximo: 5.0 | Típico: 3.0-4.0
        # Quanto maior, mais reduz threshold quando campo está passivo
        passive_threshold_reduction_factor=4.0,
        # Threshold mínimo permitido em campo passivo
        # Mínimo: 15 | Máximo: 35 | Típico: 20-30
        # Threshold nunca fica abaixo deste valor, mesmo em campo passivo
        passive_threshold_min=20,
        # Threshold para fazer raise em campo passivo
        # Mínimo: 20 | Máximo: 50 | Típico: 20-35
        # Mão precisa ter força >= este valor para raise em campo passivo
        passive_raise_threshold=28,
        # Score mínimo de oportunidade para raise em campo passivo
        # Mínimo: 0.0 | Máximo: 1.0 | Típico: 0.4-0.7
        # Oportunidade precisa ser >= este valor para considerar raise passivo
        passive_raise_score_threshold=0.4,
        # ============================================================
        # SISTEMA DE APRENDIZADO
        # ============================================================
        # Velocidade de aprendizado (quão rápido ajusta estratégia)
        # Mínimo: 0.0001 (muito lento) | Máximo: 0.01 (muito rápido) | Típico: 0.001-0.005
        # Usado como multiplicador: 1 + learning_speed
        learning_speed=0.01,
        # Win rate alto para aumentar agressão/blefe
        # Mínimo: 0.50 | Máximo: 0.70 | Típico: 0.55-0.65
        # Se win rate > este valor, aumenta agressão e blefe
        win_rate_threshold_high=0.6,
        # Win rate baixo para reduzir agressão/aumentar seletividade
        # Mínimo: 0.20 | Máximo: 0.40 | Típico: 0.25-0.35
        # Se win rate < este valor, reduz agressão e aumenta threshold
        win_rate_threshold_low=0.3,
        # Rodadas mínimas antes de começar a aprender
        # Mínimo: 5 | Máximo: 20 | Típico: 10-15
        # Bot só ajusta estratégia após este número de rodadas
        rounds_before_learning=10,
    )


class LearningPlayer(PokerBotBase):
    """Jogador que aprende e adapta estratégia continuamente."""
    
    def __init__(self, memory_file="learning_player_memory.json"):
        config = _create_config(memory_file)
        super().__init__(config)