# Poker Game - PyPokerEngine

Jogo de Poker com interface web e múltiplos bots com aprendizado adaptativo.

## 📚 Documentação

- **[Documentação Completa](docs/DOCUMENTACAO_COMPLETA.md)** - Documentação técnica completa
- **[Guia de Debugging](docs/DEBUGGING.md)** - Como resolver problemas comuns

## Estrutura do Projeto

```
poker_test/
├── players/          # Todos os bots
│   ├── tight_player.py
│   ├── aggressive_player.py
│   ├── random_player.py
│   ├── smart_player.py
│   ├── balanced_player.py
│   ├── adaptive_player.py
│   ├── conservative_aggressive_player.py
│   ├── opportunistic_player.py
│   ├── hybrid_player.py
│   └── console_player.py
├── game/             # Scripts de jogo
│   ├── game.py
│   ├── game_advanced.py
│   └── play_console.py
├── web/              # UI web
│   ├── server.py
│   ├── templates/
│   │   ├── index.html
│   │   ├── config.html
│   │   └── game.html
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── config.js
│   │   ├── game.js
│   │   └── api.js
│   └── images/       # Link para imagens
├── images/           # Imagens de cartas
└── requirements.txt
```

## Instalação

```bash
pip install -r requirements.txt
```

## Como Jogar

### Modo Web (Recomendado)

1. Inicie o servidor:
```bash
cd web
python3 server.py
```

2. Abra o navegador em: `http://localhost:5002` (ou a porta configurada na variável de ambiente `PORT`)

3. Configure seu nome na página de configuração

4. Comece a jogar!

### Modo Terminal

```bash
# Jogo básico AI vs AI
python3 -m game.game

# Jogo avançado com todas as IAs
python3 -m game.game_advanced

# Jogar contra AIs (terminal interativo)
python3 -m game.play_console
```

## Bots Disponíveis

- **Tight**: Conservador, blefa 8% das vezes
- **Aggressive**: Agressivo, blefa 35% das vezes
- **Random**: Aleatório, blefa 25% das vezes
- **Smart**: Inteligente, blefe dinâmico (15% base)
- **Balanced**: Combina Tight + Aggressive
- **Adaptive**: Combina Smart + Random (exploração)
- **ConservativeAggressive**: Conservador → Agressivo
- **Opportunistic**: Identifica oportunidades
- **Hybrid**: Alterna entre todas as estratégias

Todos os bots têm **memória persistente** e evoluem entre partidas!

## Características

- Interface web moderna com dark mode
- Múltiplos bots com diferentes estratégias
- Sistema de aprendizado adaptativo
- Memória persistente entre partidas
- Visualização de cartas com imagens
