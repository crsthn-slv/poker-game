#!/usr/bin/env python3
"""
Teste final para verificar se a solução funciona.
"""

import sys
import os
import subprocess

def test_solution():
    """Testa se a solução funciona"""
    print("="*60)
    print("TESTE FINAL DA SOLUÇÃO")
    print("="*60)
    
    # Testa com POKER_DEBUG=true
    env = os.environ.copy()
    env['POKER_DEBUG'] = 'true'
    
    print("\n1. Testando importação do HandEvaluator...")
    result1 = subprocess.run(
        [sys.executable, '-c', 
         'import sys; sys.path.insert(0, "."); '
         'from players.hand_evaluator import HandEvaluator; '
         'print("✓ HandEvaluator importado")'],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True
    )
    
    if result1.returncode == 0:
        print("  ✓ HandEvaluator importado com sucesso")
        print(f"  {result1.stdout.strip()}")
    else:
        print("  ✗ Falha na importação do HandEvaluator")
        print(f"  {result1.stderr}")
        return False
    
    print("\n2. Testando importação do win_probability_calculator...")
    result2 = subprocess.run(
        [sys.executable, '-c', 
         'import sys; sys.path.insert(0, "."); '
         'from players.win_probability_calculator import HAS_POKERKIT; '
         'print(f"HAS_POKERKIT={HAS_POKERKIT}")'],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True
    )
    
    if result2.returncode == 0 and 'HAS_POKERKIT=True' in result2.stdout:
        print("  ✓ win_probability_calculator importado com sucesso")
        print(f"  {result2.stdout.strip()}")
    else:
        print("  ✗ Falha na importação do win_probability_calculator")
        print(f"  {result2.stdout}")
        print(f"  {result2.stderr}")
        return False
    
    print("\n3. Verificando se pokerkit está acessível...")
    result3 = subprocess.run(
        [sys.executable, '-c', 
         'import pokerkit; print("✓ pokerkit OK")'],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True
    )
    
    if result3.returncode == 0:
        print("  ✓ pokerkit está acessível")
    else:
        print("  ✗ pokerkit não está acessível")
        print(f"  {result3.stderr}")
        return False
    
    print("\n" + "="*60)
    print("✓ TODOS OS TESTES PASSARAM!")
    print("="*60)
    print("\nA solução está funcionando. Agora teste o jogo com:")
    print("  POKER_DEBUG=true make run-console")
    print("\nA probabilidade de vitória deve aparecer agora!")
    
    return True

if __name__ == '__main__':
    success = test_solution()
    sys.exit(0 if success else 1)

