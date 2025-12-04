-- Match sessions table for game history management
-- Each player can have up to 256 matches, oldest are automatically deleted

CREATE TABLE IF NOT EXISTS match_sessions (
    id TEXT PRIMARY KEY,
    player_id UUID REFERENCES players(id) ON DELETE CASCADE,
    match_number INTEGER NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    current_round INTEGER DEFAULT 0,
    total_rounds INTEGER NOT NULL,
    initial_stack INTEGER NOT NULL,
    num_opponents INTEGER NOT NULL,
    session_data JSONB,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_match_sessions_player_id ON match_sessions(player_id);
CREATE INDEX IF NOT EXISTS idx_match_sessions_status ON match_sessions(status);
CREATE INDEX IF NOT EXISTS idx_match_sessions_created ON match_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_match_sessions_player_created ON match_sessions(player_id, created_at DESC);

-- Link games table to match_sessions
ALTER TABLE games ADD COLUMN IF NOT EXISTS match_session_id TEXT REFERENCES match_sessions(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_games_match_session ON games(match_session_id);

-- Function to enforce 256 match limit per player (FIFO)
CREATE OR REPLACE FUNCTION enforce_match_limit()
RETURNS TRIGGER AS $$
BEGIN
    -- Delete oldest matches beyond 256 for this player
    DELETE FROM match_sessions
    WHERE id IN (
        SELECT id FROM match_sessions
        WHERE player_id = NEW.player_id
        ORDER BY created_at ASC
        OFFSET 256
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to run after each insert
DROP TRIGGER IF EXISTS match_limit_trigger ON match_sessions;
CREATE TRIGGER match_limit_trigger
AFTER INSERT ON match_sessions
FOR EACH ROW
EXECUTE FUNCTION enforce_match_limit();

-- Function to update last_updated timestamp
CREATE OR REPLACE FUNCTION update_match_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update timestamp on session_data changes
DROP TRIGGER IF EXISTS match_update_trigger ON match_sessions;
CREATE TRIGGER match_update_trigger
BEFORE UPDATE ON match_sessions
FOR EACH ROW
EXECUTE FUNCTION update_match_timestamp();
