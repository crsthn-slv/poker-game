-- Schema para o Poker Game Web

-- Tabela de Jogadores
CREATE TABLE IF NOT EXISTS players (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nickname VARCHAR(50) UNIQUE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Jogos
CREATE TABLE IF NOT EXISTS games (
  id UUID PRIMARY KEY,
  player_id UUID REFERENCES players(id),
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  initial_stack INTEGER NOT NULL,
  small_blind INTEGER NOT NULL,
  big_blind INTEGER NOT NULL,
  num_players INTEGER NOT NULL,
  total_rounds INTEGER NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Rounds
CREATE TABLE IF NOT EXISTS rounds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id UUID REFERENCES games(id) ON DELETE CASCADE,
  round_number INTEGER NOT NULL,
  button_position INTEGER NOT NULL,
  result JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Ações (Actions)
CREATE TABLE IF NOT EXISTS actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  round_id UUID REFERENCES rounds(id) ON DELETE CASCADE,
  street VARCHAR(10) NOT NULL,
  player_uuid UUID NOT NULL,
  action VARCHAR(20) NOT NULL,
  amount INTEGER NOT NULL,
  pot_before INTEGER NOT NULL,
  stack_before INTEGER NOT NULL,
  sequence_number INTEGER NOT NULL,
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_games_player_id ON games(player_id);
CREATE INDEX IF NOT EXISTS idx_rounds_game_id ON rounds(game_id);
CREATE INDEX IF NOT EXISTS idx_actions_round_id ON actions(round_id);
CREATE INDEX IF NOT EXISTS idx_players_nickname ON players(nickname);
