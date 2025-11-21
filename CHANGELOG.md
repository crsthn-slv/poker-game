# Changelog - Organização do Projeto

## [2024-12-XX] - Melhorias de Código, Configuração e Segurança

### ✨ Melhorias Principais

#### 1. Configuração Centralizada
- **Criado**: `web/config.py` com todas as configurações centralizadas
- **Suporte a variáveis de ambiente**: PORT, HOST, ALLOWED_ORIGINS, POKER_DEBUG, etc.
- **Benefícios**: Facilita configuração para diferentes ambientes, resolve inconsistência de portas

#### 2. Melhorias de Segurança e Validação
- **Validação de inputs**: Funções `sanitize_player_name()` e `validate_player_action()`
- **Prevenção de XSS**: Sanitização de nomes de jogadores
- **Validação rigorosa**: Verificação de ações e valores antes de processar
- **CORS configurável**: Suporte a origens específicas via variável de ambiente

#### 3. Tratamento de Erros Melhorado
- **Criado**: `players/error_handling.py` com utilitários seguros
- **Logging estruturado**: Configurável via `POKER_PLAYER_LOG_LEVEL`
- **Operações seguras**: `safe_memory_save()` e `safe_memory_load()` com tratamento robusto
- **Elimina erros silenciosos**: Substitui `pass` por logging apropriado

#### 4. Refatoração de Código Duplicado
- **Criado**: `players/hand_utils.py` com funções compartilhadas
- **Criado**: `players/constants.py` com constantes nomeadas
- **Atualizado**: `players/tight_player.py` para usar novos utilitários
- **Benefícios**: Reduz duplicação, facilita manutenção, melhora legibilidade

#### 5. Melhorias de Thread Safety
- **Melhorado**: Classe `BotWrapper` com `try/finally` para limpeza garantida
- **Proteção**: Verificação antes de limpar `thinking_uuid` (evita race conditions)

#### 6. DEBUG_MODE Desativado em Produção
- **Alterado**: `web/js/game.js` - DEBUG_MODE padrão agora é `false`
- **Benefício**: Reduz logs excessivos e melhora performance

### 📁 Novos Arquivos

- `web/config.py` - Configurações centralizadas
- `players/hand_utils.py` - Utilitários compartilhados para avaliação de mão
- `players/constants.py` - Constantes nomeadas
- `players/error_handling.py` - Tratamento de erros e logging
- `docs/MELHORIAS_IMPLEMENTADAS.md` - Documentação das melhorias

### 🔧 Arquivos Modificados

- `web/server.py` - Configuração, validação, thread safety
- `web/js/game.js` - DEBUG_MODE desativado
- `players/tight_player.py` - Refatorado para usar novos utilitários
- `README.md` - Documentação atualizada (porta 5002)
- `docs/DOCUMENTACAO_COMPLETA.md` - Seção de configuração adicionada

### ✅ Compatibilidade

- ✅ Totalmente compatível com código existente
- ✅ Funciona com valores padrão se nenhuma configuração for fornecida
- ✅ **NÃO altera a lógica do PyPokerEngine** (motor original mantido intacto)

### 🚀 Como Usar

**Configuração via variáveis de ambiente:**
```bash
export PORT=5002
export ALLOWED_ORIGINS=http://localhost:3000
export POKER_DEBUG=true
python3 web/server.py
```

**Documentação completa**: Veja `docs/MELHORIAS_IMPLEMENTADAS.md`

---

## [2024-11-21] - Centralização de Memórias e Organização de Documentos

### ✨ Mudanças Principais

#### 1. Memória Centralizada dos Bots
- **Antes**: Arquivos de memória espalhados na raiz do projeto e no diretório `web/`
- **Agora**: Todos os arquivos de memória centralizados em `data/memory/`
- **Benefícios**:
  - Um único local para gerenciar memórias
  - Facilita backup e manutenção
  - Evita duplicação de dados
  - Funciona tanto para terminal quanto web

#### 2. Sistema de Utilitários
- Criado `players/memory_utils.py` com função `get_memory_path()`
- Todos os bots agora usam caminho centralizado automaticamente
- Criação automática do diretório se não existir

#### 3. Organização de Documentos
- Criado diretório `docs/` para toda documentação
- Movidos:
  - `DOCUMENTACAO_COMPLETA.md` → `docs/DOCUMENTACAO_COMPLETA.md`
  - `DEBUGGING.md` → `docs/DEBUGGING.md`
- Criado `docs/README.md` com índice da documentação

#### 4. Atualizações no Código
- Todos os 9 players atualizados para usar `get_memory_path()`
- Servidor web atualizado para resetar memórias do novo local
- Script de migração criado (`migrate_memory.py`)

### 📁 Nova Estrutura

```
poker_test/
├── data/
│   └── memory/              # ✨ NOVO: Memórias centralizadas
│       ├── tight_player_memory.json
│       ├── aggressive_player_memory.json
│       └── ...
│
├── docs/                     # ✨ NOVO: Documentação organizada
│   ├── DOCUMENTACAO_COMPLETA.md
│   ├── DEBUGGING.md
│   └── README.md
│
├── players/
│   ├── memory_utils.py       # ✨ NOVO: Utilitários de memória
│   └── ...
│
└── migrate_memory.py        # ✨ NOVO: Script de migração
```

### 🔧 Arquivos Modificados

**Players atualizados:**
- `players/tight_player.py`
- `players/aggressive_player.py`
- `players/random_player.py`
- `players/smart_player.py`
- `players/balanced_player.py`
- `players/adaptive_player.py`
- `players/conservative_aggressive_player.py`
- `players/opportunistic_player.py`
- `players/hybrid_player.py`
- `players/learning_player.py`

**Outros arquivos:**
- `web/server.py` - Atualizado para usar novo local de memórias
- `README.md` - Adicionados links para documentação
- `docs/DOCUMENTACAO_COMPLETA.md` - Atualizado com nova estrutura

### 📝 Arquivos Criados

- `players/memory_utils.py` - Função utilitária para caminhos de memória
- `docs/README.md` - Índice da documentação
- `migrate_memory.py` - Script de migração de memórias
- `.gitignore` - Ignora arquivos de memória no git

### 🗑️ Arquivos Removidos

- Arquivos `*_memory.json` da raiz do projeto (movidos para `data/memory/`)
- Arquivos `*_memory.json` do diretório `web/` (movidos para `data/memory/`)

### ✅ Compatibilidade

- ✅ Totalmente compatível com código existente
- ✅ Migração automática de arquivos antigos
- ✅ Funciona tanto no terminal quanto na web
- ✅ Sem breaking changes

### 🚀 Como Usar

**Primeira vez após atualização:**
```bash
# Migração automática (já executada)
python3 migrate_memory.py
```

**Resetar memórias:**
```bash
# Via terminal
rm data/memory/*_memory.json

# Via API web
curl -X POST http://localhost:5002/api/reset_memory
```

**Acessar documentação:**
- Documentação completa: `docs/DOCUMENTACAO_COMPLETA.md`
- Guia de debugging: `docs/DEBUGGING.md`

