from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import sys
import os
import threading
import json
import glob
import time
import random
import logging
import traceback
from datetime import datetime
import re

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pypokerengine.api.game import setup_config, start_poker
from pypokerengine.players import BasePokerPlayer
from players.tight_player import TightPlayer
from players.aggressive_player import AggressivePlayer
from players.random_player import RandomPlayer
from players.smart_player import SmartPlayer
from players.balanced_player import BalancedPlayer
from players.adaptive_player import AdaptivePlayer
from players.conservative_aggressive_player import ConservativeAggressivePlayer
from players.opportunistic_player import OpportunisticPlayer
from players.hybrid_player import HybridPlayer
from players.learning_player import LearningPlayer
from players.fish_player import FishPlayer
from players.cautious_player import CautiousPlayer
from players.moderate_player import ModeratePlayer
from players.patient_player import PatientPlayer
from players.calculated_player import CalculatedPlayer
from players.steady_player import SteadyPlayer
from players.observant_player import ObservantPlayer
from players.flexible_player import FlexiblePlayer
from players.calm_player import CalmPlayer
from players.thoughtful_player import ThoughtfulPlayer
from players.steady_aggressive_player import SteadyAggressivePlayer
from utils.hand_evaluator import HandEvaluator
from utils.game_history import GameHistory
from utils.hand_utils import get_community_cards, normalize_hole_cards
from utils.win_probability_calculator import calculate_win_probability_for_player

# Importa módulo de card_utils do PyPokerEngine para monkey patch
try:
    import pypokerengine.utils.card_utils as card_utils
except ImportError:
    card_utils = None

# Monkey patch para acelerar avaliação de mãos usando PokerKit
_original_calc_hand_info = None
_hand_evaluator = None

def _fast_calc_hand_info_flg(hole_card, community_card):
    """
    Versão otimizada de _calc_hand_info_flg usando PokerKit.
    Substitui a função lenta do PyPokerEngine.
    """
    global _hand_evaluator
    if _hand_evaluator is None:
        _hand_evaluator = HandEvaluator()
    
    try:
        # Converte listas de cartas para formato esperado
        hole_cards = hole_card if isinstance(hole_card, list) else []
        community_cards = community_card if isinstance(community_card, list) else []
        
        # Avalia usando PokerKit
        score = _hand_evaluator.evaluate(hole_cards, community_cards)
        
        # PyPokerEngine espera um dict com 'hand' e 'strength'
        # Retorna formato compatível
        # Nota: PokerKit retorna score onde menor = melhor, PyPokerEngine pode esperar diferente
        # Mas vamos manter compatibilidade retornando o score diretamente
        return score
    except Exception as e:
        # Em caso de erro, usa método original se disponível
        if _original_calc_hand_info:
            return _original_calc_hand_info(hole_card, community_card)
        print(f"[HandEvaluator] Erro em _fast_calc_hand_info_flg: {e}")
        # Retorna valor padrão (pior mão possível)
        return 7462

def apply_pokerkit_patch():
    """
    Aplica monkey patch para substituir _calc_hand_info_flg do PyPokerEngine por versão otimizada usando PokerKit.
    """
    global _original_calc_hand_info, _hand_evaluator
    
    if card_utils is None:
        print("[HandEvaluator] card_utils não disponível, pulando monkey patch")
        return
    
    if hasattr(card_utils, '_calc_hand_info_flg'):
        _original_calc_hand_info = card_utils._calc_hand_info_flg
        card_utils._calc_hand_info_flg = _fast_calc_hand_info_flg
        _hand_evaluator = HandEvaluator()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"✅ [HandEvaluator] [{timestamp}] Monkey patch aplicado - PokerKit ativado para avaliação rápida de mãos")
    else:
        print("[HandEvaluator] _calc_hand_info_flg não encontrado em card_utils, pulando monkey patch")

# Importa configurações centralizadas
try:
    from config import (
        SERVER_PORT, SERVER_HOST, DEBUG_MODE, ALLOWED_ORIGINS,
        DEFAULT_MAX_ROUNDS, DEFAULT_INITIAL_STACK, DEFAULT_SMALL_BLIND,
        POKER_DEBUG
    )
except ImportError:
    # Fallback se não conseguir importar (para compatibilidade)
    import os
    SERVER_PORT = int(os.environ.get('PORT', 5002))
    SERVER_HOST = os.environ.get('HOST', '0.0.0.0')
    DEBUG_MODE = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
    DEFAULT_MAX_ROUNDS = int(os.environ.get('MAX_ROUNDS', 10))
    DEFAULT_INITIAL_STACK = int(os.environ.get('INITIAL_STACK', 100))
    DEFAULT_SMALL_BLIND = int(os.environ.get('SMALL_BLIND', 5))
    POKER_DEBUG = os.environ.get('POKER_DEBUG', 'false').lower() == 'true'

app = Flask(__name__, 
            template_folder='templates',
            static_folder='.',
            static_url_path='')

# Configura CORS com origens permitidas
cors_origins = ALLOWED_ORIGINS if ALLOWED_ORIGINS != ['*'] else '*'
CORS(app, resources={r"/api/*": {"origins": cors_origins}})

# Configuração de logging
DEBUG_MODE = POKER_DEBUG

def _log_error(message, error=None, context=None):
    """Log centralizado de erros com contexto."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] ERROR: {message}"
    
    if context:
        log_msg += f" | Context: {context}"
    
    if error:
        log_msg += f" | Error: {str(error)}"
        if DEBUG_MODE:
            log_msg += f"\n{traceback.format_exc()}"
    
    print(log_msg)
    
    if DEBUG_MODE and error:
        traceback.print_exc()

def _log_debug(message, data=None):
    """Log de debug (apenas se DEBUG_MODE estiver ativo)."""
    if DEBUG_MODE:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] DEBUG: {message}"
        if data:
            log_msg += f" | Data: {data}"
        print(log_msg)

# Serve imagens
@app.route('/images/<path:filename>')
def images(filename):
    images_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images')
    return send_from_directory(images_path, filename)

# Serve arquivos estáticos (CSS, JS)
@app.route('/css/<path:filename>')
def css(filename):
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'css')
    return send_from_directory(css_path, filename)

@app.route('/js/<path:filename>')
def js(filename):
    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'js')
    return send_from_directory(js_path, filename)

# Estado do jogo
game_lock = threading.Lock()
game_state = {
    'active': False,
    'current_round': None,
    'player_name': 'Jogador',
    'player_uuid': None,
    'game_result': None,
    'thinking_uuid': None,  # UUID do bot que está pensando
    'round_data_cleared': False,  # Flag para indicar que dados de fim de round foram limpos manualmente
    'timeout_error': None,  # Erro de timeout do jogador
    'error': None,  # Erro geral do jogo
    'statistics_visible': True  # Visibilidade do painel de estatísticas
}

# Wrapper para Bots com delay e loading
class BotWrapper(BasePokerPlayer):
    def __init__(self, bot_algorithm, delay_min=1, delay_max=3):
        super().__init__()
        self.bot = bot_algorithm
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.uuid = None

    def declare_action(self, valid_actions, hole_card, round_state):
        # Simula tempo de pensamento
        delay = random.uniform(self.delay_min, self.delay_max)
        
        # Atualiza thinking_uuid de forma thread-safe
        with game_lock:
            # Salva UUID anterior para restaurar se necessário
            previous_thinking = game_state.get('thinking_uuid')
            game_state['thinking_uuid'] = self.uuid
            
        try:
            time.sleep(delay)
            return self.bot.declare_action(valid_actions, hole_card, round_state)
        finally:
            # Garante que thinking_uuid é limpo mesmo se houver exceção
            with game_lock:
                # Só limpa se ainda for nosso UUID (evita sobrescrever outro bot)
                if game_state.get('thinking_uuid') == self.uuid:
                    game_state['thinking_uuid'] = None

    def receive_game_start_message(self, game_info):
        self.bot.receive_game_start_message(game_info)
        # Encontra seu próprio UUID
        for seat in game_info['seats']:
            if seat['player']['name'] == self.bot.name if hasattr(self.bot, 'name') else None: # Nome pode não estar acessível fácil aqui, mas uuid sim se já tiver
                 pass
        # Melhor: pega uuid do setup
        
    def receive_round_start_message(self, round_count, hole_card, seats):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        bot_name = getattr(self.bot, 'name', type(self.bot).__name__)
        print(f"🟡 [SERVER] [{timestamp}] BotWrapper.receive_round_start_message - Bot: {bot_name}, Round: {round_count}")
        
        start_time = time.time()
        try:
            self.bot.receive_round_start_message(round_count, hole_card, seats)
            elapsed_time = time.time() - start_time
            print(f"🟡 [SERVER] [{timestamp}] BotWrapper.receive_round_start_message FINALIZADO - Bot: {bot_name}, Tempo: {elapsed_time:.3f}s")
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"🟡 [SERVER] [{timestamp}] ❌ ERRO em BotWrapper.receive_round_start_message - Bot: {bot_name}, Tempo: {elapsed_time:.3f}s, Erro: {e}")
            _log_error(f"Erro em receive_round_start_message do bot {bot_name}", e)

    def receive_street_start_message(self, street, round_state):
        self.bot.receive_street_start_message(street, round_state)

    def receive_game_update_message(self, action, round_state):
        self.bot.receive_game_update_message(action, round_state)

    def receive_round_result_message(self, winners, hand_info, round_state):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        bot_name = getattr(self.bot, 'name', type(self.bot).__name__)
        print(f"🟡 [SERVER] [{timestamp}] BotWrapper.receive_round_result_message - Bot: {bot_name}, UUID: {self.uuid}")
        
        start_time = time.time()
        try:
            self.bot.receive_round_result_message(winners, hand_info, round_state)
            elapsed_time = time.time() - start_time
            print(f"🟡 [SERVER] [{timestamp}] BotWrapper.receive_round_result_message FINALIZADO - Bot: {bot_name}, Tempo: {elapsed_time:.3f}s")
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"🟡 [SERVER] [{timestamp}] ❌ ERRO em BotWrapper.receive_round_result_message - Bot: {bot_name}, Tempo: {elapsed_time:.3f}s, Erro: {e}")
            _log_error(f"Erro em receive_round_result_message do bot {bot_name}", e)

    def set_uuid(self, uuid):
        self.uuid = uuid
        if hasattr(self.bot, 'set_uuid'): # Alguns bots podem não ter
             self.bot.uuid = uuid # Tenta setar direto se for BasePokerPlayer

# Player web que recebe ações via API
class WebPlayer(BasePokerPlayer):
    def __init__(self, initial_stack=100):
        super().__init__()
        self.pending_action = None
        self.action_received = threading.Event()
        self.uuid = None
        self.initial_stack = initial_stack
        # Sistema de histórico
        self.game_history = None  # Será inicializado quando UUID for definido
    
    def set_uuid(self, uuid):
        """Método chamado pelo PyPokerEngine para definir o UUID do jogador."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        old_uuid = self.uuid
        self.uuid = uuid
        print(f"🟢 [SERVER] [{timestamp}] WebPlayer.set_uuid chamado: {old_uuid} -> {uuid}")
        # Atualiza game_state imediatamente quando UUID é definido
        with game_lock:
            game_state['player_uuid'] = self.uuid
    
    def declare_action(self, valid_actions, hole_card, round_state):
        # CRÍTICO: Reseta o evento ANTES de esperar pela ação
        # Isso garante que não há estado residual de ações anteriores
        self.action_received.clear()
        self.pending_action = None
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"🟢 [SERVER] [{timestamp}] declare_action CHAMADO - Event resetado, aguardando ação do jogador")
        print(f"🟢 [SERVER] [{timestamp}] declare_action - web_player UUID: {self.uuid}")
        print(f"🟢 [SERVER] [{timestamp}] declare_action - web_player id: {id(self)}")
        print(f"🟢 [SERVER] [{timestamp}] declare_action - action_received.is_set() após clear: {self.action_received.is_set()}")
        
        # Notifica o frontend que é a vez do jogador
        serialized_state = self._serialize_round_state(round_state)
        # Quando declare_action é chamado, este jogador é o current_player
        serialized_state['current_player_uuid'] = self.uuid
        
        with game_lock:
            # Preserva round_count e outras informações existentes
            current_round = game_state.get('current_round') or {}
            if not isinstance(current_round, dict):
                current_round = {}
            old_is_player_turn = current_round.get('is_player_turn', False)
            current_round.update({
                'valid_actions': valid_actions,
                'hole_card': hole_card,
                'round_state': serialized_state,
                'is_player_turn': True  # É a vez do jogador quando declare_action é chamado
            })
            game_state['current_round'] = current_round
            if old_is_player_turn != True:
                print(f"🟢 [SERVER] [{timestamp}] declare_action - is_player_turn setado para True (era {old_is_player_turn})")
        
        # Espera pela ação do jogador com timeout
        # Timeout de 60 segundos para evitar travamento
        timeout_seconds = 60
        start_wait_time = time.time()
        print(f"🟢 [SERVER] [{timestamp}] declare_action - Iniciando espera por ação (timeout: {timeout_seconds}s)")
        
        action_received = self.action_received.wait(timeout=timeout_seconds)
        wait_duration = time.time() - start_wait_time
        
        if not action_received:
            # Timeout: define erro no game_state e retorna exceção
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            print(f"⚠️ [SERVER] [{timestamp}] TIMEOUT em declare_action - Jogador não respondeu em {wait_duration:.2f}s")
            _log_error("Timeout em declare_action - jogador não respondeu", None)
            
            # Obtém round_count atual
            with game_lock:
                current_round = game_state.get('current_round', {})
                round_count = current_round.get('round_count', 0)
                game_state['timeout_error'] = {
                    'message': f'Tempo de resposta esgotado. Você não respondeu em {wait_duration:.2f}s (tempo limite: 60s)',
                    'timestamp': timestamp,
                    'round_count': round_count
                }
                game_state['active'] = False  # Pausa o jogo
            
            # Lança exceção para indicar timeout
            raise TimeoutError(f"Jogador não respondeu em {wait_duration:.2f}s")
        
        # Ação recebida com sucesso
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"🟢 [SERVER] [{timestamp}] declare_action - Ação recebida após {wait_duration:.2f}s")
        
        self.action_received.clear()
        
        action, amount = self.pending_action
        self.pending_action = None
        print(f"🟢 [SERVER] [{timestamp}] declare_action - Retornando ação: {action}, amount: {amount}")
        
        # Registra ação no histórico
        if self.game_history and self.uuid:
            # Obtém cartas do jogador
            hole_cards = None
            if hole_card:
                hole_cards = normalize_hole_cards(hole_card)
            
            # Tenta calcular probabilidade de vitória
            win_prob = None
            try:
                win_prob_data = calculate_win_probability_for_player(
                    player_uuid=self.uuid,
                    round_state=round_state,
                    return_confidence=False
                )
                if win_prob_data is not None:
                    win_prob = win_prob_data
            except Exception:
                pass  # Ignora erros no cálculo de probabilidade
            
            self.game_history.record_action(
                player_uuid=self.uuid,
                action=action,
                amount=amount,
                round_state=round_state,
                my_hole_cards=hole_cards,
                my_win_probability=win_prob
            )
        
        return action, amount
    
    def _serialize_hand_info(self, hand_info):
        """Serializa hand_info para JSON, lidando com dicts e objetos."""
        if not hand_info:
            return []
        
        serialized = []
        for item in hand_info:
            if isinstance(item, dict):
                # Já é um dicionário, usa diretamente
                # Garante que hole_card seja uma lista se existir
                if 'hole_card' in item and item['hole_card']:
                    if isinstance(item['hole_card'], tuple):
                        item['hole_card'] = list(item['hole_card'])
                    elif not isinstance(item['hole_card'], list):
                        item['hole_card'] = [item['hole_card']]
                serialized.append(item)
            elif hasattr(item, '__dict__'):
                # É um objeto, converte para dict
                item_dict = item.__dict__.copy()
                # Garante que hole_card seja uma lista se existir
                if 'hole_card' in item_dict and item_dict['hole_card']:
                    if isinstance(item_dict['hole_card'], tuple):
                        item_dict['hole_card'] = list(item_dict['hole_card'])
                    elif not isinstance(item_dict['hole_card'], list):
                        item_dict['hole_card'] = [item_dict['hole_card']]
                serialized.append(item_dict)
            else:
                # Tipo desconhecido, tenta converter para string ou dict básico
                try:
                    serialized.append(str(item))
                except:
                    serialized.append({'error': 'Could not serialize hand_info item'})
        return serialized
    
    def _serialize_winners(self, winners):
        """Serializa winners para JSON, garantindo formato consistente."""
        if not winners:
            return []
        
        serialized = []
        for winner in winners:
            if isinstance(winner, dict):
                serialized.append(winner)
            elif hasattr(winner, '__dict__'):
                serialized.append(winner.__dict__)
            elif hasattr(winner, 'get'):
                # Objeto tipo dict mas não é dict nativo
                serialized.append(dict(winner))
            else:
                # Tenta extrair uuid e outras propriedades comuns
                winner_dict = {}
                if hasattr(winner, 'uuid'):
                    winner_dict['uuid'] = winner.uuid
                if hasattr(winner, 'name'):
                    winner_dict['name'] = winner.name
                serialized.append(winner_dict if winner_dict else {'uuid': str(winner)})
        return serialized
    
    def _serialize_round_state(self, round_state):
        """Serializa round_state para JSON."""
        try:
            seats = round_state.get('seats', []) if isinstance(round_state, dict) else []
        except:
            seats = []
        
        # Adiciona informações de paid (quanto cada jogador apostou) e stack
        serialized_seats = []
        for seat in seats:
            try:
                serialized_seat = {
                    'uuid': seat.get('uuid') if isinstance(seat, dict) else getattr(seat, 'uuid', None),
                    'name': seat.get('name', 'Unknown') if isinstance(seat, dict) else getattr(seat, 'name', 'Unknown'),
                    'stack': seat.get('stack', 0) if isinstance(seat, dict) else getattr(seat, 'stack', 0),
                    'state': seat.get('state', 'participating') if isinstance(seat, dict) else getattr(seat, 'state', 'participating'),
                    'paid': seat.get('paid', 0) if isinstance(seat, dict) else getattr(seat, 'paid', 0)
                }
                serialized_seats.append(serialized_seat)
            except Exception as e:
                _log_error("Erro ao serializar seat", e, {"seat": str(seat)[:100]})
                continue
        
        # Identifica o próximo jogador a jogar (current_player)
        # Isso é determinado pelo action_histories e pela ordem dos seats
        current_player_uuid = None
        try:
            action_histories = round_state.get('action_histories', {}) if isinstance(round_state, dict) else {}
            street = round_state.get('street', 'preflop') if isinstance(round_state, dict) else 'preflop'
            
            # Tenta encontrar o próximo jogador baseado nas ações
            # Primeiro, verifica se há ações nesta street
            if street in action_histories:
                street_actions = action_histories[street]
                if street_actions:
                    # Pega o último jogador que agiu
                    last_action = street_actions[-1]
                    last_player_uuid = last_action.get('uuid') if isinstance(last_action, dict) else getattr(last_action, 'uuid', None)
                    
                    # Encontra o próximo jogador na ordem circular
                    last_index = next((i for i, s in enumerate(seats) if (s.get('uuid') if isinstance(s, dict) else getattr(s, 'uuid', None)) == last_player_uuid), -1)
                    if last_index >= 0:
                        # Procura o próximo jogador participando
                        for i in range(1, len(seats)):
                            next_index = (last_index + i) % len(seats)
                            next_seat = seats[next_index]
                            seat_state = next_seat.get('state') if isinstance(next_seat, dict) else getattr(next_seat, 'state', 'participating')
                            seat_uuid = next_seat.get('uuid') if isinstance(next_seat, dict) else getattr(next_seat, 'uuid', None)
                            if seat_state == 'participating' and seat_uuid != last_player_uuid:
                                current_player_uuid = seat_uuid
                                break
            else:
                # Se não há ações nesta street, o primeiro jogador participando é o current
                for seat in seats:
                    seat_state = seat.get('state') if isinstance(seat, dict) else getattr(seat, 'state', 'participating')
                    if seat_state == 'participating':
                        current_player_uuid = seat.get('uuid') if isinstance(seat, dict) else getattr(seat, 'uuid', None)
                        break
        except Exception as e:
            _log_error("Erro ao determinar current_player_uuid", e)
            current_player_uuid = None
        
        try:
            pot = round_state.get('pot', {}) if isinstance(round_state, dict) else {}
            community_card = round_state.get('community_card', []) if isinstance(round_state, dict) else []
            action_histories = round_state.get('action_histories', {}) if isinstance(round_state, dict) else {}
            
            # Log do pote para debug (apenas se mudou significativamente)
            pot_amount = pot.get('main', {}).get('amount', 0) if isinstance(pot, dict) else 0
            _log_debug("Pot serializado", {'amount': pot_amount, 'pot_structure': pot})
        except:
            pot = {}
            community_card = []
            action_histories = {}
        
        return {
            'pot': pot,
            'seats': serialized_seats,
            'street': street if 'street' in locals() else 'preflop',
            'community_card': community_card,
            'action_histories': action_histories,
            'current_player_uuid': current_player_uuid
        }
    
    def receive_game_start_message(self, game_info):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # PyPokerEngine já define self.uuid automaticamente quando o jogador é registrado
        # Se não estiver definido, tenta encontrar pelo nome nos seats
        if not self.uuid:
            # Tenta encontrar pelo nome
            seats = game_info.get('seats', [])
            print(f"🟢 [SERVER] [{timestamp}] WebPlayer.receive_game_start_message - self.uuid não definido, procurando pelo nome")
            print(f"🟢 [SERVER] [{timestamp}] game_info structure: {type(game_info)}, seats type: {type(seats)}, seats count: {len(seats) if isinstance(seats, list) else 'N/A'}")
            
            # Tenta diferentes estruturas possíveis
            for seat in seats if isinstance(seats, list) else []:
                seat_name = None
                seat_uuid = None
                
                # Tenta diferentes formatos de seat
                if isinstance(seat, dict):
                    seat_name = seat.get('name') or (seat.get('player', {}).get('name') if isinstance(seat.get('player'), dict) else None)
                    seat_uuid = seat.get('uuid') or (seat.get('player', {}).get('uuid') if isinstance(seat.get('player'), dict) else None)
                elif hasattr(seat, 'name'):
                    seat_name = getattr(seat, 'name', None)
                    seat_uuid = getattr(seat, 'uuid', None)
                
                if seat_name == game_state['player_name'] and seat_uuid:
                    self.uuid = seat_uuid
                    print(f"🟢 [SERVER] [{timestamp}] UUID encontrado pelo nome: {self.uuid}")
                    break
        
        # Se ainda não encontrou, loga erro detalhado
        if not self.uuid:
            print(f"🔴 [SERVER] [{timestamp}] ERRO CRÍTICO: Não foi possível determinar UUID do jogador!")
            print(f"🔴 [SERVER] [{timestamp}] player_name: {game_state['player_name']}")
            print(f"🔴 [SERVER] [{timestamp}] game_info keys: {list(game_info.keys()) if isinstance(game_info, dict) else 'N/A'}")
            seats = game_info.get('seats', [])
            if isinstance(seats, list):
                print(f"🔴 [SERVER] [{timestamp}] seats structure (primeiro 2): {seats[:2] if len(seats) >= 2 else seats}")
        
        print(f"🟢 [SERVER] [{timestamp}] WebPlayer.receive_game_start_message - UUID final: {self.uuid}")
        with game_lock:
            old_uuid = game_state.get('player_uuid')
            game_state['player_uuid'] = self.uuid
            if old_uuid != self.uuid:
                print(f"🟢 [SERVER] [{timestamp}] player_uuid atualizado no game_state: {old_uuid} -> {self.uuid}")
    
    def receive_round_start_message(self, round_count, hole_card, seats):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"🟢 [SERVER] [{timestamp}] === WebPlayer.receive_round_start_message CHAMADO ===")
        print(f"🟢 [SERVER] [{timestamp}] Round count: {round_count}")
        print(f"🟢 [SERVER] [{timestamp}] Has hole_card: {hole_card is not None}")
        print(f"🟢 [SERVER] [{timestamp}] Seats count: {len(seats) if seats else 0}")
        print(f"🟢 [SERVER] [{timestamp}] ✅ NOVO ROUND INICIADO PELO PYPOKERENGINE!")
        
        _log_debug("=== receive_round_start_message CHAMADO ===", {
            'round_count': round_count,
            'has_hole_card': hole_card is not None,
            'seats_count': len(seats) if seats else 0
        })
        with game_lock:
            # Sempre preserva round_count quando um novo round começa
            # Preserva outras informações se existirem (como thinking_uuid)
            current_round = game_state.get('current_round') or {}
            if not isinstance(current_round, dict):
                current_round = {}
        
            # IMPORTANTE: Se round_ended estava True, significa que acabamos de terminar um round
            # Nesse caso, NÃO sobrescrevemos imediatamente - deixamos o frontend processar primeiro
            # Mas se já passou tempo suficiente, podemos limpar
            previous_round_ended = current_round.get('round_ended', False)
            previous_round_count = current_round.get('round_count')
            
            # Limpa dados de fim de round quando novo round começa
            cleaned_round = {
                'round_count': round_count,
                'hole_card': hole_card if self.uuid else None,  # Só mostra cartas do jogador
                'seats': seats,
                'round_ended': False,  # Novo round começou, então round_ended é False
                'is_player_turn': False  # Limpa no início do round
            }
            # Remove dados de fim de round se existirem
            if 'final_stacks' in current_round:
                print(f"🟢 [SERVER] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] Limpando final_stacks do round anterior")
            if 'winners' in current_round:
                print(f"🟢 [SERVER] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] Limpando winners do round anterior")
            if 'pot_amount' in current_round:
                print(f"🟢 [SERVER] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] Limpando pot_amount do round anterior")
            
            current_round.update(cleaned_round)
            game_state['current_round'] = current_round
            game_state['active'] = True  # Garante que o jogo está ativo
            game_state['round_data_cleared'] = False  # Reseta flag quando novo round começa normalmente
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            print(f"🟢 [SERVER] [{timestamp}] === Estado do jogo atualizado com novo round ===")
            print(f"🟢 [SERVER] [{timestamp}] Round anterior: {previous_round_count} -> Novo round: {round_count}")
            print(f"🟢 [SERVER] [{timestamp}] Round ended anterior: {previous_round_ended} -> Novo: False")
            print(f"🟢 [SERVER] [{timestamp}] Game active: {game_state.get('active')}")
        
        _log_debug("Round iniciado", {
            'round_count': round_count,
            'previous_round_ended': previous_round_ended,
            'new_round_ended': False
        })
        
        # Inicializa histórico se ainda não foi inicializado
        if not self.game_history and self.uuid:
            self.game_history = GameHistory(self.uuid, self.initial_stack)
            # Registra jogadores
            if seats:
                self.game_history.register_players(seats)
                num_players = len([s for s in seats if isinstance(s, dict)])
                self.game_history.set_game_config(
                    small_blind=0,  # Será atualizado quando disponível
                    big_blind=0,   # Será atualizado quando disponível
                    max_rounds=10,  # Default
                    num_players=num_players
                )
        
        # Inicia novo round no histórico
        if self.game_history and seats:
            button_position = 0  # Default
            self.game_history.start_round(round_count, seats, button_position)
    
    def receive_street_start_message(self, street, round_state):
        with game_lock:
            # Preserva round_count e outras informações existentes
            current_round = game_state.get('current_round') or {}
            if not isinstance(current_round, dict):
                current_round = {}
            serialized_state = self._serialize_round_state(round_state)
            
            # Verifica se é a vez do jogador humano
            # IMPORTANTE: Após uma nova street, o PyPokerEngine pode chamar declare_action
            # imediatamente, então não devemos resetar is_player_turn aqui
            # Deixamos que declare_action defina is_player_turn quando for realmente a vez
            current_player_uuid = serialized_state.get('current_player_uuid')
            is_player_turn = (current_player_uuid == self.uuid) if current_player_uuid and self.uuid else False
            
            # Preserva round_ended se já estiver True (não sobrescreve)
            round_ended = current_round.get('round_ended', False)
            
            # Preserva is_player_turn se já estiver True (não sobrescreve com False)
            # Isso garante que se declare_action já foi chamado, não perdemos essa informação
            existing_is_player_turn = current_round.get('is_player_turn', False)
            if existing_is_player_turn:
                is_player_turn = True
            
            current_round.update({
                'street': street,
                'round_state': serialized_state,
                'is_player_turn': is_player_turn,
                'round_ended': round_ended  # Preserva se já estiver True
            })
            game_state['current_round'] = current_round
        
        # Registra início de nova street no histórico
        if self.game_history:
            self.game_history.start_street(street, round_state)
    
    def receive_game_update_message(self, action, round_state):
        try:
            # Encontra nome do jogador pela ação
            # Garante que action é um dict
            if not isinstance(action, dict):
                if hasattr(action, '__dict__'):
                    action = action.__dict__
                elif hasattr(action, 'get'):
                    action = dict(action)
                else:
                    action = {'uuid': getattr(action, 'uuid', None), 
                             'action': getattr(action, 'action', 'unknown'),
                             'amount': getattr(action, 'amount', 0)}
            
            action_data = {
                'uuid': action.get('uuid') if isinstance(action, dict) else None,
                'action': action.get('action', 'unknown') if isinstance(action, dict) else 'unknown',
                'amount': action.get('amount', 0) if isinstance(action, dict) else 0
            }
            
            # Tenta encontrar o nome do jogador
            try:
                seats = round_state.get('seats', []) if isinstance(round_state, dict) else []
                for seat in seats:
                    seat_uuid = seat.get('uuid') if isinstance(seat, dict) else getattr(seat, 'uuid', None)
                    if seat_uuid == action_data['uuid']:
                        action_data['name'] = seat.get('name', 'Unknown') if isinstance(seat, dict) else getattr(seat, 'name', 'Unknown')
                        break
            except Exception as e:
                _log_error("Erro ao encontrar nome do jogador", e, {"action_uuid": action_data.get('uuid')})
                action_data['name'] = 'Unknown'
            
            serialized_state = self._serialize_round_state(round_state)
            # Após uma ação, o próximo jogador é determinado pela ordem dos seats
            # O current_player_uuid já foi calculado pelo _serialize_round_state
            
            # Verifica se o próximo jogador (após esta ação) é o jogador humano
            next_player_uuid = serialized_state.get('current_player_uuid')
            is_next_player_turn = (next_player_uuid == self.uuid) if next_player_uuid and self.uuid else False
            
            # Log para debug
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            action_was_from_player = (action_data.get('uuid') == self.uuid) if self.uuid else False
            print(f"🟢 [SERVER] [{timestamp}] receive_game_update_message - Action from: {action_data.get('name', 'Unknown')}, Next player UUID: {next_player_uuid}, Is player turn: {is_next_player_turn}")
            
            with game_lock:
                # Preserva round_count e outras informações existentes
                current_round = game_state.get('current_round') or {}
                if not isinstance(current_round, dict):
                    current_round = {}
                # Preserva round_ended se já estiver True (não sobrescreve)
                round_ended = current_round.get('round_ended', False)
                
                # IMPORTANTE: Se declare_action já foi chamado e setou is_player_turn=True,
                # não devemos sobrescrever com False. Isso garante que após a primeira ação,
                # quando o PyPokerEngine chama declare_action novamente, mantemos o estado correto.
                # Mas se o próximo jogador realmente é o humano, atualizamos para True.
                existing_is_player_turn = current_round.get('is_player_turn', False)
                if is_next_player_turn:
                    # Próximo jogador é o humano, seta True
                    final_is_player_turn = True
                elif existing_is_player_turn:
                    # Já estava True (declare_action foi chamado), mantém True
                    final_is_player_turn = True
                else:
                    # Não é a vez do jogador
                    final_is_player_turn = False
                
                current_round.update({
                    'action': action_data,
                    'round_state': serialized_state,
                    'is_player_turn': final_is_player_turn,
                    'round_ended': round_ended  # Preserva se já estiver True
                })
                game_state['current_round'] = current_round
            
            # Registra ação no histórico (de outros jogadores)
            if self.game_history and isinstance(action, dict):
                action_type = action.get('action', '')
                action_amount = action.get('amount', 0)
                paid = action.get('paid', 0)
                
                # Tenta obter UUID do jogador que fez a ação
                player_uuid = None
                player_name = action.get('player', '')
                seats = round_state.get('seats', [])
                for seat in seats:
                    if isinstance(seat, dict):
                        seat_name = seat.get('name', '')
                        if seat_name == player_name:
                            player_uuid = seat.get('uuid')
                            break
                
                if player_uuid:
                    # Usa 'paid' para CALL, 'amount' para outras ações
                    final_amount = paid if action_type == 'CALL' and paid > 0 else action_amount
                    self.game_history.record_action(
                        player_uuid=player_uuid,
                        action=action_type,
                        amount=final_amount,
                        round_state=round_state
                    )
                    
                    # Atualiza configurações de blinds se detectar SMALLBLIND ou BIGBLIND
                    if action_type == 'SMALLBLIND' and final_amount > 0:
                        self.game_history.history["game_config"]["small_blind"] = final_amount
                    elif action_type == 'BIGBLIND' and final_amount > 0:
                        self.game_history.history["game_config"]["big_blind"] = final_amount
        except Exception as e:
            _log_error("Erro em receive_game_update_message", e, {
                "action_type": type(action).__name__,
                "round_state_type": type(round_state).__name__ if round_state else None
            })
    
    def receive_round_result_message(self, winners, hand_info, round_state):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"🔴 [SERVER] [{timestamp}] === WebPlayer.receive_round_result_message CHAMADO ===")
        print(f"🔴 [SERVER] [{timestamp}] Winners count: {len(winners) if winners else 0}")
        print(f"🔴 [SERVER] [{timestamp}] Has hand_info: {hand_info is not None}")
        print(f"🔴 [SERVER] [{timestamp}] Has round_state: {round_state is not None}")
        
        _log_debug("=== receive_round_result_message CHAMADO ===", {
            'winners_count': len(winners) if winners else 0,
            'has_hand_info': hand_info is not None,
            'has_round_state': round_state is not None
        })
        
        start_time = time.time()
        try:
            serialized_state = self._serialize_round_state(round_state)
            
            # Serializa winners e hand_info de forma segura
            serialized_winners = self._serialize_winners(winners) if winners else []
            serialized_hand_info = self._serialize_hand_info(hand_info) if hand_info else []
            
            # Calcula informações finais do round
            final_stacks = {}
            
            # Cria um mapa de cartas por UUID a partir do hand_info
            cards_map = {}
            _log_debug("Processando hand_info para extrair cartas", {
                'hand_info_count': len(serialized_hand_info) if serialized_hand_info else 0
            })
            
            for hand in serialized_hand_info:
                if isinstance(hand, dict):
                    hand_uuid = hand.get('uuid') or hand.get('player_uuid')
                    if hand_uuid:
                        # Tenta obter cartas de diferentes formatos possíveis
                        cards = (hand.get('hole_card') or 
                                hand.get('cards') or 
                                hand.get('hole_cards') or
                                None)
                        
                        _log_debug(f"Processando hand para UUID {hand_uuid}", {
                            'has_hole_card': 'hole_card' in hand,
                            'has_cards': 'cards' in hand,
                            'has_hole_cards': 'hole_cards' in hand,
                            'cards_value': cards,
                            'cards_type': type(cards).__name__ if cards else None
                        })
                        
                        if cards:
                            # Garante que é uma lista
                            if isinstance(cards, list):
                                cards_map[hand_uuid] = cards
                                _log_debug(f"Cartas encontradas para {hand_uuid}", {
                                    'cards': cards,
                                    'count': len(cards)
                                })
                            elif isinstance(cards, str):
                                # Se for string, tenta converter
                                cards_map[hand_uuid] = [cards]
                            elif isinstance(cards, tuple):
                                # Se for tupla, converte para lista
                                cards_map[hand_uuid] = list(cards)
            
            # Calcula quanto cada vencedor ganhou
            winner_amounts = {}
            try:
                pot_amount = serialized_state.get('pot', {}).get('main', {}).get('amount', 0)
                if serialized_winners:
                    # Divide o pot entre os vencedores (pode haver empate)
                    amount_per_winner = pot_amount / len(serialized_winners) if pot_amount > 0 else 0
                    for winner in serialized_winners:
                        winner_uuid = winner.get('uuid') if isinstance(winner, dict) else None
                        if winner_uuid:
                            winner_amounts[winner_uuid] = amount_per_winner
            except:
                pass
            
            for seat in serialized_state.get('seats', []):
                try:
                    seat_uuid = seat.get('uuid') if isinstance(seat, dict) else None
                    seat_state = seat.get('state') if isinstance(seat, dict) else 'participating'
                    
                    if seat_uuid:
                        # Verifica se este jogador ganhou
                        won = False
                        won_amount = 0
                        for winner in serialized_winners:
                            winner_uuid = winner.get('uuid') if isinstance(winner, dict) else None
                            if winner_uuid == seat_uuid:
                                won = True
                                won_amount = winner_amounts.get(winner_uuid, 0)
                                break
                        
                        # Obtém cartas do mapa (só se não deu fold)
                        cards = None
                        if seat_state != 'folded':
                            cards = cards_map.get(seat_uuid)
                            
                            # Se não encontrou no mapa, tenta obter diretamente do round_state original
                            if not cards:
                                try:
                                    # Verifica no round_state original (antes da serialização)
                                    if isinstance(round_state, dict):
                                        rs_seats = round_state.get('seats', [])
                                        for rs_seat in rs_seats:
                                            rs_seat_uuid = rs_seat.get('uuid') if isinstance(rs_seat, dict) else getattr(rs_seat, 'uuid', None)
                                            if rs_seat_uuid == seat_uuid:
                                                # Tenta obter hole_card do seat
                                                rs_cards = None
                                                if isinstance(rs_seat, dict):
                                                    rs_cards = rs_seat.get('hole_card')
                                                elif hasattr(rs_seat, 'hole_card'):
                                                    rs_cards = rs_seat.hole_card
                                                
                                                if rs_cards:
                                                    if isinstance(rs_cards, list):
                                                        cards = rs_cards
                                                    elif isinstance(rs_cards, tuple):
                                                        cards = list(rs_cards)
                                                    elif isinstance(rs_cards, str):
                                                        cards = [rs_cards]
                                                    break
                                except Exception as e:
                                    _log_error(f"Erro ao tentar obter cartas do round_state para {seat_uuid}", e)
                            
                            # Se ainda não encontrou, tenta obter do hand_info original (não serializado)
                            if not cards and hand_info:
                                try:
                                    for hand in hand_info:
                                        hand_uuid = None
                                        hand_cards = None
                                        
                                        if isinstance(hand, dict):
                                            hand_uuid = hand.get('uuid') or hand.get('player_uuid')
                                            hand_cards = hand.get('hole_card') or hand.get('cards') or hand.get('hole_cards')
                                        elif hasattr(hand, 'uuid'):
                                            hand_uuid = hand.uuid
                                            hand_cards = getattr(hand, 'hole_card', None) or getattr(hand, 'cards', None)
                                        
                                        if hand_uuid == seat_uuid and hand_cards:
                                            if isinstance(hand_cards, list):
                                                cards = hand_cards
                                            elif isinstance(hand_cards, tuple):
                                                cards = list(hand_cards)
                                            elif isinstance(hand_cards, str):
                                                cards = [hand_cards]
                                            break
                                except Exception as e:
                                    _log_error(f"Erro ao tentar obter cartas do hand_info original para {seat_uuid}", e)
                        
                        _log_debug(f"Finalizando seat {seat_uuid}", {
                            'name': seat.get('name', 'Unknown') if isinstance(seat, dict) else 'Unknown',
                            'won': won,
                            'folded': seat_state == 'folded',
                            'has_cards': cards is not None,
                            'cards': cards if cards else None
                        })
                        
                        final_stacks[seat_uuid] = {
                            'name': seat.get('name', 'Unknown') if isinstance(seat, dict) else 'Unknown',
                            'stack': seat.get('stack', 0) if isinstance(seat, dict) else 0,
                            'won': won,
                            'won_amount': won_amount,
                            'cards': cards,  # Cartas (None se deu fold)
                            'folded': seat_state == 'folded'
                        }
                except Exception as e:
                    _log_error("Erro ao processar seat em final_stacks", e, {"seat_uuid": seat.get('uuid') if isinstance(seat, dict) else 'unknown'})
                    continue
            
            # Obtém pot_amount de forma segura
            pot_amount = 0
            try:
                pot = serialized_state.get('pot', {})
                if isinstance(pot, dict):
                    main_pot = pot.get('main', {})
                    if isinstance(main_pot, dict):
                        pot_amount = main_pot.get('amount', 0)
            except:
                pot_amount = 0
            
            with game_lock:
                # Verifica se os dados foram limpos manualmente (via force_next_round)
                # Se sim, não adiciona os dados de fim de round novamente
                if game_state.get('round_data_cleared', False):
                    timestamp_check = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    print(f"🔴 [SERVER] [{timestamp_check}] receive_round_result_message: Dados foram limpos manualmente, ignorando atualização")
                    print(f"🔴 [SERVER] [{timestamp_check}] Reseta flag round_data_cleared")
                    game_state['round_data_cleared'] = False  # Reseta a flag
                    # Não atualiza os dados de fim de round, mas continua para atualizar round_state se necessário
                    current_round = game_state.get('current_round') or {}
                    if not isinstance(current_round, dict):
                        current_round = {}
                    # Atualiza apenas round_state (pode ter informações do novo round)
                    if 'round_state' not in current_round or current_round.get('round_ended', False):
                        current_round['round_state'] = serialized_state
                        current_round['round_ended'] = False  # Novo round começou
                        game_state['current_round'] = current_round
                    return  # Não adiciona winners, final_stacks, etc.
                
                # Preserva round_count e outras informações existentes
                current_round = game_state.get('current_round') or {}
                if not isinstance(current_round, dict):
                    current_round = {}
                
                # Obtém round_count atual
                round_count = current_round.get('round_count', 0)
                
                current_round.update({
                    'winners': serialized_winners,
                    'hand_info': serialized_hand_info,
                    'round_state': serialized_state,
                    'round_ended': True,  # Round terminou
                    'final_stacks': final_stacks,
                    'pot_amount': pot_amount,
                    'is_player_turn': False  # Limpa turno quando round termina
                })
                game_state['current_round'] = current_round
                elapsed_time = time.time() - start_time
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                # Registra resultado do round no histórico
                if self.game_history:
                    self.game_history.record_round_result(winners, hand_info, round_state)
                    
                    # Verifica se é o último round (10 rounds é o padrão)
                    round_number = self.game_history.current_round.get("round_number", 0) if self.game_history.current_round else 0
                    if round_number >= 10:
                        # Salva histórico ao final do jogo
                        try:
                            history_file = self.game_history.save()
                            print(f"🔴 [SERVER] [{timestamp}] Histórico salvo em: {history_file}")
                        except Exception as e:
                            print(f"🔴 [SERVER] [{timestamp}] Erro ao salvar histórico: {e}")
                            _log_error("Erro ao salvar histórico", e)
                
                print(f"🔴 [SERVER] [{timestamp}] === WebPlayer.receive_round_result_message FINALIZADO ===")
                print(f"🔴 [SERVER] [{timestamp}] Tempo de execução: {elapsed_time:.3f}s")
                print(f"🔴 [SERVER] [{timestamp}] Round count: {round_count}")
                print(f"🔴 [SERVER] [{timestamp}] Round ended: True")
                print(f"🔴 [SERVER] [{timestamp}] Winners count: {len(serialized_winners)}")
                print(f"🔴 [SERVER] [{timestamp}] Pot amount: {pot_amount}")
                print(f"🔴 [SERVER] [{timestamp}] Game active: {game_state.get('active')}")
                
                # Verifica se o jogo deve terminar
                if round_count >= DEFAULT_MAX_ROUNDS:
                    print(f"🔴 [SERVER] [{timestamp}] ⚠️ ATENÇÃO: Round count ({round_count}) >= MAX_ROUNDS ({DEFAULT_MAX_ROUNDS})")
                    print(f"🔴 [SERVER] [{timestamp}] ⚠️ O jogo deve terminar após este round!")
                else:
                    print(f"🔴 [SERVER] [{timestamp}] Aguardando PyPokerEngine iniciar próximo round...")
                    print(f"🔴 [SERVER] [{timestamp}] Próximo round esperado: {round_count + 1}/{DEFAULT_MAX_ROUNDS}")
                
                _log_debug("Round terminado", {
                    'round_count': current_round.get('round_count'),
                    'round_ended': True,
                    'winners_count': len(serialized_winners),
                    'pot_amount': pot_amount
                })
        except Exception as e:
            elapsed_time = time.time() - start_time
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            print(f"🔴 [SERVER] [{timestamp}] ❌ ERRO em receive_round_result_message após {elapsed_time:.3f}s")
            _log_error("Erro crítico em receive_round_result_message", e, {
                "winners_type": type(winners).__name__,
                "hand_info_type": type(hand_info).__name__,
                "round_state_type": type(round_state).__name__
            })
            # Tenta manter o estado anterior ou criar um estado mínimo
            with game_lock:
                if 'current_round' not in game_state or not game_state['current_round']:
                    game_state['current_round'] = {
                        'round_ended': True,
                        'error': str(e)
                    }

web_player = WebPlayer(initial_stack=DEFAULT_INITIAL_STACK)

@app.route('/')
def index():
    # Redireciona direto para a página de configuração
    from flask import redirect
    return redirect('/config.html')

@app.route('/config.html')
def config():
    return render_template('config.html')

@app.route('/game.html')
def game():
    return render_template('game.html')

def sanitize_player_name(name):
    """Sanitiza o nome do jogador para prevenir XSS."""
    if not name or not isinstance(name, str):
        return 'Jogador'
    # Remove caracteres perigosos, mantém apenas alfanuméricos, espaços e alguns caracteres especiais
    sanitized = re.sub(r'[<>"\']', '', name)
    sanitized = sanitized.strip()
    # Limita tamanho
    sanitized = sanitized[:50]
    return sanitized if sanitized else 'Jogador'

@app.route('/api/start_game', methods=['POST'])
def start_game():
    global game_state, web_player
    
    try:
        # CRÍTICO: Verifica se já existe um jogo ativo antes de iniciar um novo
        with game_lock:
            if game_state.get('active', False):
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                print(f"⚠️ [SERVER] [{timestamp}] Tentativa de iniciar novo jogo enquanto um jogo já está ativo")
                return jsonify({
                    'status': 'error',
                    'message': 'Já existe um jogo ativo. Por favor, aguarde o jogo atual terminar ou reinicie o servidor.'
                }), 400
        
        data = request.json or {}
        player_name = data.get('player_name', 'Jogador')
        player_count = int(data.get('player_count', 5))
        
        # IMPORTANTE: Usa o valor do request, não o default
        # Se não for fornecido, usa DEFAULT_INITIAL_STACK como fallback
        initial_stack_raw = data.get('initial_stack')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"🔵 [SERVER] [{timestamp}] start_game - Dados recebidos: {data}")
        print(f"🔵 [SERVER] [{timestamp}] start_game - initial_stack_raw (tipo: {type(initial_stack_raw).__name__}): {initial_stack_raw}")
        
        if initial_stack_raw is not None:
            try:
                initial_stack = int(initial_stack_raw)
                print(f"🔵 [SERVER] [{timestamp}] start_game - initial_stack convertido: {initial_stack}")
            except (ValueError, TypeError) as e:
                print(f"⚠️ [SERVER] [{timestamp}] Erro ao converter initial_stack: {e}")
                return jsonify({
                    'status': 'error',
                    'message': f'initial_stack inválido: {initial_stack_raw}'
                }), 400
        else:
            initial_stack = DEFAULT_INITIAL_STACK
            print(f"🔵 [SERVER] [{timestamp}] start_game - initial_stack não fornecido, usando default: {initial_stack}")
        
        small_blind_raw = data.get('small_blind')
        print(f"🔵 [SERVER] [{timestamp}] start_game - small_blind_raw (tipo: {type(small_blind_raw).__name__}): {small_blind_raw}")
        
        if small_blind_raw is not None:
            try:
                small_blind = int(small_blind_raw)
                print(f"🔵 [SERVER] [{timestamp}] start_game - small_blind convertido: {small_blind}")
            except (ValueError, TypeError) as e:
                print(f"⚠️ [SERVER] [{timestamp}] Erro ao converter small_blind: {e}")
                return jsonify({
                    'status': 'error',
                    'message': f'small_blind inválido: {small_blind_raw}'
                }), 400
        else:
            # Calcula blinds automaticamente baseado na stack inicial
            from game.blind_manager import BlindManager
            blind_manager = BlindManager(initial_reference_stack=initial_stack)
            small_blind, big_blind = blind_manager.get_blinds()
            print(f"🔵 [SERVER] [{timestamp}] start_game - small_blind não fornecido, calculado automaticamente: SB={small_blind}, BB={big_blind}")
        
        statistics_visible = data.get('statistics_visible', True)
        
        # Validação de configuração
        if player_count < 2 or player_count > 9:
            return jsonify({
                'status': 'error',
                'message': 'player_count must be between 2 and 9'
            }), 400
        
        if initial_stack <= 0:
            return jsonify({
                'status': 'error',
                'message': 'initial_stack must be greater than 0'
            }), 400
        
        if small_blind <= 0 or small_blind >= initial_stack:
            return jsonify({
                'status': 'error',
                'message': 'small_blind must be greater than 0 and less than initial_stack'
            }), 400
        
        # Sanitiza e valida nome do jogador
        player_name = sanitize_player_name(player_name)
        
        # Log para debug - verifica se o valor está sendo usado corretamente
        print(f"🟢 [SERVER] [{timestamp}] start_game - Valores finais: initial_stack: {initial_stack}, small_blind: {small_blind}")
        
        # CRÍTICO: Limpa completamente o estado antes de iniciar novo jogo
        with game_lock:
            # Reseta completamente o estado do jogo
            game_state = {
                'active': False,  # Será setado para True após iniciar thread
                'current_round': None,
                'player_name': player_name,
                'player_uuid': None,  # Será setado quando WebPlayer receber UUID
                'game_result': None,
                'thinking_uuid': None,
                'round_data_cleared': False,
                'statistics_visible': statistics_visible
            }
        
        # Cria novo web_player
        web_player = WebPlayer(initial_stack=initial_stack)
        
        # Aplica monkey patch do PokerKit para acelerar avaliação de mãos
        apply_pokerkit_patch()
        
        # Configuração do jogo (usa valores fornecidos - garantido acima)
        config = setup_config(
            max_round=DEFAULT_MAX_ROUNDS,
            initial_stack=initial_stack,  # Valor do request, não default
            small_blind_amount=small_blind  # Valor do request, não default
        )
        config.register_player(name=player_name, algorithm=web_player)
        
        # Nomes brasileiros para bots
        bot_names = [
            "João", "Maria", "Pedro", "Ana", "Lucas", "Julia", "Mateus", "Larissa",
            "Gabriel", "Letícia", "Rafael", "Camila", "Gustavo", "Beatriz", "Felipe",
            "Amanda", "Bruno", "Fernanda", "Daniel", "Mariana", "Thiago", "Bruna",
            "Leonardo", "Jessica", "Rodrigo", "Luana", "Alex", "Patricia", "Eduardo", "Vanessa"
        ]
        random.shuffle(bot_names)
        
        # Seleciona bots aleatórios e suas estratégias
        available_bots = [
            TightPlayer(), AggressivePlayer(), SmartPlayer(), 
            RandomPlayer(), BalancedPlayer(), AdaptivePlayer(),
            ConservativeAggressivePlayer(), OpportunisticPlayer(), HybridPlayer(),
            LearningPlayer(), FishPlayer(), CautiousPlayer(),
            ModeratePlayer(), PatientPlayer(), CalculatedPlayer(),
            SteadyPlayer(), ObservantPlayer(), FlexiblePlayer(),
            CalmPlayer(), ThoughtfulPlayer(), SteadyAggressivePlayer()
        ]
        # Registra número de bots baseado em player_count
        selected_bots = random.sample(available_bots, min(player_count, len(available_bots)))
        
        for i, bot in enumerate(selected_bots):
            try:
                wrapper = BotWrapper(bot)
                config.register_player(name=bot_names[i], algorithm=wrapper)
            except Exception as e:
                _log_error(f"Erro ao registrar bot {i}", e)
                continue
        
        # CRÍTICO: Marca jogo como ativo ANTES de iniciar thread para evitar múltiplos jogos
        with game_lock:
            game_state['active'] = True
        
        # Inicia jogo em thread separada
        def run_game():
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            print(f"🟣 [SERVER] [{timestamp}] === THREAD DO JOGO INICIADA ===")
            print(f"🟣 [SERVER] [{timestamp}] Chamando start_poker()...")
            
            try:
                result = start_poker(config, verbose=0)
                timestamp_end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                print(f"🟣 [SERVER] [{timestamp_end}] === start_poker() RETORNOU ===")
                print(f"🟣 [SERVER] [{timestamp_end}] Result type: {type(result).__name__}")
                
                with game_lock:
                    game_state['game_result'] = result
                    game_state['active'] = False
                    print(f"🟣 [SERVER] [{timestamp_end}] Jogo finalizado. Active: False")
            except TimeoutError as e:
                # Timeout do jogador - já foi tratado em WebPlayer.declare_action
                timestamp_error = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                print(f"🟣 [SERVER] [{timestamp_error}] ⏱️ TIMEOUT do jogador - jogo pausado")
                print(f"🟣 [SERVER] [{timestamp_error}] Mensagem: {e}")
                # game_state['timeout_error'] já foi definido em WebPlayer.declare_action
                with game_lock:
                    if 'timeout_error' not in game_state:
                        game_state['timeout_error'] = {
                            'message': str(e),
                            'timestamp': timestamp_error,
                            'round_count': game_state.get('current_round', {}).get('round_count', 0)
                        }
                    game_state['active'] = False
                    print(f"🟣 [SERVER] [{timestamp_error}] Jogo pausado devido a timeout. Active: False")
            except Exception as e:
                timestamp_error = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                print(f"🟣 [SERVER] [{timestamp_error}] ❌ ERRO CRÍTICO na thread do jogo: {e}")
                print(f"🟣 [SERVER] [{timestamp_error}] Traceback:")
                traceback.print_exc()
                _log_error("Erro ao executar jogo", e)
                with game_lock:
                    game_state['error'] = str(e)
                    game_state['active'] = False
                    print(f"🟣 [SERVER] [{timestamp_error}] Game state atualizado com erro. Active: False")
        
        thread = threading.Thread(target=run_game)
        thread.daemon = True
        thread.start()
        
        _log_debug("Jogo iniciado", {"player_name": player_name, "bots_count": len(selected_bots)})
        return jsonify({'status': 'started'})
    except Exception as e:
        _log_error("Erro em start_game", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

def validate_player_action(action, amount):
    """Valida ação do jogador antes de processar."""
    valid_actions = ['fold', 'call', 'raise']
    
    if not action or not isinstance(action, str):
        return False, 'Ação inválida ou não fornecida'
    
    action_lower = action.lower()
    if action_lower not in valid_actions:
        return False, f'Ação deve ser uma de: {", ".join(valid_actions)}'
    
    if not isinstance(amount, (int, float)):
        return False, 'Valor da aposta deve ser um número'
    
    if amount < 0:
        return False, 'Valor da aposta não pode ser negativo'
    
    # Valida limites razoáveis (evita valores extremos)
    if amount > 10000:
        return False, 'Valor da aposta muito alto (máximo: 10000)'
    
    return True, None

@app.route('/api/player_action', methods=['POST'])
def player_action():
    try:
        data = request.json or {}
        action = data.get('action')
        amount = data.get('amount', 0)
        
        # Valida ação
        is_valid, error_message = validate_player_action(action, amount)
        if not is_valid:
            return jsonify({'status': 'error', 'message': error_message}), 400
        
        # Normaliza action para lowercase
        action = action.lower()
        
        # Validação adicional: se for call, verifica se amount não excede stack do jogador
        # Se exceder, converte para raise (all-in) com amount igual ao stack
        if action == 'call' and web_player and web_player.uuid:
            with game_lock:
                current_round = game_state.get('current_round', {})
                round_state = current_round.get('round_state', {})
                seats = round_state.get('seats', [])
                
                # Encontra o seat do jogador
                player_seat = None
                for seat in seats:
                    if isinstance(seat, dict) and seat.get('uuid') == web_player.uuid:
                        player_seat = seat
                        break
                
                if player_seat:
                    player_stack = player_seat.get('stack', 0)
                    # Se amount excede stack, converte para raise (all-in)
                    if amount > player_stack:
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                        print(f"🟡 [SERVER] [{timestamp}] Convertendo call para all-in: call amount ({amount}) > stack ({player_stack}), convertendo para raise com {player_stack}")
                        action = 'raise'
                        amount = player_stack
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        if not web_player:
            print(f"⚠️ [SERVER] [{timestamp}] player_action - web_player não existe")
            return jsonify({'status': 'error', 'message': 'WebPlayer não inicializado'}), 400
        
        # Log detalhado do estado atual
        action_received_state = web_player.action_received.is_set()
        has_pending_action = web_player.pending_action is not None
        web_player_uuid = getattr(web_player, 'uuid', None)
        
        print(f"🔵 [SERVER] [{timestamp}] player_action - Estado antes de processar:")
        print(f"🔵 [SERVER] [{timestamp}]   - action_received.is_set(): {action_received_state}")
        print(f"🔵 [SERVER] [{timestamp}]   - pending_action: {web_player.pending_action}")
        print(f"🔵 [SERVER] [{timestamp}]   - web_player.uuid: {web_player_uuid}")
        print(f"🔵 [SERVER] [{timestamp}]   - Ação recebida: {action}, amount: {amount}")
        
        # Verifica se já há uma ação pendente (pode acontecer se o jogador clicar múltiplas vezes)
        if web_player.action_received.is_set():
            print(f"⚠️ [SERVER] [{timestamp}] player_action - Já existe ação pendente, ignorando nova ação")
            print(f"⚠️ [SERVER] [{timestamp}]   - Ação pendente atual: {web_player.pending_action}")
            return jsonify({'status': 'error', 'message': 'Já existe uma ação pendente. Aguarde sua vez novamente.'}), 400
        
        # Define a ação pendente e sinaliza que foi recebida
        web_player.pending_action = (action, amount)
        web_player.action_received.set()
        
        print(f"🟢 [SERVER] [{timestamp}] player_action - Ação recebida e processada: {action}, amount: {amount}")
        print(f"🟢 [SERVER] [{timestamp}] player_action - Event setado, aguardando declare_action processar")
        _log_debug("Ação do jogador recebida", {"action": action, "amount": amount})
        return jsonify({'status': 'ok'})
    except Exception as e:
        _log_error("Erro em player_action", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/game_state', methods=['GET'])
def get_game_state():
    try:
        with game_lock:
            # Cria uma cópia do estado para evitar problemas de serialização
            state_copy = {}
            for key, value in game_state.items():
                try:
                    # Tenta serializar para garantir que é JSON válido
                    json.dumps(value)
                    state_copy[key] = value
                except (TypeError, ValueError) as e:
                    _log_error(f"Erro ao serializar {key} em game_state", e)
                    state_copy[key] = None
            
            # Log detalhado para debug
            current_round = state_copy.get('current_round', {})
            round_count = current_round.get('round_count') if current_round else None
            round_ended = current_round.get('round_ended') if current_round else None
            
            # Log apenas quando há mudanças significativas ou quando round_ended está True
            if round_ended or (round_count and round_count > 0):
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                print(f"🔵 [SERVER] [{timestamp}] get_game_state chamado - Active: {state_copy.get('active')}, Round: {round_count}, Round ended: {round_ended}")
            
            _log_debug("game_state enviado", {
                'active': state_copy.get('active'),
                'has_current_round': state_copy.get('current_round') is not None,
                'thinking_uuid': state_copy.get('thinking_uuid'),
                'player_uuid': state_copy.get('player_uuid'),
                'round_ended': round_ended,
                'is_player_turn': current_round.get('is_player_turn') if current_round else None
            })
            
            return jsonify(state_copy)
    except Exception as e:
        _log_error("Erro em get_game_state", e)
        return jsonify({'error': str(e), 'active': False}), 500

def initialize_game_state():
    """
    Inicializa/reseta completamente o estado do jogo.
    Chamada quando o servidor inicia para garantir que não há partidas em andamento.
    """
    global game_state, web_player
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"🔄 [SERVER] [{timestamp}] === INICIALIZANDO ESTADO DO JOGO ===")
    
    with game_lock:
        game_state = {
            'active': False,
            'current_round': None,
            'player_name': 'Jogador',
            'player_uuid': None,
            'game_result': None,
            'thinking_uuid': None,
            'round_data_cleared': False,
            'timeout_error': None,
            'error': None,
            'statistics_visible': True
        }
    
    # Cria novo web_player limpo
    web_player = WebPlayer(initial_stack=DEFAULT_INITIAL_STACK)
    
    print(f"🔄 [SERVER] [{timestamp}] ✅ Estado do jogo resetado - pronto para nova partida")
    print(f"🔄 [SERVER] [{timestamp}]   active: {game_state['active']}")
    print(f"🔄 [SERVER] [{timestamp}]   current_round: {game_state['current_round']}")
    print(f"🔄 [SERVER] [{timestamp}]   player_uuid: {game_state['player_uuid']}")

@app.route('/api/reset_game', methods=['POST'])
def reset_game():
    """Endpoint para resetar o jogo manualmente via API."""
    initialize_game_state()
    return jsonify({'status': 'reset'})

@app.route('/api/reset_memory', methods=['POST'])
def reset_memory():
    try:
        # Caminho para o diretório centralizado de memória
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        memory_dir = os.path.join(project_root, 'data', 'memory')
        
        # Encontra todos os arquivos JSON de memória
        memory_files = glob.glob(os.path.join(memory_dir, '*_memory.json'))
        
        deleted_count = 0
        for f in memory_files:
            try:
                os.remove(f)
                deleted_count += 1
            except Exception as e:
                print(f"Erro ao deletar {f}: {e}")
                
        return jsonify({'status': 'success', 'message': f'{deleted_count} memórias resetadas'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/force_next_round', methods=['POST'])
def force_next_round():
    """Força limpeza de dados de fim de round para permitir que o jogo continue.
    
    Este endpoint é chamado quando o PyPokerEngine não inicia automaticamente o próximo round.
    Limpa final_stacks, winners e pot_amount do estado atual, permitindo que o frontend
    detecte que um novo round pode começar.
    """
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"🟠 [SERVER] [{timestamp}] === force_next_round CHAMADO ===")
        
        with game_lock:
            current_round = game_state.get('current_round')
            if not current_round or not isinstance(current_round, dict):
                print(f"🟠 [SERVER] [{timestamp}] ⚠️ current_round não encontrado ou inválido")
                return jsonify({'status': 'error', 'message': 'No current round found'}), 400
            
            round_count = current_round.get('round_count')
            had_final_stacks = 'final_stacks' in current_round
            had_winners = 'winners' in current_round
            had_pot_amount = 'pot_amount' in current_round
            
            print(f"🟠 [SERVER] [{timestamp}] Estado antes da limpeza:")
            print(f"🟠 [SERVER] [{timestamp}]   Round count: {round_count}")
            print(f"🟠 [SERVER] [{timestamp}]   Round ended: {current_round.get('round_ended')}")
            print(f"🟠 [SERVER] [{timestamp}]   Had final_stacks: {had_final_stacks}")
            print(f"🟠 [SERVER] [{timestamp}]   Had winners: {had_winners}")
            print(f"🟠 [SERVER] [{timestamp}]   Had pot_amount: {had_pot_amount}")
            
            # Remove dados de fim de round
            if 'final_stacks' in current_round:
                del current_round['final_stacks']
                print(f"🟠 [SERVER] [{timestamp}] ✅ final_stacks removido")
            
            if 'winners' in current_round:
                del current_round['winners']
                print(f"🟠 [SERVER] [{timestamp}] ✅ winners removido")
            
            if 'hand_info' in current_round:
                del current_round['hand_info']
                print(f"🟠 [SERVER] [{timestamp}] ✅ hand_info removido")
            
            if 'pot_amount' in current_round:
                del current_round['pot_amount']
                print(f"🟠 [SERVER] [{timestamp}] ✅ pot_amount removido")
            
            # Garante que round_ended é False
            current_round['round_ended'] = False
            
            # Mantém round_count e outras informações importantes
            # O round_state deve ser mantido pois pode ter informações do novo round
            
            game_state['current_round'] = current_round
            game_state['active'] = True  # Garante que o jogo está ativo
            game_state['round_data_cleared'] = True  # Marca que dados foram limpos manualmente
            
            print(f"🟠 [SERVER] [{timestamp}] === force_next_round FINALIZADO ===")
            print(f"🟠 [SERVER] [{timestamp}] Estado após limpeza:")
            print(f"🟠 [SERVER] [{timestamp}]   Round count: {current_round.get('round_count')}")
            print(f"🟠 [SERVER] [{timestamp}]   Round ended: {current_round.get('round_ended')}")
            print(f"🟠 [SERVER] [{timestamp}]   Game active: {game_state.get('active')}")
            print(f"🟠 [SERVER] [{timestamp}]   Round data cleared flag: True")
            
            return jsonify({
                'status': 'ok',
                'message': 'Round data cleaned',
                'round_count': round_count,
                'round_ended': False
            })
    except Exception as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"🟠 [SERVER] [{timestamp}] ❌ ERRO em force_next_round: {e}")
        traceback.print_exc()
        _log_error("Erro em force_next_round", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Reseta o estado do jogo ao iniciar o servidor
    # Garante que sempre começa na página inicial, sem partidas em andamento
    initialize_game_state()
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"🚀 [SERVER] [{timestamp}] === SERVIDOR INICIANDO ===")
    print(f"🚀 [SERVER] [{timestamp}] Host: {SERVER_HOST}, Port: {SERVER_PORT}")
    print(f"🚀 [SERVER] [{timestamp}] Debug Mode: {DEBUG_MODE}")
    print(f"🚀 [SERVER] [{timestamp}] === PRONTO PARA RECEBER CONEXÕES ===")
    
    app.run(debug=DEBUG_MODE, host=SERVER_HOST, port=SERVER_PORT)

