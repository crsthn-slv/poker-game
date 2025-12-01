"""
Cliente Supabase para persistência de histórico de jogos.

Salva dados de jogo em formato otimizado no PostgreSQL do Supabase.
"""

import os
import psycopg2
from psycopg2.extras import execute_values, Json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()


class SupabaseClient:
    """Cliente para interação com Supabase PostgreSQL."""
    
    def __init__(self):
        """Inicializa conexão com Supabase."""
        self.config = {
            'host': os.getenv('SUPABASE_HOST'),
            'port': os.getenv('SUPABASE_PORT', '5432'),
            'database': os.getenv('SUPABASE_DATABASE', 'postgres'),
            'user': os.getenv('SUPABASE_USER', 'postgres'),
            'password': os.getenv('SUPABASE_PASSWORD')
        }
        
        # Valida configuração
        if not all([self.config['host'], self.config['password']]):
            raise ValueError(
                "Supabase credentials not configured. "
                "Please set SUPABASE_HOST and SUPABASE_PASSWORD environment variables."
            )
        
        self.conn = None
    
    def connect(self):
        """Estabelece conexão com banco de dados."""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.config)
        return self.conn
    
    def close(self):
        """Fecha conexão com banco de dados."""
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def ensure_player(self, nickname: str) -> str:
        """
        Garante que jogador existe no banco, retorna player_id.
        
        Args:
            nickname: Nickname do jogador
            
        Returns:
            UUID do jogador (string)
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Tenta inserir, ou atualiza last_seen se já existe
            cursor.execute("""
                INSERT INTO players (nickname, created_at, last_seen)
                VALUES (%s, NOW(), NOW())
                ON CONFLICT (nickname) 
                DO UPDATE SET last_seen = NOW()
                RETURNING id
            """, (nickname,))
            
            player_id = cursor.fetchone()[0]
            conn.commit()
            return str(player_id)
        finally:
            cursor.close()
    
    def save_game_history(self, history: Dict[str, Any], nickname: str) -> tuple[bool, str]:
        """
        Salva histórico de jogo em formato otimizado.
        
        Args:
            history: Histórico do jogo (formato do GameHistory)
            nickname: Nickname do jogador
            
        Returns:
            Tuple (success, error_message)
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Garante que jogador existe
            player_id = self.ensure_player(nickname)
            
            # Extrai configurações do jogo
            game_config = history.get('game_config', {})
            game_id = history.get('game_id')
            timestamp = history.get('timestamp')
            
            # Insere registro do jogo
            cursor.execute("""
                INSERT INTO games (
                    id, player_id, timestamp, initial_stack, 
                    small_blind, big_blind, num_players, total_rounds
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                game_id,
                player_id,
                timestamp,
                game_config.get('initial_stack', 0),
                game_config.get('small_blind', 0),
                game_config.get('big_blind', 0),
                game_config.get('num_players', 0),
                game_config.get('max_rounds', 0)
            ))
            
            # Insere rounds
            rounds = history.get('rounds', [])
            for round_data in rounds:
                round_id = self._save_round(cursor, game_id, round_data)
                
                # Insere ações de cada street
                streets = round_data.get('streets', [])
                for street_data in streets:
                    self._save_actions(cursor, round_id, street_data)
            
            conn.commit()
            return True, ""
            
        except Exception as e:
            conn.rollback()
            error_msg = str(e)
            print(f"[SUPABASE] Error saving game history: {error_msg}")
            return False, error_msg
        finally:
            cursor.close()
    
    def _save_round(self, cursor, game_id: str, round_data: Dict[str, Any]) -> str:
        """
        Salva dados de um round.
        
        Returns:
            UUID do round criado
        """
        cursor.execute("""
            INSERT INTO rounds (
                game_id, round_number, button_position, result
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            game_id,
            round_data.get('round_number'),
            round_data.get('button_position', 0),
            Json(round_data.get('result', {}))
        ))
        
        return str(cursor.fetchone()[0])
    
    def _save_actions(self, cursor, round_id: str, street_data: Dict[str, Any]):
        """Salva ações de uma street."""
        street = street_data.get('street')
        actions = street_data.get('actions', [])
        
        # Prepara dados para inserção em lote
        action_values = []
        for idx, action in enumerate(actions):
            # Extrai metadata adicional (cartas do jogador, probabilidade, etc)
            metadata = {}
            if 'my_hole_cards' in action:
                metadata['my_hole_cards'] = action['my_hole_cards']
            if 'my_win_probability' in action:
                metadata['my_win_probability'] = action['my_win_probability']
            if 'pot_odds' in action:
                metadata['pot_odds'] = action['pot_odds']
            
            action_values.append((
                round_id,
                street,
                action.get('player_uuid'),
                action.get('action'),
                action.get('amount', 0),
                action.get('pot_before', 0),
                action.get('stack_before', 0),
                idx,  # sequence_number
                Json(metadata) if metadata else None
            ))
        
        if action_values:
            execute_values(
                cursor,
                """
                INSERT INTO actions (
                    round_id, street, player_uuid, action, amount,
                    pot_before, stack_before, sequence_number, metadata
                )
                VALUES %s
                """,
                action_values
            )
    
    def get_player_stats(self, nickname: str) -> Optional[Dict[str, Any]]:
        """
        Obtém estatísticas de um jogador.
        
        Args:
            nickname: Nickname do jogador
            
        Returns:
            Dict com estatísticas ou None se jogador não existe
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    p.id,
                    p.nickname,
                    p.created_at,
                    p.last_seen,
                    COUNT(DISTINCT g.id) as total_games,
                    COUNT(DISTINCT r.id) as total_rounds
                FROM players p
                LEFT JOIN games g ON p.id = g.player_id
                LEFT JOIN rounds r ON g.id = r.game_id
                WHERE p.nickname = %s
                GROUP BY p.id, p.nickname, p.created_at, p.last_seen
            """, (nickname,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            return {
                'player_id': str(result[0]),
                'nickname': result[1],
                'created_at': result[2].isoformat() if result[2] else None,
                'last_seen': result[3].isoformat() if result[3] else None,
                'total_games': result[4] or 0,
                'total_rounds': result[5] or 0
            }
        finally:
            cursor.close()

    def get_translations(self, lang_code: str) -> Dict[str, str]:
        """
        Obtém todas as traduções para um idioma específico.
        
        Args:
            lang_code: Código do idioma (ex: 'pt-br')
            
        Returns:
            Dict {key: content}
        """
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT key, content 
                FROM localizations 
                WHERE lang_code = %s
            """, (lang_code,))
            
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}
        except Exception as e:
            print(f"[SUPABASE] Error fetching translations: {e}")
            return {}
        finally:
            cursor.close()


# Instância global (singleton pattern)
_supabase_client = None


def get_supabase_client() -> SupabaseClient:
    """Retorna instância singleton do cliente Supabase."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client
