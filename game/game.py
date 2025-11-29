from pypokerengine.api.game import setup_config, start_poker
from players.fish_player import FishPlayer
from game.blind_manager import BlindManager
from players.base.poker_bot_base import set_debug_mode

set_debug_mode(True)

# Configura stack inicial
initial_stack = 100

# Calcula blinds automaticamente
blind_manager = BlindManager(initial_reference_stack=initial_stack)
small_blind, big_blind = blind_manager.get_blinds()

config = setup_config(max_round=10, initial_stack=initial_stack, small_blind_amount=small_blind)
p1 = FishPlayer()
p1.config.name = "p1"
config.register_player(name="p1", algorithm=p1)

p2 = FishPlayer()
p2.config.name = "p2"
config.register_player(name="p2", algorithm=p2)

p3 = FishPlayer()
p3.config.name = "p3"
config.register_player(name="p3", algorithm=p3)
game_result = start_poker(config, verbose=1)

print("\n=== Resultado Final do Jogo ===")
print(game_result)

