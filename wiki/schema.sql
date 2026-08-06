-- Fleet Wiki Schema — Cloudflare D1
-- The community internal wiki for the fleet's accumulated knowledge

CREATE TABLE IF NOT EXISTS pages (
  id TEXT PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  category TEXT NOT NULL, -- 'characters', 'plot', 'architecture', 'models', 'technical', 'creative'
  content TEXT NOT NULL, -- markdown
  summary TEXT, -- one-line description for listings
  tags TEXT, -- JSON array of tags
  source_file TEXT, -- original ai-writings file this was derived from
  word_count INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now')),
  author TEXT DEFAULT 'fleet', -- which agent created this
  parent_id TEXT, -- for hierarchical pages
  sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS categories (
  name TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  description TEXT,
  icon TEXT, -- emoji
  sort_order INTEGER DEFAULT 0,
  page_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS links (
  source_page TEXT NOT NULL,
  target_page TEXT NOT NULL,
  link_text TEXT,
  FOREIGN KEY (source_page) REFERENCES pages(id),
  FOREIGN KEY (target_page) REFERENCES pages(id)
);

CREATE TABLE IF NOT EXISTS search_cache (
  query_hash TEXT PRIMARY KEY,
  query_text TEXT NOT NULL,
  results TEXT NOT NULL, -- JSON array of {page_id, title, slug, score}
  created_at TEXT DEFAULT (datetime('now'))
);

-- Seed categories
INSERT OR IGNORE INTO categories (name, display_name, description, icon, sort_order) VALUES
  ('characters', 'Characters', 'The crew, the cast, the voices', '🎭', 1),
  ('plot', 'Story Universe', 'The SuperInstance saga, novellas, episodes', '📖', 2),
  ('architecture', 'Fleet Architecture', 'How the 32-repo fleet fits together', '🏗️', 3),
  ('models', 'Model Portraits', 'Cognitive fingerprints of each AI model', '🧠', 4),
  ('technical', 'Technical Concepts', 'Engineering ideas worth remembering', '⚙️', 5),
  ('creative', 'Creative Corpus', 'The ai-writings library and its themes', '✍️', 6),
  ('fleet-status', 'Fleet Status', 'Current state of repos, tests, crons', '📊', 7);

CREATE INDEX IF NOT EXISTS idx_pages_category ON pages(category);
CREATE INDEX IF NOT EXISTS idx_pages_slug ON pages(slug);
CREATE INDEX IF NOT EXISTS idx_pages_tags ON pages(tags);
CREATE INDEX IF NOT EXISTS idx_pages_updated ON pages(updated_at DESC);
