from pypokerengine.api.game import setup_config, start_poker
from players.console_player import ConsolePlayer, QuitGameException
from players.tight_player import TightPlayer
from players.aggressive_player import AggressivePlayer
from players.random_player import RandomPlayer
from players.smart_player import SmartPlayer

# Configuração do jogo
initial_stack = 100
config = setup_config(max_round=10, initial_stack=initial_stack, small_blind_amount=5)

# Registra os jogadores
# Você (ConsolePlayer) + 3 AIs com diferentes personalidades
config.register_player(name="You", algorithm=ConsolePlayer(initial_stack=initial_stack))
config.register_player(name="Tight", algorithm=TightPlayer())
config.register_player(name="Aggressive", algorithm=AggressivePlayer())
config.register_player(name="Smart", algorithm=SmartPlayer())

# Inicia o jogo
print("=" * 60)
print("Welcome to Terminal Poker!")
print("=" * 60)
print("\nYou will play against 3 AIs with different personalities:")
print("  - Tight: Conservative, bluffs 8% of the time")
print("  - Aggressive: Aggressive, bluffs 35% of the time")
print("  - Smart: Intelligent, dynamic bluff (15% base)")
print("\nUse 'f' for FOLD, 'c' for CALL, 'r' for RAISE")
print("Type 'q' at any time to quit")
print("=" * 60)
print()

try:
    game_result = start_poker(config, verbose=0)
    
    # O resultado final é mostrado pelo ConsolePlayer.receive_round_result_message
    # Não precisamos imprimir o JSON bruto aqui
    print("\n" + "=" * 60)
    print("End of Game")
    print("=" * 60)
except QuitGameException:
    print("\n\n" + "=" * 60)
    print("Game ended by user")
    print("=" * 60)
    print("\nThank you for playing! See you next time.")
    exit(0)

