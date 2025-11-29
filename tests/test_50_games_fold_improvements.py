#!/usr/bin/env python3
"""
Script para testar 50 partidas após melhorias nos thresholds de fold.
Roda partidas e gera relatório com análise de comportamento.
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

def ensure_balanced_distribution(total_games=50, bots_per_game=9):
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

def run_50_games():
    """Roda 50 partidas com 9 bots por partida e distribuição equilibrada."""
    
    print("=" * 70)
    print("Teste de 50 Partidas - 9 Bots por Partida")
    print("Melhorias nos Thresholds de Fold")
    print("=" * 70)
    print()
    
    # Limpa memórias
    print("🧹 Limpando memórias...")
    clear_all_memories()
    print()
    
    # Gera distribuição equilibrada
    print("📊 Gerando distribuição equilibrada de bots...")
    bot_selections = ensure_balanced_distribution(50, 9)
    
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
        'min_stack': 0,
        'folds': 0,
        'calls': 0,
        'raises': 0
    })
    
    print("🎮 Iniciando 50 partidas...")
    print("=" * 70)
    
    for game_num in range(1, 51):
        if game_num % 10 == 0:
            print(f"\n📈 Progresso: {game_num}/50 partidas")
        
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
    print("✅ 50 Partidas Concluídas!")
    print("=" * 70)
    
    return results, bot_stats

def generate_report(results, bot_stats):
    """Gera relatório completo com análise de comportamento."""
    
    print("\n" + "=" * 70)
    print("📊 RELATÓRIO FINAL")
    print("=" * 70)
    
    # Resumo geral
    print("\n📈 RESUMO GERAL:")
    total_games = len(results)
    print(f"  Total de partidas: {total_games}")
    print(f"  Bots participantes: {len(bot_stats)}")
    print(f"  Bots por partida: 9")
    
    # Estatísticas por bot
    print("\n🤖 ESTATÍSTICAS POR BOT:")
    print("-" * 70)
    
    # Ordena por número de vitórias
    sorted_bots = sorted(bot_stats.items(), key=lambda x: x[1]['wins'], reverse=True)
    
    report_data = {
        'total_games': total_games,
        'bots_participants': len(bot_stats),
        'bots_per_game': 9,
        'bot_stats': []
    }
    
    for bot_name, stats in sorted_bots:
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
        
        report_data['bot_stats'].append({
            'name': bot_name,
            'games_played': games,
            'wins': wins,
            'win_rate': round(win_rate, 2),
            'avg_stack': round(avg_stack, 2),
            'max_stack': stats['max_stack'],
            'min_stack': stats['min_stack']
        })
    
    # Salva dados do relatório em JSON
    with open("data/test_results_50_games.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    print("\n📄 Dados do relatório salvos em: data/test_results_50_games.json")
    print("\n" + "=" * 70)
    
    return report_data

if __name__ == "__main__":
    results, bot_stats = run_50_games()
    report_data = generate_report(results, bot_stats)




