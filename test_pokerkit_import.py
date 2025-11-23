#!/usr/bin/env python3
"""
Script de teste para diagnosticar problemas de importação do pokerkit.
"""

import sys
import os
import subprocess
import traceback

def test_1_direct_pokerkit_import():
    """Teste 1: Importação direta do pokerkit"""
    print("\n" + "="*60)
    print("TESTE 1: Importação direta do pokerkit")
    print("="*60)
    try:
        import pokerkit
        print("✓ pokerkit importado com sucesso")
        print(f"  Localização: {pokerkit.__file__}")
        from pokerkit import StandardHighHand
        print("✓ StandardHighHand importado com sucesso")
        return True
    except Exception as e:
        print(f"✗ Erro: {e}")
        traceback.print_exc()
        return False

def test_2_hand_evaluator_import():
    """Teste 2: Importação do HandEvaluator"""
    print("\n" + "="*60)
    print("TESTE 2: Importação do HandEvaluator")
    print("="*60)
    try:
        # Adiciona o diretório atual ao path
        sys.path.insert(0, os.getcwd())
        from players.hand_evaluator import HandEvaluator
        print("✓ HandEvaluator importado com sucesso")
        evaluator = HandEvaluator()
        print("✓ HandEvaluator instanciado com sucesso")
        return True
    except Exception as e:
        print(f"✗ Erro: {e}")
        traceback.print_exc()
        return False

def test_3_win_probability_calculator_import():
    """Teste 3: Importação do win_probability_calculator"""
    print("\n" + "="*60)
    print("TESTE 3: Importação do win_probability_calculator")
    print("="*60)
    try:
        sys.path.insert(0, os.getcwd())
        from players.win_probability_calculator import HAS_POKERKIT, HandEvaluator
        print(f"✓ win_probability_calculator importado")
        print(f"  HAS_POKERKIT: {HAS_POKERKIT}")
        print(f"  HandEvaluator: {HandEvaluator}")
        if HAS_POKERKIT and HandEvaluator:
            print("✓ PokerKit disponível")
            return True
        else:
            print("✗ PokerKit não disponível")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        traceback.print_exc()
        return False

def test_4_module_execution_without_debug():
    """Teste 4: Execução como módulo sem debug"""
    print("\n" + "="*60)
    print("TESTE 4: Execução como módulo (sem POKER_DEBUG)")
    print("="*60)
    try:
        # Remove POKER_DEBUG se existir
        env = os.environ.copy()
        if 'POKER_DEBUG' in env:
            del env['POKER_DEBUG']
        
        # Executa importação do módulo
        result = subprocess.run(
            [sys.executable, '-c', 
             'import sys; sys.path.insert(0, "."); '
             'from players.win_probability_calculator import HAS_POKERKIT; '
             'print(f"HAS_POKERKIT={HAS_POKERKIT}")'],
            cwd=os.getcwd(),
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0 and 'HAS_POKERKIT=True' in result.stdout:
            print("✓ Módulo executado com sucesso (sem debug)")
            return True
        else:
            print("✗ Módulo falhou (sem debug)")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        traceback.print_exc()
        return False

def test_5_module_execution_with_debug():
    """Teste 5: Execução como módulo com debug"""
    print("\n" + "="*60)
    print("TESTE 5: Execução como módulo (com POKER_DEBUG=true)")
    print("="*60)
    try:
        env = os.environ.copy()
        env['POKER_DEBUG'] = 'true'
        
        result = subprocess.run(
            [sys.executable, '-c', 
             'import sys; sys.path.insert(0, "."); '
             'from players.win_probability_calculator import HAS_POKERKIT; '
             'print(f"HAS_POKERKIT={HAS_POKERKIT}")'],
            cwd=os.getcwd(),
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"Exit code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0 and 'HAS_POKERKIT=True' in result.stdout:
            print("✓ Módulo executado com sucesso (com debug)")
            return True
        else:
            print("✗ Módulo falhou (com debug)")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        traceback.print_exc()
        return False

def test_6_python_path_analysis():
    """Teste 6: Análise do sys.path"""
    print("\n" + "="*60)
    print("TESTE 6: Análise do sys.path")
    print("="*60)
    try:
        import pokerkit
        pokerkit_path = pokerkit.__file__
        print(f"✓ pokerkit encontrado em: {pokerkit_path}")
        
        print("\n  sys.path:")
        for i, path in enumerate(sys.path):
            marker = "✓" if pokerkit_path.startswith(path) else " "
            print(f"    {marker} [{i}] {path}")
        
        # Verifica se o caminho do pokerkit está no sys.path
        pokerkit_dir = os.path.dirname(pokerkit_path)
        if pokerkit_dir in sys.path:
            print(f"\n✓ Diretório do pokerkit está no sys.path")
            return True
        else:
            print(f"\n✗ Diretório do pokerkit NÃO está no sys.path")
            print(f"  Diretório necessário: {pokerkit_dir}")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        traceback.print_exc()
        return False

def test_7_import_order():
    """Teste 7: Ordem de importação"""
    print("\n" + "="*60)
    print("TESTE 7: Teste de ordem de importação")
    print("="*60)
    try:
        # Simula a ordem de importação do jogo
        sys.path.insert(0, os.getcwd())
        
        # Primeiro importa o que o jogo importa
        from pypokerengine.api.game import setup_config
        print("✓ pypokerengine importado")
        
        # Depois tenta importar HandEvaluator
        from players.hand_evaluator import HandEvaluator
        print("✓ HandEvaluator importado após pypokerengine")
        
        # Depois tenta importar win_probability_calculator
        from players.win_probability_calculator import HAS_POKERKIT
        print(f"✓ win_probability_calculator importado, HAS_POKERKIT={HAS_POKERKIT}")
        
        if HAS_POKERKIT:
            print("✓ Ordem de importação OK")
            return True
        else:
            print("✗ Ordem de importação causou problema")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        traceback.print_exc()
        return False

def test_8_multiple_imports():
    """Teste 8: Múltiplas importações (simula execução repetida)"""
    print("\n" + "="*60)
    print("TESTE 8: Múltiplas importações (simula execução repetida)")
    print("="*60)
    try:
        sys.path.insert(0, os.getcwd())
        
        results = []
        for i in range(5):
            # Limpa módulos importados
            modules_to_remove = [k for k in sys.modules.keys() 
                               if k.startswith('players.') or k == 'pokerkit']
            for mod in modules_to_remove:
                del sys.modules[mod]
            
            # Tenta importar novamente
            from players.win_probability_calculator import HAS_POKERKIT
            results.append(HAS_POKERKIT)
            print(f"  Tentativa {i+1}: HAS_POKERKIT={HAS_POKERKIT}")
        
        if all(results):
            print("✓ Todas as importações funcionaram")
            return True
        else:
            print(f"✗ Algumas importações falharam: {results}")
            return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        traceback.print_exc()
        return False

def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("DIAGNÓSTICO DE IMPORTAÇÃO DO POKERKIT")
    print("="*60)
    print(f"Python: {sys.executable}")
    print(f"Versão: {sys.version}")
    print(f"Diretório atual: {os.getcwd()}")
    
    results = []
    
    results.append(("Importação direta pokerkit", test_1_direct_pokerkit_import()))
    results.append(("Importação HandEvaluator", test_2_hand_evaluator_import()))
    results.append(("Importação win_probability_calculator", test_3_win_probability_calculator_import()))
    results.append(("Análise sys.path", test_6_python_path_analysis()))
    results.append(("Ordem de importação", test_7_import_order()))
    results.append(("Múltiplas importações", test_8_multiple_imports()))
    results.append(("Módulo sem debug", test_4_module_execution_without_debug()))
    results.append(("Módulo com debug", test_5_module_execution_with_debug()))
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSOU" if result else "✗ FALHOU"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n✓ Todos os testes passaram! O problema pode estar em outro lugar.")
    else:
        print("\n✗ Alguns testes falharam. Verifique os detalhes acima.")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

