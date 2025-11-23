# Documentação de Algoritmos e Cálculos por Etapa do Jogo

Esta documentação detalha todos os algoritmos, cálculos e métodos utilizados em cada etapa do jogo de poker (Preflop, Flop, Turn e River).

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [PREFLOP](#preflop)
3. [FLOP](#flop)
4. [TURN](#turn)
5. [RIVER](#river)
6. [Algoritmos Compartilhados](#algoritmos-compartilhados)
7. [Bibliotecas Utilizadas](#bibliotecas-utilizadas)

---

## Visão Geral

O sistema utiliza três abordagens principais para avaliação de mãos:

1. **Avaliação Heurística** (`hand_utils.py`): Cálculo rápido baseado em regras simples
2. **PokerKit** (`hand_evaluator.py`): Avaliação precisa usando biblioteca especializada
3. **Simulação Monte Carlo** (`win_probability_calculator.py`): Estimativa de probabilidade de vitória

---

## PREFLOP

**Cartas disponíveis:** Apenas 2 hole cards (cartas do jogador)

### 1. Nome da Mão (`get_hand_strength_heuristic`)

**Algoritmo:** Verificação simples de par

```python
# players/console_formatter.py, linhas 376-385
card_ranks = [card[1] for card in hole_cards]

if card_ranks[0] == card_ranks[1]:
    return "One Pair"
else:
    return "High Card"
```

**Lógica:**
- Se os ranks das 2 cartas são iguais → `"One Pair"`
- Caso contrário → `"High Card"`

**Não usa PokerKit** porque não há cartas comunitárias suficientes para formar uma mão completa.

---

### 2. Nível de Força (`get_hand_strength_level`)

**Algoritmo:** Avaliação heurística baseada em características das hole cards

**Fonte:** `hand_utils.evaluate_hand_strength()`

#### Tabela de Pontuação:

| Característica | Score | Descrição |
|----------------|-------|-----------|
| **Par** | 50-62 | Base: 50 + valor do rank (2-14) |
| **Duas cartas altas** (A, K, Q, J) | 45 | Ambas são A, K, Q ou J |
| **Uma carta alta** | 30 | Apenas uma é A, K, Q ou J |
| **Mesmo naipe** | 20 | Suited (mesmo naipe) |
| **Cartas baixas** | 10 | Nenhuma carta alta |

#### Conversão para Nível:

```python
# players/console_formatter.py, linhas 422-429
if base_strength >= 70:
    return "Excellent"
elif base_strength >= 50:
    return "Good"
elif base_strength >= 30:
    return "Fair"
else:
    return "Poor"
```

**Exemplos:**
- `A♥ 7♠`: Uma carta alta → Score 30 → `"Fair"`
- `A♥ K♠`: Duas cartas altas → Score 45 → `"Good"`
- `A♥ A♠`: Par de Ás → Score 50+14=64 → `"Good"`
- `7♠ 2♣`: Cartas baixas → Score 10 → `"Poor"`

---

### 3. Probabilidade de Vitória (`calculate_win_probability_for_player`)

**Algoritmo:** Simulação Monte Carlo adaptativa com PokerKit

**Parâmetros:**
- `num_simulations`: Calculado dinamicamente por street (padrão)
  - Preflop: 2000 simulações
  - Flop: 2000 simulações
  - Turn: 1500 simulações
  - River: 1000 simulações
- `use_parallel`: Ativa paralelização (padrão: False)
- `return_confidence`: Retorna intervalo de confiança (padrão: False)

**Otimizações Implementadas:**

1. **Lazy Loading do HandEvaluator:**
   - Instância singleton criada apenas quando necessário
   - Reutilizada em todas as chamadas

2. **Cache de Conversões:**
   - Função `_pypoker_to_pokerkit_cached()` com `@lru_cache(maxsize=128)`
   - Cache compartilhado entre todas as instâncias
   - Acelera conversões repetidas de cartas

3. **Early Exit Adaptativo:**
   - Para quando margem de erro ≤ 2% (configurável)
   - Verifica a cada 50 simulações após mínimo de 100
   - Reduz tempo de cálculo quando precisão já é suficiente

4. **Paralelização Opcional:**
   - Usa `ProcessPoolExecutor` para simulações paralelas
   - Ativada apenas para 500+ simulações (reduz overhead)
   - Suporta early exit mesmo em modo paralelo

#### Processo:

1. **Preparação:**
   ```python
   # Obtém HandEvaluator (lazy loading singleton)
   hand_evaluator = _get_hand_evaluator()
   
   # Gera deck completo (52 cartas)
   full_deck = [f"{suit}{rank}" for suit in ['S','H','D','C'] 
                                     for rank in ['2','3',...,'A']]
   
   # Remove cartas conhecidas (hole cards + community cards)
   known_cards = set(player_cards + community_cards)
   remaining_deck = [card for card in full_deck if card not in known_cards]
   ```

2. **Para cada simulação (com early exit):**
   ```python
   # Seleciona cartas necessárias de uma vez (mais eficiente)
   selected_cards = random.sample(remaining_deck, 
                                  needed_community_cards + cards_needed_for_opponents)
   
   # Completa cartas comunitárias
   simulated_community = list(community_cards)
   simulated_community.extend(selected_cards[:needed_community_cards])
   
   # Simula cartas dos oponentes
   for opponent in active_opponents:
       opponent_cards = selected_cards[card_index:card_index+2]
       card_index += 2
   ```

3. **Avaliação:**
   ```python
   # Avalia mão do jogador (usa cache de conversões)
   player_score = hand_evaluator.evaluate(player_cards, simulated_community)
   
   # Avalia mão de cada oponente
   for opponent_cards in opponents:
       opponent_score = hand_evaluator.evaluate(opponent_cards, simulated_community)
       
       # Compara: menor score = melhor mão
       if opponent_score < player_score:
           player_loses = True
           break
   ```

4. **Early Exit (a cada 50 simulações após mínimo de 100):**
   ```python
   if simulation_num >= min_simulations and (simulation_num + 1) % 50 == 0:
       margin = calculate_confidence_interval(wins, simulation_num + 1)
       if margin <= 0.02:  # 2% de margem de erro
           num_simulations = simulation_num + 1
           break  # Para early
   ```

5. **Resultado:**
   ```python
   win_probability = wins / num_simulations  # Ex: 840/2000 = 0.42 = 42%
   
   # Com intervalo de confiança (preflop)
   if return_confidence:
       return {
           'prob': win_probability,
           'min': min_prob,
           'max': max_prob,
           'margin': margin
       }
   ```

**Complexidade:** O(n × m × k)
- n = número de simulações (2000 preflop, adaptativo com early exit)
- m = número de oponentes (3)
- k = avaliação PokerKit (~O(1), otimizada com cache)

**Tempo estimado:**
- Preflop: ~200-400ms (com early exit pode ser menor)
- Flop: ~150-300ms
- Turn: ~100-200ms
- River: ~50-100ms
- Com paralelização: ~2-4x mais rápido (depende do hardware)

---

## FLOP

**Cartas disponíveis:** 2 hole cards + 3 cartas comunitárias (5 cartas no total)

### 1. Nome da Mão (`get_hand_strength_heuristic`)

**Algoritmo:** Avaliação completa usando PokerKit

**Condição:** `if community_cards and len(community_cards) >= 3`

#### Processo:

1. **Conversão de formato:**
   ```python
   # PyPokerEngine: 'SA' (Suit + Rank)
   # PokerKit: 'As' (Rank + suit lowercase)
   
   hole_str = 'AsKh'  # Exemplo: A♠ K♥
   board_str = '2d3c4s'  # Exemplo: 2♦ 3♣ 4♠
   ```

2. **Avaliação PokerKit:**
   ```python
   hand_obj = StandardHighHand.from_game(hole_str, board_str)
   score = max_index - hand_obj.entry.index  # Inverte: menor = melhor
   ```

3. **Mapeamento de Score para Nome:**
   ```python
   # players/console_formatter.py, linhas 353-372
   if score <= 1:
       return "Royal Flush"
   elif score <= 10:
       return "Straight Flush"
   elif score <= 166:
       return "Four of a Kind"
   elif score <= 322:
       return "Full House"
   elif score <= 1599:
       return "Flush"
   elif score <= 1609:
       return "Straight"
   elif score <= 2467:
       return "Three of a Kind"
   elif score <= 3325:
       return "Two Pair"
   elif score <= 6185:
       return "One Pair"
   else:
       return "High Card"
   ```

**Tabela de Scores PokerKit:**

| Mão | Score Range | Exemplo |
|-----|-------------|---------|
| Royal Flush | 0-1 | A♠ K♠ Q♠ J♠ T♠ |
| Straight Flush | 2-10 | 9♠ 8♠ 7♠ 6♠ 5♠ |
| Four of a Kind | 11-166 | A♠ A♥ A♦ A♣ K♠ |
| Full House | 167-322 | A♠ A♥ A♦ K♠ K♥ |
| Flush | 323-1599 | A♠ K♠ Q♠ J♠ 9♠ |
| Straight | 1600-1609 | A♠ K♥ Q♦ J♣ T♠ |
| Three of a Kind | 1610-2467 | A♠ A♥ A♦ K♠ Q♠ |
| Two Pair | 2468-3325 | A♠ A♥ K♠ K♥ Q♠ |
| One Pair | 3326-6185 | A♠ A♥ K♠ Q♠ J♠ |
| High Card | 6186-7462 | A♠ K♥ Q♦ J♣ 9♠ |

---

### 2. Nível de Força (`get_hand_strength_level`)

**Algoritmo:** Mapeamento direto do score PokerKit

```python
# players/console_formatter.py, linhas 406-413
if score <= 166:  # Royal Flush até Four of a Kind
    return "Excellent"
elif score <= 2467:  # Full House até Three of a Kind
    return "Good"
elif score <= 3325:  # Flush até Two Pair
    return "Fair"
else:  # One Pair ou High Card
    return "Poor"
```

**Exemplos:**
- Royal Flush (score 1) → `"Excellent"`
- Full House (score 200) → `"Good"`
- Flush (score 500) → `"Fair"`
- One Pair (score 5000) → `"Poor"`

---

### 3. Probabilidade de Vitória

**Algoritmo:** Monte Carlo adaptativo com early exit

**Diferenças:**
- Cartas comunitárias já conhecidas (3 cartas)
- Deck restante menor: 52 - 2 (hole) - 3 (flop) = 47 cartas
- Simula apenas 2 cartas comunitárias faltantes (turn + river)
- Número de simulações: 2000 (padrão, pode ser menor com early exit)

**Processo:**
```python
# Cartas conhecidas agora incluem o flop
known_cards = set(player_cards + community_cards)  # 5 cartas
remaining_deck = [card for card in full_deck if card not in known_cards]  # 47 cartas

# Para cada simulação (com early exit):
# 1. Seleciona cartas necessárias de uma vez (mais eficiente)
selected_cards = random.sample(remaining_deck, 
                                needed_community_cards + cards_needed_for_opponents)

# 2. Completa apenas turn + river (2 cartas)
simulated_community = list(community_cards)  # Já tem 3
simulated_community.extend(selected_cards[:needed_community_cards])  # Adiciona 2

# 3. Resto do processo igual ao preflop (com early exit)
```

**Precisão:** Mais precisa que no preflop (menos incerteza)
**Tempo:** ~150-300ms (pode ser menor com early exit)

---

## TURN

**Cartas disponíveis:** 2 hole cards + 4 cartas comunitárias (6 cartas no total)

### 1. Nome da Mão

**Algoritmo:** Idêntico ao Flop (PokerKit)

**Diferença:** Agora há 4 cartas comunitárias, então a avaliação é ainda mais precisa.

### 2. Nível de Força

**Algoritmo:** Idêntico ao Flop

### 3. Probabilidade de Vitória

**Algoritmo:** Monte Carlo adaptativo com early exit

**Diferenças:**
- Deck restante: 52 - 2 (hole) - 4 (turn) = 46 cartas
- Simula apenas 1 carta comunitária faltante (river)
- Número de simulações: 1500 (padrão, pode ser menor com early exit)

**Precisão:** Muito mais precisa que Flop
**Tempo:** ~100-200ms (pode ser menor com early exit)

---

## RIVER

**Cartas disponíveis:** 2 hole cards + 5 cartas comunitárias (7 cartas no total)

### 1. Nome da Mão

**Algoritmo:** Idêntico ao Flop/Turn (PokerKit)

**Diferença:** Mão completa! Não há mais incerteza sobre a mão final.

### 2. Nível de Força

**Algoritmo:** Idêntico ao Flop/Turn

### 3. Probabilidade de Vitória

**Algoritmo:** Monte Carlo adaptativo com máxima precisão

**Diferenças:**
- Deck restante: 52 - 2 (hole) - 5 (river) = 45 cartas
- Não precisa simular cartas comunitárias (já estão todas)
- Simula apenas cartas dos oponentes
- Número de simulações: 1000 (padrão, pode ser menor com early exit)

**Processo:**
```python
# Cartas conhecidas: hole + river completo
known_cards = set(player_cards + community_cards)  # 7 cartas
remaining_deck = [card for card in full_deck if card not in known_cards]  # 45 cartas

# Para cada simulação (com early exit):
# 1. Não precisa completar community (já está completo)
simulated_community = list(community_cards)  # Já tem 5

# 2. Seleciona cartas dos oponentes de uma vez
selected_cards = random.sample(remaining_deck, cards_needed_for_opponents)

# 3. Apenas simula cartas dos oponentes
for opponent in active_opponents:
    opponent_cards = selected_cards[card_index:card_index+2]
    card_index += 2
    # Avalia e compara
```

**Precisão:** Máxima (apenas incerteza sobre cartas dos oponentes)
**Tempo:** ~50-100ms (pode ser menor com early exit)

---

## Algoritmos Compartilhados

### 1. Conversão de Formato de Cartas

**Arquivo:** `players/hand_evaluator.py`

**Função:** `_pypoker_to_pokerkit_cached(card_str)` (com cache LRU)

**Mapeamento:**
- **PyPokerEngine:** `'SA'` (Suit + Rank, uppercase)
- **PokerKit:** `'As'` (Rank + suit, lowercase)

**Otimização:** Cache LRU com `@lru_cache(maxsize=128)`
- Cache compartilhado entre todas as instâncias de HandEvaluator
- Acelera conversões repetidas de cartas
- Reduz overhead de processamento

**Tabela de Conversão:**

| PyPokerEngine | PokerKit | Descrição |
|---------------|----------|-----------|
| `'SA'` | `'As'` | Ás de Espadas |
| `'HK'` | `'Kh'` | Rei de Copas |
| `'DQ'` | `'Qd'` | Dama de Ouros |
| `'CJ'` | `'Jc'` | Valete de Paus |

**Código:**
```python
@lru_cache(maxsize=128)
def _pypoker_to_pokerkit_cached(card_str: str) -> Optional[str]:
    # Extrai suit e rank
    suit_char = card_str[0].upper()  # 'S'
    rank_str = card_str[1:].upper()  # 'A'
    
    # Converte suit para lowercase usando mapeamento global
    pokerkit_suit = _SUIT_MAP.get(suit_char)  # 'S' -> 's'
    pokerkit_rank = _RANK_MAP.get(rank_str)   # 'A' -> 'A'
    
    # Cria string PokerKit: rank + suit
    pokerkit_card_str = pokerkit_rank + pokerkit_suit  # 'A' + 's' = 'As'
    return pokerkit_card_str
```

**Performance:**
- Primeira chamada: ~0.001ms (conversão)
- Chamadas subsequentes: ~0.0001ms (cache hit)
- Melhoria: ~10x mais rápido para cartas repetidas

---

### 2. Avaliação Heurística de Hole Cards

**Arquivo:** `players/hand_utils.py`

**Função:** `evaluate_hand_strength(hole_card, community_cards=None)`

**Algoritmo:** Análise baseada em regras

#### Regras (em ordem de prioridade):

1. **Par nas hole cards:**
   ```python
   if card_ranks[0] == card_ranks[1]:
       base_strength = 50 + get_rank_value(rank)  # 50-64
       
       # Se há community cards, verifica melhorias
       if community_cards:
           if max(rank_counts) >= 3:
               return 80  # Three of a Kind
           if len(pairs) >= 2:
               return 70  # Two Pair
   ```

2. **Cartas altas:**
   ```python
   high_cards = ['A', 'K', 'Q', 'J']
   if all(rank in high_cards for rank in card_ranks):
       return 45  # Duas cartas altas
   elif any(rank in high_cards for rank in card_ranks):
       return 30  # Uma carta alta
   ```

3. **Mesmo naipe (suited):**
   ```python
   if card_suits[0] == card_suits[1]:
       if community_cards and same_suit_count >= 3:
           return 60  # Flush possível
       return 20  # Suited
   ```

4. **Cartas baixas:**
   ```python
   return 10  # Default para cartas baixas
   ```

**Complexidade:** O(1) - análise simples de 2 cartas

---

### 3. Comparação de Mãos

**Arquivo:** `players/hand_evaluator.py`

**Função:** `compare_hands(hand1_score, hand2_score)`

**Algoritmo:**
```python
if hand1_score < hand2_score:
    return -1  # hand1 é melhor (menor = melhor)
elif hand1_score > hand2_score:
    return 1   # hand2 é melhor
else:
    return 0   # Empate
```

**Nota:** Scores são invertidos (menor = melhor) para compatibilidade com formato anterior.

---

## Bibliotecas Utilizadas

### 1. PokerKit

**Biblioteca:** `pokerkit`

**Uso:** `from pokerkit import StandardHighHand`

**Função principal:**
```python
hand_obj = StandardHighHand.from_game(hole_str, board_str)
score = hand_obj.entry.index
```

**Características:**
- Avaliação precisa e rápida
- Suporta todas as variantes de poker
- Usa algoritmos otimizados (lookup tables)

**Documentação:** https://pokerkit.readthedocs.io/

---

### 2. PyPokerEngine

**Biblioteca:** `pypokerengine`

**Uso:** Motor principal do jogo

**Funções utilizadas:**
- `setup_config()`: Configuração do jogo
- `start_poker()`: Inicia o jogo
- `BasePokerPlayer`: Classe base para jogadores

**Formato de cartas:** `'SA'`, `'HK'`, etc. (Suit + Rank)

---

## Resumo por Etapa

| Etapa | Cartas | Nome da Mão | Nível | Win Prob | Simulações | Algoritmo Principal |
|-------|--------|-------------|-------|----------|------------|---------------------|
| **Preflop** | 2 | Heurística simples | Heurística | Monte Carlo (2000) | 2000 | Verificação de par + MC adaptativo |
| **Flop** | 5 | PokerKit | PokerKit | Monte Carlo (2000) | 2000 | PokerKit + MC adaptativo |
| **Turn** | 6 | PokerKit | PokerKit | Monte Carlo (1500) | 1500 | PokerKit + MC adaptativo |
| **River** | 7 | PokerKit | PokerKit | Monte Carlo (1000) | 1000 | PokerKit + MC adaptativo |

**Nota:** Números de simulações podem ser menores com early exit adaptativo (margem de erro ≤ 2%).

---

## Notas de Performance

### Tempo de Execução Estimado:

- **Avaliação heurística:** < 1ms
- **Avaliação PokerKit:** ~0.1-1ms por mão (com cache de conversões)
- **Simulação Monte Carlo (adaptativa):**
  - Preflop: ~200-400ms (2000 sims, pode ser menor com early exit)
  - Flop: ~150-300ms (2000 sims)
  - Turn: ~100-200ms (1500 sims)
  - River: ~50-100ms (1000 sims)
  - Com paralelização: ~2-4x mais rápido (depende do hardware)

### Otimizações Implementadas:

1. **Monkey Patch:** Substitui função lenta do PyPokerEngine por versão PokerKit
2. **Lazy Loading:** HandEvaluator é instanciado apenas quando necessário (singleton)
3. **Cache de Conversões:** LRU cache compartilhado para conversões de cartas (10x mais rápido)
4. **Early Exit Adaptativo:** Monte Carlo para quando margem de erro ≤ 2%
   - Verifica a cada 50 simulações após mínimo de 100
   - Reduz tempo de cálculo quando precisão já é suficiente
5. **Paralelização Opcional:** ProcessPoolExecutor para simulações paralelas
   - Ativada apenas para 500+ simulações (reduz overhead)
   - Suporta early exit mesmo em modo paralelo
6. **Cache de Probabilidade:** No console_player, probabilidade é cacheada por street
   - Só recalcula quando street muda ou jogador desiste (fold)
   - Mantém estabilidade no preflop entre ações

### Melhorias de Performance:

| Otimização | Ganho Estimado | Aplicação |
|------------|----------------|-----------|
| Cache de conversões | ~10x | Todas as avaliações |
| Lazy loading | Reduz overhead de inicialização | Primeira chamada |
| Early exit | 20-50% menos simulações | Monte Carlo |
| Paralelização | 2-4x | Simulações grandes (500+) |
| Cache de probabilidade | Evita recálculos desnecessários | Console player |

---

## Referências

- **PokerKit:** https://github.com/uoftcprg/pokerkit
- **PyPokerEngine:** https://github.com/ishikota/PyPokerEngine
- **Monte Carlo Method:** https://en.wikipedia.org/wiki/Monte_Carlo_method

---

**Última atualização:** 2024
**Versão:** 2.0

---

## Changelog

### Versão 2.0 (2024)

**Otimizações Implementadas:**

1. **Cache de Conversões:**
   - Adicionado `@lru_cache(maxsize=128)` em `_pypoker_to_pokerkit_cached()`
   - Cache compartilhado entre todas as instâncias
   - Melhoria de ~10x em conversões repetidas

2. **Lazy Loading do HandEvaluator:**
   - Implementado padrão singleton com `_get_hand_evaluator()`
   - Instância criada apenas quando necessário
   - Reduz overhead de inicialização

3. **Early Exit Adaptativo:**
   - Monte Carlo para quando margem de erro ≤ 2%
   - Verifica a cada 50 simulações após mínimo de 100
   - Reduz tempo de cálculo em 20-50%

4. **Paralelização Opcional:**
   - Suporte a `ProcessPoolExecutor` para simulações paralelas
   - Ativada apenas para 500+ simulações
   - Melhoria de 2-4x em hardware multi-core

5. **Cache de Probabilidade:**
   - Probabilidade cacheada por street no console_player
   - Só recalcula quando street muda ou jogador desiste
   - Mantém estabilidade no preflop entre ações

6. **Números de Simulações Otimizados:**
   - Preflop: 2000 (reduzido de 5000)
   - Flop: 2000 (reduzido de 3000)
   - Turn: 1500 (reduzido de 2000)
   - River: 1000 (mantido)

