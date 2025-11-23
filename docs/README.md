# Documentação do Projeto

Este diretório contém toda a documentação do projeto de Poker Texas Hold'em.

## 📚 Documentação Principal

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

## 🔧 Documentação Técnica

### 🎯 [Algoritmos e Estratégias](ALGORITHMS_DOCUMENTATION.md)
Documentação detalhada sobre os algoritmos utilizados:
- Estratégias de cada bot
- Cálculo de probabilidades
- Avaliação de mãos
- Sistema de aprendizado

### 🎲 [Gerenciador de Blinds](BLIND_MANAGER.md)
Documentação sobre o sistema de blinds:
- Como funciona o blind manager
- Configuração de blinds
- Estrutura e implementação

## 🐛 Debugging e Troubleshooting

### 🐛 [Guia de Debugging](DEBUGGING.md)
Guia completo para identificar e resolver problemas:
- Como identificar erros de serialização
- Como ativar modo debug
- Checklist de problemas comuns
- Como testar manualmente
- Logs e mensagens de erro

### 📊 [Debug de Probabilidade](DEBUG_PROBABILITY.md)
Guia específico para debug do cálculo de probabilidade:
- Como ativar modo debug de probabilidade
- Onde os logs são salvos
- O que é registrado
- Como interpretar os logs

## 📋 Planejamento e Melhorias

### 💡 [Sugestões de Melhorias](SUGESTOES_MELHORIAS.md)
Documento com sugestões e melhorias futuras:
- Padronização de nomenclaturas
- Melhorias nos algoritmos
- Refatoração de código
- Otimizações de performance

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

