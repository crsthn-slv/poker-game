# Documentação do Projeto

Este diretório contém toda a documentação do projeto de Poker.

## Documentos Disponíveis

### 📘 [Documentação Completa](DOCUMENTACAO_COMPLETA.md)
Documentação técnica completa do sistema, incluindo:
- Visão geral do projeto
- Estrutura de arquivos
- Sistema de jogadores (bots)
- Sistema de aprendizado
- Interface web
- Servidor Flask
- Fluxo do jogo
- Detalhes técnicos

### 🤖 [Funcionamento dos Bots](FUNCIONAMENTO_BOTS.md)
Documentação detalhada sobre como os bots funcionam:
- Estrutura base dos bots
- Sistema de memória persistente
- Tipos de bots e estratégias
- Ciclo de vida de um bot
- Sistema de aprendizado
- Componentes compartilhados

### 🛠️ [Como Criar um Novo Bot](COMO_CRIAR_NOVO_BOT.md)
Guia passo a passo para criar um novo bot:
- Estrutura básica
- Implementação passo a passo
- Adicionando sistema de memória
- Implementando aprendizado
- Registrando o bot
- Testando o bot
- Exemplos completos

### 🐛 [Guia de Debugging](DEBUGGING.md)
Guia completo para identificar e resolver problemas:
- Como identificar erros de serialização
- Como ativar modo debug
- Checklist de problemas comuns
- Como testar manualmente
- Logs e mensagens de erro

## Estrutura de Dados

### Memória dos Bots
Todas as memórias dos bots estão centralizadas em `data/memory/`:
- `tight_player_memory.json`
- `aggressive_player_memory.json`
- `random_player_memory.json`
- `smart_player_memory.json`
- `balanced_player_memory.json`
- `adaptive_player_memory.json`
- E outros...

### Como Resetar Memórias

**Via API (Web):**
```bash
curl -X POST http://localhost:5002/api/reset_memory
```

**Via Terminal:**
```bash
rm data/memory/*_memory.json
```

## Links Úteis

- [README Principal](../README.md) - Guia rápido de instalação e uso
- [Requirements](../requirements.txt) - Dependências do projeto

