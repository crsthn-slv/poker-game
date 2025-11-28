# Funcionamento dos Bots e Sistema de Memória

Esta documentação explica em detalhes como os bots funcionam, suas estruturas, estratégias e como o sistema de memória persistente opera.

## ⚠️ Arquitetura Refatorada

**IMPORTANTE:** Os bots foram refatorados para usar uma arquitetura baseada em configuração que elimina ~85% de código duplicado.

- **Nova arquitetura:** Todos os bots herdam de `PokerBotBase` e usam `BotConfig` para configuração
- **Lógica compartilhada:** Toda a lógica está em `PokerBotBase`, bots concretos são apenas configuração
- **Documentação da arquitetura:** Veja `docs/ARQUITETURA_BOTS.md` para detalhes completos
- **Como criar novo bot:** Veja `docs/COMO_CRIAR_NOVO_BOT.md` (agora muito mais simples!)

**Esta documentação explica o funcionamento interno e as funcionalidades disponíveis. Para criar novos bots, veja a documentação de arquitetura.**

## Índice

1. [Estrutura Base dos Bots](#estrutura-base-dos-bots)
2. [Sistema de Memória Persistente](#sistema-de-memória-persistente)
3. [Tipos de Bots e Estratégias](#tipos-de-bots-e-estratégias)
4. [Ciclo de Vida de um Bot](#ciclo-de-vida-de-um-bot)
5. [Sistema de Aprendizado](#sistema-de-aprendizado)
6. [Reação em Tempo Real às Ações dos Oponentes](#reação-em-tempo-real-às-ações-dos-oponentes)
7. [Análise de Blefe em Tempo Real](#análise-de-blefe-em-tempo-real)
8. [Componentes Compartilhados](#componentes-compartilhados)

---

## Estrutura Base dos Bots

### Arquitetura Refatorada

Todos os bots agora usam uma **arquitetura baseada em configuração** que elimina duplicação de código. A estrutura hierárquica é: `BasePokerPlayer` (do PyPokerEngine) → `PokerBotBase` (lógica compartilhada) → Bots concretos (apenas configuração).

### Componentes Principais

#### 1. PokerBotBase

Classe base que contém **TODA a lógica compartilhada**. Todos os bots herdam desta classe. Ela implementa todos os métodos necessários do `BasePokerPlayer` automaticamente.

#### 2. BotConfig

Dataclass que contém toda a configuração de um bot (sem lógica). Define todos os parâmetros que diferenciam um bot do outro.

#### 3. Função `_create_config()`

Cada bot tem sua própria função `_create_config()` que retorna um `BotConfig` pré-configurado com os valores específicos da personalidade desse bot.

**Nota:** Para mais detalhes sobre a arquitetura, veja `docs/ARQUITETURA_BOTS.md`.

### Métodos Implementados Automaticamente

O `PokerBotBase` já implementa **TODOS** os métodos obrigatórios do `BasePokerPlayer`. Você não precisa implementá-los!

#### 1. `declare_action(valid_actions, hole_card, round_state)`

**O que faz automaticamente:**
- Analisa ações do round atual
- Avalia força da mão
- Analisa possível blefe dos oponentes
- Decide se deve blefar (baseado na probabilidade configurada)
- Escolhe ação (fold/call/raise) baseado em configuração
- Registra ação na memória

#### 2. `receive_game_start_message(game_info)`

**O que faz:** Inicializa stack inicial automaticamente.

#### 3. `receive_round_start_message(round_count, hole_card, seats)`

**O que faz:**
- Salva memória periodicamente (a cada 5 rounds)
- Armazena cartas no registry para exibição

#### 4. `receive_street_start_message(street, round_state)`

**O que faz:** Hook vazio (pode ser sobrescrito se necessário).

#### 5. `receive_game_update_message(action, round_state)`

**O que faz:** Registra ações dos oponentes na memória automaticamente.

#### 6. `receive_round_result_message(winners, hand_info, round_state)`

**O que faz:**
- Processa resultado do round
- Atualiza estatísticas
- Executa aprendizado baseado em configuração
- Salva memória

**Nota:** Se precisar de aprendizado customizado, você pode sobrescrever este método, mas geralmente o aprendizado padrão é suficiente.

---

## Sistema de Memória Persistente Unificada

### Estrutura Unificada

Todos os bots agora usam a **mesma estrutura de memória**, diferenciando-se apenas nos valores iniciais e na forma como evoluem/aprendem. Isso torna o sistema mais consistente e fácil de manter.

### Localização dos Arquivos

Todos os arquivos de memória são armazenados centralmente em `data/memory/`, com um arquivo JSON para cada bot.

### Módulo Compartilhado

A estrutura de memória é gerenciada pelos módulos compartilhados:
- `unified_memory.py`: Funções utilitárias para criar e manipular memória
- `memory_manager.py`: Classe `UnifiedMemoryManager` que facilita o uso pelos bots

### Estrutura dos Arquivos de Memória

Todos os bots usam a mesma estrutura JSON contendo:
1. **Parâmetros de estratégia** (bluff_probability, aggression_level, tightness_threshold)
2. **Estatísticas** (total_rounds, wins)
3. **Histórico de oponentes** (ações observadas, cartas quando disponíveis, resultados)
4. **Histórico de rounds** (ações do bot, resultados, contexto)

### Diferenças entre Bots

Todos os bots usam a mesma estrutura e lógica (via `PokerBotBase`), mas com **valores de configuração diferentes**. A diferença está em:
1. **Valores iniciais** (definidos na função `_create_config()`)
2. **Parâmetros de comportamento** (thresholds, multiplicadores, etc.)
3. **Evolução/aprendizado**: cada bot ajusta esses parâmetros de forma diferente baseado em seus resultados

**Importante:** A lógica de decisão é **idêntica** para todos os bots (está em `PokerBotBase`). A personalidade vem apenas da configuração.

### Carregamento de Memória

A memória é carregada automaticamente pelo `PokerBotBase` na inicialização usando `UnifiedMemoryManager`. O processo:
1. Carrega memória anterior se existir
2. Se não existir, cria estrutura padrão usando valores do `BotConfig`
3. Falha silenciosamente (não quebra o jogo)

### Salvamento de Memória

A memória é salva em dois momentos principais:
1. **Periodicamente** (a cada 5 rounds) no início de cada round
2. **Após aprendizado** no fim de cada round

O método de salvamento serializa a estrutura de memória completa, escreve no arquivo de memória e falha silenciosamente em caso de erro (não quebra o jogo).

### Reação em Tempo Real

Durante `declare_action()`, os bots analisam ações do round atual antes de decidir. Isso permite que os bots **reajam imediatamente** às ações dos oponentes, não apenas aprendam após o round.

### Sistema de Identificação de Oponentes (UUIDs Fixos)

**IMPORTANTE:** O sistema usa UUIDs determinísticos baseados na classe do bot para garantir rastreamento consistente.

**Como Funciona:**
- Cada tipo de bot tem um UUID fixo baseado em sua classe (não no nome)
- O mesmo tipo de bot sempre tem o mesmo UUID, independente do nome ou da partida
- Isso garante que os bots reconheçam corretamente os mesmos oponentes entre partidas
- Todos os 21 bots conhecidos são pré-registrados na memória desde o início

**Vantagens:**
- Rastreamento consistente: um bot sempre reconhece o mesmo oponente
- Memória não cresce infinitamente: máximo de 20 oponentes por bot (21 bots totais - 1 próprio)
- Aprendizado acumulado: parâmetros globais são mantidos entre partidas

### Registro de Ações e Oponentes

Durante o jogo, os bots registram:
1. **Ações próprias** em `declare_action()`: identifica oponentes e registra a ação realizada
2. **Ações dos oponentes** em `receive_game_update_message()`: registra ações dos oponentes na memória
3. **Resultados e cartas** em `receive_round_result_message()`: processa resultado completo incluindo cartas dos oponentes que chegaram ao showdown

### Histórico de Oponentes

Para cada oponente, o bot registra:
- **Nome** do oponente
- **Estatísticas de interação** com este oponente
- **Ações observadas** durante cada round
- **Cartas** (quando o oponente chega ao showdown)
- **Força da mão** calculada a partir das cartas
- **Resultado** contra esse oponente
- **Análise simples** (ex: "blefe_sucesso" se tinha mão ruim mas ganhou)

Isso permite que o bot aprenda padrões observados sem inferir valores abstratos.

**Nota:** O histórico de oponentes é usado para aprendizado de longo prazo. Para reação em tempo real, os bots usam análise de ações do round atual.

---
## Ciclo de Vida de um Bot

### 1. Inicialização (`__init__`)

**O que o `PokerBotBase.__init__()` faz automaticamente:**
1. Armazena configuração em `self.config`
2. Inicializa `UnifiedMemoryManager` com valores do config
3. Carrega memória anterior (se existir) ou cria nova
4. Carrega parâmetros da memória (bluff_probability, aggression_level, etc.)
5. Inicializa estado interno (initial_stack, current_stack)

**Você não precisa fazer nada disso!** Apenas chame `super().__init__(config)`.

### 2. Início do Jogo (`receive_game_start_message`)

**Quando:** Uma vez, antes do primeiro round.

**Responsabilidade:** Capturar configurações iniciais do jogo (stack inicial, etc.)

### 3. Início de Round (`receive_round_start_message`)

**Quando:** No início de cada round.

**Responsabilidade:**
- Preparar para novo round
- Salvar memória periodicamente
- Registrar cartas para exibição (web)

### 4. Durante o Round (Múltiplas Chamadas)

#### 4.1. Declaração de Ação (`declare_action`)

**Fluxo automático:**
1. Identifica oponentes
2. Analisa ações do round atual
3. Avalia força da mão
4. Analisa possível blefe dos oponentes
5. Carrega parâmetros atualizados da memória (globais)
6. Decide se deve blefar (baseado em parâmetros globais)
7. Escolhe ação (blefe ou normal) baseado em configuração
8. Registra ação na memória
9. Retorna ação e valor

**Você não precisa implementar isso!** Tudo é automático baseado na configuração.

#### 4.2. Atualização de Estado (`receive_game_update_message`)

**O que faz automaticamente:**
- Registra ações dos oponentes na memória
- Atualiza histórico de oponentes

#### 4.3. Mudança de Street (`receive_street_start_message`)

**O que faz:** Hook vazio (pode ser sobrescrito se necessário).

### 5. Fim de Round (`receive_round_result_message`)

**O que faz automaticamente:**
1. Processa resultado usando `memory_manager.process_round_result()`
   - Registra round contra cada oponente
2. Atualiza stack atual
3. Atualiza estatísticas (total_rounds, wins)
4. Executa aprendizado global baseado em configuração:
   - Ajusta agressão/blefe quando win rate > threshold alto
   - Reduz agressão/aumenta threshold quando win rate < threshold baixo
   - Velocidade controlada por learning_speed
5. Salva memória atualizada

**Você não precisa implementar isso!** O aprendizado padrão é suficiente para a maioria dos casos.

---

## Sistema de Aprendizado

### Tipos de Aprendizado

#### 1. Aprendizado Conservador (TightPlayer)

**Características:**
- Ajustes lentos e cuidadosos
- Só ajusta quando situação está muito ruim
- Mantém histórico curto (10 rodadas)

**Lógica:**
- Só ajusta quando win rate < 30% OU 3+ perdas seguidas
- Aumenta threshold quando win rate < 30%
- Reduz blefe após 3+ perdas consecutivas

#### 2. Aprendizado Agressivo (AggressivePlayer)

**Características:**
- Ajustes rápidos baseados em performance recente
- Mantém histórico médio (20 rodadas)
- Ajusta múltiplos parâmetros simultaneamente

**Lógica:**
- Ajusta agressão e blefe baseado em win rate recente
- Aumenta agressão quando win rate > 60%
- Reduz agressão quando win rate < 30%

#### 3. Aprendizado Avançado (SmartPlayer)

**Características:**
- Análise multi-dimensional
- Mantém histórico longo (50 rodadas)
- Rastreia múltiplas métricas (street, pot size, blefe)

**Lógica:**
- Ajusta baseado em múltiplos fatores:
  - Sucesso de blefes
  - Performance por street
  - Estratégia por tamanho de pot

#### 4. Aprendizado Adaptativo (LearningPlayer)

**Características:**
- Rastreia padrões dos oponentes
- Usa learning rate para suavizar atualizações
- Adapta estratégia baseado em comportamento dos oponentes

**Lógica:**
- Atualiza padrões de oponente com learning rate
- Ajusta estratégia baseado nos oponentes
- Reduz blefe contra oponentes agressivos

### Algoritmos de Aprendizado

#### Epsilon-Greedy (AdaptivePlayer)

Combina exploração (escolhe aleatoriamente uma porcentagem das vezes) com exploração (usa análise na maioria das vezes). Reduz exploração gradualmente ao longo do tempo.

#### Ajuste Dinâmico de Probabilidade

Ajusta blefe baseado na performance (stack atual vs inicial). Se performance > 120%: aumenta blefe. Se performance < 80%: reduz blefe.

#### Normalização de Probabilidades

Normaliza probabilidades de ações para que a soma seja igual a 1, garantindo que as decisões sejam consistentes.

---

## Reação em Tempo Real às Ações dos Oponentes

### Visão Geral

Todos os bots agora **reagem em tempo real** às ações dos oponentes no mesmo round antes de tomar sua decisão. Isso torna o jogo mais dinâmico e realista, pois os bots ajustam seu comportamento baseado no que está acontecendo na mesa.

### Como Funciona

#### 1. Análise de Ações do Round Atual

Antes de decidir sua ação, cada bot analisa as ações que já aconteceram na street atual. A análise retorna informações sobre:
- Se há raises na street atual
- Quantos raises foram feitos
- Quantos calls foram feitos
- Última ação dos oponentes
- Nível total de agressão (0.0 a 1.0)
- Se o campo está passivo (muitos calls, nenhum raise)
- Score de oportunidade de agressão (0.0 a 1.0)

#### 2. Ajuste de Comportamento

Baseado nas ações observadas, os bots ajustam:

**Quando detectam raises:**
- **Aumentam threshold de seletividade** (ficam mais conservadores)
- **Reduzem ou evitam blefe** (especialmente com 2+ raises)
- **Ajustam agressão** (reduzem quando há muita agressão na mesa)

**Quando detectam campo passivo:**
- **Reduzem threshold** (jogam mais mãos)
- **Aumentam agressão temporariamente**
- **Fazem raise com mãos médias** quando a oportunidade é alta

#### 3. Análise por Street

A análise funciona em todas as streets (preflop, flop, turn, river):
- Cada street é analisada **independentemente**
- Ações de streets anteriores não afetam a análise da street atual
- O bot reage apenas às ações que aconteceram na street atual

### Comportamento por Tipo de Bot

#### Bots Conservadores (TightPlayer, ConservativeAggressivePlayer, CautiousPlayer)
- **Reação forte a raises**: Aumentam threshold significativamente (+8 a +17 pontos)
- **Evitam blefe completamente** quando há 2+ raises
- **Ficam ainda mais seletivos** em situações agressivas

#### Bots Agressivos (AggressivePlayer, SteadyAggressivePlayer)
- **Reação moderada**: Aumentam threshold, mas mantêm agressão
- **Reduzem agressão em 10%** quando há 2+ raises
- **Ainda tentam raise**, mas com mais seletividade

#### Bots Inteligentes (SmartPlayer, LearningPlayer, AdaptivePlayer)
- **Análise balanceada**: Ajustam threshold baseado em contexto
- **Evitam blefe** quando há muita agressão (2+ raises)
- **Ajustam estratégia** considerando múltiplos fatores

#### Bots Balanceados (BalancedPlayer, ModeratePlayer)
- **Reação equilibrada**: Ajustam threshold moderadamente (+5 a +9 pontos)
- **Evitam blefe** com 2+ raises
- **Mantêm estilo balanceado** mesmo com agressão

### Ajustes de Threshold Simplificados

O sistema foi simplificado para focar nos fatores mais importantes:

1. **Ajuste por Raises**: Aumenta threshold quando há raises (mais raises = mais seletivo)
2. **Ajuste por Risco**: 2 níveis baseado em % do stack
   - Baixo risco (< 20% do stack): reduz threshold em 2 pontos
   - Alto risco (>= 20% do stack): aumenta threshold em 3 pontos
3. **Ajuste por Pot Odds**: Reduz threshold em 3 pontos se pot odds > 4.0

### Diferença do Sistema Anterior

**Antes:**
- Bots decidiam apenas baseado em:
  - Força da mão
  - Parâmetros aprendidos (blefe, agressão, threshold)
  - Contexto geral (pot size, número de jogadores)
  - Histórico de rounds anteriores

**Agora:**
- Bots também consideram:
  - **Ações que aconteceram no round atual**
  - **Quantidade de raises observados**
  - **Última ação dos oponentes**
  - **Nível de agressão na mesa**

### Vantagens

1. **Jogo mais dinâmico**: Bots reagem ao que está acontecendo agora
2. **Mais realista**: Comportamento similar a jogadores humanos
3. **Adaptação imediata**: Não precisa esperar fim do round para ajustar
4. **Reação a todos os oponentes**: Analisa ações de bots e jogador humano igualmente

### Limitações

- Análise é **por street**: Não considera ações de streets anteriores no mesmo round
- Análise é **simples**: Não considera valores dos raises, apenas a presença
- Não diferencia **quem** fez raise: Trata todos os oponentes igualmente

---

## Análise de Blefe em Tempo Real

### Visão Geral

Todos os bots agora **analisam se os oponentes podem estar blefando** antes de tomar sua decisão. Isso permite que os bots paguem blefes quando têm mãos razoáveis, tornando o jogo mais estratégico e realista.

### Como Funciona

#### 1. Análise de Possível Blefe

Antes de decidir sua ação, cada bot analisa se os oponentes podem estar blefando. A análise retorna:
- **possible_bluff_probability**: Probabilidade de blefe (0.0 a 1.0)
- **should_call_bluff**: Se deve pagar possível blefe (bool)
- **bluff_confidence**: Confiança na análise (0.0 a 1.0)
- **analysis_factors**: Fatores que indicam blefe (dict)

#### 2. Fatores que Indicam Possível Blefe

A análise considera múltiplos fatores:

**Múltiplos raises (2+):**
- Alta probabilidade de blefe (+0.4)
- Indica que oponente pode estar tentando intimidar

**Alta agressão (>60% raises vs calls):**
- Probabilidade moderada de blefe (+0.2)
- Muitos raises em relação a calls

**Street inicial (preflop/flop):**
- Probabilidade baixa de blefe (+0.1)
- Mais comum blefar em streets iniciais

**Pot pequeno (<50):**
- Probabilidade baixa de blefe (+0.1)
- Mais fácil blefar em pots pequenos

**Histórico de blefes do oponente:**
- Se oponente tem histórico de blefes bem-sucedidos (+0.1)
- Usa memória para identificar oponentes que blefam frequentemente

#### 3. Decisão de Pagar Blefe

A análise recomenda pagar blefe quando:
- Com mão forte (≥40): sempre paga
- Com mão média (≥30) + alta probabilidade (>0.5): paga
- Com mão média-fraca (≥25) + muito alta probabilidade (>0.7): paga

#### 4. Integração na Lógica do Bot

A análise é usada na lógica de ação normal. Se a análise indica possível blefe e deve pagar, o bot considera fazer call mesmo com mão média, desde que a mão seja maior ou igual ao threshold personalizado do bot.

### Valores por Personalidade

Cada bot tem um **threshold personalizado** para pagar blefe, refletindo sua personalidade:

#### Conservadores (mais seletivos)
- **TightPlayer**: 32
- **CautiousPlayer**: 30
- **PatientPlayer**: 28
- **ConservativeAggressivePlayer**: 29

#### Agressivos (pagam blefe mais facilmente)
- **AggressivePlayer**: 22
- **SteadyAggressivePlayer**: 24
- **OpportunisticPlayer**: 23
- **RandomPlayer**: 24
- **FishPlayer**: 23

#### Inteligentes (análise balanceada)
- **SmartPlayer**: 28
- **LearningPlayer**: 27
- **CalculatedPlayer**: 28
- **ThoughtfulPlayer**: 27
- **CalmPlayer**: 27

#### Balanceados (valores médios)
- **BalancedPlayer**: 26
- **ModeratePlayer**: 26
- **FlexiblePlayer**: 25
- **SteadyPlayer**: 26
- **ObservantPlayer**: 26

#### Outros
- **AdaptivePlayer**: 25
- **HybridPlayer**: 25

### Diferença da Análise de Ações

**Análise de Ações:**
- Detecta **quantos raises** foram feitos
- Ajusta **threshold de seletividade** do bot
- Reduz **probabilidade de blefe** do próprio bot

**Análise de Blefe:**
- Detecta se **oponentes podem estar blefando**
- Calcula **probabilidade de blefe** dos oponentes
- Recomenda se deve **pagar o blefe** baseado na mão própria

### Vantagens

1. **Jogo mais estratégico**: Bots pagam blefes quando têm mão razoável
2. **Mais realista**: Comportamento similar a jogadores humanos experientes
3. **Personalidade preservada**: Cada bot tem threshold diferente
4. **Aprende com histórico**: Usa memória de blefes anteriores dos oponentes

### Limitações

- Análise é **probabilística**: Não garante que oponente está blefando
- Não considera **valores dos raises**: Apenas quantidade
- Não diferencia **quem** fez raise: Trata todos igualmente
- Histórico é **limitado**: Apenas últimos 5 rounds por oponente

---

## Componentes Compartilhados

### 1. `hand_utils.py`

Fornece funções utilitárias para avaliação de mãos:
- Avalia força básica da mão
- Converte rank da carta para valor numérico
- Padroniza formato das cartas
- Extrai cartas comunitárias

### 2. `constants.py`

Define constantes compartilhadas:
- Probabilidades de blefe padrão
- Thresholds de força de mão
- Níveis de agressão
- Tamanhos de pot
- Taxas de aprendizado

### 3. `error_handling.py`

Fornece tratamento seguro de erros:
- Salva memória com tratamento de erros
- Carrega memória com tratamento de erros

### 4. `memory_utils.py`

Utilitários para gerenciamento de memória:
- Retorna caminho completo para arquivo de memória

### 5. `action_analyzer.py`

Utilitário para análise de ações do round atual e possível blefe:
- **analyze_current_round_actions**: Analisa ações dos oponentes na street atual
  - Retorna informações sobre raises, calls, e nível de agressão
  - Detecta campo passivo (is_passive, passive_opportunity_score)
  - Exclui ações próprias da análise
  - Funciona em todas as streets (preflop, flop, turn, river)
- **analyze_possible_bluff**: Analisa se oponentes podem estar blefando
  - Calcula probabilidade de blefe baseado em múltiplos fatores
  - Considera histórico de blefes dos oponentes (se disponível)
  - Recomenda se deve pagar blefe baseado na força da mão própria
  - Retorna: probabilidade, recomendação, confiança e fatores analisados

---

## Resumo do Fluxo de Decisão

Para entender como um bot decide sua ação, siga este fluxo:

1. **Recebe `declare_action`** com estado atual
2. **Atualiza informações internas** (stack, contexto)
3. **Analisa ações do round atual**
   - Detecta se há raises na street atual
   - Conta quantos raises foram feitos
   - Identifica última ação dos oponentes
4. **Avalia força da mão**
5. **Analisa possível blefe dos oponentes**
   - Calcula probabilidade de blefe baseado em múltiplos fatores
   - Determina se deve pagar blefe baseado na mão própria
6. **Ajusta threshold baseado em ações atuais**
   - Se há raises: aumenta threshold (fica mais seletivo)
   - Se 2+ raises: aumenta threshold significativamente
7. **Ajusta threshold por risco** (simplificado: 2 níveis baseado em % do stack)
8. **Ajusta threshold por pot odds** (simplificado: 1 threshold)
9. **Decide se deve blefar** baseado em probabilidade
   - Se 2+ raises, evita blefe completamente
10. **Se blefar:**
   - Analisa contexto da mesa
   - Escolhe entre CALL ou RAISE
   - Retorna ação
11. **Se não blefar:**
    - Se análise indica possível blefe e deve pagar:
      - Compara mão com threshold personalizado
      - Se mão ≥ threshold: faz CALL (paga blefe)
    - Caso contrário:
      - Compara força da mão com threshold ajustado
      - Se mão muito forte: RAISE
      - Se mão forte e agressão alta: RAISE
      - Senão: CALL
    - Retorna ação
12. **Após o round:**
    - Recebe resultado em `receive_round_result_message`
    - Atualiza estatísticas
    - Aprende com resultado
    - Ajusta estratégia
    - Salva memória

---

## Considerações Finais

### Persistência entre Partidas

- Memórias são carregadas na inicialização de cada bot
- Memórias são salvas periodicamente e ao fim de cada round
- Bots mantêm aprendizado entre partidas
- Bots evoluem com o tempo

### Thread Safety

- Cada bot é uma instância separada
- Memórias são salvas de forma atômica (escrita completa ou falha)
- Não há compartilhamento de estado entre bots (exceto via `cards_registry`)

### Performance

- Salvamento de memória é feito assincronamente (não bloqueia jogo)
- Históricos são limitados (10-50 rodadas) para evitar crescimento infinito
- **Oponentes rastreados**: Máximo de 20 oponentes por bot (21 bots totais - 1 próprio)
- **Parâmetros globais**: Mantidos e evoluem com aprendizado
- **UUIDs fixos**: Garantem rastreamento consistente e evitam duplicação de oponentes
- Operações de arquivo falham silenciosamente para não quebrar o jogo

### Debugging

- Use `POKER_PLAYER_LOG_LEVEL=DEBUG` para ver logs detalhados
- Logs aparecem no console/terminal
- Memórias podem ser inspecionadas diretamente nos arquivos JSON
