import { DurableObject } from "cloudflare:workers";
import type {
  IncomingMessage,
  Job,
  JobResult,
  WorldSnapshot,
  MessageHistoryEntry,
  BuildCommand,
  WorldBuild,
} from "../types";

/** Lease duration: a claimed job is considered stale after 3 minutes. */
const LEASE_MS = 3 * 60 * 1000;
/** Max claim attempts before a job is permanently errored. */
const MAX_ATTEMPTS = 3;
/** Rate limit: max messages per session per window. */
const RATE_LIMIT_MAX = 10;
/** Rate limit window in ms (1 minute). */
const RATE_LIMIT_WINDOW_MS = 60 * 1000;
/** Pruning: jobs older than this are deleted. */
const PRUNE_AFTER_MS = 24 * 60 * 60 * 1000; // 24h
/** Alarm interval for pruning sweep. */
const ALARM_INTERVAL_MS = 60 * 60 * 1000; // 1h

// SQL rows are returned as Record<string, SqlStorageValue> by the DO SQLite API
type SqlRow = Record<string, SqlStorageValue>;

export class LucineerSession extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);

    // Initialize SQLite schema with all columns
    this.ctx.storage.sql.exec(`
      CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        player_name TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        reply TEXT,
        commands TEXT,
        files TEXT,
        error TEXT,
        created_at INTEGER NOT NULL,
        completed_at INTEGER,
        claimed_at INTEGER,
        claimed_by TEXT,
        lease_expires_at INTEGER,
        attempts INTEGER NOT NULL DEFAULT 0
      );

      CREATE TABLE IF NOT EXISTS world_state (
        session_id TEXT PRIMARY KEY,
        snapshot TEXT NOT NULL,
        updated_at INTEGER NOT NULL
      );

      CREATE TABLE IF NOT EXISTS message_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        player_name TEXT NOT NULL,
        message TEXT NOT NULL,
        reply TEXT,
        timestamp INTEGER NOT NULL
      );

      CREATE INDEX IF NOT EXISTS idx_jobs_session ON jobs(session_id);
      CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
      CREATE INDEX IF NOT EXISTS idx_jobs_claimed ON jobs(claimed_at);
      CREATE INDEX IF NOT EXISTS idx_history_session ON message_history(session_id);

      CREATE TABLE IF NOT EXISTS active_sessions (
        session_id TEXT PRIMARY KEY,
        last_seen INTEGER NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_active_sessions_seen ON active_sessions(last_seen);

      CREATE TABLE IF NOT EXISTS world_builds (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        type TEXT NOT NULL,
        position_x REAL NOT NULL,
        position_y REAL NOT NULL,
        position_z REAL NOT NULL,
        materials TEXT NOT NULL,
        player_name TEXT NOT NULL,
        unfinished_hook TEXT,
        timestamp INTEGER NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_world_builds_session ON world_builds(session_id);

      CREATE TABLE IF NOT EXISTS bond_state (
        session_id TEXT PRIMARY KEY,
        player_name TEXT NOT NULL,
        bond_level INTEGER NOT NULL DEFAULT 0,
        updated_at INTEGER NOT NULL
      );
    `);

    // Migrate existing tables: add columns if missing
    this.migrateSchema();

    // Schedule first pruning alarm if not already set
    this.ctx.storage.setAlarm(Date.now() + ALARM_INTERVAL_MS).catch(() => {});
  }

  /**
   * Add columns to pre-existing tables without dropping data.
   * SQLite's ALTER TABLE ADD COLUMN fails silently if the column already exists.
   */
  private migrateSchema(): void {
    const additions = [
      "ALTER TABLE jobs ADD COLUMN claimed_at INTEGER",
      "ALTER TABLE jobs ADD COLUMN claimed_by TEXT",
      "ALTER TABLE jobs ADD COLUMN lease_expires_at INTEGER",
      "ALTER TABLE jobs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0",
    ];
    for (const sql of additions) {
      try {
        this.ctx.storage.sql.exec(sql);
      } catch {
        // column already exists — expected
      }
    }

    // Migrate old 'processing' status to 'pending' so the new claiming flow picks them up
    try {
      this.ctx.storage.sql.exec(
        `UPDATE jobs SET status = 'pending' WHERE status = 'processing'`,
      );
    } catch {
      // table may not exist yet on first deploy
    }
  }

  // Diagnostic — return schema info
  async diag(): Promise<Record<string, unknown>> {
    try {
      const cursor = this.ctx.storage.sql.exec("PRAGMA table_info(jobs)");
      const cols = cursor.toArray().map((r: SqlRow) => String(r["name"]));
      const countCursor = this.ctx.storage.sql.exec("SELECT COUNT(*) as n FROM jobs");
      const count = countCursor.toArray()[0] as SqlRow;
      return { columns: cols, totalJobs: Number(count["n"]), status: "ok" };
    } catch (e) {
      return { error: String(e), status: "fail" };
    }
  }

  // ---------------------------------------------------------------------------
  // Session registry (stored in the "default" DO so batch claim can fan out)
  // ---------------------------------------------------------------------------

  async registerSession(sessionId: string): Promise<void> {
    const now = Date.now();
    this.ctx.storage.sql.exec(
      `INSERT INTO active_sessions (session_id, last_seen)
       VALUES (?, ?)
       ON CONFLICT(session_id) DO UPDATE SET last_seen = excluded.last_seen`,
      sessionId,
      now,
    );
  }

  async getActiveSessions(): Promise<string[]> {
    const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000; // 7 days
    this.ctx.storage.sql.exec(
      `DELETE FROM active_sessions WHERE last_seen < ?`,
      cutoff,
    );
    const cursor = this.ctx.storage.sql.exec(
      `SELECT session_id FROM active_sessions ORDER BY last_seen DESC`,
    );
    return cursor.toArray().map((r: SqlRow) => String(r["session_id"]));
  }

  /**
   * Extend the lease on a claimed job so long-running processors don't lose it.
   * Only updates jobs that are still status='claimed'. If workerId is provided,
   * only renews leases owned by that worker.
   */
  async renewLease(jobId: string, workerId?: string): Promise<Job | null> {
    const now = Date.now();
    const leaseExpiresAt = now + LEASE_MS;

    this.ctx.storage.sql.exec(
      `UPDATE jobs
       SET lease_expires_at = ?
       WHERE id = ?
         AND status = 'claimed'
         AND (? IS NULL OR claimed_by = ?)`,
      leaseExpiresAt,
      jobId,
      workerId ?? null,
      workerId ?? null,
    );

    return this.getJob(jobId);
  }

  /**
   * Generate a job ID that encodes the session ID so getJob can route
   * to the correct Durable Object without a lookup.
   * Format: `<urlEncodedSessionId>.<randomHex>`
   */
  private generateJobId(sessionId: string): string {
    const bytes = new Uint8Array(12);
    crypto.getRandomValues(bytes);
    const rand = Array.from(bytes)
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
    return `${encodeURIComponent(sessionId)}.${rand}`;
  }

  // ---------------------------------------------------------------------------
  // Alarm — periodic pruning of old jobs and history
  // ---------------------------------------------------------------------------

  async alarm(): Promise<void> {
    const cutoff = Date.now() - PRUNE_AFTER_MS;

    // Delete completed/errored jobs older than 24h
    this.ctx.storage.sql.exec(
      `DELETE FROM jobs WHERE completed_at IS NOT NULL AND completed_at < ?`,
      cutoff,
    );

    // Delete old message history
    this.ctx.storage.sql.exec(
      `DELETE FROM message_history WHERE timestamp < ?`,
      cutoff,
    );

    // Reclaim stale claimed jobs (lease expired, within retry limit)
    this.cleanupStaleJobs();

    // Schedule next sweep
    await this.ctx.storage.setAlarm(Date.now() + ALARM_INTERVAL_MS);
  }

  // ---------------------------------------------------------------------------
  // Rate limiting
  // ---------------------------------------------------------------------------

  /**
   * Returns true if the session is within the rate limit (and records the request).
   * Returns false if the session has exceeded RATE_LIMIT_MAX messages in the last minute.
   */
  async checkRateLimit(sessionId: string): Promise<boolean> {
    const now = Date.now();
    const windowStart = now - RATE_LIMIT_WINDOW_MS;

    const cursor = this.ctx.storage.sql.exec(
      `SELECT COUNT(*) as count FROM jobs WHERE session_id = ? AND created_at > ?`,
      sessionId,
      windowStart,
    );
    const row = cursor.toArray()[0] as SqlRow;
    const count = Number(row?.count ?? 0);

    return count < RATE_LIMIT_MAX;
  }

  // ---------------------------------------------------------------------------
  // Job lifecycle
  // ---------------------------------------------------------------------------

  async createJob(msg: IncomingMessage): Promise<{ jobId: string }> {
    const jobId = this.generateJobId(msg.sessionId);
    const now = Date.now();

    this.ctx.storage.sql.exec(
      `INSERT INTO jobs (id, session_id, player_name, message, status, created_at, attempts)
       VALUES (?, ?, ?, ?, 'pending', ?, 0)`,
      jobId,
      msg.sessionId,
      msg.playerName,
      msg.message,
      now,
    );

    // Record in message history
    this.ctx.storage.sql.exec(
      `INSERT INTO message_history (job_id, session_id, player_name, message, timestamp)
       VALUES (?, ?, ?, ?, ?)`,
      jobId,
      msg.sessionId,
      msg.playerName,
      msg.message,
      now,
    );

    // Update world state if provided
    if (msg.worldSnapshot) {
      this.ctx.storage.sql.exec(
        `INSERT INTO world_state (session_id, snapshot, updated_at)
         VALUES (?, ?, ?)
         ON CONFLICT(session_id) DO UPDATE SET snapshot = excluded.snapshot, updated_at = excluded.updated_at`,
        msg.sessionId,
        JSON.stringify(msg.worldSnapshot),
        now,
      );
    }

    return { jobId };
  }

  async getJob(jobId: string): Promise<Job | null> {
    const cursor = this.ctx.storage.sql.exec(
      `SELECT * FROM jobs WHERE id = ?`,
      jobId,
    );
    const row = cursor.toArray()[0] as SqlRow | undefined;
    if (!row) return null;

    return this.rowToJob(row);
  }

  async setJobResult(jobId: string, result: JobResult): Promise<void> {
    const now = Date.now();

    this.ctx.storage.sql.exec(
      `UPDATE jobs
       SET status = 'complete', reply = ?, commands = ?, files = ?, completed_at = ?
       WHERE id = ?`,
      result.reply,
      JSON.stringify(result.commands ?? []),
      JSON.stringify(result.files ?? []),
      now,
      jobId,
    );

    // Update message history with reply
    this.ctx.storage.sql.exec(
      `UPDATE message_history SET reply = ? WHERE job_id = ?`,
      result.reply,
      jobId,
    );
  }

  async setJobError(jobId: string, error: string): Promise<void> {
    this.ctx.storage.sql.exec(
      `UPDATE jobs SET status = 'error', error = ?, completed_at = ? WHERE id = ?`,
      error,
      Date.now(),
      jobId,
    );
  }

  // ---------------------------------------------------------------------------
  // Job claiming — atomic batch claim with lease + retry support
  // ---------------------------------------------------------------------------

  /**
   * Atomically claim up to `limit` pending jobs for processing.
   *
   * This is the preferred claiming method over getPendingJobs + claimJob,
   * because it performs the state transition (pending → claimed) in the same
   * transaction as the selection, eliminating the race where two processors
   * both grab the same job.
   *
   * Steps:
   * 1. Reclaim expired leases (status='claimed' AND lease_expires_at < now)
   *    - If attempts >= MAX_ATTEMPTS → mark as error (dead-letter)
   *    - Otherwise → reset to 'pending' so they can be re-claimed
   * 2. Select pending jobs (status='pending', claimed_at IS NULL)
   * 3. Atomically transition them to 'claimed' with lease expiry
   */
  async claimPendingJobs(workerId: string, limit = 5): Promise<Job[]> {
    const now = Date.now();
    const leaseExpiresAt = now + LEASE_MS;

    // Step 1: Retire jobs that exceeded max attempts
    this.ctx.storage.sql.exec(
      `UPDATE jobs
       SET status = 'error',
           error = 'Max attempts (' || ? || ') exceeded — lease expired',
           completed_at = ?
       WHERE status = 'claimed'
         AND lease_expires_at IS NOT NULL
         AND lease_expires_at < ?
         AND attempts >= ?`,
      MAX_ATTEMPTS,
      now,
      now,
      MAX_ATTEMPTS,
    );

    // Step 2: Reset expired leases back to pending (within retry limit)
    this.ctx.storage.sql.exec(
      `UPDATE jobs
       SET status = 'pending',
           claimed_at = NULL,
           claimed_by = NULL,
           lease_expires_at = NULL
       WHERE status = 'claimed'
         AND lease_expires_at IS NOT NULL
         AND lease_expires_at < ?`,
      now,
    );

    // Step 3: Select candidate jobs
    const cursor = this.ctx.storage.sql.exec(
      `SELECT * FROM jobs
       WHERE status = 'pending'
         AND claimed_at IS NULL
       ORDER BY created_at ASC
       LIMIT ?`,
      limit,
    );
    const rows = cursor.toArray() as SqlRow[];

    if (rows.length === 0) return [];

    // Step 4: Atomically claim all selected jobs
    const ids = rows.map((r) => r["id"] as string);
    const placeholders = ids.map(() => "?").join(",");

    this.ctx.storage.sql.exec(
      `UPDATE jobs
       SET status = 'claimed',
           claimed_at = ?,
           claimed_by = ?,
           lease_expires_at = ?,
           attempts = attempts + 1
       WHERE id IN (${placeholders})
         AND status = 'pending'
         AND claimed_at IS NULL`,
      now,
      workerId,
      leaseExpiresAt,
      ...ids,
    );

    // Step 5: Return the claimed jobs (re-read to get updated values)
    const claimedCursor = this.ctx.storage.sql.exec(
      `SELECT * FROM jobs WHERE id IN (${placeholders})`,
      ...ids,
    );
    const claimedRows = claimedCursor.toArray() as SqlRow[];

    return claimedRows.map((row) => this.rowToJob(row));
  }

  /**
   * Claim a single job by ID. Used by the per-job claim endpoint.
   * Less efficient than claimPendingJobs but needed for backward compat.
   */
  async claimJob(jobId: string): Promise<Job | null> {
    const now = Date.now();
    const leaseExpiresAt = now + LEASE_MS;

    // Atomic conditional update: only claim if pending and unclaimed
    this.ctx.storage.sql.exec(
      `UPDATE jobs
       SET status = 'claimed',
           claimed_at = ?,
           claimed_by = 'single-claim',
           lease_expires_at = ?,
           attempts = attempts + 1
       WHERE id = ?
         AND status = 'pending'
         AND claimed_at IS NULL`,
      now,
      leaseExpiresAt,
      jobId,
    );

    const job = await this.getJob(jobId);
    if (!job) return null;

    // Check if WE claimed it (claimed_at should be close to now)
    if (job.claimedAt && Math.abs(job.claimedAt - now) < 1000) {
      // We claimed it. Check max attempts.
      if ((job.attempts ?? 0) >= MAX_ATTEMPTS) {
        await this.setJobError(jobId, `Max attempts (${MAX_ATTEMPTS}) exceeded`);
        return null;
      }
      return job;
    }

    // Someone else claimed it first, or it was already claimed
    return null;
  }

  /**
   * Mark jobs as errored if they've been claimed but never completed
   * and their lease has expired beyond recovery.
   * Returns the number of stale jobs cleaned up.
   */
  async cleanupStaleJobs(): Promise<number> {
    const now = Date.now();
    const leaseExpired = now - LEASE_MS;

    // Find claimed jobs whose lease has expired
    const staleCursor = this.ctx.storage.sql.exec(
      `SELECT id, attempts FROM jobs
       WHERE status = 'claimed'
         AND lease_expires_at IS NOT NULL
         AND lease_expires_at < ?`,
      leaseExpired,
    );
    const staleJobs = staleCursor.toArray() as SqlRow[];

    let cleaned = 0;

    for (const stale of staleJobs) {
      const attempts = Number(stale["attempts"] ?? 0);
      if (attempts >= MAX_ATTEMPTS) {
        // Permanently fail this job
        this.ctx.storage.sql.exec(
          `UPDATE jobs SET status = 'error',
               error = 'Job timed out after max attempts and lease expired',
               completed_at = ?
           WHERE id = ?`,
          now,
          stale["id"],
        );
        cleaned++;
      }
    }

    // Reset expired leases back to pending so they can be re-claimed
    this.ctx.storage.sql.exec(
      `UPDATE jobs
       SET status = 'pending',
           claimed_at = NULL,
           claimed_by = NULL,
           lease_expires_at = NULL
       WHERE status = 'claimed'
         AND lease_expires_at IS NOT NULL
         AND lease_expires_at < ?`,
      leaseExpired,
    );

    return cleaned;
  }

  // ---------------------------------------------------------------------------
  // Pending jobs — returns unclaimed jobs for backward compat
  // ---------------------------------------------------------------------------

  /**
   * Returns jobs that are available for processing.
   * Calls cleanupStaleJobs() first, then returns jobs where:
   *   - status = 'pending'
   *   - claimed_at IS NULL (not currently being worked on)
   *
   * NOTE: Processors should prefer claimPendingJobs() for atomic batch claiming.
   * This endpoint is kept for backward compatibility but does NOT guarantee
   * that another processor won't grab the same job before you call claimJob().
   */
  async getPendingJobs(): Promise<Job[]> {
    // Clean up stale jobs first
    await this.cleanupStaleJobs();

    const cursor = this.ctx.storage.sql.exec(
      `SELECT * FROM jobs
       WHERE status = 'pending'
         AND claimed_at IS NULL
       ORDER BY created_at ASC
       LIMIT 10`,
    );
    const rows = cursor.toArray() as SqlRow[];
    return rows.map((row) => this.rowToJob(row));
  }

  // ---------------------------------------------------------------------------
  // World state
  // ---------------------------------------------------------------------------

  async updateWorldState(sessionId: string, snapshot: WorldSnapshot): Promise<void> {
    this.ctx.storage.sql.exec(
      `INSERT INTO world_state (session_id, snapshot, updated_at)
       VALUES (?, ?, ?)
       ON CONFLICT(session_id) DO UPDATE SET snapshot = excluded.snapshot, updated_at = excluded.updated_at`,
      sessionId,
      JSON.stringify(snapshot),
      Date.now(),
    );
  }

  async getWorldState(sessionId: string): Promise<WorldSnapshot | null> {
    const cursor = this.ctx.storage.sql.exec(
      `SELECT snapshot FROM world_state WHERE session_id = ?`,
      sessionId,
    );
    const row = cursor.toArray()[0] as SqlRow | undefined;
    if (!row) return null;
    return JSON.parse(row["snapshot"] as string) as WorldSnapshot;
  }

  // ---------------------------------------------------------------------------
  // Message history
  // ---------------------------------------------------------------------------

  async getMessageHistory(
    sessionId: string,
    limit = 50,
  ): Promise<MessageHistoryEntry[]> {
    const cursor = this.ctx.storage.sql.exec(
      `SELECT job_id, session_id, player_name, message, reply, timestamp
       FROM message_history
       WHERE session_id = ?
       ORDER BY timestamp DESC
       LIMIT ?`,
      sessionId,
      limit,
    );
    const rows = cursor.toArray() as SqlRow[];
    return rows.map((row) => ({
      jobId: row["job_id"] as string,
      sessionId: row["session_id"] as string,
      playerName: row["player_name"] as string,
      message: row["message"] as string,
      reply: (row["reply"] as string) ?? undefined,
      timestamp: row["timestamp"] as number,
    }));
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  private rowToJob(row: SqlRow): Job {
    return {
      id: row["id"] as string,
      sessionId: row["session_id"] as string,
      playerName: row["player_name"] as string,
      message: row["message"] as string,
      status: row["status"] as Job["status"],
      reply: (row["reply"] as string) ?? undefined,
      commands: row["commands"]
        ? (JSON.parse(row["commands"] as string) as BuildCommand[])
        : undefined,
      files: row["files"]
        ? (JSON.parse(row["files"] as string) as Job["files"])
        : undefined,
      error: (row["error"] as string) ?? undefined,
      createdAt: row["created_at"] as number,
      completedAt: (row["completed_at"] as number) ?? undefined,
      claimedAt: (row["claimed_at"] as number) ?? undefined,
      claimedBy: (row["claimed_by"] as string) ?? undefined,
      leaseExpiresAt: (row["lease_expires_at"] as number) ?? undefined,
      attempts: (row["attempts"] as number) ?? 0,
    };
  }
}
