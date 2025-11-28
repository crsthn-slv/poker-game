# Como Criar um Novo Bot

Guia rápido para criar um novo bot de poker usando a **arquitetura refatorada baseada em configuração**.

## 🎯 Nova Arquitetura (Simplificada)

Com a refatoração, criar um novo bot é **muito mais simples**: apenas configuração!

A lógica está toda em `PokerBotBase`, você só precisa definir a **configuração**.

## Processo Simplificado

### Passo 1: Criar Arquivo do Bot

Crie um novo arquivo em `players/` com o nome do bot (ex: `meu_novo_bot_player.py`).

### Passo 2: Definir Função de Configuração

Crie uma função `_create_config()` que retorna um `BotConfig` com todos os parâmetros personalizados do seu bot. Esta função define:
- Identificação do bot (nome e arquivo de memória)
- Parâmetros de personalidade base (blefe, agressão, seletividade)
- Thresholds de decisão (fold, raise, mãos fortes)
- Comportamento de blefe (probabilidades de call vs raise)
- Reação a ações dos oponentes (sensibilidade a raises)
- Detecção e pagamento de blefe (threshold personalizado)
- Comportamento em campo passivo (aumento de agressão)
- Sistema de aprendizado (velocidade, thresholds de win rate)

### Passo 3: Criar Classe do Bot

Crie uma classe que herda de `PokerBotBase` e implementa apenas o método `__init__()` que:
1. Chama `_create_config()` para obter a configuração
2. Passa a configuração para `super().__init__(config)`

**Pronto!** Seu bot está funcionando.

## O que o PokerBotBase já faz automaticamente

O `PokerBotBase` já implementa **TUDO** para você:

✅ **Análise de ações do round atual** - Detecta raises, calls e nível de agressão
✅ **Análise de possível blefe** - Calcula probabilidade de blefe dos oponentes
✅ **Decisão de blefe** - Baseada em configuração e contexto
✅ **Ação normal** - Com todos os ajustes contextuais (raises, campo passivo, etc.)
✅ **Detecção de campo passivo** - Aumenta agressão quando detecta oportunidade
✅ **Pagamento de blefes** - Baseado em threshold configurado
✅ **Todos os métodos `receive_*`** - Handlers de eventos do jogo
✅ **Sistema de aprendizado** - Baseado em configuração
✅ **Gerenciamento de memória** - Completo e automático

**Você não precisa implementar nada disso!** Apenas configure os parâmetros.

## Parâmetros de Configuração

O `BotConfig` define todos os parâmetros do bot. Principais campos:

### Parâmetros de Personalidade
- `default_bluff`: Probabilidade inicial de blefe (0.0-1.0)
- `default_aggression`: Nível inicial de agressão (0.0-1.0)
- `default_tightness`: Threshold inicial de seletividade (0-100)

### Thresholds de Decisão
- `fold_threshold_base`: Threshold base para fold
- `raise_threshold`: Threshold mínimo para considerar raise
- `strong_hand_threshold`: Threshold para mão muito forte

### Comportamento de Blefe
- `bluff_call_ratio`: Probabilidade de fazer call vs raise no blefe
- `bluff_raise_prob_few_players`: Probabilidade de raise no blefe com poucos jogadores
- `bluff_raise_prob_many_players`: Probabilidade de raise no blefe com muitos jogadores

### Ajustes Contextuais
- `passive_aggression_boost`: Quanto aumenta agressão em campo passivo
- `raise_count_sensitivity`: Sensibilidade a raises (multiplicador)
- `bluff_detection_threshold`: Threshold para pagar blefe detectado

### Aprendizado
- `learning_speed`: Velocidade de aprendizado (0.001 = lento, 0.01 = rápido)
- `win_rate_threshold_high`: Win rate alto para aumentar agressão
- `win_rate_threshold_low`: Win rate baixo para reduzir agressão
- `rounds_before_learning`: Rodadas mínimas antes de aprender

**Veja `players/base/bot_config.py` para todos os campos disponíveis.**

## Estrutura de Memória

O `UnifiedMemoryManager` (gerenciado automaticamente pelo `PokerBotBase`) gerencia uma estrutura de memória que contém:
- Parâmetros de estratégia (bluff_probability, aggression_level, tightness_threshold) - atualizados pelo aprendizado
- Estatísticas (total_rounds, wins)
- Histórico de oponentes (ações observadas, cartas quando disponíveis, resultados)
- Histórico de rounds (ações do bot, resultados, contexto)

**Campos personalizados:** Se precisar, você pode adicionar campos customizados no preset, mas a maioria dos casos não precisa.

## Aprendizado Automático

O `PokerBotBase` já implementa aprendizado automático baseado na configuração:

- **Ajusta agressão e blefe** quando win rate > `win_rate_threshold_high`
- **Reduz agressão e aumenta threshold** quando win rate < `win_rate_threshold_low`
- **Velocidade de aprendizado** controlada por `learning_speed`
- **Aprende apenas após** `rounds_before_learning` rodadas

**Você não precisa implementar aprendizado manualmente!** Apenas configure os parâmetros no preset.

### Personalizando Aprendizado

Se precisar de aprendizado customizado, você pode sobrescrever `receive_round_result_message()`:

1. Chama o aprendizado padrão com `super().receive_round_result_message()`
2. Adiciona lógica customizada se necessário

**Nota:** Na maioria dos casos, o aprendizado padrão é suficiente. Apenas sobrescreva se precisar de comportamento muito específico.

## Registrando o Bot

### Modo Web

Adicione o bot na lista de bots disponíveis em `web/server.py` para que ele apareça na interface web.

## Funcionalidades Avançadas

### Reação em Tempo Real às Ações

Todos os bots devem analisar ações do round atual e possível blefe. Isso é feito automaticamente pelo `PokerBotBase`:

1. Analisa ações do round atual - Detecta raises, calls e nível de agressão
2. Analisa possível blefe dos oponentes - Calcula probabilidade de blefe
3. Usa nas decisões - Ajusta threshold baseado em ações e paga blefe baseado em análise

### Escolhendo o Threshold para Pagar Blefe

O threshold deve refletir a personalidade do bot:

- **Conservadores** (Tight, Cautious): 28-32 (mais seletivos)
- **Agressivos** (Aggressive, Opportunistic): 22-24 (pagam mais facilmente)
- **Inteligentes** (Smart, Learning): 27-28 (análise balanceada)
- **Balanceados** (Balanced, Moderate): 25-26 (valores médios)

## Checklist Simplificado

Com a nova arquitetura, criar um bot é muito mais simples:

- [ ] Criar arquivo `players/meu_novo_bot_player.py`
- [ ] Criar função `_create_config()` com todos os parâmetros de `BotConfig`
- [ ] Criar classe que herda de `PokerBotBase` (não de `BasePokerPlayer`)
- [ ] Implementar apenas `__init__()` que chama `_create_config()` e `super().__init__(config)`
- [ ] Registrar em `web/server.py` (se usar modo web)

**Isso é tudo!** O `PokerBotBase` já implementa:
- ✅ `declare_action()` com toda a lógica
- ✅ Análise de ações do round atual
- ✅ Análise de possível blefe
- ✅ Detecção de campo passivo
- ✅ Todos os métodos `receive_*`
- ✅ Sistema de aprendizado
- ✅ Gerenciamento de memória

## Escolhendo Valores de Configuração

### Por Personalidade

**Bots Agressivos:**
- `default_bluff`: 0.18-0.25
- `default_aggression`: 0.58-0.65
- `default_tightness`: 25-26
- `bluff_detection_threshold`: 22-24
- `passive_aggression_boost`: 0.25-0.35
- `passive_raise_threshold`: 20-25

**Bots Conservadores:**
- `default_bluff`: 0.12-0.15
- `default_aggression`: 0.48-0.54
- `default_tightness`: 29-35
- `bluff_detection_threshold`: 28-32
- `passive_aggression_boost`: 0.08-0.15
- `passive_raise_threshold`: 45-50

**Bots Balanceados:**
- `default_bluff`: 0.15-0.17
- `default_aggression`: 0.52-0.57
- `default_tightness`: 27-28
- `bluff_detection_threshold`: 25-28
- `passive_aggression_boost`: 0.15-0.20
- `passive_raise_threshold`: 28-35

**Veja exemplos em `players/aggressive_player.py`, `players/balanced_player.py`, etc. para referência.**

## Recursos

- **Exemplos de bots:** `players/aggressive_player.py`, `players/balanced_player.py`, `players/cautious_player.py` (todos com configuração completa)
- **Classe base:** `players/base/poker_bot_base.py` (toda a lógica)
- **Configuração:** `players/base/bot_config.py` (todos os parâmetros)
- **Sistema de memória:** `utils/memory_manager.py` (gerenciado automaticamente)
- **Análise de ações:** `utils/action_analyzer.py` (usado automaticamente)
- **Documentação completa:** 
  - `docs/FUNCIONAMENTO_BOTS.md` - Funcionamento detalhado
  - `docs/ARQUITETURA_BOTS.md` - Arquitetura refatorada

## Funcionalidades Automáticas

Todas essas funcionalidades são **implementadas automaticamente** pelo `PokerBotBase`:

✅ **Análise de ações em tempo real** - Usa análise automática de ações do round atual
✅ **Detecção de campo passivo** - Ajusta comportamento automaticamente baseado em `passive_aggression_boost`
✅ **Análise de possível blefe** - Usa análise automática de blefe dos oponentes
✅ **Pagamento de blefes** - Baseado em `bluff_detection_threshold` configurado
✅ **Avaliação de força da mão** - Usa avaliação automática de força da mão
✅ **Ajuste de threshold** - Baseado em `raise_count_sensitivity` e `raise_threshold_adjustment_*`
✅ **Sistema de aprendizado** - Baseado em `learning_speed` e `win_rate_threshold_*`

**Você não precisa implementar nada disso!** Apenas configure os parâmetros no preset.

### Como Funciona Internamente

O `PokerBotBase.declare_action()` já faz tudo:

1. Analisa ações do round atual
2. Avalia força da mão
3. Analisa possível blefe dos oponentes
4. Ajusta threshold baseado em ações
5. Decide se deve blefar
6. Escolhe ação (fold/call/raise)
7. Registra ação na memória

Tudo baseado na configuração do `BotConfig` que você definiu no preset.

### Personalizando Comportamento

Se precisar de comportamento muito específico, você pode:

1. **Ajustar parâmetros no preset** (recomendado)
2. **Sobrescrever métodos específicos** em seu bot (avançado)

**Nota:** Na maioria dos casos, ajustar os parâmetros do preset é suficiente.
