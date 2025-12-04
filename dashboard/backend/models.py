"""
Data models for SplitMind Dashboard
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enumeration"""
    UNCLAIMED = "unclaimed"
    UP_NEXT = "up_next"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MERGED = "merged"


class Task(BaseModel):
    """Task model"""
    id: str
    task_id: Optional[int] = None  # Auto-incrementing task ID per project
    title: str
    description: Optional[str] = None
    prompt: Optional[str] = None  # Custom agent prompt for this task
    status: TaskStatus = TaskStatus.UNCLAIMED
    branch: str
    session: Optional[str] = None
    # List of task IDs that must be completed first
    dependencies: List[str] = []
    # Higher priority tasks are assigned first (0 = normal, 1+ = higher)
    priority: int = 0
    owned_files: List[str] = []  # Files exclusively owned by this task
    shared_files: List[str] = []  # Files that may be modified (with care)
    creates_files: List[str] = []  # New files this task will create
    merge_order: int = 0  # Explicit merge sequence order
    exclusive_files: List[str] = []  # Files only this task should modify
    # Files that might be modified (requires coordination)
    shared_files: List[str] = []
    # Tasks whose output is needed for setup
    initialization_deps: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    merged_at: Optional[datetime] = None


class Agent(BaseModel):
    """AI Agent model"""
    id: str
    session_name: str
    task_id: str
    task_title: str
    branch: str
    status: str = "running"  # "running", "completed", "failed"
    progress: int = 0
    started_at: datetime = Field(default_factory=datetime.now)
    logs: List[str] = []
    last_activity: Optional[datetime] = None
    output_preview: Optional[str] = None


class Project(BaseModel):
    """Project model"""
    id: str
    name: str
    path: str
    description: Optional[str] = None
    project_overview: Optional[str] = None  # Detailed project description
    # Initial prompt for plan generation
    initial_prompt: Optional[str] = None
    plan: Optional[str] = None              # Generated project plan
    max_agents: int = 5
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    git_remote: Optional[str] = None
    # Whether the project path is a Git repository
    is_git_repo: Optional[bool] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProjectStats(BaseModel):
    """Project statistics"""
    total_tasks: int = 0
    unclaimed_tasks: int = 0
    up_next_tasks: int = 0
    in_progress_tasks: int = 0
    completed_tasks: int = 0
    merged_tasks: int = 0
    active_agents: int = 0
    total_agents_run: int = 0


class OrchestratorConfig(BaseModel):
    """Orchestrator configuration"""
    max_concurrent_agents: int = 5
    auto_merge: bool = False
    merge_strategy: str = "merge"  # merge, squash, ff
    auto_spawn_interval: int = 60  # seconds
    enabled: bool = False
    # API provider: "anthropic", "openai", "azure", etc.
    api_provider: str = "anthropic"
    api_key: Optional[str] = None  # Generic API key for plan generation
    api_model: str = "claude-sonnet-4-20250514"  # Model to use for generation
    # Base URL for API endpoint (for custom/self-hosted providers)
    api_base_url: Optional[str] = None
    # API version (for providers that require it)
    api_version: Optional[str] = None


class PlanGenerationRequest(BaseModel):
    """Request model for plan generation"""
    project_overview: str
    initial_prompt: str


class PlanGenerationResponse(BaseModel):
    """Response model for plan generation"""
    plan: str
    # List of task titles and descriptions
    suggested_tasks: List[Dict[str, str]]


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str  # task_update, agent_update, log, notification
    project_id: Optional[str] = None
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
