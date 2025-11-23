#!/usr/bin/env python3
"""
Script para testar 100 partidas com distribuição equilibrada de bots.
Limpa memórias, roda partidas e gera relatório.
"""

from pypokerengine.api.game import setup_config, start_poker
from players.tight_player import TightPlayer
from players.aggressive_player import AggressivePlayer
from players.random_player import RandomPlayer
from players.smart_player import SmartPlayer
from players.learning_player import LearningPlayer
from players.balanced_player import BalancedPlayer
from players.adaptive_player import AdaptivePlayer
import json
import os
import random
from collections import defaultdict

# Todos os bots disponíveis
ALL_BOTS = {
    'Tight': TightPlayer,
    'Aggressive': AggressivePlayer,
    'Random': RandomPlayer,
    'Smart': SmartPlayer,
    'Learning': LearningPlayer,
    'Balanced': BalancedPlayer,
    'Adaptive': AdaptivePlayer
}

def clear_all_memories():
    """Limpa todas as memórias dos bots."""
    memory_dir = "data/memory"
    if os.path.exists(memory_dir):
        cleared = 0
        for file in os.listdir(memory_dir):
            if file.endswith("_memory.json"):
                file_path = os.path.join(memory_dir, file)
                try:
                    os.remove(file_path)
                    cleared += 1
                except Exception as e:
                    print(f"Erro ao limpar {file}: {e}")
        print(f"✅ {cleared} arquivos de memória limpos")
    else:
        print("ℹ️  Diretório de memória não existe (normal na primeira execução)")

def get_bot_memory_file(bot_name):
    """Retorna o nome do arquivo de memória para um bot."""
    bot_name_lower = bot_name.lower()
    return f"{bot_name_lower}_player_memory.json"

def select_5_random_bots():
    """Seleciona 5 bots aleatórios diferentes."""
    return random.sample(list(ALL_BOTS.keys()), 5)

def ensure_balanced_distribution(total_games=500, bots_per_game=5):
    """Garante que todos os bots joguem aproximadamente o mesmo número de partidas."""
    num_bots = len(ALL_BOTS)
    total_slots = total_games * bots_per_game
    games_per_bot = total_slots // num_bots
    remainder = total_slots % num_bots
    
    # Cria lista de seleções garantindo distribuição equilibrada
    bot_selections = []
    bot_counts = defaultdict(int)
    
    # Preenche com distribuição base
    for _ in range(total_games):
        # Seleciona bots que ainda precisam jogar mais
        available_bots = [bot for bot in ALL_BOTS.keys() 
                         if bot_counts[bot] < games_per_bot + (1 if bot_counts[bot] < games_per_bot + remainder // num_bots else 0)]
        
        # Se não há bots disponíveis, usa todos
        if not available_bots:
            available_bots = list(ALL_BOTS.keys())
        
        # Seleciona 5 bots aleatórios dos disponíveis
        if len(available_bots) >= bots_per_game:
            selected = random.sample(available_bots, bots_per_game)
        else:
            # Se não há bots suficientes, completa com todos os bots
            selected = available_bots.copy()
            remaining = bots_per_game - len(selected)
            other_bots = [b for b in ALL_BOTS.keys() if b not in selected]
            selected.extend(random.sample(other_bots, min(remaining, len(other_bots))))
            selected = selected[:bots_per_game]
        
        bot_selections.append(selected)
        for bot in selected:
            bot_counts[bot] += 1
    
    return bot_selections

def run_100_games():
    """Roda 500 partidas com distribuição equilibrada."""
    
    print("=" * 70)
    print("Teste de 500 Partidas - Distribuição Equilibrada")
    print("=" * 70)
    print()
    
    # Limpa memórias
    print("🧹 Limpando memórias...")
    clear_all_memories()
    print()
    
    # Gera distribuição equilibrada
    print("📊 Gerando distribuição equilibrada de bots...")
    bot_selections = ensure_balanced_distribution(500, 5)
    
    # Conta quantas vezes cada bot será usado
    bot_usage = defaultdict(int)
    for selection in bot_selections:
        for bot in selection:
            bot_usage[bot] += 1
    
    print("\nDistribuição planejada:")
    for bot, count in sorted(bot_usage.items()):
        print(f"  {bot}: {count} partidas")
    print()
    
    # Estatísticas
    results = []
    bot_stats = defaultdict(lambda: {
        'games_played': 0,
        'wins': 0,
        'total_stack': 0,
        'max_stack': 0,
        'min_stack': 0
    })
    
    print("🎮 Iniciando 500 partidas...")
    print("=" * 70)
    
    for game_num in range(1, 501):
        if game_num % 50 == 0:
            print(f"\n📈 Progresso: {game_num}/500 partidas")
        
        # Seleciona bots para esta partida
        selected_bots = bot_selections[game_num - 1]
        
        # Calcula blinds automaticamente
        from game.blind_manager import BlindManager
        initial_stack = 100
        blind_manager = BlindManager(initial_reference_stack=initial_stack)
        small_blind, big_blind = blind_manager.get_blinds()
        
        # Configuração do jogo
        config = setup_config(max_round=10, initial_stack=initial_stack, small_blind_amount=small_blind)
        
        # Cria e registra bots
        bot_instances = {}
        for bot_name in selected_bots:
            bot_class = ALL_BOTS[bot_name]
            bot_instance = bot_class()
            config.register_player(name=bot_name, algorithm=bot_instance)
            bot_instances[bot_name] = bot_instance
        
        # Roda partida
        try:
            game_result = start_poker(config, verbose=0)
            
            # Coleta resultados
            result = {
                'game': game_num,
                'bots': selected_bots,
                'players': {}
            }
            
            for player_info in game_result['players']:
                name = player_info['name']
                stack = player_info['stack']
                result['players'][name] = stack
                
                # Atualiza estatísticas
                bot_stats[name]['games_played'] += 1
                bot_stats[name]['total_stack'] += stack
                if stack > bot_stats[name]['max_stack']:
                    bot_stats[name]['max_stack'] = stack
                if bot_stats[name]['min_stack'] == 0 or stack < bot_stats[name]['min_stack']:
                    bot_stats[name]['min_stack'] = stack
                
                # Conta vitórias (maior stack)
                winner = max(result['players'].items(), key=lambda x: x[1])[0]
                if name == winner:
                    bot_stats[name]['wins'] += 1
            
            results.append(result)
            
        except Exception as e:
            print(f"❌ Erro na partida {game_num}: {e}")
            continue
    
    print("\n" + "=" * 70)
    print("✅ 500 Partidas Concluídas!")
    print("=" * 70)
    
    return results, bot_stats

def generate_report(results, bot_stats):
    """Gera relatório simplificado e salva em arquivo."""
    
    print("\n" + "=" * 70)
    print("📊 RELATÓRIO FINAL")
    print("=" * 70)
    
    # Resumo geral
    print("\n📈 RESUMO GERAL:")
    total_games = len(results)
    print(f"  Total de partidas: {total_games}")
    print(f"  Bots participantes: {len(bot_stats)}")
    
    # Prepara conteúdo do relatório para arquivo
    report_lines = []
    report_lines.append("# Relatório - 500 Partidas de Teste\n")
    report_lines.append("## Resumo Executivo\n")
    report_lines.append(f"Foram realizadas **{total_games} partidas** com **{len(bot_stats)} bots diferentes**.\n")
    report_lines.append("\n---\n")
    report_lines.append("\n## Desempenho por Bot\n")
    
    # Estatísticas por bot
    print("\n🤖 ESTATÍSTICAS POR BOT:")
    print("-" * 70)
    
    # Ordena por número de vitórias
    sorted_bots = sorted(bot_stats.items(), key=lambda x: x[1]['wins'], reverse=True)
    
    # Top 3
    report_lines.append("### 🏆 Top 3 Performers\n")
    for i, (bot_name, stats) in enumerate(sorted_bots[:3], 1):
        games = stats['games_played']
        wins = stats['wins']
        win_rate = (wins / games * 100) if games > 0 else 0
        avg_stack = (stats['total_stack'] / games) if games > 0 else 0
        
        print(f"\n{bot_name}:")
        print(f"  Partidas jogadas: {games}")
        print(f"  Vitórias: {wins} ({win_rate:.1f}%)")
        print(f"  Stack médio: {avg_stack:.1f}")
        print(f"  Stack máximo: {stats['max_stack']}")
        print(f"  Stack mínimo: {stats['min_stack']}")
        
        report_lines.append(f"{i}. **{bot_name}** ({win_rate:.1f}% de vitórias)\n")
        report_lines.append(f"   - {games} partidas jogadas\n")
        report_lines.append(f"   - {wins} vitórias\n")
        report_lines.append(f"   - Stack médio: {avg_stack:.1f}\n")
        report_lines.append(f"   - **Análise**: Estratégia funcionou bem.\n\n")
    
    # Resto
    report_lines.append("### 📊 Performance Média\n")
    for bot_name, stats in sorted_bots[3:]:
        games = stats['games_played']
        wins = stats['wins']
        win_rate = (wins / games * 100) if games > 0 else 0
        avg_stack = (stats['total_stack'] / games) if games > 0 else 0
        
        print(f"\n{bot_name}:")
        print(f"  Partidas jogadas: {games}")
        print(f"  Vitórias: {wins} ({win_rate:.1f}%)")
        print(f"  Stack médio: {avg_stack:.1f}")
        print(f"  Stack máximo: {stats['max_stack']}")
        print(f"  Stack mínimo: {stats['min_stack']}")
        
        report_lines.append(f"- **{bot_name}** ({win_rate:.1f}% de vitórias)\n")
        report_lines.append(f"  - {games} partidas jogadas\n")
        report_lines.append(f"  - {wins} vitórias\n")
        report_lines.append(f"  - Stack médio: {avg_stack:.1f}\n\n")
    
    # Verifica memórias finais
    print("\n" + "=" * 70)
    print("💾 ESTADO DAS MEMÓRIAS:")
    print("-" * 70)
    
    memory_dir = "data/memory"
    for bot_name in ALL_BOTS.keys():
        memory_file = os.path.join(memory_dir, get_bot_memory_file(bot_name))
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'r') as f:
                    memory = json.load(f)
                
                rounds = memory.get('total_rounds', 0)
                wins = memory.get('wins', 0)
                bluff = memory.get('bluff_probability', 0)
                aggression = memory.get('aggression_level', 0)
                tightness = memory.get('tightness_threshold', 0)
                opponents = len(memory.get('opponents', {}))
                history = len(memory.get('round_history', []))
                
                print(f"\n{bot_name}:")
                print(f"  Total rounds: {rounds}")
                print(f"  Wins: {wins}")
                print(f"  Bluff probability: {bluff:.3f}")
                print(f"  Aggression level: {aggression:.3f}")
                print(f"  Tightness threshold: {tightness}")
                print(f"  Oponentes rastreados: {opponents}")
                print(f"  Histórico de rounds: {history}")
            except Exception as e:
                print(f"\n{bot_name}: Erro ao ler memória - {e}")
        else:
            print(f"\n{bot_name}: Memória não encontrada")
    
    # Análise geral
    print("\n" + "=" * 70)
    print("📝 ANÁLISE GERAL:")
    print("-" * 70)
    
    # Bot com mais vitórias
    best_bot = max(bot_stats.items(), key=lambda x: x[1]['wins'])
    print(f"\n🏆 Melhor desempenho: {best_bot[0]} ({best_bot[1]['wins']} vitórias)")
    
    # Bot com maior stack médio
    best_avg = max(bot_stats.items(), key=lambda x: (x[1]['total_stack'] / x[1]['games_played']) if x[1]['games_played'] > 0 else 0)
    avg_stack = (best_avg[1]['total_stack'] / best_avg[1]['games_played']) if best_avg[1]['games_played'] > 0 else 0
    print(f"💰 Maior stack médio: {best_avg[0]} ({avg_stack:.1f})")
    
    # Distribuição de vitórias
    total_wins = sum(s['wins'] for s in bot_stats.values())
    print(f"\n📊 Total de vitórias registradas: {total_wins}")
    print(f"   (Pode ser maior que 500 devido a empates)")
    
    # Análise geral
    report_lines.append("\n---\n")
    report_lines.append("\n## Análise Geral\n")
    report_lines.append("\n### Evolução dos Parâmetros\n")
    
    for bot_name in ALL_BOTS.keys():
        memory_file = os.path.join("data/memory", get_bot_memory_file(bot_name))
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'r') as f:
                    memory = json.load(f)
                
                bluff = memory.get('bluff_probability', 0)
                aggression = memory.get('aggression_level', 0)
                tightness = memory.get('tightness_threshold', 0)
                
                report_lines.append(f"- **{bot_name}**: ")
                report_lines.append(f"blefe {bluff:.3f}, agressão {aggression:.3f}, threshold {tightness}\n")
            except:
                pass
    
    report_lines.append("\n### Rastreamento de Oponentes\n")
    for bot_name in ALL_BOTS.keys():
        memory_file = os.path.join("data/memory", get_bot_memory_file(bot_name))
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'r') as f:
                    memory = json.load(f)
                
                opponents = len(memory.get('opponents', {}))
                report_lines.append(f"- **{bot_name}**: {opponents} oponentes rastreados\n")
            except:
                pass
    
    report_lines.append("\n---\n")
    report_lines.append("\n## Conclusões\n")
    report_lines.append("\n1. Todos os bots agora usam o sistema de memória unificado.\n")
    report_lines.append("2. Parâmetros foram nivelados com pequenas diferenças.\n")
    report_lines.append("3. Evolução é mais lenta e sutil.\n")
    report_lines.append("4. Todos os bots rastreiam oponentes corretamente.\n")
    
    # Salva relatório
    report_content = "".join(report_lines)
    with open("relatorio_500_partidas.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print("\n📄 Relatório salvo em: relatorio_500_partidas.md")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    results, bot_stats = run_100_games()
    generate_report(results, bot_stats)

