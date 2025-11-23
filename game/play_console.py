from pypokerengine.api.game import setup_config, start_poker
from players.console_player import ConsolePlayer, QuitGameException
from players.tight_player import TightPlayer
from players.aggressive_player import AggressivePlayer
from players.random_player import RandomPlayer
from players.smart_player import SmartPlayer
from players.learning_player import LearningPlayer
from players.balanced_player import BalancedPlayer
from players.adaptive_player import AdaptivePlayer
from players.conservative_aggressive_player import ConservativeAggressivePlayer
from players.opportunistic_player import OpportunisticPlayer
from players.hybrid_player import HybridPlayer
from players.fish_player import FishPlayer
from game.blind_manager import BlindManager
import random

# Lista de bots disponíveis com suas descrições
AVAILABLE_BOTS = [
    {
        'class': TightPlayer,
        'name': 'Tight',
        'description': 'Conservador, blefa 8% das vezes'
    },
    {
        'class': AggressivePlayer,
        'name': 'Aggressive',
        'description': 'Agressivo, blefa 35% das vezes'
    },
    {
        'class': RandomPlayer,
        'name': 'Random',
        'description': 'Jogador aleatório'
    },
    {
        'class': SmartPlayer,
        'name': 'Smart',
        'description': 'Inteligente, blefe dinâmico (15% base)'
    },
    {
        'class': LearningPlayer,
        'name': 'Learning',
        'description': 'Aprende e se adapta com o tempo'
    },
    {
        'class': BalancedPlayer,
        'name': 'Balanced',
        'description': 'Jogador equilibrado'
    },
    {
        'class': AdaptivePlayer,
        'name': 'Adaptive',
        'description': 'Adapta-se às situações do jogo'
    },
    {
        'class': ConservativeAggressivePlayer,
        'name': 'ConservativeAggressive',
        'description': 'Conservador-agressivo misto'
    },
    {
        'class': OpportunisticPlayer,
        'name': 'Opportunistic',
        'description': 'Procura oportunidades para ganhar'
    },
    {
        'class': HybridPlayer,
        'name': 'Hybrid',
        'description': 'Estratégia híbrida combinada'
    },
    {
        'class': FishPlayer,
        'name': 'Fish',
        'description': 'Jogador iniciante'
    }
]


def get_user_input(prompt, default_value=None, input_type=int, min_value=None, max_value=None, error_message=None):
    """Solicita entrada do usuário com validação."""
    while True:
        try:
            if default_value is not None:
                user_input = input(f"{prompt} (default: {default_value}) or 'q' to quit: ").strip()
            else:
                user_input = input(f"{prompt} or 'q' to quit: ").strip()
            
            if user_input.lower() == 'q':
                raise QuitGameException()
            
            if not user_input and default_value is not None:
                return default_value
            
            value = input_type(user_input)
            
            # Validação com mensagem de erro unificada
            if min_value is not None and max_value is not None:
                if value < min_value or value > max_value:
                    if error_message:
                        print(f"Error: {error_message}")
                    else:
                        print(f"Error: The value must be between {min_value} and {max_value}")
                    continue
            elif min_value is not None and value < min_value:
                if error_message:
                    print(f"Error: {error_message}")
                else:
                    print(f"Error: The value must be at least {min_value}")
                continue
            elif max_value is not None and value > max_value:
                if error_message:
                    print(f"Error: {error_message}")
                else:
                    print(f"Error: The value must be at most {max_value}")
                continue
            
            return value
        except ValueError:
            print(f"Error: Please enter a valid number")
        except QuitGameException:
            raise


def select_random_bots(num_bots_needed):
    """Seleciona bots aleatoriamente da lista disponível."""
    if num_bots_needed > len(AVAILABLE_BOTS):
        print(f"Warning: You requested {num_bots_needed} bots, but we only have {len(AVAILABLE_BOTS)} available.")
        print(f"Using all {len(AVAILABLE_BOTS)} available bots.")
        return random.sample(AVAILABLE_BOTS, len(AVAILABLE_BOTS))
    
    return random.sample(AVAILABLE_BOTS, num_bots_needed)


if __name__ == "__main__":
    # Configurações padrão
    DEFAULT_INITIAL_STACK = 1000
    DEFAULT_NUM_BOTS = 5
    MIN_STACK = 100
    MAX_STACK = 10000
    MIN_BOTS = 2
    MAX_BOTS = 9
    
    # Configuração inicial do jogo
    print("=" * 60)
    print("Welcome to Terminal Poker!")
    print("=" * 60)
    print("\nDefault settings:")
    print(f"  - Initial chips: {DEFAULT_INITIAL_STACK}")
    print(f"  - Number of bots: {DEFAULT_NUM_BOTS}")
    print("\nPress [Enter] to start with default settings")
    print("Press [c] to change settings")
    print("Press [q] to quit")
    
    # Solicita confirmação ou alteração
    while True:
        try:
            user_choice = input("\n>> ").strip().lower()
            
            if user_choice == 'q':
                raise QuitGameException()
            elif user_choice == 'c':
                # Usuário quer alterar configurações
                # Mostra informações sobre limites
                print("\n" + "=" * 60)
                print("Game Settings")
                print("=" * 60)
                print(f"\nLimits:")
                print(f"  - Stack: must be between {MIN_STACK} and {MAX_STACK}")
                print(f"  - Number of bots: must be between {MIN_BOTS} and {MAX_BOTS}")
                print("=" * 60 + "\n")
                
                initial_stack = get_user_input(
                    "Initial chips",
                    default_value=DEFAULT_INITIAL_STACK,
                    min_value=MIN_STACK,
                    max_value=MAX_STACK,
                    error_message=f"The stack must be between {MIN_STACK} and {MAX_STACK}"
                )
                
                num_bots = get_user_input(
                    "Number of bots",
                    default_value=DEFAULT_NUM_BOTS,
                    min_value=MIN_BOTS,
                    max_value=MAX_BOTS,
                    error_message=f"The number of bots must be between {MIN_BOTS} and {MAX_BOTS}"
                )
                num_players = num_bots + 1
                break
            elif user_choice == '' or user_choice == '\n':
                # Usuário pressionou Enter, usa configurações padrão
                initial_stack = DEFAULT_INITIAL_STACK
                num_bots = DEFAULT_NUM_BOTS
                num_players = num_bots + 1
                break
            else:
                print("Invalid option. Press [Enter], [c] or [q]")
        except QuitGameException:
            raise
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            exit(0)
    
    # Seleciona bots aleatoriamente
    selected_bots = select_random_bots(num_bots)
    
    # Calcula blinds automaticamente baseado na stack inicial
    blind_manager = BlindManager(initial_reference_stack=initial_stack)
    small_blind, big_blind = blind_manager.get_blinds()
    
    # Configura o jogo com os blinds calculados automaticamente
    config = setup_config(max_round=10, initial_stack=initial_stack, small_blind_amount=small_blind)
    
    # Registra o jogador humano
    config.register_player(name="You", algorithm=ConsolePlayer(initial_stack=initial_stack))
    
    # Registra os bots selecionados aleatoriamente
    for bot_info in selected_bots:
        config.register_player(
            name=bot_info['name'],
            algorithm=bot_info['class']()
        )
    
    # Mostra informações do jogo
    print("\n" + "=" * 60)
    print(f"Game Configuration:")
    print(f"  - Initial chips: {initial_stack}")
    print(f"  - Small Blind (SB): {small_blind}")
    print(f"  - Big Blind (BB): {big_blind}")
    print(f"  - Stack depth: ~{initial_stack // big_blind} BB")
    print(f"  - Number of bots: {num_bots}")
    print(f"\nRandomly selected bots:")
    for bot_info in selected_bots:
        print(f"  - {bot_info['name']}")
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

