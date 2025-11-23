# Modo Debug - Cálculo de Probabilidade

Este documento explica como ativar e usar o modo debug para análise detalhada do cálculo de probabilidade de vitória.

## Como Ativar

Para ativar o modo debug, defina a variável de ambiente `POKER_DEBUG_PROBABILITY` como `true` antes de executar o jogo:

### Linux/macOS:
```bash
export POKER_DEBUG_PROBABILITY=true
python3 -m game.play_console
```

### Windows (PowerShell):
```powershell
$env:POKER_DEBUG_PROBABILITY="true"
python -m game.play_console
```

### Windows (CMD):
```cmd
set POKER_DEBUG_PROBABILITY=true
python -m game.play_console
```

## Onde os Logs são Salvos

Os logs de debug são salvos em:
```
logs/probability_debug.log
```

## O que é Registrado

O modo debug registra informações detalhadas sobre cada cálculo de probabilidade:

### 1. Início da Simulação
- Street atual (preflop, flop, turn, river)
- Cartas do jogador
- Cartas comunitárias
- Número de oponentes
- Número de simulações planejadas
- Tamanho do deck restante
- Cartas de 4 disponíveis no deck (útil para detectar casos como trinca)

### 2. Progresso da Simulação
- A cada 200 simulações (modo sequencial)
- A cada 2 batches (modo paralelo)
- Mostra:
  - Número de simulações realizadas
  - Número de vitórias
  - Probabilidade atual
  - Margem de erro
  - Intervalo de confiança

### 3. Early Exit
- Quando o early exit é ativado
- Estatísticas finais quando para antes do número máximo de simulações

### 4. Casos Especiais (Primeiras 10 Simulações)
- Quando um oponente vence
- Cartas do oponente
- Mão do oponente vs mão do jogador
- Scores de ambas as mãos

### 5. Estatísticas Finais
- Total de simulações realizadas
- Número de vitórias
- Probabilidade final
- Margem de erro
- Intervalo de confiança
- Se early exit foi usado
- Estatísticas de derrotas:
  - Quantas vezes oponente teve Three of a Kind
  - Quantas vezes oponente teve Two Pair
  - Quantas vezes oponente teve One Pair melhor
  - Quantas vezes oponente teve High Card melhor

## Mudanças Implementadas

### 1. Correção Crítica: Cartas dos Oponentes (v2.1)
- **BUG CORRIGIDO:** A simulação estava usando cartas conhecidas dos oponentes do `cards_registry`
- **Problema:** Isso causava probabilidades incorretas (especialmente 100%) porque "conhecia" as cartas dos oponentes
- **Solução:** A simulação agora **SEMPRE** distribui cartas dos oponentes aleatoriamente
- **Impacto:** Probabilidades agora são corretas e realistas
- **Validação:** Testes automáticos garantem que probabilidade nunca é 100% (exceto quando há apenas 1 jogador ativo)

### 2. Mínimo de Simulações Aumentado
- **Antes:** Mínimo de 100 simulações antes de considerar early exit
- **Agora:** Mínimo de 1000 simulações antes de considerar early exit
- **Motivo:** Garantir que eventos raros (como oponentes com trinca) sejam capturados

### 3. Modo Debug Melhorado (v2.1)
- Logging detalhado de todas as etapas
- Estatísticas de casos especiais
- Rastreamento de early exit
- Informações sobre cartas disponíveis no deck
- **NOVO:** Mostra `'opponent_cards_simulation': 'random'` para confirmar simulação aleatória
- **NOVO:** Mostra distribuição de mãos dos oponentes (`opponent_hand_distribution`)
- **NOVO:** Warning automático se probabilidade for 100% (para detectar problemas)
- **NOVO:** Mostra mão do jogador no resultado final para análise

## Exemplo de Log (v2.1 - Corrigido)

```
[2024-01-15 10:30:45.123] === INÍCIO SIMULAÇÃO MONTE CARLO === | {
    'street': 'river', 
    'player_cards': ['H6', 'SK'], 
    'community_cards': ['S9', 'HQ', 'C4', 'D4', 'D5'], 
    'num_opponents': 3, 
    'num_simulations': 1000, 
    'min_simulations': 1000, 
    'remaining_deck_size': 45, 
    'opponent_cards_simulation': 'random',  # ← NOVO: Confirma simulação aleatória
    'remaining_4s': ['H4', 'S4']
}

[2024-01-15 10:30:45.456] Progresso simulação | {
    'simulations': 200, 
    'wins': 190, 
    'prob': '0.9500', 
    'margin': '0.0305', 
    'interval': '[0.9195, 0.9805]'
}

[2024-01-15 10:30:45.789] Simulação 1: Oponente vence | {
    'opponent_cards': ['H4', 'C7'], 
    'opponent_hand': 'Three of a Kind', 
    'opponent_score': 150, 
    'player_hand': 'One Pair', 
    'player_score': 5000
}

[2024-01-15 10:30:46.012] === RESULTADO FINAL SIMULAÇÃO === | {
    'total_simulations': 1000, 
    'wins': 952, 
    'prob': '0.9520 (95.20%)', 
    'margin': '0.0133', 
    'interval': '[0.9387, 0.9653]', 
    'early_exit': False, 
    'player_hand': 'One Pair',  # ← NOVO: Mão do jogador
    'num_opponents': 3,  # ← NOVO: Número de oponentes
    'debug_stats': {
        'opponent_three_of_kind': 48, 
        'opponent_two_pair': 0, 
        'opponent_one_pair_better': 0, 
        'opponent_high_card_better': 0, 
        'player_wins': 952
    },
    'opponent_hand_distribution': {  # ← NOVO: Distribuição de mãos
        'three_of_kind_pct': '100.0%',
        'two_pair_pct': '0.0%',
        'one_pair_better_pct': '0.0%',
        'high_card_better_pct': '0.0%'
    }
}
```

### ⚠️ Exemplo de Log com Problema (ANTES da correção)

```
# Este tipo de log NÃO deve mais aparecer:
'known_opponent_cards': ['knfzefynideypzsqjqfzpi', 'hffvaipttunxgbckdfvwvp']  # ← ERRADO

# E nunca deve haver:
'prob': '1.0000 (100.00%)',  # Com múltiplos oponentes ativos (exceto se todos desistiram)
'warning': 'Probabilidade 100% detectada - verifique se há problema na simulação'
```

## Análise dos Logs

Ao analisar os logs, procure por:

1. **Probabilidades de 100%**: 
   - ⚠️ **IMPORTANTE**: Com a correção implementada, probabilidade de 100% **NÃO deveria aparecer** quando há múltiplos oponentes ativos
   - Se aparecer, há um problema na simulação
   - Único caso válido: quando há apenas 1 jogador ativo (todos os outros desistiram)

2. **Oponente Cards Simulation**: 
   - Verifique que aparece `'opponent_cards_simulation': 'random'` nos logs
   - Isso confirma que as cartas dos oponentes estão sendo simuladas aleatoriamente
   - **NÃO deve haver** `'known_opponent_cards'` com UUIDs de oponentes ativos

3. **Early Exit Prematuro**: Verifique se o early exit está parando muito cedo

4. **Distribuição de Mãos dos Oponentes**: 
   - O log mostra `opponent_hand_distribution` com percentuais de tipos de mãos
   - Verifique se a distribuição faz sentido (não pode ser 100% de um tipo específico)

5. **Casos de Three of a Kind**: Quantas vezes oponentes tiveram trinca (deve ser proporcional à probabilidade real)

6. **Warning de Probabilidade 100%**: 
   - Se aparecer `'warning': 'Probabilidade 100% detectada'`, investigue
   - Isso indica que a simulação pode ter um problema

7. **Cartas de 4 Disponíveis**: No river, se há cartas de 4 no deck, a probabilidade não pode ser 100%

## Desativar Debug

Para desativar, simplesmente não defina a variável de ambiente ou defina como `false`:

```bash
unset POKER_DEBUG_PROBABILITY
# ou
export POKER_DEBUG_PROBABILITY=false
```

---

## Validação e Testes

Para validar que a simulação está funcionando corretamente:

### Executar Testes Automáticos

```bash
python -m pytest tests/test_win_probability.py -v
```

Os testes verificam:
- ✅ Cartas dos oponentes são sempre simuladas aleatoriamente (não usadas do registry)
- ✅ Probabilidade nunca é 100% quando há múltiplos oponentes ativos
- ✅ Probabilidade só é 100% quando há apenas 1 jogador ativo
- ✅ Simulação produz resultados variáveis (usa aleatoriedade)

### Verificar Logs Manualmente

1. Execute o jogo com debug ativado:
   ```bash
   export POKER_DEBUG_PROBABILITY=true
   python3 -m game.play_console
   ```

2. Analise o arquivo `logs/probability_debug.log`:
   - Verifique que `opponent_cards_simulation` está como `'random'`
   - Verifique que **NÃO há** `known_opponent_cards` com UUIDs de oponentes ativos
   - Verifique que probabilidades nunca são 100% (exceto quando há apenas 1 jogador)

---

## Histórico de Correções

### v2.1 (2024) - Correção Crítica

**Problema Identificado:**
- A simulação Monte Carlo estava usando cartas conhecidas dos oponentes do `cards_registry`
- Isso causava probabilidades incorretas (especialmente 100%) quando havia múltiplos oponentes ativos
- O `cards_registry` é usado para exibição no final do round, mas estava sendo incorretamente usado na simulação

**Correção Implementada:**
- Removido uso de cartas conhecidas dos oponentes na simulação
- Sempre distribui cartas dos oponentes aleatoriamente durante a simulação
- Adicionado aviso automático se probabilidade for 100% (para detectar problemas futuros)
- Melhorados logs de debug com mais informações de análise

**Testes Adicionados:**
- `test_opponent_cards_not_used_from_registry`: Valida que cartas do registry não são usadas
- `test_probability_not_100_percent_with_multiple_opponents`: Valida que nunca é 100% com múltiplos oponentes
- `test_simulation_variability`: Valida que há aleatoriedade na simulação

