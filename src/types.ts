// Type definitions for Lucineer Relay Worker
// Phase 1 Day 1-3: shared-secret auth, job claiming, R2 trajectory writer

export interface Env {
  /** Durable Object namespace for session-scoped job/state storage.
   *  Typed to LucineerSession so RPC calls are checked at compile time.
   */
  LUCINEER_SESSION: DurableObjectNamespace<import("./do/LucineerSession").LucineerSession>;
  /** Processor-facing key for /api/jobs/pending, /api/job/:id/result, /api/state, etc. */
  LUCINEER_INTERNAL_KEY: string;
  /** Legacy key — still accepted on internal endpoints during transition. */
  LUCINEER_KEY?: string;
  /** Shared secret for inter-service auth (memory/vector ↔ relay). */
  LUCINEER_SHARED_SECRET?: string;
  /** R2 bucket for MOLT trajectory logs. */
  LUCINEER_TRAJECTORIES: R2Bucket;
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

// --- MOLT Trajectory types ---

/**
 * A single event in a MOLT trajectory.
 * Trajectories capture the full deep-path of a build job:
 * perception context, casting decisions, pipeline stages,
 * sandbox results, and final outcomes.
 */
export interface TrajectoryEvent {
  /** Event type: pipeline stage, perception, decision, etc. */
  type: string;
  /** Timestamp (ms epoch) */
  timestamp: number;
  /** Job ID this event belongs to */
  jobId?: string;
  /** Pipeline stage: intent, plan, sandbox, code, voice, safety */
  stage?: string;
  /** Model used for this event */
  model?: string;
  /** Channel (SWMIDI channel map) */
  channel?: number;
  /** The actual content — prompt, response, decision, etc. */
  data?: Record<string, unknown>;
  /** Error mask bits (Layer 1 FLUX constraint engine) */
  errorMask?: number;
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

export type JobStatus = "pending" | "claimed" | "complete" | "error";

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
  /** ID of the worker that claimed this job. */
  claimedBy?: string;
  /** Lease expiry timestamp (ms epoch). When this passes, the job can be reclaimed. */
  leaseExpiresAt?: number;
  /** Number of times this job has been claimed by a processor. */
  attempts?: number;
}

export interface MessageHistoryEntry {
  jobId: string;
  sessionId: string;
  playerName: string;
  message: string;
  reply?: string;
  timestamp: number;
}

// --- DO RPC interface ---

export interface LucineerSessionRPC {
  createJob(msg: IncomingMessage): Promise<{ jobId: string }>;
  getJob(jobId: string): Promise<Job | null>;
  setJobResult(jobId: string, result: JobResult): Promise<void>;
  setJobError(jobId: string, error: string): Promise<void>;
  updateWorldState(sessionId: string, snapshot: WorldSnapshot): Promise<void>;
  getWorldState(sessionId: string): Promise<WorldSnapshot | null>;
  getPendingJobs(): Promise<Job[]>;
  claimPendingJobs(workerId: string, limit?: number): Promise<Job[]>;
  claimJob(jobId: string): Promise<Job | null>;
  cleanupStaleJobs(): Promise<number>;
  getMessageHistory(sessionId: string, limit?: number): Promise<MessageHistoryEntry[]>;
  /** Check rate limit for a session: returns true if within allowed burst. */
  checkRateLimit(sessionId: string): Promise<boolean>;
  /** Diagnostic dump of this DO's jobs table schema/job count. */
  diag(): Promise<Record<string, unknown>>;
  /** Register a session as active so batch claim can fan out to it. */
  registerSession(sessionId: string): Promise<void>;
  /** Return recently-active session IDs stored in this DO's registry. */
  getActiveSessions(): Promise<string[]>;
  /** Extend the lease on a claimed job. Returns the updated job or null. */
  renewLease(jobId: string, workerId?: string): Promise<Job | null>;
}
