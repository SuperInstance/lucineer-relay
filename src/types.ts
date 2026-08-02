// Type definitions for Lucineer Relay Worker

export interface Env {
  LUCINEER_SESSION: DurableObjectNamespace;
  LUCINEER_KEY: string;
  OPENCLAW_CALLBACK_URL: string;
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

export type JobStatus = "processing" | "complete" | "error";

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
  getMessageHistory(sessionId: string, limit?: number): Promise<MessageHistoryEntry[]>;
}
