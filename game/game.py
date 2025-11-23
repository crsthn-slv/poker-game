from pypokerengine.api.game import setup_config, start_poker
from players.fish_player import FishPlayer
from game.blind_manager import BlindManager

# Configura stack inicial
initial_stack = 100

# Calcula blinds automaticamente
blind_manager = BlindManager(initial_reference_stack=initial_stack)
small_blind, big_blind = blind_manager.get_blinds()

config = setup_config(max_round=10, initial_stack=initial_stack, small_blind_amount=small_blind)
config.register_player(name="p1", algorithm=FishPlayer())
config.register_player(name="p2", algorithm=FishPlayer())
config.register_player(name="p3", algorithm=FishPlayer())
game_result = start_poker(config, verbose=1)

print("\n=== Resultado Final do Jogo ===")
print(game_result)

