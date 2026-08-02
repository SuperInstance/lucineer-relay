import { DurableObject } from "cloudflare:workers";
import type {
  IncomingMessage,
  Job,
  JobResult,
  WorldSnapshot,
  MessageHistoryEntry,
  BuildCommand,
} from "../types";

interface StoredMessageHistory {
  entries: MessageHistoryEntry[];
}

export class LucineerSession extends DurableObject {
  constructor(ctx: DurableObjectState, env: unknown) {
    super(ctx, env as never);
    // Initialize SQLite schema
    this.ctx.storage.sql.exec(`
      CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        player_name TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'processing',
        reply TEXT,
        commands TEXT,
        files TEXT,
        error TEXT,
        created_at INTEGER NOT NULL,
        completed_at INTEGER
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
      CREATE INDEX IF NOT EXISTS idx_history_session ON message_history(session_id);
    `);
  }

  // Generate a random job ID
  private generateJobId(): string {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    return Array.from(bytes)
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async createJob(msg: IncomingMessage): Promise<{ jobId: string }> {
    const jobId = this.generateJobId();
    const now = Date.now();

    this.ctx.storage.sql.exec(
      `INSERT INTO jobs (id, session_id, player_name, message, status, created_at)
       VALUES (?, ?, ?, ?, 'processing', ?)`,
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

    return {
      id: row["id"] as string,
      sessionId: row["session_id"] as string,
      playerName: row["player_name"] as string,
      message: row["message"] as string,
      status: row["status"] as Job["status"],
      reply: (row["reply"] as string) ?? undefined,
      commands: row["commands"] ? (JSON.parse(row["commands"] as string) as BuildCommand[]) : undefined,
      files: row["files"] ? (JSON.parse(row["files"] as string) as Job["files"]) : undefined,
      error: (row["error"] as string) ?? undefined,
      createdAt: row["created_at"] as number,
      completedAt: (row["completed_at"] as number) ?? undefined,
    };
  }

  async setJobResult(jobId: string, result: JobResult): Promise<void> {
    const now = Date.now();

    this.ctx.storage.sql.exec(
      `UPDATE jobs SET status = 'complete', reply = ?, commands = ?, files = ?, completed_at = ?
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

  async getPendingJobs(): Promise<Job[]> {
    const cursor = this.ctx.storage.sql.exec<Record<string, unknown>>(
      `SELECT * FROM jobs WHERE status = 'processing' ORDER BY created_at ASC LIMIT 10`,
    );
    const rows = cursor.toArray();
    return rows.map((row) => ({
      id: row["id"] as string,
      sessionId: row["session_id"] as string,
      playerName: row["player_name"] as string,
      message: row["message"] as string,
      status: row["status"] as Job["status"],
      reply: (row["reply"] as string) ?? undefined,
      commands: row["commands"] ? (JSON.parse(row["commands"] as string) as BuildCommand[]) : undefined,
      files: row["files"] ? (JSON.parse(row["files"] as string) as Job["files"]) : undefined,
      error: (row["error"] as string) ?? undefined,
      createdAt: row["created_at"] as number,
      completedAt: (row["completed_at"] as number) ?? undefined,
    }));
  }

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
}
