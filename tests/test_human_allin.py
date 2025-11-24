#!/usr/bin/env python3
"""
Teste que simula um jogo real onde o jogador humano faz all-in (aposta tudo).
Testa se o sistema lida corretamente com:
1. Valor de call mostrado corretamente (valor adicional, não total)
2. Jogador que fica com poucas fichas após all-in
3. Jogador que não consegue pagar blinds no próximo round
"""

from pypokerengine.api.game import setup_config, start_poker
from players.console_player import ConsolePlayer, QuitGameException
from players.tight_player import TightPlayer
from players.aggressive_player import AggressivePlayer
from game.blind_manager import BlindManager
import io
import sys
from unittest.mock import patch


class MockConsolePlayer(ConsolePlayer):
    """ConsolePlayer mockado que faz ações pré-definidas."""
    
    def __init__(self, actions_sequence, initial_stack=1000, small_blind=None, big_blind=None):
        # Cria input_receiver customizado que retorna ações pré-definidas
        self.actions_sequence = actions_sequence
        self.action_index = 0
        self.current_valid_actions = None
        self.raise_amounts = {}  # Armazena valores de raise por índice
        self.awaiting_raise_amount = False  # Flag para saber se estamos esperando valor de raise
        
        # Chama __init__ do pai com input_receiver customizado
        def custom_input_receiver(msg):
            """Input receiver que retorna ações da sequência."""
            # Se estamos esperando valor de raise, retorna o valor
            if self.awaiting_raise_amount:
                self.awaiting_raise_amount = False
                # Procura o último raise na sequência
                for i in range(self.action_index - 1, -1, -1):
                    if i < len(self.actions_sequence):
                        action = self.actions_sequence[i]
                        if isinstance(action, tuple) and action[0] == 'raise':
                            return str(action[1])
                        elif action == 'raise' and i in self.raise_amounts:
                            return str(self.raise_amounts[i])
                # Se não encontrou, retorna um valor padrão (será ajustado pelo código)
                return '100'
            
            if self.action_index >= len(self.actions_sequence):
                return 'f'  # Fold se acabaram as ações
            
            action = self.actions_sequence[self.action_index]
            
            # Se for raise, verifica se tem valor específico
            if isinstance(action, tuple):
                action_type, amount = action
                if action_type == 'raise':
                    self.raise_amounts[self.action_index] = amount
                    self.action_index += 1
                    self.awaiting_raise_amount = True
                    return 'r'
                elif action_type == 'allin':
                    self.action_index += 1
                    return 'a'
            
            self.action_index += 1
            
            # Mapeia ação para flag
            if action == 'fold':
                return 'f'
            elif action == 'call':
                return 'c'
            elif action == 'raise':
                self.awaiting_raise_amount = True
                return 'r'
            elif action == 'allin':
                return 'a'
            else:
                return 'f'  # Default: fold
        
        super().__init__(input_receiver=custom_input_receiver, initial_stack=initial_stack, 
                        small_blind=small_blind, big_blind=big_blind)


def test_human_allin_scenario():
    """Testa cenário onde jogador humano faz all-in e fica com poucas fichas."""
    print("=" * 60)
    print("Teste: Jogador humano faz all-in")
    print("=" * 60)
    
    initial_stack = 1000
    blind_manager = BlindManager(initial_reference_stack=initial_stack)
    small_blind, big_blind = blind_manager.get_blinds()
    
    print(f"\nConfiguração:")
    print(f"  - Stack inicial: {initial_stack}")
    print(f"  - Small Blind: {small_blind}")
    print(f"  - Big Blind: {big_blind}")
    
    # Sequência de ações: call várias vezes até fazer all-in
    # Simula um cenário onde o jogador vai fazendo call até ficar com poucas fichas
    # Usa uma sequência longa para garantir que o jogo execute vários rounds
    actions_sequence = ['call'] * 50  # 50 calls para garantir que o jogo execute
    
    config = setup_config(max_round=5, initial_stack=initial_stack, small_blind_amount=small_blind)
    
    # Cria jogador humano mockado
    human_player = MockConsolePlayer(
        actions_sequence=actions_sequence,
        initial_stack=initial_stack,
        small_blind=small_blind,
        big_blind=big_blind
    )
    
    config.register_player(name="You", algorithm=human_player)
    config.register_player(name="Bot1", algorithm=TightPlayer())
    config.register_player(name="Bot2", algorithm=AggressivePlayer())
    
    # Captura output para não poluir o console
    captured_output = io.StringIO()
    
    try:
        with patch('sys.stdout', captured_output):
            game_result = start_poker(config, verbose=0)
        
        print("\n✅ Teste concluído com sucesso!")
        print(f"\nResultado do jogo:")
        
        # Obtém informações dos players
        players_info = game_result.get('players', [])
        round_states = game_result.get('round_states', [])
        
        print(f"  - Rounds jogados: {len(round_states)}")
        
        # Verifica stack final do jogador humano
        human_stack = None
        for player_info in players_info:
            if isinstance(player_info, dict) and player_info.get('name') == 'You':
                human_stack = player_info.get('stack', 0)
                print(f"  - Stack final do jogador humano: {human_stack}")
                break
        
        # Se não encontrou nos players, tenta nos round_states
        if human_stack is None and round_states:
            last_round = round_states[-1]
            seats = last_round.get('seats', [])
            for seat in seats:
                if isinstance(seat, dict) and seat.get('name') == 'You':
                    human_stack = seat.get('stack', 0)
                    print(f"  - Stack final do jogador humano: {human_stack}")
                    break
        
        if human_stack is not None:
            if human_stack == 0:
                print("  ⚠️  Jogador foi eliminado")
            elif human_stack < big_blind:
                print(f"  ⚠️  Jogador tem poucas fichas ({human_stack} < {big_blind} BB)")
                print("     Pode não conseguir pagar blinds no próximo round")
                print("     ✓ Sistema deve mostrar '(Out of chips - cannot pay blinds)'")
            else:
                print("  ✓ Jogador ainda tem fichas suficientes")
        
        # Verifica se houve algum round onde o jogador não participou
        print(f"\n  Verificando rounds para detectar não-participação:")
        for i, round_state in enumerate(round_states):
            seats = round_state.get('seats', [])
            action_histories = round_state.get('action_histories', {})
            
            # Verifica se o jogador humano tem ações neste round
            has_actions = False
            for street_history in action_histories.values():
                if isinstance(street_history, list):
                    for action in street_history:
                        if isinstance(action, dict):
                            player_name = action.get('player', '')
                            if player_name == 'You':
                                has_actions = True
                                break
                    if has_actions:
                        break
            
            if not has_actions:
                # Verifica stack do jogador neste round
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('name') == 'You':
                        stack = seat.get('stack', 0)
                        if stack > 0:
                            print(f"    Round {i+1}: Jogador não participou (stack: {stack})")
                            print(f"      ✓ Sistema deve mostrar '(Out of chips - cannot pay blinds)'")
                        break
        
    except QuitGameException:
        print("\n⚠️  Jogo foi interrompido pelo jogador")
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_call_amount_display():
    """Testa se o valor de call está sendo exibido corretamente."""
    print("\n" + "=" * 60)
    print("Teste: Verificação do valor de call exibido")
    print("=" * 60)
    
    initial_stack = 1000
    blind_manager = BlindManager(initial_reference_stack=initial_stack)
    small_blind, big_blind = blind_manager.get_blinds()
    
    # Cria um ConsolePlayer simples para testar formatação
    from utils.console_formatter import ConsoleFormatter
    formatter = ConsoleFormatter()
    
    # Simula valid_actions com call
    valid_actions = [
        {'action': 'fold', 'amount': 0},
        {'action': 'call', 'amount': 50},  # Valor adicional a pagar
        {'action': 'raise', 'amount': {'min': 100, 'max': 1000}}
    ]
    
    # Testa formatação sem round_state (comportamento antigo)
    actions_display_old = formatter.format_action_costs(valid_actions)
    print(f"\nFormatação antiga (sem round_state):")
    for text, available in actions_display_old:
        print(f"  - {text} (disponível: {available})")
    
    # Testa formatação com round_state (comportamento novo)
    round_state = {
        'street': 'preflop',
        'action_histories': {
            'preflop': [
                {'uuid': 'player1', 'action': 'SMALLBLIND', 'amount': small_blind},
                {'uuid': 'player2', 'action': 'BIGBLIND', 'amount': big_blind},
                {'uuid': 'player3', 'action': 'RAISE', 'amount': 100}
            ]
        }
    }
    
    actions_display_new = formatter.format_action_costs(valid_actions, round_state, 'player4')
    print(f"\nFormatação nova (com round_state):")
    for text, available in actions_display_new:
        print(f"  - {text} (disponível: {available})")
    
    print("\n✅ Teste de formatação concluído!")
    return True


def test_allin_with_low_stack():
    """Testa especificamente o all-in quando o jogador tem poucas fichas."""
    print("\n" + "=" * 60)
    print("Teste: All-in com stack baixo (simula o bug reportado)")
    print("=" * 60)
    
    initial_stack = 1000
    blind_manager = BlindManager(initial_reference_stack=initial_stack)
    small_blind, big_blind = blind_manager.get_blinds()
    
    print(f"\nConfiguração:")
    print(f"  - Stack inicial: {initial_stack}")
    print(f"  - Small Blind: {small_blind}")
    print(f"  - Big Blind: {big_blind}")
    
    # Sequência de ações que simula o cenário do usuário:
    # 1. Call inicial
    # 2. Raise
    # 3. Call do raise
    # 4. Call novamente (fica com poucas fichas)
    # 5. Tenta fazer all-in (deve funcionar agora)
    actions_sequence = [
        'call',  # Preflop: call do big blind
        ('raise', 300),  # Raise de 300
        'call',  # Call do raise
        'call',  # Call novamente (fica com poucas fichas)
        'allin',  # Tenta fazer all-in - DEVE FUNCIONAR
    ]
    
    config = setup_config(max_round=2, initial_stack=initial_stack, small_blind_amount=small_blind)
    
    # Cria jogador humano mockado
    human_player = MockConsolePlayer(
        actions_sequence=actions_sequence,
        initial_stack=initial_stack,
        small_blind=small_blind,
        big_blind=big_blind
    )
    
    config.register_player(name="You", algorithm=human_player)
    config.register_player(name="Bot1", algorithm=TightPlayer())
    config.register_player(name="Bot2", algorithm=AggressivePlayer())
    
    # Captura output para análise
    captured_output = io.StringIO()
    allin_success = False
    error_occurred = False
    
    try:
        with patch('sys.stdout', captured_output):
            game_result = start_poker(config, verbose=0)
        
        # Analisa o output capturado
        output = captured_output.getvalue()
        
        # Verifica se houve erro de all-in
        if "Erro: Não foi possível determinar stack para all-in" in output:
            error_occurred = True
            print("\n❌ ERRO DETECTADO: 'Não foi possível determinar stack para all-in'")
            print("   A correção não funcionou!")
        else:
            allin_success = True
            print("\n✅ All-in executado sem erros!")
        
        # Verifica se o all-in foi realmente executado
        if "all-in" in output.lower() or "allin" in output.lower():
            print("✅ All-in detectado no output do jogo")
        else:
            print("⚠️  All-in não detectado no output (pode ter dado fold antes)")
        
        # Verifica stack final
        players_info = game_result.get('players', [])
        round_states = game_result.get('round_states', [])
        
        human_stack = None
        for player_info in players_info:
            if isinstance(player_info, dict) and player_info.get('name') == 'You':
                human_stack = player_info.get('stack', 0)
                break
        
        if human_stack is None and round_states:
            last_round = round_states[-1]
            seats = last_round.get('seats', [])
            for seat in seats:
                if isinstance(seat, dict) and seat.get('name') == 'You':
                    human_stack = seat.get('stack', 0)
                    break
        
        if human_stack is not None:
            print(f"\nStack final do jogador: {human_stack}")
            if human_stack == 0:
                print("  ✓ Jogador fez all-in e foi eliminado (esperado)")
        
        print(f"\nRounds jogados: {len(round_states)}")
        
        return allin_success and not error_occurred
        
    except QuitGameException:
        print("\n⚠️  Jogo foi interrompido pelo jogador")
        return False
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧪 Iniciando testes de all-in do jogador humano\n")
    
    # Testa formatação de call
    test_call_amount_display()
    
    # Testa all-in especificamente (novo teste)
    allin_test_passed = test_allin_with_low_stack()
    
    # Testa cenário completo de all-in
    test_human_allin_scenario()
    
    print("\n" + "=" * 60)
    if allin_test_passed:
        print("✅ Teste de all-in PASSOU!")
    else:
        print("❌ Teste de all-in FALHOU!")
    print("Todos os testes concluídos!")
    print("=" * 60)

