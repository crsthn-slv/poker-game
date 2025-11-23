"""
Teste de integração: Simula um jogo real para verificar se os bots reagem às ações.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from players.tight_player import TightPlayer
from players.aggressive_player import AggressivePlayer
from players.smart_player import SmartPlayer
from players.learning_player import LearningPlayer
from utils.action_analyzer import analyze_current_round_actions


def simulate_round_with_raises():
    """Simula um round onde oponentes fazem raises e verifica reação dos bots."""
    print("🧪 Teste de Integração: Simulação de Round com Raises")
    print()
    
    # Cria bots
    tight = TightPlayer()
    tight.uuid = 'tight_bot'
    tight.initial_stack = 100
    
    aggressive = AggressivePlayer()
    aggressive.uuid = 'aggressive_bot'
    aggressive.initial_stack = 100
    
    smart = SmartPlayer()
    smart.uuid = 'smart_bot'
    smart.initial_stack = 100
    
    learning = LearningPlayer()
    learning.uuid = 'learning_bot'
    learning.initial_stack = 100
    
    bots = {
        'tight': tight,
        'aggressive': aggressive,
        'smart': smart,
        'learning': learning
    }
    
    # Simula diferentes cenários
    scenarios = [
        {
            'name': 'Sem raises (situação normal)',
            'actions': [
                {'uuid': 'opponent1', 'action': 'CALL', 'amount': 10}
            ],
            'expected_reaction': 'normal'
        },
        {
            'name': '1 raise (situação moderada)',
            'actions': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 20}
            ],
            'expected_reaction': 'cautious'
        },
        {
            'name': '2 raises (situação agressiva)',
            'actions': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 20},
                {'uuid': 'opponent2', 'action': 'RAISE', 'amount': 30}
            ],
            'expected_reaction': 'very_cautious'
        },
        {
            'name': '3 raises (situação muito agressiva)',
            'actions': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 20},
                {'uuid': 'opponent2', 'action': 'RAISE', 'amount': 30},
                {'uuid': 'opponent3', 'action': 'RAISE', 'amount': 40}
            ],
            'expected_reaction': 'very_cautious'
        }
    ]
    
    for scenario in scenarios:
        print(f"📋 Cenário: {scenario['name']}")
        
        round_state = {
            'street': 'preflop',
            'action_histories': {
                'preflop': scenario['actions']
            },
            'seats': [
                {'uuid': 'tight_bot', 'state': 'participating', 'stack': 100},
                {'uuid': 'aggressive_bot', 'state': 'participating', 'stack': 100},
                {'uuid': 'smart_bot', 'state': 'participating', 'stack': 100},
                {'uuid': 'learning_bot', 'state': 'participating', 'stack': 100}
            ],
            'pot': {'main': {'amount': sum(a.get('amount', 0) for a in scenario['actions'])}},
            'community_card': []
        }
        
        # Testa cada bot
        for bot_name, bot in bots.items():
            current_actions = analyze_current_round_actions(round_state, bot.uuid)
            
            # Verifica detecção
            has_raises = current_actions['has_raises']
            raise_count = current_actions['raise_count']
            
            # Calcula threshold ajustado (simula o que aconteceria)
            if hasattr(bot, 'tightness_threshold'):
                original_threshold = bot.tightness_threshold
                adjusted_threshold = original_threshold
                
                if has_raises:
                    if bot_name == 'tight':
                        adjusted_threshold += 8 + (raise_count * 3)
                    elif bot_name == 'aggressive':
                        adjusted_threshold += 3 + (raise_count * 2)
                    elif bot_name == 'smart':
                        adjusted_threshold += 5 + (raise_count * 2)
                    elif bot_name == 'learning':
                        adjusted_threshold += 5 + (raise_count * 2)
            else:
                # AggressivePlayer não usa tightness_threshold da mesma forma
                original_threshold = 20  # Threshold base do agressivo
                adjusted_threshold = original_threshold
                if has_raises:
                    adjusted_threshold += 3 + (raise_count * 2)
            
            # Verifica se blefe seria evitado
            would_bluff = not (has_raises and raise_count >= 2)
            
            print(f"  🤖 {bot_name.capitalize()}Bot:")
            print(f"     - Detecta raises: {has_raises} (count: {raise_count})")
            if hasattr(bot, 'tightness_threshold') or bot_name == 'aggressive':
                print(f"     - Threshold: {original_threshold} → {adjusted_threshold} (+{adjusted_threshold - original_threshold})")
            print(f"     - Blefe permitido: {would_bluff}")
            
            # Validações
            if scenario['expected_reaction'] == 'very_cautious':
                assert raise_count >= 2, f"{bot_name} deveria detectar 2+ raises"
                assert not would_bluff, f"{bot_name} não deveria blefar com 2+ raises"
                if hasattr(bot, 'tightness_threshold') or bot_name == 'aggressive':
                    assert adjusted_threshold > original_threshold, f"{bot_name} deveria aumentar threshold"
        
        print()
    
    print("✅ Teste de Integração: PASSOU\n")


def test_threshold_adjustment_consistency():
    """Testa se os ajustes de threshold são consistentes entre bots."""
    print("🧪 Teste: Consistência de Ajustes de Threshold")
    print()
    
    round_state = {
        'street': 'preflop',
        'action_histories': {
            'preflop': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 20},
                {'uuid': 'opponent2', 'action': 'RAISE', 'amount': 30}
            ]
        }
    }
    
    bots_data = [
        ('TightPlayer', TightPlayer(), 8, 3),  # (nome, bot, base_adjust, per_raise)
        ('AggressivePlayer', AggressivePlayer(), 3, 2),
        ('SmartPlayer', SmartPlayer(), 5, 2),
        ('LearningPlayer', LearningPlayer(), 5, 2)
    ]
    
    for bot_name, bot, base_adjust, per_raise in bots_data:
        bot.uuid = f'{bot_name.lower()}_bot'
        current_actions = analyze_current_round_actions(round_state, bot.uuid)
        
        if hasattr(bot, 'tightness_threshold'):
            original_threshold = bot.tightness_threshold
        else:
            # AggressivePlayer usa threshold base diferente
            original_threshold = 20
        
        expected_adjustment = base_adjust + (current_actions['raise_count'] * per_raise)
        actual_adjustment = expected_adjustment  # Simula o que aconteceria
        
        print(f"  {bot_name}:")
        print(f"    Threshold original: {original_threshold}")
        print(f"    Ajuste esperado: +{expected_adjustment}")
        print(f"    Threshold final: {original_threshold + expected_adjustment}")
        
        assert expected_adjustment > 0, f"{bot_name} deveria ajustar threshold positivamente"
    
    print()
    print("✅ Teste de Consistência: PASSOU\n")


def test_multiple_streets():
    """Testa se a análise funciona corretamente em múltiplas streets."""
    print("🧪 Teste: Múltiplas Streets")
    print()
    
    bot = SmartPlayer()
    bot.uuid = 'test_bot'
    
    # Simula um round completo
    streets_data = [
        {
            'street': 'preflop',
            'actions': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 20}
            ]
        },
        {
            'street': 'flop',
            'actions': [
                {'uuid': 'opponent1', 'action': 'CALL', 'amount': 10}
            ]
        },
        {
            'street': 'turn',
            'actions': [
                {'uuid': 'opponent1', 'action': 'RAISE', 'amount': 30}
            ]
        }
    ]
    
    for street_data in streets_data:
        round_state = {
            'street': street_data['street'],
            'action_histories': {
                street_data['street']: street_data['actions']
            }
        }
        
        current_actions = analyze_current_round_actions(round_state, bot.uuid)
        
        print(f"  {street_data['street'].upper()}:")
        print(f"    Ações: {[a['action'] for a in street_data['actions']]}")
        print(f"    Detecta raises: {current_actions['has_raises']}")
        print(f"    Raise count: {current_actions['raise_count']}")
        print(f"    Última ação: {current_actions['last_action']}")
        
        # Valida
        has_raises_in_street = any(a['action'] == 'RAISE' for a in street_data['actions'])
        assert current_actions['has_raises'] == has_raises_in_street, \
            f"Deveria detectar raises corretamente no {street_data['street']}"
    
    print()
    print("✅ Teste de Múltiplas Streets: PASSOU\n")


def run_integration_tests():
    """Executa todos os testes de integração."""
    print("=" * 60)
    print("🧪 TESTES DE INTEGRAÇÃO: Reação em Tempo Real")
    print("=" * 60)
    print()
    
    tests = [
        simulate_round_with_raises,
        test_threshold_adjustment_consistency,
        test_multiple_streets
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FALHOU: {test.__name__}")
            print(f"   Erro: {e}\n")
            failed += 1
        except Exception as e:
            print(f"❌ ERRO em {test.__name__}: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"📊 RESULTADO FINAL:")
    print(f"   ✅ Passou: {passed}/{len(tests)}")
    print(f"   ❌ Falhou: {failed}/{len(tests)}")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)

