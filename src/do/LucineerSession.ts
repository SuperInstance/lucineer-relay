import { DurableObject } from "cloudflare:workers";
import type {
  IncomingMessage,
  Job,
  JobResult,
  WorldSnapshot,
  MessageHistoryEntry,
  BuildCommand,
} from "../types";

/** Lease duration: a claimed job is considered stale after 5 minutes. */
const CLAIM_LEASE_MS = 5 * 60 * 1000;
/** Max claim attempts before a job is permanently errored. */
const MAX_ATTEMPTS = 3;
/** Rate limit: max messages per session per window. */
const RATE_LIMIT_MAX = 10;
/** Rate limit window in ms (1 minute). */
const RATE_LIMIT_WINDOW_MS = 60 * 1000;

interface StoredMessageHistory {
  entries: MessageHistoryEntry[];
}

export class LucineerSession extends DurableObject {
  constructor(ctx: DurableObjectState, env: unknown) {
    super(ctx, env as never);
    // Initialize SQLite schema with claimed_at and attempts columns
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
      CREATE INDEX IF NOT EXISTS idx_history_session ON message_history(session_id);
    `);

    // Migrate existing tables: add claimed_at and attempts if missing
    try {
      this.migrateSchema();
    } catch (e) {
      console.error("Migration failed:", e);
    }

    // Create indexes on migrated columns AFTER migration ensures columns exist
    try {
      this.ctx.storage.sql.exec(
        `CREATE INDEX IF NOT EXISTS idx_jobs_claimed ON jobs(claimed_at)`
      );
    } catch { /* index may already exist */ }
  }

  /**
   * Add columns to pre-existing tables without dropping data.
   * SQLite's ALTER TABLE ADD COLUMN is idempotent-safe with this pattern.
   */
  private migrateSchema(): void {
    try {
      this.ctx.storage.sql.exec(`ALTER TABLE jobs ADD COLUMN claimed_at INTEGER`);
    } catch { /* column already exists */ }
    try {
      this.ctx.storage.sql.exec(`ALTER TABLE jobs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0`);
    } catch { /* column already exists */ }

    // Migrate old 'processing' status to 'pending' so the new claiming flow picks them up
    this.ctx.storage.sql.exec(
      `UPDATE jobs SET status = 'pending' WHERE status = 'processing'`,
    );
  }

  // Diagnostic — return schema info
  async diag(): Promise<Record<string, unknown>> {
    try {
      const cursor = this.ctx.storage.sql.exec("PRAGMA table_info(jobs)");
      const cols = cursor.toArray().map((r: Record<string, unknown>) => r["name"]);
      const countCursor = this.ctx.storage.sql.exec("SELECT COUNT(*) as n FROM jobs");
      const count = countCursor.toArray()[0] as Record<string, unknown>;
      return { columns: cols, totalJobs: count["n"], status: "ok" };
    } catch (e) {
      return { error: String(e), status: "fail" };
    }
  }

  // Generate a random job ID
  private generateJobId(): string {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return Array.from(bytes)
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
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

    // Count recent jobs from this session
    const cursor = this.ctx.storage.sql.exec<{ count: number }>(
      `SELECT COUNT(*) as count FROM jobs WHERE session_id = ? AND created_at > ?`,
      sessionId,
      windowStart,
    );
    const row = cursor.toArray()[0];
    const count = row?.count ?? 0;

    return count < RATE_LIMIT_MAX;
  }

  // ---------------------------------------------------------------------------
  // Job lifecycle
  // ---------------------------------------------------------------------------

  async createJob(msg: IncomingMessage): Promise<{ jobId: string }> {
    const jobId = this.generateJobId();
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
    const cursor = this.ctx.storage.sql.exec<Record<string, unknown>>(
      `SELECT * FROM jobs WHERE id = ?`,
      jobId,
    );
    const row = cursor.toArray()[0];
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
  // Job claiming — FIX #6
  // ---------------------------------------------------------------------------

  /**
   * Atomically claim a job for processing.
   * Sets claimed_at = NOW() only if claimed_at is NULL or older than the lease period.
   * Returns the claimed job, or null if the job was already claimed by another processor.
   *
   * This prevents the race condition where two processors both grab the same job.
   */
  async claimJob(jobId: string): Promise<Job | null> {
    const now = Date.now();
    const leaseExpired = now - CLAIM_LEASE_MS;

    // Atomic conditional update: only claim if unclaimed or lease expired
    // and the job hasn't exceeded max attempts
    const cursor = this.ctx.storage.sql.exec<{ changes: number }>(
      `UPDATE jobs
       SET claimed_at = ?,
           attempts = attempts + 1
       WHERE id = ?
         AND status = 'pending'
         AND (claimed_at IS NULL OR claimed_at < ?)`,
      now,
      jobId,
      leaseExpired,
    );

    // In Durable Object SQLite, we check if the update affected any rows
    // by re-querying the job
    const job = await this.getJob(jobId);
    if (!job) return null;

    // Verify we actually claimed it (claimed_at should be close to now)
    if (job.claimedAt && Math.abs(job.claimedAt - now) < 1000) {
      // We claimed it. Check if it's now past max attempts.
      if ((job.attempts ?? 0) >= MAX_ATTEMPTS) {
        await this.setJobError(jobId, `Max attempts (${MAX_ATTEMPTS}) exceeded`);
        return null;
      }
      return job;
    }

    // Someone else claimed it first
    return null;
  }

  /**
   * Mark jobs as errored if they've been claimed but never completed
   * and their lease has expired beyond recovery.
   * Returns the number of stale jobs cleaned up.
   */
  async cleanupStaleJobs(): Promise<number> {
    const now = Date.now();
    const leaseExpired = now - CLAIM_LEASE_MS;

    // Find jobs that have been claimed but the lease has expired and they're still pending
    // (meaning a processor crashed mid-work)
    const staleCursor = this.ctx.storage.sql.exec<{ id: string; attempts: number }>(
      `SELECT id, attempts FROM jobs
       WHERE status = 'pending'
         AND claimed_at IS NOT NULL
         AND claimed_at < ?`,
      leaseExpired,
    );
    const staleJobs = staleCursor.toArray();

    let cleaned = 0;

    for (const stale of staleJobs) {
      if (stale.attempts >= MAX_ATTEMPTS) {
        // Permanently fail this job
        this.ctx.storage.sql.exec(
          `UPDATE jobs SET status = 'error',
               error = 'Job timed out after max attempts (' || ? || ') and lease expired',
               completed_at = ?
           WHERE id = ?`,
          MAX_ATTEMPTS,
          now,
          stale.id,
        );
        cleaned++;
      }
      // Jobs that haven't hit max attempts stay 'pending' with their claimed_at
      // so they can be re-claimed by another processor (reset claimed_at to null
      // so claimJob picks them up again)
    }

    // Reset claimed_at for jobs within retry limit so they can be re-claimed
    this.ctx.storage.sql.exec(
      `UPDATE jobs SET claimed_at = NULL
       WHERE status = 'pending'
         AND claimed_at IS NOT NULL
         AND claimed_at < ?`,
      leaseExpired,
    );

    return cleaned;
  }

  // ---------------------------------------------------------------------------
  // Pending jobs — now with cleanup + claim-aware filtering
  // ---------------------------------------------------------------------------

  /**
   * Returns jobs that are available for processing.
   * Calls cleanupStaleJobs() first, then returns jobs where:
   *   - status = 'pending'
   *   - claimed_at IS NULL (not currently being worked on)
   *
   * Processors should call claimJob(jobId) immediately after selecting a job
   * from this list to prevent race conditions with other processors.
   */
  async getPendingJobs(): Promise<Job[]> {
    // Clean up stale jobs first
    await this.cleanupStaleJobs();

    const cursor = this.ctx.storage.sql.exec<Record<string, unknown>>(
      `SELECT * FROM jobs
       WHERE status = 'pending'
         AND claimed_at IS NULL
       ORDER BY created_at ASC
       LIMIT 10`,
    );
    const rows = cursor.toArray();
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
    const cursor = this.ctx.storage.sql.exec<Record<string, unknown>>(
      `SELECT snapshot FROM world_state WHERE session_id = ?`,
      sessionId,
    );
    const row = cursor.toArray()[0];
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
    const cursor = this.ctx.storage.sql.exec<MessageHistoryEntry>(
      `SELECT job_id, session_id, player_name, message, reply, timestamp
       FROM message_history
       WHERE session_id = ?
       ORDER BY timestamp DESC
       LIMIT ?`,
      sessionId,
      limit,
    );
    return cursor.toArray();
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  private rowToJob(row: Record<string, unknown>): Job {
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
      attempts: (row["attempts"] as number) ?? 0,
    };
  }
}
