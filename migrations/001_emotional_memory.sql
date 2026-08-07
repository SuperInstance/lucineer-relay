-- ═══════════════════════════════════════════════════════════════════════════
-- The Listener's Ear — Emotional Memory Schema
-- D1 table for storing player emotional events in the Slackwater game.
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS emotional_events (
  id           TEXT PRIMARY KEY,
  player_id    TEXT NOT NULL,
  emotion      TEXT NOT NULL,
  intensity    REAL DEFAULT 0.5,
  context      TEXT,
  session_id   TEXT,
  build_theme  TEXT,
  created_at   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_emotional_player ON emotional_events(player_id);
CREATE INDEX IF NOT EXISTS idx_emotional_emotion ON emotional_events(emotion);
CREATE INDEX IF NOT EXISTS idx_emotional_created ON emotional_events(created_at DESC);
