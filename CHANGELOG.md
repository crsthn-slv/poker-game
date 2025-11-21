# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.0.0] - 2025-11-21

### Adicionado
- Interface web completa com Flask
- 9 bots diferentes com estratégias únicas
- Sistema de aprendizado adaptativo
- Memória persistente entre partidas
- Visualização completa de cartas, pot e stacks
- Sistema de rounds (10 rounds por partida)
- Modo debug com logs detalhados
- Endpoint `/api/force_next_round` para forçar início de próximo round
- Timeout em `declare_action` para evitar travamentos
- Sistema de validação de ações do jogador
- Sanitização de inputs para prevenir XSS
- Configuração centralizada via `web/config.py`
- Tratamento robusto de erros com `players/error_handling.py`
- Utilitários compartilhados em `players/hand_utils.py` e `players/constants.py`
- Documentação completa em `docs/`
- Testes automatizados
- CI/CD com GitHub Actions
- Dependabot para atualizações de dependências
- Templates de issues e pull requests
- Código de conduta e política de segurança
- Makefile para comandos comuns
- Pre-commit hooks para qualidade de código
- EditorConfig para consistência de código

### Corrigido
- Bug onde próximo round não iniciava automaticamente
- Problema de fold automático quando jogador não respondia
- Erro 405 ao chamar endpoint `force_next_round` (requeria reiniciar servidor)
- Dados de fim de round sendo restaurados após limpeza
- Race conditions no `BotWrapper`
- Inconsistência de portas entre servidor e frontend

### Melhorado
- Thread safety em operações críticas
- Logging estruturado e configurável
- Detecção de novo round mais robusta
- Performance do salvamento de memória
- Documentação e comentários no código
- Estrutura do projeto organizada

### Segurança
- Validação de inputs do usuário
- Sanitização de nomes de jogadores
- CORS configurável
- Tratamento seguro de operações de arquivo

## [0.1.0] - 2024-12-XX

### Adicionado
- Versão inicial do projeto
- Bots básicos com estratégias simples
- Interface web básica
- Sistema de memória básico

---

[1.0.0]: https://github.com/crsthn-slv/poker-game/releases/tag/v1.0.0
[0.1.0]: https://github.com/crsthn-slv/poker-game/releases/tag/v0.1.0
