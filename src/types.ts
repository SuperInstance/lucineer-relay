// Type definitions for Lucineer Relay Worker
// Updated: 2026-08-02 — Fixes #3, #5, #6: split auth, job claiming, filtering signal

export interface Env {
  LUCINEER_SESSION: DurableObjectNamespace;
  /** Processor-facing key for /api/jobs/pending, /api/job/:id/result, /api/state endpoints. */
  LUCINEER_INTERNAL_KEY: string;
  /** Legacy key — still accepted on internal endpoints during transition. */
  LUCINEER_KEY?: string;
  OPENCLAW_CALLBACK_URL?: string;
}

// --- Request payloads ---

export interface IncomingMessage {
  sessionId: string;
  playerName: string;
  message: string;
  playerState?: PlayerState;
  worldSnapshot?: WorldSnapshot;
}

export interface PlayerState {
  position?: { x: number; y: number; z: number };
  health?: number;
  inventory?: string[];
  [key: string]: unknown;
}

export interface WorldSnapshot {
  objects?: WorldObject[];
  timestamp?: number;
  [key: string]: unknown;
}

export interface WorldObject {
  id: string;
  type: string;
  position: { x: number; y: number; z: number };
  properties?: Record<string, unknown>;
}

export interface JobResult {
  reply: string;
  commands: BuildCommand[];
  files?: RemoteFile[];
}

// --- Internal types ---

export interface BuildCommand {
  type: string;
  target: string;
  params: Record<string, unknown>;
}

export interface RemoteFile {
  name: string;
  url: string;
  description?: string;
}

export type JobStatus = "pending" | "processing" | "complete" | "error";

export interface Job {
  id: string;
  sessionId: string;
  playerName: string;
  message: string;
  status: JobStatus;
  reply?: string;
  commands?: BuildCommand[];
  files?: RemoteFile[];
  error?: string;
  createdAt: number;
  completedAt?: number;
  /** Timestamp when a processor claimed this job (ms epoch). */
  claimedAt?: number;
  /** Number of times this job has been claimed by a processor. */
  attempts?: number;
}

export interface MessageHistoryEntry {
  jobId: string;
  playerName: string;
  message: string;
  reply?: string;
  timestamp: number;
}

// --- DO RPC interfaces ---

export interface LucineerSessionRPC {
  createJob(msg: IncomingMessage): Promise<{ jobId: string }>;
  getJob(jobId: string): Promise<Job | null>;
  setJobResult(jobId: string, result: JobResult): Promise<void>;
  setJobError(jobId: string, error: string): Promise<void>;
  updateWorldState(sessionId: string, snapshot: WorldSnapshot): Promise<void>;
  getWorldState(sessionId: string): Promise<WorldSnapshot | null>;
  getPendingJobs(): Promise<Job[]>;
  claimJob(jobId: string): Promise<Job | null>;
  cleanupStaleJobs(): Promise<number>;
  getMessageHistory(sessionId: string, limit?: number): Promise<MessageHistoryEntry[]>;
  /** Check rate limit for a session: returns true if within allowed burst. */
  checkRateLimit(sessionId: string): Promise<boolean>;
}
