#!/usr/bin/env python3
"""
Teste que simula exatamente a execução do jogo para encontrar o problema.
"""

import sys
import os
import subprocess
import traceback

def test_game_module_execution():
    """Testa a execução real do módulo game.play_console"""
    print("\n" + "="*60)
    print("TESTE: Execução real do módulo game.play_console")
    print("="*60)
    
    # Testa com POKER_DEBUG=true (o caso que falha)
    env = os.environ.copy()
    env['POKER_DEBUG'] = 'true'
    
    print("Executando: python3 -m game.play_console (com POKER_DEBUG=true)")
    print("Aguardando 5 segundos para capturar saída inicial...")
    
    try:
        process = subprocess.Popen(
            [sys.executable, '-m', 'game.play_console'],
            cwd=os.getcwd(),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Lê as primeiras linhas da saída
        import time
        time.sleep(2)  # Aguarda um pouco
        
        # Tenta ler algumas linhas
        output_lines = []
        error_lines = []
        
        # Lê stdout
        try:
            for _ in range(50):  # Lê até 50 linhas
                line = process.stdout.readline()
                if not line:
                    break
                output_lines.append(line.rstrip())
                if len(output_lines) >= 20:  # Limita a 20 linhas
                    break
        except:
            pass
        
        # Lê stderr
        try:
            for _ in range(50):
                line = process.stderr.readline()
                if not line:
                    break
                error_lines.append(line.rstrip())
                if len(error_lines) >= 20:
                    break
        except:
            pass
        
        # Mata o processo
        process.terminate()
        try:
            process.wait(timeout=2)
        except:
            process.kill()
        
        print("\n--- STDOUT (primeiras 20 linhas) ---")
        for line in output_lines[:20]:
            print(line)
        
        if error_lines:
            print("\n--- STDERR (primeiras 20 linhas) ---")
            for line in error_lines[:20]:
                print(line)
        
        # Procura por indicadores de problema
        has_import_error = any('No module named' in line or 'ModuleNotFoundError' in line 
                             for line in output_lines + error_lines)
        has_pokerkit_false = any('HAS_POKERKIT=False' in line 
                                for line in output_lines + error_lines)
        has_win_probability = any('Win probability' in line 
                                 for line in output_lines)
        
        print("\n--- ANÁLISE ---")
        if has_import_error:
            print("✗ Erro de importação detectado")
            return False
        elif has_pokerkit_false:
            print("✗ HAS_POKERKIT=False detectado")
            return False
        elif has_win_probability:
            print("✓ Probabilidade de vitória sendo exibida")
            return True
        else:
            print("? Não foi possível determinar o status")
            return None
            
    except Exception as e:
        print(f"✗ Erro ao executar teste: {e}")
        traceback.print_exc()
        return False

def test_import_at_module_level():
    """Testa importação no nível do módulo (como acontece quando executa -m)"""
    print("\n" + "="*60)
    print("TESTE: Importação no nível do módulo")
    print("="*60)
    
    env = os.environ.copy()
    env['POKER_DEBUG'] = 'true'
    
    # Simula o que acontece quando executa python3 -m game.play_console
    test_code = '''
import sys
import os

# Simula o que acontece quando executa como módulo
# O Python adiciona o diretório do script ao sys.path[0]
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Tenta importar como o jogo faz
try:
    from utils.win_probability_calculator import HAS_POKERKIT, HandEvaluator
    print(f"Importação bem-sucedida: HAS_POKERKIT={HAS_POKERKIT}")
    if HAS_POKERKIT:
        print("SUCCESS: PokerKit disponível")
    else:
        print("FAIL: PokerKit não disponível")
except Exception as e:
    print(f"FAIL: Erro na importação: {e}")
    import traceback
    traceback.print_exc()
'''
    
    result = subprocess.run(
        [sys.executable, '-c', test_code],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    print(f"Exit code: {result.returncode}")
    print("Output:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
    
    if 'SUCCESS' in result.stdout:
        return True
    elif 'FAIL' in result.stdout:
        return False
    else:
        return None

def test_import_with_pypokerengine():
    """Testa se importar pypokerengine antes causa problema"""
    print("\n" + "="*60)
    print("TESTE: Importação com pypokerengine primeiro")
    print("="*60)
    
    env = os.environ.copy()
    env['POKER_DEBUG'] = 'true'
    
    test_code = '''
import sys
import os
sys.path.insert(0, os.getcwd())

# Importa pypokerengine primeiro (como o jogo faz)
from pypokerengine.api.game import setup_config
print("✓ pypokerengine importado")

# Depois tenta importar win_probability_calculator
from utils.win_probability_calculator import HAS_POKERKIT, HandEvaluator
print(f"✓ win_probability_calculator importado: HAS_POKERKIT={HAS_POKERKIT}")

if HAS_POKERKIT:
    print("SUCCESS")
else:
    print("FAIL")
'''
    
    result = subprocess.run(
        [sys.executable, '-c', test_code],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=10
    )
    
    print("Output:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)
    
    return 'SUCCESS' in result.stdout

def main():
    """Executa todos os testes de simulação"""
    print("\n" + "="*60)
    print("TESTES DE SIMULAÇÃO DO JOGO")
    print("="*60)
    print(f"Python: {sys.executable}")
    print(f"Diretório: {os.getcwd()}")
    
    results = []
    
    results.append(("Importação no nível do módulo", test_import_at_module_level()))
    results.append(("Importação com pypokerengine", test_import_with_pypokerengine()))
    results.append(("Execução real do jogo", test_game_module_execution()))
    
    print("\n" + "="*60)
    print("RESUMO")
    print("="*60)
    
    for name, result in results:
        if result is True:
            status = "✓ PASSOU"
        elif result is False:
            status = "✗ FALHOU"
        else:
            status = "? INDETERMINADO"
        print(f"  {status}: {name}")
    
    all_passed = all(r is True for _, r in results)
    if all_passed:
        print("\n✓ Todos os testes passaram!")
    else:
        print("\n✗ Alguns testes falharam. Verifique os detalhes acima.")
    
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

