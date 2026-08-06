/**
 * Fleet Wiki Worker — community internal wiki on Cloudflare
 * 
 * Endpoints:
 * GET  /                    — wiki home page (HTML)
 * GET  /api/pages           — list all pages (optional ?category=)
 * GET  /api/pages/:slug     — get single page
 * POST /api/pages           — create/update page (agent write)
 * GET  /api/categories      — list categories with page counts
 * GET  /api/search?q=...    — semantic search via Vectorize + D1
 * GET  /wiki/:slug          — render page as HTML
 */

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS });
    }
    
    // API routes
    if (path === '/api/categories') {
      return handleCategories(env);
    }
    
    if (path === '/api/pages') {
      const category = url.searchParams.get('category');
      return handlePagesList(env, category);
    }
    
    if (path === '/api/search') {
      const q = url.searchParams.get('q');
      if (!q) return json({ error: 'Missing query parameter q' }, 400);
      return handleSearch(env, q);
    }
    
    if (path.startsWith('/api/pages/') && request.method === 'GET') {
      const slug = path.replace('/api/pages/', '');
      return handlePageGet(env, slug);
    }
    
    if (path === '/api/pages' && request.method === 'POST') {
      return handlePageCreate(env, await request.json());
    }
    
    // Wiki page render
    if (path.startsWith('/wiki/') && path !== '/wiki/') {
      const slug = path.replace('/wiki/', '');
      return renderWikiPage(env, slug);
    }
    
    // Home page
    if (path === '/' || path === '/wiki') {
      return renderHome(env);
    }
    
    return json({ error: 'Not found' }, 404);
  }
};

async function handleCategories(env) {
  const result = await env.DB.prepare(`
    SELECT * FROM categories ORDER BY sort_order
  `).all();
  return json(result.results);
}

async function handlePagesList(env, category) {
  const stmt = category
    ? env.DB.prepare(`SELECT id, slug, title, category, summary, tags, word_count, updated_at FROM pages WHERE category = ? ORDER BY sort_order, title`).bind(category)
    : env.DB.prepare(`SELECT id, slug, title, category, summary, tags, word_count, updated_at FROM pages ORDER BY category, sort_order, title`);
  const result = await stmt.all();
  return json(result.results);
}

async function handlePageGet(env, slug) {
  const page = await env.DB.prepare(`SELECT * FROM pages WHERE slug = ?`).bind(slug).first();
  if (!page) return json({ error: 'Page not found' }, 404);
  
  // Get linked pages
  const links = await env.DB.prepare(`
    SELECT p.slug, p.title FROM links l 
    JOIN pages p ON p.id = l.target_page 
    WHERE l.source_page = ?
  `).bind(page.id).all();
  
  page.links = links.results;
  return json(page);
}

async function handlePageCreate(env, data) {
  const id = data.id || crypto.randomUUID();
  const slug = data.slug || slugify(data.title);
  
  await env.DB.prepare(`
    INSERT OR REPLACE INTO pages (id, slug, title, category, content, summary, tags, source_file, word_count, author, parent_id, sort_order, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
  `).bind(
    id, slug, data.title, data.category || 'technical',
    data.content || '', data.summary || '', 
    JSON.stringify(data.tags || []), data.source_file || null,
    (data.content || '').split(/\s+/).length, data.author || 'fleet',
    data.parent_id || null, data.sort_order || 0
  ).run();
  
  // Update category count
  await env.DB.prepare(`
    UPDATE categories SET page_count = (SELECT COUNT(*) FROM pages WHERE category = ?) WHERE name = ?
  `).bind(data.category || 'technical', data.category || 'technical').run();
  
  return json({ id, slug, status: 'ok' });
}

async function handleSearch(env, query) {
  // First try Vectorize for semantic search
  try {
    // Generate embedding via Cloudflare AI
    const embedding = await env.AI.run('@cf/baai/bge-base-en-v1.5', { text: query });
    const vectorResults = await env.VECTORIZE.query(embedding.data[0], { topK: 10 });
    
    // Fetch page details from D1 for matched files
    const matchedIds = vectorResults.matches.map(m => m.id);
    const placeholders = matchedIds.map(() => '?').join(',');
    const pages = await env.DB.prepare(
      `SELECT slug, title, category, summary FROM pages WHERE id IN (${placeholders})`
    ).bind(...matchedIds).all();
    
    return json({
      query,
      results: vectorResults.matches.map((m, i) => ({
        ...pages.results[i],
        score: m.score,
      })),
      source: 'vectorize'
    });
  } catch (e) {
    // Fallback to D1 full-text search
    const results = await env.DB.prepare(`
      SELECT slug, title, category, summary FROM pages 
      WHERE title LIKE ? OR content LIKE ? OR summary LIKE ?
      LIMIT 10
    `).bind(`%${query}%`, `%${query}%`, `%${query}%`).all();
    
    return json({ query, results: results.results, source: 'd1-fallback' });
  }
}

async function renderHome(env) {
  const categories = await env.DB.prepare(`SELECT * FROM categories ORDER BY sort_order`).all();
  const recentPages = await env.DB.prepare(`
    SELECT slug, title, category, summary, updated_at FROM pages 
    ORDER BY updated_at DESC LIMIT 10
  `).all();
  
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fleet Wiki — Community Memory</title>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    :root { --bg: #071214; --bg2: #0a1518; --card: #0e1f23; --copper: #c4774a; --text: #d4cfc4; --dim: #5a554d; }
    body { background: var(--bg); color: var(--text); font-family: Inter, sans-serif; padding: 2rem; max-width: 900px; margin: 0 auto; }
    h1 { font-family: Cormorant Garamond, serif; font-size: 2.5rem; color: var(--copper); margin-bottom: 0.5rem; }
    .subtitle { color: var(--dim); margin-bottom: 2rem; font-size: 0.95rem; }
    .search-bar { width: 100%; padding: 0.8rem 1rem; background: var(--card); border: 1px solid var(--copper); color: var(--text); font-size: 1rem; border-radius: 4px; margin-bottom: 2rem; }
    .categories { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
    .cat-card { background: var(--card); padding: 1.2rem; border-radius: 6px; border: 1px solid #1a3038; text-decoration: none; color: var(--text); transition: border-color 0.2s; }
    .cat-card:hover { border-color: var(--copper); }
    .cat-icon { font-size: 1.8rem; margin-bottom: 0.5rem; }
    .cat-name { font-family: Cormorant Garamond, serif; font-size: 1.3rem; color: var(--copper); }
    .cat-desc { font-size: 0.85rem; color: var(--dim); margin-top: 0.3rem; }
    .cat-count { font-size: 0.75rem; color: var(--copper); margin-top: 0.5rem; }
    .recent { border-top: 1px solid #1a3038; padding-top: 1.5rem; }
    .recent h2 { font-family: Cormorant Garamond, serif; color: var(--copper); margin-bottom: 1rem; }
    .recent-item { padding: 0.5rem 0; border-bottom: 1px solid #112025; display: flex; justify-content: space-between; }
    .recent-item a { color: var(--text); text-decoration: none; }
    .recent-item a:hover { color: var(--copper); }
    .recent-item .cat { font-size: 0.75rem; color: var(--dim); }
    .recent-item .date { font-size: 0.75rem; color: var(--dim); }
    a { color: var(--copper); }
  </style>
</head>
<body>
  <h1>⚒️ Fleet Wiki</h1>
  <p class="subtitle">Community memory for the SuperInstance fleet — ${recentPages.results.length} pages across ${categories.results.length} categories</p>
  
  <input class="search-bar" placeholder="Search the corpus..." onkeydown="if(event.key==='Enter'){window.location='/api/search?q='+encodeURIComponent(this.value)}">
  
  <div class="categories">
    ${categories.results.map(c => `
      <a class="cat-card" href="/api/pages?category=${c.name}">
        <div class="cat-icon">${c.icon}</div>
        <div class="cat-name">${c.display_name}</div>
        <div class="cat-desc">${c.description || ''}</div>
        <div class="cat-count">${c.page_count} pages</div>
      </a>
    `).join('')}
  </div>
  
  <div class="recent">
    <h2>Recently Updated</h2>
    ${recentPages.results.map(p => `
      <div class="recent-item">
        <a href="/wiki/${p.slug}">${p.title}</a>
        <span class="cat">${p.category}</span>
        <span class="date">${p.updated_at}</span>
      </div>
    `).join('')}
  </div>
</body>
</html>`;
  
  return new Response(html, { headers: { 'Content-Type': 'text/html' } });
}

async function renderWikiPage(env, slug) {
  const page = await env.DB.prepare(`SELECT * FROM pages WHERE slug = ?`).bind(slug).first();
  if (!page) return new Response('Page not found', { status: 404 });
  
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${page.title} — Fleet Wiki</title>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600&family=Inter:wght@300;400;500;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    :root { --bg: #071214; --bg2: #0a1518; --card: #0e1f23; --copper: #c4774a; --text: #d4cfc4; --dim: #5a554d; }
    body { background: var(--bg); color: var(--text); font-family: Inter, sans-serif; padding: 2rem; max-width: 700px; margin: 0 auto; line-height: 1.7; }
    h1 { font-family: Cormorant Garamond, serif; font-size: 2rem; color: var(--copper); margin-bottom: 0.5rem; }
    .meta { color: var(--dim); font-size: 0.85rem; margin-bottom: 2rem; }
    .content { white-space: pre-wrap; font-size: 0.95rem; }
    pre, code { font-family: JetBrains Mono, monospace; }
    pre { background: var(--card); padding: 1rem; border-radius: 4px; overflow-x: auto; margin: 1rem 0; }
    a { color: var(--copper); }
    .back { margin-bottom: 1.5rem; display: inline-block; font-size: 0.85rem; }
  </style>
</head>
<body>
  <a class="back" href="/">← Fleet Wiki</a>
  <h1>${page.title}</h1>
  <div class="meta">${page.category} · ${page.word_count} words · by ${page.author} · ${page.updated_at}</div>
  <div class="content">${page.content}</div>
</body>
</html>`;
  
  return new Response(html, { headers: { 'Content-Type': 'text/html' } });
}

function slugify(text) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS },
  });
}
