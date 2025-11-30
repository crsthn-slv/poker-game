"""
Servidor FastAPI para o jogo de Poker.
Gerencia sessões de jogo, WebSockets e integração com o motor de jogo.
"""

import os
import sys
import uuid
import asyncio
import threading
import json
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

# Adiciona diretório raiz ao path para importar módulos do jogo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pypokerengine.api.game import setup_config, start_poker

# Importa classes do jogo existente
from players.tight_player import TightPlayer
from players.aggressive_player import AggressivePlayer
from players.random_player import RandomPlayer
from players.smart_player import SmartPlayer
from players.learning_player import LearningPlayer
from players.balanced_player import BalancedPlayer
from players.adaptive_player import AdaptivePlayer
from game.blind_manager import BlindManager

# Importa componentes web
from web.web_player import WebPlayer
from web.supabase_client import get_supabase_client

# Configuração de Bots Disponíveis (reutilizado do play_console.py)
AVAILABLE_BOTS = {
    'Blaze': TightPlayer,
    'Riley': AggressivePlayer,
    'Sloan': RandomPlayer,
    'Dexter': SmartPlayer,
    'Ivory': LearningPlayer,
    'Maverick': BalancedPlayer,
    'Nova': AdaptivePlayer
}

class GameConfig(BaseModel):
    nickname: str
    initial_stack: int = 1000
    num_bots: int = 5
    show_probability: bool = False

class GameSession:
    """Gerencia uma sessão de jogo ativa."""
    def __init__(self, session_id: str, config: GameConfig):
        self.session_id = session_id
        self.config = config
        self.websocket: Optional[WebSocket] = None
        self.web_player: Optional[WebPlayer] = None
        self.game_thread: Optional[threading.Thread] = None
        self.is_active = True
        self.game_result = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.websocket = websocket
        print(f"[SERVER] WebSocket connected for session {self.session_id}")

    def disconnect(self):
        self.websocket = None
        print(f"[SERVER] WebSocket disconnected for session {self.session_id}")

    def send_update(self, event_type: str, data: Any):
        """Envia atualização para o WebSocket (thread-safe)."""
        if self.websocket:
            # Como isso é chamado da thread do jogo, precisamos agendar no event loop
            asyncio.run_coroutine_threadsafe(
                self.websocket.send_json({
                    "type": event_type,
                    "data": data
                }),
                loop
            )

# Armazenamento de sessões em memória
sessions: Dict[str, GameSession] = {}
loop = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global loop
    loop = asyncio.get_running_loop()
    yield
    # Cleanup

app = FastAPI(lifespan=lifespan)

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve arquivos estáticos (frontend)
app.mount("/static", StaticFiles(directory="web/static"), name="static")

@app.post("/api/game/new")
async def create_game(config: GameConfig):
    """Cria uma nova sessão de jogo."""
    session_id = str(uuid.uuid4())
    session = GameSession(session_id, config)
    sessions[session_id] = session
    
    print(f"[SERVER] Created new session {session_id} for {config.nickname}")
    return {"session_id": session_id}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Endpoint WebSocket para comunicação em tempo real."""
    if session_id not in sessions:
        await websocket.close(code=4004, reason="Session not found")
        return

    session = sessions[session_id]
    await session.connect(websocket)

    try:
        # Inicia o jogo em uma thread separada
        start_game_thread(session)

        # Loop de recebimento de mensagens
        while True:
            data = await websocket.receive_json()
            
            # Processa ações do jogador
            if data.get("type") == "action":
                action_data = data.get("data", {})
                action = action_data.get("action")
                amount = action_data.get("amount", 0)
                
                if session.web_player:
                    print(f"[SERVER] Received action for {session_id}: {action} {amount}")
                    session.web_player.input_queue.put((action, amount))
            
    except WebSocketDisconnect:
        session.disconnect()
    except Exception as e:
        print(f"[SERVER] Error in websocket: {e}")
        session.disconnect()

def run_poker_game(session: GameSession):
    """Executa o loop do jogo PyPokerEngine."""
    try:
        print(f"[GAME] Starting game loop for {session.session_id}")
        
        # 1. Configura Blinds
        blind_manager = BlindManager(initial_reference_stack=session.config.initial_stack)
        small_blind, big_blind = blind_manager.get_blinds()
        
        # 2. Setup Config
        config = setup_config(
            max_round=10, 
            initial_stack=session.config.initial_stack, 
            small_blind_amount=small_blind
        )
        
        # 3. Cria e registra WebPlayer (Humano)
        web_player = WebPlayer(
            initial_stack=session.config.initial_stack,
            small_blind=small_blind,
            big_blind=big_blind,
            show_win_probability=session.config.show_probability,
            on_game_update=session.send_update
        )
        web_player.set_game_id(session.session_id)
        web_player.set_player_name(session.config.nickname)
        session.web_player = web_player
        
        # Define UUID fixo para o jogador humano (importante para logs)
        # O ConsolePlayer usa o nome para gerar UUID, vamos garantir consistência
        # Mas o WebPlayer herda do ConsolePlayer que faz isso no __init__ se tiver nome?
        # Não, o ConsolePlayer não recebe nome no init.
        # Vamos registrar com o nickname
        config.register_player(name=session.config.nickname, algorithm=web_player)
        
        # 4. Registra Bots
        import random
        available_bots_list = list(AVAILABLE_BOTS.items())
        # Garante que não pede mais bots do que existem
        num_bots = min(session.config.num_bots, len(available_bots_list))
        selected_bots = random.sample(available_bots_list, num_bots)
        
        for bot_name, bot_class in selected_bots:
            bot_instance = bot_class()
            bot_instance.config.name = bot_name # Importante para fixar UUID
            config.register_player(name=bot_name, algorithm=bot_instance)
            
        # 5. Inicia o Jogo (Bloqueante)
        session.send_update("status", "Starting game...")
        game_result = start_poker(config, verbose=0)
        
        # 6. Jogo terminou
        session.game_result = game_result
        session.send_update("game_over", {"result": "Game finished"})
        
        # 7. Salva histórico no Supabase
        print(f"[GAME] Saving history for {session.session_id}")
        supabase = get_supabase_client()
        if web_player.game_history:
            # O ConsolePlayer/WebPlayer mantém o histórico em self.game_history (instância de GameHistory)
            # Precisamos acessar o dict interno
            history_data = web_player.game_history.history
            success = supabase.save_game_history(history_data, session.config.nickname)
            if success:
                session.send_update("notification", "Game history saved to Supabase!")
            else:
                session.send_update("error", "Failed to save game history.")
                
    except Exception as e:
        print(f"[GAME] Error in game loop: {e}")
        import traceback
        traceback.print_exc()
        session.send_update("error", f"Game error: {str(e)}")

def start_game_thread(session: GameSession):
    """Inicia a thread do jogo."""
    thread = threading.Thread(target=run_poker_game, args=(session,))
    thread.daemon = True
    thread.start()
    session.game_thread = thread

if __name__ == "__main__":
    import uvicorn
    # Cria diretório static se não existir
    os.makedirs("web/static", exist_ok=True)
    
    print("Starting Web Poker Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
