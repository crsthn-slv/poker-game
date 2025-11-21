from pypokerengine.api.game import setup_config, start_poker
from players.console_player import ConsolePlayer
from players.tight_player import TightPlayer
from players.aggressive_player import AggressivePlayer
from players.random_player import RandomPlayer
from players.smart_player import SmartPlayer

# Configuração do jogo
config = setup_config(max_round=10, initial_stack=100, small_blind_amount=5)

# Registra os jogadores
# Você (ConsolePlayer) + 3 AIs com diferentes personalidades
config.register_player(name="Você", algorithm=ConsolePlayer())
config.register_player(name="Tight", algorithm=TightPlayer())
config.register_player(name="Aggressive", algorithm=AggressivePlayer())
config.register_player(name="Smart", algorithm=SmartPlayer())

# Inicia o jogo
print("=" * 60)
print("Bem-vindo ao Poker no Terminal!")
print("=" * 60)
print("\nVocê jogará contra 3 AIs com diferentes personalidades:")
print("  - Tight: Conservador, blefa 8% das vezes")
print("  - Aggressive: Agressivo, blefa 35% das vezes")
print("  - Smart: Inteligente, blefe dinâmico (15% base)")
print("\nUse 'f' para FOLD, 'c' para CALL, 'r' para RAISE")
print("=" * 60)
print()

game_result = start_poker(config, verbose=0)

print("\n" + "=" * 60)
print("Resultado Final do Jogo")
print("=" * 60)
print(game_result)

