/**
 * RequestQueue.ts — Request queueing and response caching for the Worker relay.
 *
 * When multiple players build simultaneously, requests queue instead of
 * dropping. When someone builds the same thing twice, cached responses
 * return instantly without hitting the AI pipeline.
 *
 * Architecture:
 *   - Queue: in-Worker Map<sessionId, IncomingMessage[]> with a concurrency
 *     limiter. Since Cloudflare Workers are single-threaded per isolate,
 *     we just need to ensure we don't overwhelm the Durable Object with
 *     concurrent job submissions. The queue batches up to `MAX_BATCH`
 *     messages per drain cycle.
 *   - Cache: Map<cacheKey, {response, expiry}> with TTL-based eviction.
 *     Keys are normalized player messages. Template matches are already
 *     instant (pure computation) — this cache covers the deep path.
 */

import type {
  Env,
  IncomingMessage,
} from "./types";

// ─── Configuration ───────────────────────────────────────────────────────────

/** Max concurrent jobs per session before queueing kicks in. */
const MAX_CONCURRENT_PER_SESSION = 3;

/** Cache TTL in milliseconds (10 minutes). */
const CACHE_TTL_MS = 10 * 60 * 1000;

/** Max cache entries (prevent memory growth in the isolate). */
const CACHE_MAX_ENTRIES = 200;

/** Queue drain interval in ms. */
const QUEUE_DRAIN_INTERVAL_MS = 500;

// ─── Types ───────────────────────────────────────────────────────────────────

interface QueuedRequest {
  sessionId: string;
  message: IncomingMessage;
  enqueuedAt: number;
}

interface CacheEntry {
  response: Record<string, unknown>;
  expiry: number;
}

// ─── Request Queue ───────────────────────────────────────────────────────────

export class RequestQueue {
  private queue: QueuedRequest[] = [];
  private processing: Map<string, number> = new Map(); // sessionId → count
  private maxConcurrent: number;

  constructor(maxConcurrent: number = MAX_CONCURRENT_PER_SESSION) {
    this.maxConcurrent = maxConcurrent;
  }

  /**
   * Enqueue a request. Returns position in queue (0 = immediate).
   */
  enqueue(message: IncomingMessage): number {
    const sessionId = message.sessionId;
    const current = this.processing.get(sessionId) ?? 0;

    if (current < this.maxConcurrent) {
      // Process immediately — don't queue
      this.processing.set(sessionId, current + 1);
      return 0;
    }

    // Queue it
    const entry: QueuedRequest = {
      sessionId,
      message,
      enqueuedAt: Date.now(),
    };
    this.queue.push(entry);
    return this.queue.filter((r) => r.sessionId === sessionId).length;
  }

  /**
   * Mark a request as complete, freeing a slot and returning the next
   * queued request for that session (if any).
   */
  complete(sessionId: string): IncomingMessage | null {
    const current = this.processing.get(sessionId) ?? 0;
    if (current > 0) {
      this.processing.set(sessionId, current - 1);
    }

    // Find next queued request for this session
    const idx = this.queue.findIndex((r) => r.sessionId === sessionId);
    if (idx === -1) return null;

    const next = this.queue.splice(idx, 1)[0];
    this.processing.set(sessionId, (this.processing.get(sessionId) ?? 0) + 1);
    return next.message;
  }

  /**
   * Get queue depth for a session.
   */
  depth(sessionId: string): number {
    return this.queue.filter((r) => r.sessionId === sessionId).length;
  }

  /**
   * Get total queue depth across all sessions.
   */
  totalDepth(): number {
    return this.queue.length;
  }

  /**
   * Get queue stats for diagnostics.
   */
  stats(): { queued: number; sessions: string[]; depths: Record<string, number> } {
    const depths: Record<string, number> = {};
    const sessions = new Set<string>();
    for (const r of this.queue) {
      sessions.add(r.sessionId);
      depths[r.sessionId] = (depths[r.sessionId] ?? 0) + 1;
    }
    return {
      queued: this.queue.length,
      sessions: [...sessions],
      depths,
    };
  }
}

// ─── Response Cache ──────────────────────────────────────────────────────────

export class ResponseCache {
  private cache: Map<string, CacheEntry> = new Map();
  private ttlMs: number;
  private maxEntries: number;

  constructor(ttlMs: number = CACHE_TTL_MS, maxEntries: number = CACHE_MAX_ENTRIES) {
    this.ttlMs = ttlMs;
    this.maxEntries = maxEntries;
  }

  /**
   * Normalize a message into a cache key.
   * Lowercases, trims, collapses whitespace, strips punctuation
   * so "Build me a  house!" and "build me a house" hit the same key.
   */
  static makeKey(message: string): string {
    return message
      .toLowerCase()
      .trim()
      .replace(/[^\w\s]/g, "")
      .replace(/\s+/g, " ");
  }

  /**
   * Get a cached response. Returns null if not cached or expired.
   */
  get(message: string): Record<string, unknown> | null {
    const key = ResponseCache.makeKey(message);
    const entry = this.cache.get(key);
    if (!entry) return null;

    if (Date.now() > entry.expiry) {
      this.cache.delete(key);
      return null;
    }

    // Move to end (LRU)
    this.cache.delete(key);
    this.cache.set(key, entry);

    return { ...entry.response, _cached: true };
  }

  /**
   * Store a response in the cache.
   */
  set(message: string, response: Record<string, unknown>): void {
    const key = ResponseCache.makeKey(message);

    // Evict if at capacity (oldest entry)
    if (this.cache.size >= this.maxEntries) {
      const oldest = this.cache.keys().next().value;
      if (oldest) this.cache.delete(oldest);
    }

    this.cache.set(key, {
      response,
      expiry: Date.now() + this.ttlMs,
    });
  }

  /**
   * Invalidate a specific cache entry.
   */
  invalidate(message: string): boolean {
    const key = ResponseCache.makeKey(message);
    return this.cache.delete(key);
  }

  /**
   * Clear all cached entries.
   */
  clear(): number {
    const count = this.cache.size;
    this.cache.clear();
    return count;
  }

  /**
   * Get cache stats.
   */
  stats(): { entries: number; maxEntries: number; ttlMs: number } {
    return {
      entries: this.cache.size,
      maxEntries: this.maxEntries,
      ttlMs: this.ttlMs,
    };
  }

  /**
   * Prune expired entries. Called periodically.
   * Returns number of entries pruned.
   */
  prune(): number {
    let pruned = 0;
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (now > entry.expiry) {
        this.cache.delete(key);
        pruned++;
      }
    }
    return pruned;
  }
}
