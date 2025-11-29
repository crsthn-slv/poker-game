"""
Utilitários para gerar UUIDs determinísticos baseados em classes de bots.

Garante que o mesmo tipo de bot sempre tenha o mesmo UUID, independente do nome.
"""
import uuid
from typing import Optional

# Namespace fixo para gerar UUIDs determinísticos de bots
BOT_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # Namespace DNS padrão

def get_bot_class_uuid(bot_instance) -> str:
    """
    Gera UUID determinístico baseado na CLASSE do bot.
    O mesmo tipo de bot sempre gera o mesmo UUID, independente do nome.
    
    Args:
        bot_instance: Instância do bot (ex: TightPlayer(), AggressivePlayer())
    
    Returns:
        UUID como string
    
    Exemplo:
        >>> bot1 = TightPlayer()
        >>> bot2 = TightPlayer()
        >>> get_bot_class_uuid(bot1) == get_bot_class_uuid(bot2)
        True
    """
    # Usa módulo + nome da classe para garantir unicidade
    bot_class = type(bot_instance)
    class_identifier = f"{bot_class.__module__}.{bot_class.__name__}"
    return str(uuid.uuid5(BOT_NAMESPACE, class_identifier))

def get_player_uuid(player_name: str = None) -> str:
    """
    Gera UUID para jogador humano.
    Se tiver nome, gera UUID determinístico. Senão, retorna None para usar UUID do PyPokerEngine.
    
    Args:
        player_name: Nome do jogador (opcional)
    
    Returns:
        UUID como string ou None
    """
    if player_name:
        # UUID determinístico baseado no nome do jogador
        return str(uuid.uuid5(BOT_NAMESPACE, f"human_player_{player_name}"))
    return None

def get_bot_class_uuid_from_name(bot_name: str) -> Optional[str]:
    """
    Tenta obter UUID fixo baseado no nome do bot.
    Usa mapeamento de nomes conhecidos para classes de bots.
    
    Args:
        bot_name: Nome do bot (ex: "Tight", "Aggressive", etc.)
    
    Returns:
        UUID como string se encontrar, None caso contrário
    """
    # Mapeamento de nomes de bots para identificadores de classe
    # Baseado nos nomes usados em test_100_games.py e play_console.py
    name_to_class_map = {
        'Tight': 'players.tight_player.TightPlayer',
        'Aggressive': 'players.aggressive_player.AggressivePlayer',
        'Random': 'players.random_player.RandomPlayer',
        'Smart': 'players.smart_player.SmartPlayer',
        'Learning': 'players.learning_player.LearningPlayer',
        'Balanced': 'players.balanced_player.BalancedPlayer',
        'Adaptive': 'players.adaptive_player.AdaptivePlayer',
        'Calculated': 'players.calculated_player.CalculatedPlayer',
        'Calm': 'players.calm_player.CalmPlayer',
        'Cautious': 'players.cautious_player.CautiousPlayer',
        'ConservativeAggressive': 'players.conservative_aggressive_player.ConservativeAggressivePlayer',
        'Fish': 'players.fish_player.FishPlayer',
        'Flexible': 'players.flexible_player.FlexiblePlayer',
        'Hybrid': 'players.hybrid_player.HybridPlayer',
        'Moderate': 'players.moderate_player.ModeratePlayer',
        'Observant': 'players.observant_player.ObservantPlayer',
        'Opportunistic': 'players.opportunistic_player.OpportunisticPlayer',
        'Patient': 'players.patient_player.PatientPlayer',
        'Steady': 'players.steady_player.SteadyPlayer',
        'SteadyAggressive': 'players.steady_aggressive_player.SteadyAggressivePlayer',
        'Thoughtful': 'players.thoughtful_player.ThoughtfulPlayer',
        # Nomes do console
        'Blaze': 'players.tight_player.TightPlayer',
        'Riley': 'players.aggressive_player.AggressivePlayer',
        'Sloan': 'players.random_player.RandomPlayer',
        'Dexter': 'players.smart_player.SmartPlayer',
        'Ivory': 'players.learning_player.LearningPlayer',
        'Maverick': 'players.balanced_player.BalancedPlayer',
        'Nova': 'players.adaptive_player.AdaptivePlayer',
        'Jett': 'players.conservative_aggressive_player.ConservativeAggressivePlayer',
        'Harper': 'players.opportunistic_player.OpportunisticPlayer',
        'Knox': 'players.hybrid_player.HybridPlayer',
        'Sable': 'players.fish_player.FishPlayer',
        'Phoenix': 'players.cautious_player.CautiousPlayer',
        'Avery': 'players.moderate_player.ModeratePlayer',
        'Sterling': 'players.patient_player.PatientPlayer',
        'Reign': 'players.calculated_player.CalculatedPlayer',
        'Jaxon': 'players.steady_player.SteadyPlayer',
        'Blair': 'players.observant_player.ObservantPlayer',
        'Lennox': 'players.flexible_player.FlexiblePlayer',
        'Karter': 'players.calm_player.CalmPlayer',
        'Ember': 'players.thoughtful_player.ThoughtfulPlayer',
        'Talon': 'players.steady_aggressive_player.SteadyAggressivePlayer',

    }
    
    class_identifier = name_to_class_map.get(bot_name)
    if class_identifier:
        return str(uuid.uuid5(BOT_NAMESPACE, class_identifier))
    return None

def get_all_known_bot_names() -> list:
    """
    Retorna lista de todos os nomes de bots conhecidos (apenas nomes principais, não aliases do console).
    
    Returns:
        Lista de nomes de bots
    """
    return [
        'Tight', 'Aggressive', 'Random', 'Smart', 'Learning', 'Balanced',
        'Adaptive', 'Calculated', 'Calm', 'Cautious', 'ConservativeAggressive',
        'Fish', 'Flexible', 'Hybrid', 'Moderate', 'Observant', 'Opportunistic',
        'Patient', 'Steady', 'SteadyAggressive', 'Thoughtful'
    ]

