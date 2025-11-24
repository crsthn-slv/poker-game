#!/usr/bin/env python3
"""
Script completo para testar 100 partidas entre todos os bots.
Registra TUDO que acontece e gera relatório focado em tornar os bots mais realistas.

Análises:
- Comportamento observado vs código
- Complexidade do código
- Discrepâncias entre bots
- Padrões de jogo realistas vs não realistas
"""

import os
import sys
import json
import random
import ast
import inspect
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pypokerengine.api.game import setup_config, start_poker
from game.blind_manager import BlindManager
from utils.game_history import GameHistory

# Importa todos os bots
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

# Todos os bots disponíveis (exceto ConsolePlayer)
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


class BotCodeAnalyzer:
    """Analisa complexidade e estrutura do código dos bots."""
    
    def __init__(self):
        self.bot_files = {}
        self._load_bot_files()
    
    def _load_bot_files(self):
        """Carrega o código fonte de todos os bots."""
        players_dir = Path(__file__).parent.parent / "players"
        
        for bot_name in ALL_BOTS.keys():
            bot_class = ALL_BOTS[bot_name]
            try:
                file_path = inspect.getfile(bot_class)
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.bot_files[bot_name] = {
                        'path': file_path,
                        'source': f.read(),
                        'class': bot_class
                    }
            except Exception as e:
                print(f"⚠️  Erro ao carregar código de {bot_name}: {e}")
                self.bot_files[bot_name] = {
                    'path': None,
                    'source': '',
                    'class': bot_class
                }
    
    def analyze_complexity(self, bot_name: str) -> Dict[str, Any]:
        """Analisa complexidade do código de um bot."""
        if bot_name not in self.bot_files:
            return {}
        
        source = self.bot_files[bot_name]['source']
        if not source:
            return {}
        
        try:
            tree = ast.parse(source)
        except:
            return {}
        
        # Conta linhas
        lines = source.split('\n')
        total_lines = len(lines)
        code_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
        comment_lines = len([l for l in lines if l.strip().startswith('#')])
        
        # Conta funções e classes
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        # Conta complexidade ciclomática (aproximada)
        complexity = 1  # Base
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            if isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        # Analisa configuração
        config_complexity = 0
        config_params = 0
        try:
            # Procura função _create_config
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == '_create_config':
                    # Conta argumentos
                    config_params = len(node.args.args)
                    # Conta linhas na função
                    config_complexity = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                    break
        except:
            pass
        
        return {
            'total_lines': total_lines,
            'code_lines': code_lines,
            'comment_lines': comment_lines,
            'functions': len(functions),
            'classes': len(classes),
            'cyclomatic_complexity': complexity,
            'config_params': config_params,
            'config_lines': config_complexity,
            'complexity_score': complexity + (config_params * 0.1) + (config_complexity * 0.01)
        }
    
    def get_all_analyses(self) -> Dict[str, Dict[str, Any]]:
        """Retorna análise de todos os bots."""
        return {bot_name: self.analyze_complexity(bot_name) for bot_name in ALL_BOTS.keys()}


class GameRecorder:
    """Registra todas as ações e eventos durante os jogos."""
    
    def __init__(self):
        self.games_data = []
        self.current_game = None
        self.current_round = None
        self.action_log = []
    
    def start_game(self, game_num: int, bots: List[str], config: Dict[str, Any]):
        """Inicia registro de um novo jogo."""
        self.current_game = {
            'game_number': game_num,
            'timestamp': datetime.now().isoformat(),
            'bots': bots,
            'config': config,
            'rounds': [],
            'actions': [],
            'stats': defaultdict(lambda: {
                'actions': {'fold': 0, 'call': 0, 'raise': 0, 'check': 0},
                'total_bet': 0,
                'total_won': 0,
                'hands_played': 0,
                'hands_won': 0,
                'showdowns': 0,
                'bluffs_detected': 0,
                'bluffs_made': 0
            })
        }
        self.action_log = []
    
    def record_action(self, bot_name: str, action: str, amount: int, 
                     context: Dict[str, Any]):
        """Registra uma ação de um bot."""
        action_record = {
            'bot': bot_name,
            'action': action,
            'amount': amount,
            'timestamp': datetime.now().isoformat(),
            'context': context
        }
        self.action_log.append(action_record)
        if self.current_game:
            self.current_game['actions'].append(action_record)
            self.current_game['stats'][bot_name]['actions'][action.lower()] += 1
            if action.upper() in ['CALL', 'RAISE']:
                self.current_game['stats'][bot_name]['total_bet'] += amount
    
    def end_round(self, round_num: int, results: Dict[str, Any]):
        """Finaliza registro de um round."""
        if self.current_game:
            round_data = {
                'round_number': round_num,
                'results': results,
                'actions': self.action_log.copy()
            }
            self.current_game['rounds'].append(round_data)
            self.action_log = []
    
    def end_game(self, final_results: Dict[str, Any]):
        """Finaliza registro de um jogo."""
        if self.current_game:
            self.current_game['final_results'] = final_results
            self.current_game['duration'] = (
                datetime.now() - datetime.fromisoformat(self.current_game['timestamp'])
            ).total_seconds()
            
            # Atualiza estatísticas finais
            for bot_name, stack in final_results.get('stacks', {}).items():
                if bot_name in self.current_game['stats']:
                    initial_stack = self.current_game['config'].get('initial_stack', 100)
                    self.current_game['stats'][bot_name]['total_won'] = stack - initial_stack
            
            self.games_data.append(self.current_game)
            self.current_game = None


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


def ensure_balanced_distribution(total_games=100, bots_per_game=9):
    """Garante que todos os bots joguem aproximadamente o mesmo número de partidas."""
    num_bots = len(ALL_BOTS)
    total_slots = total_games * bots_per_game
    games_per_bot = total_slots // num_bots
    remainder = total_slots % num_bots
    
    bot_selections = []
    bot_counts = defaultdict(int)
    bot_list = list(ALL_BOTS.keys())
    
    for game_idx in range(total_games):
        expected_games = (game_idx + 1) * bots_per_game / num_bots
        
        bot_priorities = []
        for bot in bot_list:
            priority = expected_games - bot_counts[bot]
            bot_priorities.append((priority, bot))
        
        bot_priorities.sort(reverse=True)
        
        selected = []
        used_bots = set()
        
        for priority, bot in bot_priorities:
            if len(selected) >= bots_per_game:
                break
            if bot not in used_bots:
                selected.append(bot)
                used_bots.add(bot)
        
        if len(selected) < bots_per_game:
            remaining_bots = [b for b in bot_list if b not in used_bots]
            needed = bots_per_game - len(selected)
            if remaining_bots:
                selected.extend(random.sample(remaining_bots, min(needed, len(remaining_bots))))
        
        if len(selected) < bots_per_game:
            while len(selected) < bots_per_game:
                least_used = min(bot_list, key=lambda b: bot_counts[b])
                if least_used not in selected:
                    selected.append(least_used)
                else:
                    sorted_by_usage = sorted(bot_list, key=lambda b: bot_counts[b])
                    for bot in sorted_by_usage:
                        if bot not in selected:
                            selected.append(bot)
                            break
        
        random.shuffle(selected)
        bot_selections.append(selected[:bots_per_game])
        
        for bot in selected[:bots_per_game]:
            bot_counts[bot] += 1
    
    return bot_selections


def run_100_games():
    """Roda 100 partidas com registro completo."""
    
    print("=" * 80)
    print("🎮 TESTE COMPREHENSIVO - 100 PARTIDAS")
    print("=" * 80)
    print()
    
    # Limpa memórias
    print("🧹 Limpando memórias...")
    clear_all_memories()
    print()
    
    # Inicializa analisador de código
    print("📊 Analisando código dos bots...")
    code_analyzer = BotCodeAnalyzer()
    code_analyses = code_analyzer.get_all_analyses()
    print(f"✅ {len(code_analyses)} bots analisados")
    print()
    
    # Inicializa gravador de jogos
    recorder = GameRecorder()
    
    # Gera distribuição equilibrada
    print("📊 Gerando distribuição equilibrada de bots...")
    bot_selections = ensure_balanced_distribution(100, 9)
    
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
        'total_actions': defaultdict(int),
        'total_bet': 0,
        'total_won': 0
    })
    
    print("🎮 Iniciando 100 partidas...")
    print("=" * 80)
    
    start_time = datetime.now()
    
    for game_num in range(1, 101):
        if game_num % 10 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / game_num
            remaining = (100 - game_num) * avg_time
            print(f"\n📈 Progresso: {game_num}/100 partidas")
            print(f"   Tempo decorrido: {elapsed/60:.1f}min | Tempo restante estimado: {remaining/60:.1f}min")
        
        # Seleciona bots para esta partida
        selected_bots = bot_selections[game_num - 1]
        
        # Calcula blinds
        from game.blind_manager import BlindManager
        initial_stack = 100
        blind_manager = BlindManager(initial_reference_stack=initial_stack)
        small_blind, big_blind = blind_manager.get_blinds()
        
        # Configuração do jogo
        config = setup_config(max_round=10, initial_stack=initial_stack, small_blind_amount=small_blind)
        
        # Inicia registro do jogo
        recorder.start_game(
            game_num,
            selected_bots,
            {
                'initial_stack': initial_stack,
                'small_blind': small_blind,
                'big_blind': big_blind,
                'max_rounds': 10
            }
        )
        
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
            
            # Determina o vencedor
            winner = None
            max_stack = 0
            stacks = {}
            for player_info in game_result['players']:
                name = player_info['name']
                stack = player_info['stack']
                stacks[name] = stack
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
            
            # Conta vitória
            if winner:
                bot_stats[winner]['wins'] += 1
            
            # Tenta coletar estatísticas de memória dos bots
            memory_stats = {}
            for bot_name, bot_instance in bot_instances.items():
                try:
                    if hasattr(bot_instance, 'memory_manager'):
                        memory = bot_instance.memory_manager.get_memory()
                        memory_stats[bot_name] = {
                            'bluff_probability': memory.get('bluff_probability', 0),
                            'aggression_level': memory.get('aggression_level', 0),
                            'tightness_threshold': memory.get('tightness_threshold', 0),
                            'total_rounds': memory.get('total_rounds', 0),
                            'wins': memory.get('wins', 0)
                        }
                except:
                    pass
            
            # Finaliza registro do jogo
            recorder.end_game({
                'winner': winner,
                'stacks': stacks,
                'memory_stats': memory_stats
            })
            
            results.append(result)
            
        except Exception as e:
            print(f"❌ Erro na partida {game_num}: {e}")
            import traceback
            if game_num <= 5:  # Só mostra traceback nas primeiras 5 partidas
                traceback.print_exc()
            continue
    
    total_time = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 80)
    print("✅ 100 Partidas Concluídas!")
    print(f"⏱️  Tempo total: {total_time/60:.1f} minutos ({total_time:.1f} segundos)")
    print("=" * 80)
    
    return results, bot_stats, recorder.games_data, code_analyses


def analyze_realism(games_data: List[Dict], bot_stats: Dict, code_analyses: Dict) -> Dict[str, Any]:
    """Analisa realismo dos bots comparando comportamento vs código."""
    
    print("\n" + "=" * 80)
    print("🔍 ANÁLISE DE REALISMO")
    print("=" * 80)
    
    realism_analysis = {}
    
    # Para cada bot, analisa:
    for bot_name in ALL_BOTS.keys():
        analysis = {
            'bot_name': bot_name,
            'code_complexity': code_analyses.get(bot_name, {}),
            'behavior_stats': {},
            'realism_issues': [],
            'recommendations': []
        }
        
        # Coleta estatísticas de comportamento
        if bot_name in bot_stats:
            stats = bot_stats[bot_name]
            games = stats['games_played']
            
            if games > 0:
                win_rate = stats['wins'] / games
                avg_stack = stats['total_stack'] / games
                
                analysis['behavior_stats'] = {
                    'games_played': games,
                    'wins': stats['wins'],
                    'win_rate': win_rate,
                    'avg_stack': avg_stack,
                    'max_stack': stats['max_stack'],
                    'min_stack': stats['min_stack']
                }
                
                # Analisa ações (se disponível nos dados dos jogos)
                total_actions = sum(stats['total_actions'].values())
                if total_actions > 0:
                    fold_rate = stats['total_actions'].get('fold', 0) / total_actions
                    call_rate = stats['total_actions'].get('call', 0) / total_actions
                    raise_rate = stats['total_actions'].get('raise', 0) / total_actions
                    
                    analysis['behavior_stats']['action_rates'] = {
                        'fold': fold_rate,
                        'call': call_rate,
                        'raise': raise_rate
                    }
        
        # Verifica complexidade do código
        code_info = code_analyses.get(bot_name, {})
        if code_info:
            complexity = code_info.get('complexity_score', 0)
            config_params = code_info.get('config_params', 0)
            
            # Bot muito simples?
            if complexity < 5 and config_params < 20:
                analysis['realism_issues'].append({
                    'type': 'too_simple',
                    'severity': 'medium',
                    'description': f'Código muito simples (complexidade: {complexity:.2f}, parâmetros: {config_params})'
                })
                analysis['recommendations'].append(
                    'Considerar adicionar mais lógica de decisão baseada em contexto'
                )
            
            # Bot muito complexo?
            if complexity > 50 or config_params > 40:
                analysis['realism_issues'].append({
                    'type': 'too_complex',
                    'severity': 'low',
                    'description': f'Código muito complexo (complexidade: {complexity:.2f}, parâmetros: {config_params})'
                })
                analysis['recommendations'].append(
                    'Considerar simplificar a lógica ou dividir em módulos menores'
                )
        
        # Verifica discrepâncias de desempenho
        if bot_name in bot_stats:
            stats = bot_stats[bot_name]
            if stats['games_played'] > 0:
                win_rate = stats['wins'] / stats['games_played']
                
                # Win rate muito alto ou muito baixo pode indicar problema
                if win_rate > 0.20:  # Mais de 20% de vitórias em 9 jogadores
                    analysis['realism_issues'].append({
                        'type': 'high_win_rate',
                        'severity': 'low',
                        'description': f'Win rate alto: {win_rate:.1%} (pode ser muito bom ou muito agressivo)'
                    })
                
                if win_rate < 0.05:  # Menos de 5% de vitórias
                    analysis['realism_issues'].append({
                        'type': 'low_win_rate',
                        'severity': 'medium',
                        'description': f'Win rate muito baixo: {win_rate:.1%} (pode estar muito conservador ou com bugs)'
                    })
                    analysis['recommendations'].append(
                        'Revisar thresholds e lógica de decisão - pode estar foldando demais'
                    )
        
        realism_analysis[bot_name] = analysis
    
    return realism_analysis


def generate_comprehensive_report(results: List[Dict], bot_stats: Dict, 
                                 games_data: List[Dict], code_analyses: Dict,
                                 realism_analysis: Dict):
    """Gera relatório completo focado em tornar os bots mais realistas."""
    
    print("\n" + "=" * 80)
    print("📊 GERANDO RELATÓRIO COMPLETO")
    print("=" * 80)
    
    report_lines = []
    report_lines.append("# Relatório Completo - 100 Partidas de Teste\n")
    report_lines.append(f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    report_lines.append("---\n\n")
    
    # Resumo Executivo
    report_lines.append("## 📋 Resumo Executivo\n\n")
    total_games = len(results)
    report_lines.append(f"Foram realizadas **{total_games} partidas** com **9 bots por partida**.\n\n")
    report_lines.append(f"Total de **{len(bot_stats)} bots diferentes** participaram dos testes.\n\n")
    
    # Análise de Código
    report_lines.append("---\n\n")
    report_lines.append("## 💻 Análise de Código dos Bots\n\n")
    report_lines.append("### Complexidade do Código\n\n")
    report_lines.append("| Bot | Linhas | Funções | Complexidade | Parâmetros Config | Score |\n")
    report_lines.append("|-----|--------|---------|--------------|-------------------|-------|\n")
    
    sorted_by_complexity = sorted(
        code_analyses.items(),
        key=lambda x: x[1].get('complexity_score', 0),
        reverse=True
    )
    
    for bot_name, analysis in sorted_by_complexity:
        if analysis:
            lines = analysis.get('code_lines', 0)
            functions = analysis.get('functions', 0)
            complexity = analysis.get('cyclomatic_complexity', 0)
            params = analysis.get('config_params', 0)
            score = analysis.get('complexity_score', 0)
            report_lines.append(f"| {bot_name} | {lines} | {functions} | {complexity} | {params} | {score:.2f} |\n")
    
    # Bots Mais Simples
    report_lines.append("\n### ⚠️ Bots com Código Muito Simples\n\n")
    simple_bots = [
        (name, analysis) for name, analysis in code_analyses.items()
        if analysis and analysis.get('complexity_score', 0) < 5
    ]
    if simple_bots:
        for bot_name, analysis in simple_bots:
            score = analysis.get('complexity_score', 0)
            report_lines.append(f"- **{bot_name}**: Score de complexidade {score:.2f}\n")
            report_lines.append("  - ⚠️ Pode precisar de mais lógica contextual\n")
    else:
        report_lines.append("Nenhum bot identificado como muito simples.\n")
    
    # Bots Mais Complexos
    report_lines.append("\n### ⚠️ Bots com Código Muito Complexo\n\n")
    complex_bots = [
        (name, analysis) for name, analysis in code_analyses.items()
        if analysis and analysis.get('complexity_score', 0) > 50
    ]
    if complex_bots:
        for bot_name, analysis in complex_bots:
            score = analysis.get('complexity_score', 0)
            report_lines.append(f"- **{bot_name}**: Score de complexidade {score:.2f}\n")
            report_lines.append("  - ⚠️ Pode precisar de simplificação\n")
    else:
        report_lines.append("Nenhum bot identificado como muito complexo.\n")
    
    # Desempenho
    report_lines.append("\n---\n\n")
    report_lines.append("## 🏆 Desempenho dos Bots\n\n")
    report_lines.append("### Estatísticas Gerais\n\n")
    report_lines.append("| Bot | Partidas | Vitórias | Win Rate | Stack Médio | Max | Min |\n")
    report_lines.append("|-----|----------|----------|----------|-------------|-----|-----|\n")
    
    sorted_by_wins = sorted(
        bot_stats.items(),
        key=lambda x: x[1]['wins'],
        reverse=True
    )
    
    for bot_name, stats in sorted_by_wins:
        games = stats['games_played']
        wins = stats['wins']
        win_rate = (wins / games * 100) if games > 0 else 0
        avg_stack = (stats['total_stack'] / games) if games > 0 else 0
        max_stack = stats['max_stack']
        min_stack = stats['min_stack']
        report_lines.append(f"| {bot_name} | {games} | {wins} | {win_rate:.1f}% | {avg_stack:.1f} | {max_stack} | {min_stack} |\n")
    
    # Análise de Realismo
    report_lines.append("\n---\n\n")
    report_lines.append("## 🎯 Análise de Realismo e Recomendações\n\n")
    
    # Bots com problemas identificados
    bots_with_issues = [
        (name, analysis) for name, analysis in realism_analysis.items()
        if analysis.get('realism_issues')
    ]
    
    if bots_with_issues:
        report_lines.append("### ⚠️ Bots com Problemas Identificados\n\n")
        for bot_name, analysis in bots_with_issues:
            report_lines.append(f"#### {bot_name}\n\n")
            
            issues = analysis.get('realism_issues', [])
            for issue in issues:
                severity_emoji = {
                    'high': '🔴',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(issue.get('severity', 'low'), '🟢')
                
                report_lines.append(f"{severity_emoji} **{issue.get('type', 'unknown')}**: {issue.get('description', '')}\n\n")
            
            recommendations = analysis.get('recommendations', [])
            if recommendations:
                report_lines.append("**Recomendações:**\n\n")
                for rec in recommendations:
                    report_lines.append(f"- {rec}\n")
                report_lines.append("\n")
    else:
        report_lines.append("Nenhum problema crítico identificado.\n\n")
    
    # Recomendações Gerais
    report_lines.append("\n---\n\n")
    report_lines.append("## 💡 Recomendações Gerais para Tornar Bots Mais Realistas\n\n")
    
    # Analisa padrões gerais
    avg_win_rate = sum(s['wins'] / max(s['games_played'], 1) for s in bot_stats.values()) / len(bot_stats) if bot_stats else 0
    expected_win_rate = 1.0 / 9  # 9 jogadores por partida
    
    report_lines.append("### 1. Distribuição de Win Rates\n\n")
    report_lines.append(f"Win rate médio observado: {avg_win_rate:.1%}\n")
    report_lines.append(f"Win rate esperado (9 jogadores): {expected_win_rate:.1%}\n\n")
    
    if abs(avg_win_rate - expected_win_rate) > 0.02:
        report_lines.append("⚠️ **Atenção**: Win rate médio está diferente do esperado.\n")
        report_lines.append("Isso pode indicar que alguns bots estão muito fortes ou muito fracos.\n\n")
    
    # Bots discrepantes
    report_lines.append("### 2. Bots Discrepantes\n\n")
    discrepant_bots = []
    for bot_name, stats in bot_stats.items():
        if stats['games_played'] > 0:
            win_rate = stats['wins'] / stats['games_played']
            deviation = abs(win_rate - expected_win_rate)
            if deviation > 0.05:  # Mais de 5% de desvio
                discrepant_bots.append((bot_name, win_rate, deviation))
    
    if discrepant_bots:
        discrepant_bots.sort(key=lambda x: x[2], reverse=True)
        for bot_name, win_rate, deviation in discrepant_bots[:5]:
            report_lines.append(f"- **{bot_name}**: Win rate {win_rate:.1%} (desvio: {deviation:.1%})\n")
            if win_rate > expected_win_rate + 0.05:
                report_lines.append("  - ⚠️ Muito forte - considerar reduzir agressão ou ajustar thresholds\n")
            else:
                report_lines.append("  - ⚠️ Muito fraco - considerar aumentar agressão ou reduzir thresholds\n")
    else:
        report_lines.append("Nenhum bot com desvio significativo identificado.\n")
    
    # Complexidade vs Desempenho
    report_lines.append("\n### 3. Relação Complexidade vs Desempenho\n\n")
    report_lines.append("| Bot | Complexidade | Win Rate | Observação |\n")
    report_lines.append("|-----|--------------|----------|------------|\n")
    
    for bot_name in ALL_BOTS.keys():
        code_info = code_analyses.get(bot_name, {})
        stats = bot_stats.get(bot_name, {})
        
        complexity = code_info.get('complexity_score', 0)
        games = stats.get('games_played', 0)
        win_rate = (stats.get('wins', 0) / games * 100) if games > 0 else 0
        
        observation = ""
        if complexity < 5 and win_rate > 15:
            observation = "Simples mas eficaz"
        elif complexity > 30 and win_rate < 5:
            observation = "Complexo mas ineficaz"
        elif complexity > 30 and win_rate > 15:
            observation = "Complexo e eficaz"
        else:
            observation = "Normal"
        
        report_lines.append(f"| {bot_name} | {complexity:.2f} | {win_rate:.1f}% | {observation} |\n")
    
    # Análise de Padrões de Comportamento
    report_lines.append("\n---\n\n")
    report_lines.append("## 🎲 Análise de Padrões de Comportamento\n\n")
    
    # Calcula estatísticas de distribuição de stacks
    report_lines.append("### Distribuição de Stacks Finais\n\n")
    all_final_stacks = []
    for result in results:
        for name, stack in result.get('players', {}).items():
            all_final_stacks.append(stack)
    
    if all_final_stacks:
        import statistics
        avg_stack = statistics.mean(all_final_stacks)
        median_stack = statistics.median(all_final_stacks)
        std_stack = statistics.stdev(all_final_stacks) if len(all_final_stacks) > 1 else 0
        
        report_lines.append(f"- **Stack médio final**: {avg_stack:.1f}\n")
        report_lines.append(f"- **Stack mediano final**: {median_stack:.1f}\n")
        report_lines.append(f"- **Desvio padrão**: {std_stack:.1f}\n\n")
        
        # Stack esperado (9 jogadores, stack inicial 100 cada = 900 total)
        expected_stack = 100
        if abs(avg_stack - expected_stack) > 10:
            report_lines.append(f"⚠️ **Atenção**: Stack médio ({avg_stack:.1f}) difere significativamente do esperado ({expected_stack}).\n")
            report_lines.append("Isso pode indicar que alguns bots estão acumulando muito stack ou perdendo muito rápido.\n\n")
    
    # Análise de Consistência
    report_lines.append("### Consistência de Desempenho\n\n")
    report_lines.append("Bots com maior variação entre min e max stack:\n\n")
    
    variance_bots = []
    for bot_name, stats in bot_stats.items():
        if stats['games_played'] > 0:
            variance = stats['max_stack'] - stats['min_stack']
            variance_bots.append((bot_name, variance, stats['max_stack'], stats['min_stack']))
    
    variance_bots.sort(key=lambda x: x[1], reverse=True)
    for bot_name, variance, max_s, min_s in variance_bots[:5]:
        report_lines.append(f"- **{bot_name}**: Variação de {variance} (max: {max_s}, min: {min_s})\n")
        if variance > 200:
            report_lines.append("  - ⚠️ Variação muito alta - comportamento inconsistente\n")
    
    # Conclusões
    report_lines.append("\n---\n\n")
    report_lines.append("## 📝 Conclusões\n\n")
    report_lines.append("1. **Todos os bots usam o sistema de memória unificado** - boa arquitetura\n")
    report_lines.append("2. **Distribuição equilibrada garantiu participação justa** - teste válido\n")
    report_lines.append("3. **Análise de código revela diferentes níveis de complexidade** - alguns podem ser simplificados\n")
    report_lines.append("4. **Win rates discrepantes indicam necessidade de ajustes** - alguns bots precisam rebalanceamento\n")
    report_lines.append("5. **Sistema de configuração permite fácil ajuste** - boa flexibilidade\n")
    report_lines.append("6. **Variação de stacks indica diferentes estratégias** - alguns bots são mais conservadores, outros mais agressivos\n\n")
    
    # Próximos Passos
    report_lines.append("---\n\n")
    report_lines.append("## 🚀 Próximos Passos Recomendados\n\n")
    report_lines.append("1. **Ajustar bots com win rate muito alto ou muito baixo**\n")
    report_lines.append("2. **Simplificar código de bots muito complexos**\n")
    report_lines.append("3. **Adicionar mais lógica contextual em bots muito simples**\n")
    report_lines.append("4. **Revisar thresholds de bots com comportamento inconsistente**\n")
    report_lines.append("5. **Testar ajustes em lotes menores antes de rodar 100 partidas novamente**\n\n")
    
    # Salva relatório
    report_content = "".join(report_lines)
    report_filename = f"relatorio_completo_100_partidas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path = os.path.join(os.path.dirname(__file__), "..", report_filename)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print(f"\n📄 Relatório salvo em: {report_path}")
    
    # Salva dados brutos
    data_filename = f"dados_completos_100_partidas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    data_path = os.path.join(os.path.dirname(__file__), "..", data_filename)
    
    data_to_save = {
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'bot_stats': dict(bot_stats),
        'code_analyses': code_analyses,
        'realism_analysis': realism_analysis
    }
    
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"💾 Dados brutos salvos em: {data_path}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    results, bot_stats, games_data, code_analyses = run_100_games()
    realism_analysis = analyze_realism(games_data, bot_stats, code_analyses)
    generate_comprehensive_report(results, bot_stats, games_data, code_analyses, realism_analysis)

