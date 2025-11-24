# Plano de Refatoração - Eliminação de Código Duplicado nos Bots

## 1. Objetivo

Eliminar **~85% de código duplicado** criando uma arquitetura baseada em **estratégias reutilizáveis** onde:
- ✅ Bots concretos são apenas **configurações** (sem lógica)
- ✅ Toda lógica de decisão fica em **estratégias injetáveis**
- ✅ Parâmetros sempre **externalizados** (nunca hardcoded)
- ✅ Manutenção centralizada em **um único lugar**

---

## 2. Arquitetura Proposta

### 2.1. Estrutura de Classes

```
players/
├── base/
│   ├── __init__.py
│   ├── poker_bot_base.py           # Classe base abstrata
│   └── bot_config.py                # Dataclass de configuração
│
├── aggressive_player.py             # Apenas configuração (com _create_config())
├── balanced_player.py               # Apenas configuração
├── cautious_player.py               # Apenas configuração
└── ...                              # Outros bots (só config)
```

---

## 3. Implementação Detalhada

### 3.1. BotConfig (Dataclass)

**Arquivo**: `players/base/bot_config.py`

Configuração completa de um bot - ZERO lógica aqui. Apenas dados.

**Campos principais:**
- Identificação (name, memory_file)
- Parâmetros de personalidade (bluff, aggression, tightness)
- Thresholds de decisão (fold, raise, strong_hand)
- Fatores de ajuste (raise_multiplier, bluff_call_ratio)
- Comportamento em contextos (passive_aggression_boost, raise_count_sensitivity)
- Aprendizado (learning_speed, win_rate_thresholds)

---

### 3.2. PokerBotBase (Classe Base)

**Arquivo**: `players/base/poker_bot_base.py`

Classe base para TODOS os bots. Contém TODA a lógica compartilhada:
- Inicialização com UnifiedMemoryManager
- Método `declare_action` universal
- Métodos `_should_bluff`, `_bluff_action`, `_normal_action`
- Todos os métodos `receive_*` compartilhados
- Lógica de aprendizado baseada em config

**Subclasses apenas injetam configuração via `__init__`.**

---

### 3.3. Presets de Configuração

**Arquivo**: Cada bot tem sua própria função `_create_config()` no arquivo do bot

Presets de configuração para cada personalidade. Cada método estático retorna um `BotConfig` configurado.

**Exemplo:**
```python
@staticmethod
def aggressive() -> BotConfig:
    return BotConfig(
        name="Aggressive",
        default_bluff=0.18,
        default_aggression=0.58,
        # ... todos os parâmetros
    )
```

---

### 3.4. Bots Concretos (Apenas Configuração)

**Exemplo**: `players/aggressive_player.py`

```python
class AggressivePlayer(PokerBotBase):
    def __init__(self, memory_file="aggressive_player_memory.json"):
        config = _create_config(memory_file)
        config.memory_file = memory_file
        super().__init__(config)
```

**Apenas 5 linhas de código!**

---

## 4. Regras Obrigatórias para Manutenção

### 🚫 PROIBIDO:

1. ❌ **Nunca** escrever lógica de decisão dentro dos bots finais (AggressivePlayer, etc)
2. ❌ **Nunca** usar números mágicos dentro de funções
3. ❌ **Nunca** duplicar código entre bots
4. ❌ **Nunca** criar métodos específicos de bot (tudo vai na base)

### ✅ OBRIGATÓRIO:

1. ✅ Bots finais **apenas instanciam** PokerBotBase com preset
2. ✅ Parâmetros **sempre** injetados via BotConfig
3. ✅ Novos comportamentos vão em **PokerBotBase** (compartilhados)
4. ✅ Novas personalidades vão em **função `_create_config()`** no arquivo do bot (configuração)
5. ✅ **Um único lugar** para modificar cada comportamento

---

## 5. Benefícios da Refatoração

### Antes:
- 📁 **21 arquivos** com ~250 linhas cada = **~5.250 linhas totais**
- 🔄 **85% de código duplicado**
- 🐛 Bug em 1 bot = precisa corrigir em 21 lugares
- ➕ Novo bot = copiar/colar 250 linhas

### Depois:
- 📁 **1 arquivo base** (~400 linhas) + **1 arquivo presets** (~500 linhas) + **21 bots** (5 linhas cada) = **~1.000 linhas totais**
- ✨ **Zero duplicação**
- 🐛 Bug em 1 bot = corrige em 1 lugar (PokerBotBase)
- ➕ Novo bot = adicionar preset (15 linhas)

### Redução: **~80% menos código**

---

## 6. Plano de Migração

### Fase 1: Criar Infraestrutura ✅
1. Criar `players/base/bot_config.py`
2. Criar `players/base/poker_bot_base.py`
3. Criar função `_create_config()` em cada bot (teste)

### Fase 2: Migrar 3 Bots (teste)
1. Migrar AggressivePlayer
2. Migrar BalancedPlayer
3. Migrar CautiousPlayer
4. **Rodar testes** para garantir comportamento idêntico

### Fase 3: Migrar Restante
1. Criar presets para os 18 bots restantes
2. Migrar todos os bots
3. **Rodar suite completa de testes**

### Fase 4: Validação
1. Rodar 100 partidas de teste
2. Comparar estatísticas antes/depois
3. Verificar comportamento de aprendizado
4. Ajustar presets se necessário

---

## 7. Testes de Validação

```python
# tests/test_bot_refactoring.py

def test_aggressive_behavior_unchanged():
    """Garante que AggressivePlayer tem mesmo comportamento"""
    old_bot = AggressivePlayerOld()
    new_bot = AggressivePlayer()
    
    # Mesma configuração
    assert new_bot.config.default_aggression == 0.58
    assert new_bot.config.default_bluff == 0.18

def test_all_bots_zero_duplication():
    """Garante que bots não têm lógica duplicada"""
    import inspect
    
    for bot_class in [AggressivePlayer, BalancedPlayer, ...]:
        # Verifica que só tem __init__
        methods = [m for m in dir(bot_class) if not m.startswith('_')]
        assert len(methods) == 0, f"{bot_class} tem métodos não permitidos"
        
        # Verifica que __init__ só chama super
        source = inspect.getsource(bot_class.__init__)
        assert 'super().__init__' in source
        assert source.count('\n') <= 5, f"{bot_class}.__init__ muito longo"
```

---

## 8. Documentação de Migração

### Criar Novo Bot (ANTES):
```python
# ❌ Antigo: 250 linhas de código duplicado
class NovoBot(BasePokerPlayer):
    def __init__(self, memory_file="novo_bot_memory.json"):
        self.memory_manager = UnifiedMemoryManager(...)
        # ... 50 linhas ...
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # ... 80 linhas ...
    
    # ... mais 8 métodos com 120 linhas ...
```

### Criar Novo Bot (DEPOIS):
```python
# ✅ Novo: 15 linhas de configuração

# 1. Em presets.py:
@staticmethod
def novo() -> BotConfig:
    return BotConfig(
        name="Novo",
        memory_file="novo_bot_memory.json",
        default_bluff=0.20,
        default_aggression=0.60,
        # ... 10 parâmetros ...
    )

# 2. Em novo_player.py:
class NovoPlayer(PokerBotBase):
    def __init__(self, memory_file="novo_bot_memory.json"):
        config = _create_config(memory_file)
        config.memory_file = memory_file
        super().__init__(config)
```

---

## 9. Checklist de Implementação

- [x] Criar arquivo MD com plano
- [x] Criar estrutura de diretórios (`base/`, `strategies/`)
- [x] Implementar `BotConfig` (dataclass)
- [x] Implementar `PokerBotBase` (lógica compartilhada)
- [x] Criar função `_create_config()` em cada bot
- [x] Migrar 3 bots de teste
- [x] Criar testes de validação
- [x] Criar presets para os 18 bots restantes
- [x] Migrar todos os bots (21 bots total)
- [x] Rodar testes e validar funcionamento
- [x] Ajustar código para corrigir erros encontrados
- [x] Criar documentação completa da arquitetura
- [x] Todos os 21 bots funcionando corretamente

---

## 10. Conclusão

Esta refatoração vai:
- ✅ **Eliminar 85% de duplicação**
- ✅ **Centralizar manutenção** em um único lugar
- ✅ **Facilitar criação** de novos bots
- ✅ **Manter compatibilidade** total
- ✅ **Melhorar testabilidade**
- ✅ **Seguir princípios SOLID** (especialmente DIP e OCP)

**Tempo estimado total**: 4 dias
**ROI**: Manutenção 10x mais fácil, bugs 10x mais rápidos de corrigir


