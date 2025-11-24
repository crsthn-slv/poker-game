"""
Testa se os valores de threshold por personalidade estão corretos.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re


def test_personality_thresholds():
    """Verifica se os thresholds estão corretos por personalidade."""
    print("=" * 60)
    print("🧪 TESTE: Valores de Threshold por Personalidade")
    print("=" * 60)
    print()
    
    expected_thresholds = {
        'tight_player.py': 32,
        'cautious_player.py': 30,
        'patient_player.py': 28,
        'aggressive_player.py': 22,
        'steady_aggressive_player.py': 24,
        'opportunistic_player.py': 23,
        'smart_player.py': 28,
        'learning_player.py': 27,
        'calculated_player.py': 28,
        'thoughtful_player.py': 27,
        'balanced_player.py': 26,
        'moderate_player.py': 26,
        'flexible_player.py': 25,
        'steady_player.py': 26,
        'adaptive_player.py': 25,
        'hybrid_player.py': 25,
        'conservative_aggressive_player.py': 29,
        'calm_player.py': 27,
        'observant_player.py': 26,
        'random_player.py': 24,
        'fish_player.py': 23,
    }
    
    all_ok = True
    for bot_file, expected_threshold in expected_thresholds.items():
        filepath = f'players/{bot_file}'
        if not os.path.exists(filepath):
            print(f"⚠️  {bot_file}: Arquivo não encontrado")
            all_ok = False
            continue
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Procura pelo threshold na lógica de blefe
        pattern = r'if hand_strength >= (\d+):\s*# .*paga.*blefe'
        match = re.search(pattern, content)
        
        if match:
            found_threshold = int(match.group(1))
            if found_threshold == expected_threshold:
                print(f"✅ {bot_file}: threshold={found_threshold} (correto)")
            else:
                print(f"❌ {bot_file}: threshold={found_threshold} (esperado: {expected_threshold})")
                all_ok = False
        else:
            # Tenta padrão alternativo
            pattern2 = r'if hand_strength >= (\d+):\s*# .*[Bb]lefe'
            match2 = re.search(pattern2, content)
            if match2:
                found_threshold = int(match2.group(1))
                if found_threshold == expected_threshold:
                    print(f"✅ {bot_file}: threshold={found_threshold} (correto)")
                else:
                    print(f"❌ {bot_file}: threshold={found_threshold} (esperado: {expected_threshold})")
                    all_ok = False
            else:
                print(f"⚠️  {bot_file}: Threshold não encontrado no código")
                all_ok = False
    
    print()
    print("=" * 60)
    if all_ok:
        print("✅ Todos os thresholds estão corretos!")
    else:
        print("⚠️  Alguns thresholds precisam de ajuste")
    print("=" * 60)
    
    return all_ok


def test_all_bots_have_bluff_analysis():
    """Verifica se todos os bots têm análise de blefe."""
    print()
    print("=" * 60)
    print("🧪 TESTE: Verificação de Análise de Blefe em Todos os Bots")
    print("=" * 60)
    print()
    
    bots = [f for f in os.listdir('players') 
            if f.endswith('_player.py') and f != 'console_player.py']
    
    all_ok = True
    for bot_file in sorted(bots):
        filepath = f'players/{bot_file}'
        with open(filepath, 'r') as f:
            content = f.read()
        
        has_analysis = 'analyze_possible_bluff' in content
        has_logic = 'bluff_analysis' in content and 'should_call_bluff' in content
        
        if has_analysis and has_logic:
            print(f"✅ {bot_file}: Análise de blefe implementada")
        else:
            print(f"❌ {bot_file}: Falta análise de blefe")
            all_ok = False
    
    print()
    print("=" * 60)
    if all_ok:
        print("✅ Todos os bots têm análise de blefe!")
    else:
        print("⚠️  Alguns bots precisam de implementação")
    print("=" * 60)
    
    return all_ok


if __name__ == '__main__':
    test1 = test_personality_thresholds()
    test2 = test_all_bots_have_bluff_analysis()
    
    print()
    if test1 and test2:
        print("🎉 Todos os testes passaram!")
    else:
        print("⚠️  Alguns testes falharam")

