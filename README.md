# 🎰 Poker Game - PyPokerEngine

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.2-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-PEP%208-orange.svg)](https://www.python.org/dev/peps/pep-0008/)

Jogo de Poker Texas Hold'em com interface web moderna e múltiplos bots com aprendizado adaptativo usando PyPokerEngine.

## ✨ Características

- 🎮 **Interface Web Moderna** - UI responsiva com dark mode
- 🤖 **9 Bots Diferentes** - Cada um com estratégia única e aprendizado adaptativo
- 🧠 **Sistema de Memória Persistente** - Bots aprendem e evoluem entre partidas
- 🎯 **Visualização Completa** - Cartas, pot, stacks e histórico de ações
- 🔄 **Sistema de Rounds** - 10 rounds por partida com estatísticas detalhadas
- 🐛 **Debug Mode** - Logs detalhados para troubleshooting

## 📋 Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## 🚀 Instalação

1. **Clone o repositório:**
```bash
git clone https://github.com/crsthn-slv/poker-game.git
cd poker-game
```

2. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

## 🎮 Como Jogar

### Modo Web (Recomendado)

1. **Inicie o servidor:**
```bash
cd web
python3 server.py
```

2. **Abra o navegador:**
   - Acesse: `http://localhost:5002`
   - Configure seu nome na página de configuração
   - Comece a jogar!

3. **Configurações opcionais:**
```bash
# Porta personalizada
export PORT=8080

# Modo debug
export FLASK_DEBUG=true
```

### Modo Terminal

```bash
# Jogo básico AI vs AI
python3 -m game.game

# Jogo avançado com todas as IAs
python3 -m game.game_advanced

# Jogar contra AIs (terminal interativo)
python3 -m game.play_console
```

## 🤖 Bots Disponíveis

| Bot | Estratégia | Bluff Base | Aprendizado |
|-----|-----------|------------|-------------|
| **Tight** | Conservador | 8% | Ajusta quando perde muito |
| **Aggressive** | Agressivo | 35% | Ajusta rapidamente |
| **Random** | Aleatório | 25% | Probabilidades adaptativas |
| **Smart** | Inteligente | 15% | Bluff dinâmico |
| **Balanced** | Equilibrado | 20% | Combina estratégias |
| **Adaptive** | Adaptativo | Variável | Exploração vs Exploração |
| **ConservativeAggressive** | Conservador→Agressivo | 10-30% | Transição baseada em resultados |
| **Opportunistic** | Oportunista | 18% | Identifica oportunidades |
| **Hybrid** | Híbrido | Variável | Alterna entre todas estratégias |

Todos os bots têm **memória persistente** e evoluem entre partidas!

## 📁 Estrutura do Projeto

```
poker-game/
├── players/              # Bots com diferentes estratégias
│   ├── tight_player.py
│   ├── aggressive_player.py
│   ├── smart_player.py
│   └── ...
├── game/                 # Scripts de jogo
│   ├── game.py
│   ├── game_advanced.py
│   └── play_console.py
├── web/                  # Interface web
│   ├── server.py         # Servidor Flask
│   ├── templates/        # Templates HTML
│   ├── css/              # Estilos
│   └── js/               # JavaScript
├── images/               # Imagens de cartas
├── data/                 # Dados persistentes
│   └── memory/           # Memórias dos bots
├── docs/                 # Documentação
├── tests/                # Testes
└── requirements.txt      # Dependências
```

## 📚 Documentação

- **[Documentação Completa](docs/DOCUMENTACAO_COMPLETA.md)** - Documentação técnica detalhada
- **[Guia de Debugging](docs/DEBUGGING.md)** - Como resolver problemas comuns
- **[Investigação de Bugs](docs/INVESTIGACAO_PROXIMO_ROUND.md)** - Análise de problemas conhecidos

## 🧪 Testes

```bash
# Executar todos os testes
python3 -m pytest tests/

# Teste específico
python3 -m pytest tests/test_server.py
```

## 🛠️ Desenvolvimento

### Configuração do Ambiente

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

### Debug Mode

Ative o modo debug no console do navegador:
```javascript
DEBUG_MODE = true
```

Ou no servidor:
```bash
export FLASK_DEBUG=true
export DEBUG_MODE=true
```

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor, leia o [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes sobre nosso código de conduta e processo de submissão de pull requests.

## 📝 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🙏 Agradecimentos

- [PyPokerEngine](https://github.com/ishikota/PyPokerEngine) - Motor de poker usado como base
- Comunidade open source

## 📊 Status do Projeto

- ✅ Interface web funcional
- ✅ Sistema de bots com aprendizado
- ✅ Memória persistente
- ✅ Sistema de rounds
- ✅ Debug e logging
- 🔄 Melhorias contínuas

## 🐛 Problemas Conhecidos

- Alguns bots podem demorar para salvar memória (otimização em andamento)
- PyPokerEngine pode não iniciar próximo round automaticamente (workaround implementado)

Veja [docs/INVESTIGACAO_PROXIMO_ROUND.md](docs/INVESTIGACAO_PROXIMO_ROUND.md) para mais detalhes.

## 📧 Contato

Para questões, sugestões ou problemas, abra uma [issue](https://github.com/crsthn-slv/poker-game/issues).

---

⭐ Se este projeto foi útil para você, considere dar uma estrela!
