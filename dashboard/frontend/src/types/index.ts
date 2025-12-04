export interface Project {
  id: string;
  name: string;
  path: string;
  description?: string;
  project_overview?: string;
  initial_prompt?: string;
  plan?: string;
  max_agents: number;
  active: boolean;
  created_at: string;
  updated_at: string;
  git_remote?: string;
  is_git_repo?: boolean;
}

export interface Task {
  id: string;
  task_id?: number;
  title: string;
  description?: string;
  prompt?: string;
  status: TaskStatus;
  branch: string;
  session?: string;
  dependencies?: string[];
  priority?: number;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  merged_at?: string;
}

export enum TaskStatus {
  UNCLAIMED = "unclaimed",
  UP_NEXT = "up_next",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  MERGED = "merged",
}

export interface Agent {
  id: string;
  session_name: string;
  task_id: string;
  task_title: string;
  branch: string;
  status: string;
  progress: number;
  started_at: string;
  logs: string[];
}

export interface ProjectStats {
  total_tasks: number;
  unclaimed_tasks: number;
  up_next_tasks: number;
  in_progress_tasks: number;
  completed_tasks: number;
  merged_tasks: number;
  active_agents: number;
  total_agents_run: number;
}

export interface OrchestratorConfig {
  max_concurrent_agents: number;
  auto_merge: boolean;
  merge_strategy: string;
  auto_spawn_interval: number;
  enabled: boolean;
  api_provider: string;  // API provider: "anthropic", "openai", "azure", etc.
  api_key?: string;  // Generic API key for plan generation
  api_model: string;  // Model to use for generation
  api_base_url?: string;  // Base URL for API endpoint (for custom/self-hosted providers)
  api_version?: string;  // API version (for providers that require it)
}

export interface WebSocketMessage {
  type: string;
  project_id?: string;
  data: any;
  timestamp: string;
}
