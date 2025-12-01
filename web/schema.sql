-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Players table
CREATE TABLE IF NOT EXISTS players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nickname TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Games table
CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY, -- Using TEXT because it's a UUIDv5 string from python
    player_id UUID REFERENCES players(id),
    timestamp TIMESTAMP WITH TIME ZONE,
    initial_stack INTEGER,
    small_blind INTEGER,
    big_blind INTEGER,
    num_players INTEGER,
    total_rounds INTEGER
);

-- Rounds table
CREATE TABLE IF NOT EXISTS rounds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id TEXT REFERENCES games(id),
    round_number INTEGER,
    button_position INTEGER,
    result JSONB
);

-- Actions table
CREATE TABLE IF NOT EXISTS actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    round_id UUID REFERENCES rounds(id),
    street TEXT,
    player_uuid TEXT, -- Can be bot UUID or player UUID
    action TEXT,
    amount INTEGER,
    pot_before INTEGER,
    stack_before INTEGER,
    sequence_number INTEGER,
    metadata JSONB
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_games_player_id ON games(player_id);
CREATE INDEX IF NOT EXISTS idx_rounds_game_id ON rounds(game_id);
CREATE INDEX IF NOT EXISTS idx_actions_round_id ON actions(round_id);
