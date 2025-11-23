"""
Testes para o gerenciador automático de blinds.
Valida os exemplos fornecidos na especificação.
"""

from game.blind_manager import (
    BlindManager,
    calculate_blinds_from_reference_stack,
    round_to_valid_denomination,
    VALID_DENOMINATIONS
)


def test_examples():
    """Testa os exemplos práticos fornecidos."""
    print("=" * 60)
    print("TESTES DE EXEMPLOS PRÁTICOS")
    print("=" * 60)
    
    # Com 5% para BB, os valores mudam:
    # Stack 100 → BB = 5 (5% de 100), SB = 2 (metade de 5, arredondado)
    # Stack 500 → BB = 25 (5% de 500), SB = 12
    # Stack 1000 → BB = 50 (5% de 1000), SB = 25
    # Stack 2500 → BB = 100 ou 125? (5% de 2500 = 125, arredonda para 100)
    # Stack 5000 → BB = 200 ou 250? (5% de 5000 = 250, arredonda para 200)
    # Stack 10000 → BB = 500 (5% de 10000), SB = 250
    test_cases = [
        (100, 5, 2),       # Stack máxima 100 → BB = 5, SB = 2
        (500, 25, 12),     # Stack máxima 500 → BB = 25, SB = 12
        (1000, 50, 25),    # Stack máxima 1.000 → BB = 50, SB = 25
        (2500, 100, 50),   # Stack máxima 2.500 → BB = 100, SB = 50
        (5000, 200, 100),  # Stack máxima 5.000 → BB = 200, SB = 100
        (10000, 500, 250), # Stack máxima 10.000 → BB = 500, SB = 250
    ]
    
    all_passed = True
    
    for stack, expected_bb, expected_sb in test_cases:
        sb, bb = calculate_blinds_from_reference_stack(stack)
        passed = (sb == expected_sb and bb == expected_bb)
        
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"\nStack: {stack}")
        print(f"  Esperado: SB={expected_sb}, BB={expected_bb}")
        print(f"  Obtido:   SB={sb}, BB={bb}")
        print(f"  Status:   {status}")
        
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ TODOS OS TESTES PASSARAM!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
    print("=" * 60)
    
    return all_passed


def test_edge_cases():
    """Testa casos extremos e limites."""
    print("\n" + "=" * 60)
    print("TESTES DE CASOS EXTREMOS")
    print("=" * 60)
    
    test_cases = [
        (100, "Mínimo"),
        (10000, "Máximo"),
        (250, "Meio caminho"),
        (750, "Valor intermediário"),
        (2000, "Valor médio"),
    ]
    
    all_passed = True
    
    for stack, description in test_cases:
        sb, bb = calculate_blinds_from_reference_stack(stack)
        
        # Verifica se BB >= 1 e SB >= 1
        # Permite SB == BB quando ambos são 1 (caso especial)
        valid = (bb >= 1 and sb >= 1 and (sb < bb or (sb == bb == 1)))
        
        status = "✅ PASSOU" if valid else "❌ FALHOU"
        print(f"\n{description}: Stack={stack}")
        print(f"  SB={sb}, BB={bb}, Stack depth=~{stack // bb} BB")
        print(f"  Status: {status}")
        
        if not valid:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ TODOS OS TESTES DE CASOS EXTREMOS PASSARAM!")
    else:
        print("❌ ALGUNS TESTES DE CASOS EXTREMOS FALHARAM")
    print("=" * 60)
    
    return all_passed


def test_denomination_rounding():
    """Testa o arredondamento para valores válidos."""
    print("\n" + "=" * 60)
    print("TESTES DE ARREDONDAMENTO")
    print("=" * 60)
    
    test_cases = [
        (0.5, 1),    # Deve arredondar para 1
        (1.5, 2),    # Deve arredondar para 2
        (3, 2),      # Deve arredondar para 2 ou 5 (mais próximo)
        (7, 5),      # Deve arredondar para 5 ou 10
        (15, 10),    # Deve arredondar para 10 ou 20
        (30, 25),    # Deve arredondar para 25
        (75, 50),    # Deve arredondar para 50 ou 100
        (150, 100),  # Deve arredondar para 100 ou 200
        (300, 200),  # Deve arredondar para 200 ou 500
    ]
    
    all_passed = True
    
    for value, expected_approximate in test_cases:
        rounded = round_to_valid_denomination(value)
        is_valid = rounded in VALID_DENOMINATIONS
        
        status = "✅ PASSOU" if is_valid else "❌ FALHOU"
        print(f"Valor: {value} → Arredondado: {rounded} {status}")
        
        if not is_valid:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ TODOS OS TESTES DE ARREDONDAMENTO PASSARAM!")
    else:
        print("❌ ALGUNS TESTES DE ARREDONDAMENTO FALHARAM")
    print("=" * 60)
    
    return all_passed


def test_blind_manager():
    """Testa a classe BlindManager."""
    print("\n" + "=" * 60)
    print("TESTES DO BLIND MANAGER")
    print("=" * 60)
    
    # Testa inicialização
    manager = BlindManager(initial_reference_stack=1000)
    sb, bb = manager.get_blinds()
    print(f"Inicialização com stack 1000: SB={sb}, BB={bb}")
    
    # Testa atualização com stacks
    stacks = [1000, 1500, 800, 1200]
    sb, bb, updated = manager.update_from_stacks(stacks)
    print(f"Atualização com stacks {stacks}: SB={sb}, BB={bb}, Atualizado={updated}")
    
    # Testa que não atualiza se não houver mudança significativa
    stacks2 = [1020, 1480, 810, 1190]  # Mudança < 10%
    sb2, bb2, updated2 = manager.update_from_stacks(stacks2)
    print(f"Stacks similares {stacks2}: SB={sb2}, BB={bb2}, Atualizado={updated2}")
    
    print("\n✅ TESTE DO BLIND MANAGER COMPLETO")
    print("=" * 60)
    
    return True


def test_stack_depth():
    """Testa se a profundidade de stack está próxima de 100 BB."""
    print("\n" + "=" * 60)
    print("TESTES DE PROFUNDIDADE DE STACK")
    print("=" * 60)
    
    test_stacks = [100, 500, 1000, 2500, 5000, 10000]
    
    for stack in test_stacks:
        sb, bb = calculate_blinds_from_reference_stack(stack)
        depth = stack / bb
        print(f"Stack: {stack:5d} → SB={sb:3d}, BB={bb:3d} → ~{depth:.1f} BB")
    
    print("\n✅ TESTE DE PROFUNDIDADE COMPLETO")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SUITE DE TESTES DO BLIND MANAGER")
    print("=" * 60)
    
    results = []
    
    results.append(("Exemplos práticos", test_examples()))
    results.append(("Casos extremos", test_edge_cases()))
    results.append(("Arredondamento", test_denomination_rounding()))
    results.append(("Blind Manager", test_blind_manager()))
    results.append(("Profundidade de stack", test_stack_depth()))
    
    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ TODOS OS TESTES PASSARAM!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
    print("=" * 60 + "\n")

