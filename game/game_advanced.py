from pypokerengine.api.game import setup_config, start_poker
from players.tight_player import TightPlayer
from players.aggressive_player import AggressivePlayer
from players.random_player import RandomPlayer
from players.smart_player import SmartPlayer
from players.learning_player import LearningPlayer

# Configuração do jogo
config = setup_config(max_round=10, initial_stack=100, small_blind_amount=5)

# Registra TODAS as IAs com sistema de blefe + IA com aprendizado
config.register_player(name="Tight", algorithm=TightPlayer())
config.register_player(name="Aggressive", algorithm=AggressivePlayer())
config.register_player(name="Random", algorithm=RandomPlayer())
config.register_player(name="Smart", algorithm=SmartPlayer())
config.register_player(name="Learning", algorithm=LearningPlayer())

print("=" * 60)
print("Jogo AI vs AI - IAs com Sistema de Blefe + Aprendizado")
print("=" * 60)
print("\nJogadores:")
print("  - Tight: Conservador (8% blefe)")
print("  - Aggressive: Agressivo (35% blefe)")
print("  - Random: Aleatório (25% blefe)")
print("  - Smart: Inteligente (15% base, ajusta dinamicamente)")
print("  - Learning: Aprende e se adapta com o tempo!")
print("=" * 60)
print()

game_result = start_poker(config, verbose=1)

print("\n" + "=" * 60)
print("Resultado Final do Jogo")
print("=" * 60)
print(game_result)

