#!/usr/bin/env python3
"""
Script para testar 100 partidas com distribuição equilibrada de bots.
Limpa memórias, roda partidas e gera relatório com análise de comportamento.
"""

from pypokerengine.api.game import setup_config, start_poker
from players.tight_player import TightPlayer
from players.aggressive_player import AggressivePlayer
from players.random_player import RandomPlayer
from players.smart_player import SmartPlayer
from players.learning_player import LearningPlayer
from players.balanced_player import BalancedPlayer
from players.adaptive_player import AdaptivePlayer
from players.calculated_player import CalculatedPlayer
from players.calm_player import CalmPlayer
from players.cautious_player import CautiousPlayer
from players.conservative_aggressive_player import ConservativeAggressivePlayer
from players.fish_player import FishPlayer
from players.flexible_player import FlexiblePlayer
from players.hybrid_player import HybridPlayer
from players.moderate_player import ModeratePlayer
from players.observant_player import ObservantPlayer
from players.opportunistic_player import OpportunisticPlayer
from players.patient_player import PatientPlayer
from players.steady_player import SteadyPlayer
from players.steady_aggressive_player import SteadyAggressivePlayer
from players.thoughtful_player import ThoughtfulPlayer
import json
import os
import random
from collections import defaultdict

# Todos os bots disponíveis (exceto ConsolePlayer que é para interface)
ALL_BOTS = {
    'Tight': TightPlayer,
    'Aggressive': AggressivePlayer,
    'Random': RandomPlayer,
    'Smart': SmartPlayer,
    'Learning': LearningPlayer,
    'Balanced': BalancedPlayer,
    'Adaptive': AdaptivePlayer,
    'Calculated': CalculatedPlayer,
    'Calm': CalmPlayer,
    'Cautious': CautiousPlayer,
    'ConservativeAggressive': ConservativeAggressivePlayer,
    'Fish': FishPlayer,
    'Flexible': FlexiblePlayer,
    'Hybrid': HybridPlayer,
    'Moderate': ModeratePlayer,
    'Observant': ObservantPlayer,
    'Opportunistic': OpportunisticPlayer,
    'Patient': PatientPlayer,
    'Steady': SteadyPlayer,
    'SteadyAggressive': SteadyAggressivePlayer,
    'Thoughtful': ThoughtfulPlayer
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

def ensure_balanced_distribution(total_games=100, bots_per_game=9):
    """Garante que todos os bots joguem aproximadamente o mesmo número de partidas."""
    num_bots = len(ALL_BOTS)
    total_slots = total_games * bots_per_game
    games_per_bot = total_slots // num_bots
    remainder = total_slots % num_bots
    
    # Cria lista de seleções garantindo distribuição equilibrada
    bot_selections = []
    bot_counts = defaultdict(int)
    bot_list = list(ALL_BOTS.keys())
    
    # Preenche com distribuição base
    for game_idx in range(total_games):
        # Calcula quantas vezes cada bot deveria ter jogado até agora
        expected_games = (game_idx + 1) * bots_per_game / num_bots
        
        # Prioriza bots que estão abaixo da média esperada
        bot_priorities = []
        for bot in bot_list:
            priority = expected_games - bot_counts[bot]
            bot_priorities.append((priority, bot))
        
        # Ordena por prioridade (maior prioridade = mais abaixo da média)
        bot_priorities.sort(reverse=True)
        
        # Seleciona bots priorizando os que estão mais abaixo
        selected = []
        used_bots = set()
        
        # Primeiro, pega os bots com maior prioridade
        for priority, bot in bot_priorities:
            if len(selected) >= bots_per_game:
                break
            if bot not in used_bots:
                selected.append(bot)
                used_bots.add(bot)
        
        # Se ainda não temos 9 bots, completa aleatoriamente
        if len(selected) < bots_per_game:
            remaining_bots = [b for b in bot_list if b not in used_bots]
            needed = bots_per_game - len(selected)
            if remaining_bots:
                selected.extend(random.sample(remaining_bots, min(needed, len(remaining_bots))))
        
        # Garante que temos exatamente bots_per_game bots
        if len(selected) < bots_per_game:
            # Se ainda faltam, completa com repetição dos menos usados
            while len(selected) < bots_per_game:
                least_used = min(bot_list, key=lambda b: bot_counts[b])
                if least_used not in selected:
                    selected.append(least_used)
                else:
                    # Se já está na lista, pega o próximo menos usado
                    sorted_by_usage = sorted(bot_list, key=lambda b: bot_counts[b])
                    for bot in sorted_by_usage:
                        if bot not in selected:
                            selected.append(bot)
                            break
        
        # Embaralha para evitar padrões
        random.shuffle(selected)
        bot_selections.append(selected[:bots_per_game])
        
        # Atualiza contadores
        for bot in selected[:bots_per_game]:
            bot_counts[bot] += 1
    
    return bot_selections

def run_100_games():
    """Roda 100 partidas com 9 bots por partida e distribuição equilibrada."""
    
    print("=" * 70)
    print("Teste de 100 Partidas - 9 Bots por Partida")
    print("Distribuição Equilibrada")
    print("=" * 70)
    print()
    
    # Limpa memórias
    print("🧹 Limpando memórias...")
    clear_all_memories()
    print()
    
    # Gera distribuição equilibrada
    print("📊 Gerando distribuição equilibrada de bots...")
    bot_selections = ensure_balanced_distribution(100, 9)
    
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
    
    print("🎮 Iniciando 100 partidas...")
    print("=" * 70)
    
    for game_num in range(1, 101):
        if game_num % 10 == 0:
            print(f"\n📈 Progresso: {game_num}/100 partidas")
        
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
            
            # Determina o vencedor (maior stack)
            winner = None
            max_stack = 0
            for player_info in game_result['players']:
                name = player_info['name']
                stack = player_info['stack']
                result['players'][name] = stack
                
                if stack > max_stack:
                    max_stack = stack
                    winner = name
                
                # Atualiza estatísticas
                bot_stats[name]['games_played'] += 1
                bot_stats[name]['total_stack'] += stack
                if stack > bot_stats[name]['max_stack']:
                    bot_stats[name]['max_stack'] = stack
                if bot_stats[name]['min_stack'] == 0 or stack < bot_stats[name]['min_stack']:
                    bot_stats[name]['min_stack'] = stack
            
            # Conta vitória do vencedor
            if winner:
                bot_stats[winner]['wins'] += 1
            
            results.append(result)
            
        except Exception as e:
            print(f"❌ Erro na partida {game_num}: {e}")
            continue
    
    print("\n" + "=" * 70)
    print("✅ 100 Partidas Concluídas!")
    print("=" * 70)
    
    return results, bot_stats

def analyze_behavior(results, bot_stats):
    """Analisa o comportamento entre os bots."""
    print("\n" + "=" * 70)
    print("🔍 ANÁLISE DE COMPORTAMENTO")
    print("=" * 70)
    
    # Matriz de interações (quando bots jogam juntos)
    interactions = defaultdict(lambda: defaultdict(int))
    head_to_head = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'games': 0}))
    
    for result in results:
        bots_in_game = result['bots']
        winner = max(result['players'].items(), key=lambda x: x[1])[0]
        
        # Conta interações
        for i, bot1 in enumerate(bots_in_game):
            for bot2 in bots_in_game[i+1:]:
                interactions[bot1][bot2] += 1
                interactions[bot2][bot1] += 1
        
        # Head-to-head
        for bot in bots_in_game:
            if bot == winner:
                for opponent in bots_in_game:
                    if opponent != bot:
                        head_to_head[bot][opponent]['wins'] += 1
                        head_to_head[bot][opponent]['games'] += 1
                        head_to_head[opponent][bot]['games'] += 1
    
    # Encontra pares mais frequentes
    print("\n🤝 PARES DE BOTS MAIS FREQUENTES:")
    print("-" * 70)
    pair_counts = []
    for bot1 in interactions:
        for bot2 in interactions[bot1]:
            if bot1 < bot2:  # Evita duplicatas
                pair_counts.append((bot1, bot2, interactions[bot1][bot2]))
    
    pair_counts.sort(key=lambda x: x[2], reverse=True)
    for bot1, bot2, count in pair_counts[:10]:
        print(f"  {bot1} vs {bot2}: {count} partidas juntos")
    
    # Head-to-head mais significativos
    print("\n⚔️ HEAD-TO-HEAD (Top 10):")
    print("-" * 70)
    h2h_list = []
    for bot1 in head_to_head:
        for bot2 in head_to_head[bot1]:
            stats = head_to_head[bot1][bot2]
            if stats['games'] >= 3:  # Mínimo de 3 partidas
                win_rate = (stats['wins'] / stats['games'] * 100) if stats['games'] > 0 else 0
                h2h_list.append((bot1, bot2, stats['wins'], stats['games'], win_rate))
    
    h2h_list.sort(key=lambda x: x[3], reverse=True)  # Ordena por número de partidas
    for bot1, bot2, wins, games, win_rate in h2h_list[:10]:
        print(f"  {bot1} vs {bot2}: {wins}/{games} vitórias ({win_rate:.1f}%)")
    
    return interactions, head_to_head

def generate_report(results, bot_stats):
    """Gera relatório completo com análise de comportamento."""
    
    print("\n" + "=" * 70)
    print("📊 RELATÓRIO FINAL")
    print("=" * 70)
    
    # Análise de comportamento
    interactions, head_to_head = analyze_behavior(results, bot_stats)
    
    # Resumo geral
    print("\n📈 RESUMO GERAL:")
    total_games = len(results)
    print(f"  Total de partidas: {total_games}")
    print(f"  Bots participantes: {len(bot_stats)}")
    print(f"  Bots por partida: 9")
    
    # Prepara conteúdo do relatório para arquivo
    report_lines = []
    report_lines.append("# Relatório - 100 Partidas de Teste\n")
    report_lines.append("## Resumo Executivo\n")
    report_lines.append(f"Foram realizadas **{total_games} partidas** com **9 bots por partida**.\n")
    report_lines.append(f"Total de **{len(bot_stats)} bots diferentes** participaram dos testes.\n")
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
    
    # Análise de comportamento no relatório
    report_lines.append("\n---\n")
    report_lines.append("\n## Análise de Comportamento\n")
    
    # Pares mais frequentes
    pair_counts = []
    for bot1 in interactions:
        for bot2 in interactions[bot1]:
            if bot1 < bot2:
                pair_counts.append((bot1, bot2, interactions[bot1][bot2]))
    pair_counts.sort(key=lambda x: x[2], reverse=True)
    
    report_lines.append("\n### Pares de Bots Mais Frequentes\n")
    for bot1, bot2, count in pair_counts[:15]:
        report_lines.append(f"- **{bot1}** e **{bot2}**: {count} partidas juntos\n")
    
    # Head-to-head
    h2h_list = []
    for bot1 in head_to_head:
        for bot2 in head_to_head[bot1]:
            stats = head_to_head[bot1][bot2]
            if stats['games'] >= 3:
                win_rate = (stats['wins'] / stats['games'] * 100) if stats['games'] > 0 else 0
                h2h_list.append((bot1, bot2, stats['wins'], stats['games'], win_rate))
    h2h_list.sort(key=lambda x: x[3], reverse=True)
    
    report_lines.append("\n### Head-to-Head Significativos\n")
    for bot1, bot2, wins, games, win_rate in h2h_list[:15]:
        report_lines.append(f"- **{bot1}** vs **{bot2}**: {wins}/{games} vitórias ({win_rate:.1f}%)\n")
    
    # Análise geral
    report_lines.append("\n---\n")
    report_lines.append("\n## Evolução dos Parâmetros\n")
    
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
    report_lines.append("\n1. Todos os bots usam o sistema de memória unificado.\n")
    report_lines.append("2. Distribuição equilibrada garantiu participação justa de todos os bots.\n")
    report_lines.append("3. Análise de comportamento revela padrões de interação entre bots.\n")
    report_lines.append("4. Head-to-head mostra quais bots têm vantagem em confrontos diretos.\n")
    
    # Salva relatório
    report_content = "".join(report_lines)
    with open("relatorio_100_partidas.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print("\n📄 Relatório salvo em: relatorio_100_partidas.md")
    print("\n" + "=" * 70)

if __name__ == "__main__":
    results, bot_stats = run_100_games()
    generate_report(results, bot_stats)

