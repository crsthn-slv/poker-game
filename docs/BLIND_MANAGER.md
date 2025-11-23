# Gerenciador Automático de Blinds

## Visão Geral

O `BlindManager` é um sistema automático que calcula os valores de Small Blind (SB) e Big Blind (BB) de forma proporcional às stacks dos jogadores, garantindo valores estáveis e adequados para o jogo.

## Características

### Cálculo Base
- **BB**: 5% da stack de referência (maior stack na mesa)
- **SB**: Metade do BB
- **Stack de referência**: Sempre a maior stack presente na mesa

### Valores Válidos
Os blinds são arredondados para valores "bonitos" da seguinte lista:
```
[1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000]
```

### Estabilidade
Os blinds só são atualizados quando há mudança significativa:
- O BB calculado muda pelo menos 1 nível na lista de denominações, OU
- A stack de referência varia mais de 10%

Isso evita mudanças frequentes e confusas durante o jogo.

## Exemplos de Cálculo

| Stack Máxima | BB   | SB   | Profundidade (~BB) |
|--------------|------|------|-------------------|
| 100          | 5    | 2    | ~20 BB            |
| 500          | 25   | 12   | ~20 BB            |
| 1.000        | 50   | 25   | ~20 BB            |
| 2.500        | 100  | 50   | ~25 BB            |
| 5.000        | 200  | 100  | ~25 BB            |
| 10.000       | 500  | 250  | ~20 BB            |

## Uso Básico

### Inicialização Simples

```python
from game.blind_manager import BlindManager

# Inicializa com stack de referência
initial_stack = 1000
blind_manager = BlindManager(initial_reference_stack=initial_stack)

# Obtém os blinds calculados
small_blind, big_blind = blind_manager.get_blinds()
print(f"SB: {small_blind}, BB: {big_blind}")
# Output: SB: 5, BB: 10
```

### Uso em Configuração de Jogo

```python
from pypokerengine.api.game import setup_config
from game.blind_manager import BlindManager

initial_stack = 2500

# Calcula blinds automaticamente
blind_manager = BlindManager(initial_reference_stack=initial_stack)
small_blind, big_blind = blind_manager.get_blinds()

# Usa no setup do jogo
config = setup_config(
    max_round=10,
    initial_stack=initial_stack,
    small_blind_amount=small_blind  # Valor calculado automaticamente
)
```

### Atualização Dinâmica

```python
from game.blind_manager import BlindManager

blind_manager = BlindManager(initial_reference_stack=1000)

# Em algum momento durante o jogo, obtém stacks dos jogadores
stacks = [1200, 800, 1500, 900]  # Stacks atuais

# Atualiza os blinds baseado nas stacks atuais
sb, bb, was_updated = blind_manager.update_from_stacks(stacks)

if was_updated:
    print(f"Blinds atualizados: SB={sb}, BB={bb}")
else:
    print(f"Blinds mantidos: SB={sb}, BB={bb}")
```

## API da Classe BlindManager

### Métodos Principais

#### `__init__(initial_reference_stack=None)`
Inicializa o gerenciador com uma stack de referência opcional.

```python
manager = BlindManager(initial_reference_stack=1000)
```

#### `get_blinds()`
Retorna os blinds atuais.

```python
sb, bb = manager.get_blinds()
```

#### `update_from_stacks(stacks)`
Atualiza os blinds baseado em uma lista de stacks dos jogadores.
Retorna `(small_blind, big_blind, was_updated)`.

```python
sb, bb, updated = manager.update_from_stacks([1000, 1500, 800])
```

#### `reset(new_reference_stack=None)`
Reseta o gerenciador com uma nova stack de referência.

```python
manager.reset(new_reference_stack=2000)
```

## Funções Auxiliares

### `calculate_blinds_from_reference_stack(reference_stack)`
Calcula SB e BB diretamente de uma stack de referência, sem usar a classe.

```python
from game.blind_manager import calculate_blinds_from_reference_stack

sb, bb = calculate_blinds_from_reference_stack(500)
print(f"SB: {sb}, BB: {bb}")  # Output: SB: 2, BB: 5
```

### `calculate_blinds_from_stacks(stacks)`
Calcula SB e BB diretamente de uma lista de stacks.

```python
from game.blind_manager import calculate_blinds_from_stacks

sb, bb = calculate_blinds_from_stacks([1000, 1500, 800])
print(f"SB: {sb}, BB: {bb}")  # Output: SB: 10, BB: 20
```

## Integração nos Arquivos do Projeto

O BlindManager já está integrado nos seguintes arquivos:

1. **`game/play_console.py`**: Jogo de console
2. **`game/game.py`**: Jogo básico
3. **`game/game_advanced.py`**: Jogo avançado
4. **`test_100_games.py`**: Testes
5. **`web/server.py`**: Servidor web (calcula automaticamente se não fornecido)

## Objetivos Alcançados

✅ Blinds proporcionais às stacks dos jogadores  
✅ Profundidade de stack inicial em torno de 20-25 BB  
✅ Valores arredondados para denominações "bonitas"  
✅ Estabilidade (evita mudanças frequentes)  
✅ Suporte a stacks entre 100 e 10.000  
✅ Garantia de BB ≥ 1 e SB ≥ 1  

## Validação

Execute os testes para validar a implementação:

```bash
python3 test_blind_manager.py
```

Os testes validam:
- Todos os exemplos práticos fornecidos
- Casos extremos (mínimo, máximo, valores intermediários)
- Arredondamento correto para valores válidos
- Funcionalidade do BlindManager
- Profundidade de stack (~100 BB)

## Observações Importantes

1. **Valores Intermediários**: O sistema permite valores intermediários para SB quando necessário (ex: SB=12 quando BB=25), desde que sejam mais precisos que os valores arredondados.

2. **Caso Especial**: Quando BB=1, ambos SB e BB podem ser 1 (violação da regra SB < BB, mas necessária para stacks muito baixas).

3. **Compatibilidade**: O PyPokerEngine usa apenas `small_blind_amount` na configuração. O big blind é calculado automaticamente pelo engine (geralmente 2x o small blind).

4. **Limitações do PyPokerEngine**: O PyPokerEngine não suporta mudanças dinâmicas de blinds durante o jogo. Os blinds são definidos no início e permanecem fixos. O BlindManager está preparado para atualizações futuras caso isso seja necessário.

