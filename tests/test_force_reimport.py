#!/usr/bin/env python3
"""
Teste que força reimportação e verifica problemas de cache.
"""

import sys
import os
import importlib

def test_force_reimport():
    """Força reimportação dos módulos para verificar problemas de cache"""
    print("\n" + "="*60)
    print("TESTE: Força reimportação")
    print("="*60)
    
    # Limpa todos os módulos relacionados
    modules_to_remove = [
        'pokerkit',
        'pokerkit.utilities',
        'players',
        'players.hand_evaluator',
        'players.win_probability_calculator',
    ]
    
    for mod in list(sys.modules.keys()):
        if any(mod.startswith(m) for m in modules_to_remove):
            print(f"  Removendo módulo do cache: {mod}")
            del sys.modules[mod]
    
    # Tenta importar novamente
    try:
        sys.path.insert(0, os.getcwd())
        
        # Força importação do pokerkit primeiro
        import pokerkit
        print(f"✓ pokerkit importado: {pokerkit.__file__}")
        
        # Força importação do HandEvaluator
        from utils.hand_evaluator import HandEvaluator
        print("✓ HandEvaluator importado")
        
        # Força importação do win_probability_calculator
        importlib.reload(sys.modules.get('players.win_probability_calculator', None))
        from utils.win_probability_calculator import HAS_POKERKIT, HandEvaluator as HE
        print(f"✓ win_probability_calculator importado: HAS_POKERKIT={HAS_POKERKIT}")
        
        if HAS_POKERKIT:
            print("\n✓ SUCCESS: Reimportação funcionou")
            return True
        else:
            print("\n✗ FAIL: HAS_POKERKIT=False após reimportação")
            return False
            
    except Exception as e:
        print(f"\n✗ FAIL: Erro na reimportação: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_import_with_explicit_path():
    """Testa importação com caminho explícito"""
    print("\n" + "="*60)
    print("TESTE: Importação com caminho explícito")
    print("="*60)
    
    try:
        # Adiciona explicitamente o site-packages ao path
        import site
        site_packages = site.getsitepackages()
        print(f"Site packages encontrados: {site_packages}")
        
        for sp in site_packages:
            if sp not in sys.path:
                sys.path.insert(0, sp)
                print(f"  Adicionado ao path: {sp}")
        
        # Tenta importar
        import pokerkit
        print(f"✓ pokerkit importado: {pokerkit.__file__}")
        
        from utils.hand_evaluator import HandEvaluator
        print("✓ HandEvaluator importado")
        
        from utils.win_probability_calculator import HAS_POKERKIT
        print(f"✓ HAS_POKERKIT={HAS_POKERKIT}")
        
        if HAS_POKERKIT:
            print("\n✓ SUCCESS")
            return True
        else:
            print("\n✗ FAIL")
            return False
            
    except Exception as e:
        print(f"\n✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bytecode_cache():
    """Verifica se há problemas com cache de bytecode"""
    print("\n" + "="*60)
    print("TESTE: Verificação de cache de bytecode")
    print("="*60)
    
    import py_compile
    import glob
    
    # Procura por arquivos .pyc
    pyc_files = glob.glob('**/*.pyc', recursive=True)
    pycache_dirs = glob.glob('**/__pycache__', recursive=True)
    
    print(f"Arquivos .pyc encontrados: {len(pyc_files)}")
    print(f"Diretórios __pycache__ encontrados: {len(pycache_dirs)}")
    
    if pycache_dirs:
        print("\nDiretórios __pycache__:")
        for d in pycache_dirs[:10]:  # Mostra até 10
            print(f"  {d}")
    
    # Verifica se há .pyc para os módulos problemáticos
    problematic_pyc = [
        'players/__pycache__/hand_evaluator.cpython-*.pyc',
        'players/__pycache__/win_probability_calculator.cpython-*.pyc',
    ]
    
    found_problematic = False
    for pattern in problematic_pyc:
        files = glob.glob(pattern)
        if files:
            print(f"\n⚠ Arquivos .pyc encontrados para: {pattern}")
            for f in files:
                print(f"  {f}")
            found_problematic = True
    
    if found_problematic:
        print("\n⚠ Cache de bytecode pode estar causando problemas")
        print("  Solução: Remover arquivos .pyc e __pycache__")
        return False
    else:
        print("\n✓ Nenhum problema de cache detectado")
        return True

def main():
    """Executa testes de reimportação"""
    print("\n" + "="*60)
    print("TESTES DE REIMPORTAÇÃO E CACHE")
    print("="*60)
    
    results = []
    results.append(("Força reimportação", test_force_reimport()))
    results.append(("Importação com caminho explícito", test_import_with_explicit_path()))
    results.append(("Verificação de cache", test_bytecode_cache()))
    
    print("\n" + "="*60)
    print("RESUMO")
    print("="*60)
    
    for name, result in results:
        status = "✓ PASSOU" if result else "✗ FALHOU"
        print(f"  {status}: {name}")
    
    all_passed = all(results)
    return all_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

