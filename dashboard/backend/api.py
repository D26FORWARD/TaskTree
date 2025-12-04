"""
FastAPI backend for SplitMind Dashboard
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio
import json
import os
import platform
import subprocess

from .models import (
    Project, Task, TaskStatus, Agent, ProjectStats,
    OrchestratorConfig, WebSocketMessage,
    PlanGenerationRequest, PlanGenerationResponse
)
from .config import config_manager
from .project_manager import ProjectManager
from .orchestrator import OrchestratorManager
from .websocket_manager import WebSocketManager
from .claude_integration import claude

# Import A2AMCP orchestrator
try:
    from .a2amcp_orchestrator import A2AMCPOrchestrator, is_a2amcp_available
    a2amcp_available = True
except ImportError:
    a2amcp_available = False
    def is_a2amcp_available(): return False

# WebSocket manager
ws_manager = WebSocketManager()

# Orchestrator manager - use A2AMCP version if available
if a2amcp_available and is_a2amcp_available():
    print("🤝 Using A2AMCP-enhanced orchestrator for agent coordination")
    orchestrator = A2AMCPOrchestrator(ws_manager)
else:
    if a2amcp_available:
        print(
            "⚠️  A2AMCP SDK available but server not running. Using standard orchestrator.")
    else:
        print("📦 A2AMCP SDK not installed. Using standard orchestrator.")
    orchestrator = OrchestratorManager(ws_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    print("🚀 SplitMind Dashboard API started")
    yield
    # Shutdown
    try:
        await orchestrator.stop()
        # Close all websocket connections
        for conn in list(ws_manager.active_connections):
            try:
                await conn.close()
            except:
                pass
        ws_manager.active_connections.clear()
    except Exception:
        pass
    print("👋 SplitMind Dashboard API stopped")

# Create FastAPI app with lifespan management
app = FastAPI(
    title="SplitMind Command Center",
    description="AI Coder Orchestration Dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Project Management Endpoints
# ============================================================================

@app.get("/api/projects", response_model=List[Project])
async def get_projects():
    """Get all projects"""
    return config_manager.get_projects()


@app.post("/api/projects", response_model=Project)
async def create_project(project_data: dict):
    """Create a new project"""
    try:
        # Create a Project instance with defaults for missing fields
        from datetime import datetime

        # Ensure required fields are present
        required_fields = ['id', 'name', 'path']
        for field in required_fields:
            if field not in project_data:
                raise HTTPException(
                    status_code=400, detail=f"Missing required field: {field}")

        # Add defaults for optional fields
        project_data.setdefault('created_at', datetime.now())
        project_data.setdefault('updated_at', datetime.now())
        project_data.setdefault('active', True)
        project_data.setdefault('max_agents', 5)

        # Create Project instance
        project = Project(**project_data)
        new_project = config_manager.add_project(project)

        # Notify via WebSocket
        await ws_manager.broadcast(WebSocketMessage(
            type="project_created",
            project_id=new_project.id,
            data=new_project.dict()
        ))

        return new_project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """Get a specific project"""
    project = config_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.put("/api/projects/{project_id}", response_model=Project)
async def update_project(project_id: str, updates: dict):
    """Update a project"""
    try:
        updated_project = config_manager.update_project(project_id, updates)

        # Notify via WebSocket
        await ws_manager.broadcast(WebSocketMessage(
            type="project_updated",
            project_id=updated_project.id,
            data=updated_project.dict()
        ))

        return updated_project
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, cleanup_files: bool = False):
    """Delete a project with optional complete cleanup"""
    try:
        # Get project info before deletion
        project = config_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Stop orchestrator if running for this project
        if orchestrator.current_project_id == project_id:
            await orchestrator.stop()

        if cleanup_files:
            # Perform complete cleanup like reset endpoint but more thorough
            pm = ProjectManager(project_id)

            # Kill all tmux sessions for this project
            result = subprocess.run(
                ["tmux", "ls"], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if project_id in line:
                        session_name = line.split(':')[0]
                        subprocess.run(
                            ["tmux", "kill-session", "-t", session_name])

            # Remove all worktrees
            worktrees_dir = Path(pm.project_path) / "worktrees"
            if worktrees_dir.exists():
                # First, remove git worktrees properly
                result = subprocess.run(
                    ["git", "worktree", "list"],
                    cwd=pm.project_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    # Skip main worktree
                    for line in result.stdout.strip().split('\n')[1:]:
                        if line:
                            worktree_path = line.split()[0]
                            subprocess.run(
                                ["git", "worktree", "remove",
                                    worktree_path, "--force"],
                                cwd=pm.project_path,
                                capture_output=True
                            )

                # Then remove the directory
                import shutil
                shutil.rmtree(worktrees_dir, ignore_errors=True)

            # Clean up git branches (except main/master)
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=pm.project_path,
                capture_output=True
            )
            result = subprocess.run(
                ["git", "branch"],
                cwd=pm.project_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    branch = line.strip().replace('* ', '')
                    if branch not in ['main', 'master'] and not branch.startswith('('):
                        subprocess.run(
                            ["git", "branch", "-D", branch],
                            cwd=pm.project_path,
                            capture_output=True
                        )

            # Remove .splitmind directory completely
            splitmind_dir = Path(pm.project_path) / ".splitmind"
            if splitmind_dir.exists():
                import shutil
                shutil.rmtree(splitmind_dir, ignore_errors=True)

            # Clean up status files
            status_dir = Path("/tmp/splitmind-status")
            if status_dir.exists():
                for status_file in status_dir.glob(f"*{project_id}*.status"):
                    status_file.unlink()

        # Remove project from configuration
        config_manager.delete_project(project_id)

        # Notify via WebSocket
        await ws_manager.broadcast(WebSocketMessage(
            type="project_deleted",
            project_id=project_id,
            data={
                "project_id": project_id,
                "cleanup_performed": cleanup_files
            }
        ))

        cleanup_message = " with complete cleanup" if cleanup_files else ""
        return {"message": f"Project deleted{cleanup_message}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/projects/{project_id}/reset")
async def reset_project(project_id: str):
    """Reset a project - removes all tasks, worktrees, and tmux sessions"""
    try:
        pm = ProjectManager(project_id)

        # Stop orchestrator if running
        if orchestrator.current_project_id == project_id:
            await orchestrator.stop()

        # Kill all tmux sessions for this project
        import subprocess
        result = subprocess.run(["tmux", "ls"], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if project_id in line:
                    session_name = line.split(':')[0]
                    subprocess.run(
                        ["tmux", "kill-session", "-t", session_name])

        # Remove all worktrees
        worktrees_dir = Path(pm.project_path) / "worktrees"
        if worktrees_dir.exists():
            # First, remove git worktrees properly
            result = subprocess.run(
                ["git", "worktree", "list"],
                cwd=pm.project_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Skip main worktree
                for line in result.stdout.strip().split('\n')[1:]:
                    if line:
                        worktree_path = line.split()[0]
                        subprocess.run(
                            ["git", "worktree", "remove",
                                worktree_path, "--force"],
                            cwd=pm.project_path,
                            capture_output=True
                        )

            # Then remove the directory
            import shutil
            shutil.rmtree(worktrees_dir, ignore_errors=True)

        # Clean up git branches (except main/master)
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=pm.project_path,
            capture_output=True
        )
        result = subprocess.run(
            ["git", "branch"],
            cwd=pm.project_path,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                branch = line.strip().replace('* ', '')
                if branch not in ['main', 'master']:
                    subprocess.run(
                        ["git", "branch", "-D", branch],
                        cwd=pm.project_path,
                        capture_output=True
                    )

        # Remove tasks.md
        tasks_file = Path(pm.project_path) / ".splitmind" / "tasks.md"
        if tasks_file.exists():
            tasks_file.unlink()

        # Clean up status files
        status_dir = Path("/tmp/splitmind-status")
        if status_dir.exists():
            for status_file in status_dir.glob(f"*{project_id}*.status"):
                status_file.unlink()

        # Notify via WebSocket
        await ws_manager.broadcast(WebSocketMessage(
            type="project_reset",
            project_id=project_id,
            data={"message": "Project reset successfully"}
        ))

        return {"message": "Project reset successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset project: {str(e)}")


@app.get("/api/projects/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(project_id: str):
    """Get project statistics"""
    try:
        pm = ProjectManager(project_id)
        return pm.get_stats()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Task Management Endpoints
# ============================================================================

@app.get("/api/projects/{project_id}/tasks", response_model=List[Task])
async def get_tasks(project_id: str):
    """Get all tasks for a project"""
    try:
        pm = ProjectManager(project_id)
        return pm.get_tasks()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/projects/{project_id}/tasks", response_model=Task)
async def create_task(project_id: str, title: str, description: Optional[str] = None,
                      prompt: Optional[str] = None, priority: int = 0,
                      dependencies: Optional[List[str]] = None):
    """Create a new task"""
    try:
        pm = ProjectManager(project_id)
        task = pm.add_task(title, description, dependencies, priority, prompt)

        # Notify via WebSocket
        await ws_manager.broadcast(WebSocketMessage(
            type="task_created",
            project_id=project_id,
            data=task.dict()
        ))

        return task
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/api/projects/{project_id}/tasks/{task_id}", response_model=Task)
async def update_task(project_id: str, task_id: str, updates: dict):
    """Update a task"""
    print(
        f"🔧 Update task request: project_id={project_id}, task_id={task_id}, updates={updates}")
    try:
        pm = ProjectManager(project_id)
        task = pm.update_task(task_id, updates)

        # Notify via WebSocket
        await ws_manager.broadcast(WebSocketMessage(
            type="task_updated",
            project_id=project_id,
            data=task.dict()
        ))

        print(f"✅ Task updated successfully: {task.title}")
        return task
    except ValueError as e:
        print(f"❌ Task update failed: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ Unexpected error updating task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_id}/tasks/{task_id}")
async def delete_task(project_id: str, task_id: str):
    """Delete a task"""
    try:
        pm = ProjectManager(project_id)
        pm.delete_task(task_id)

        # Notify via WebSocket
        await ws_manager.broadcast(WebSocketMessage(
            type="task_deleted",
            project_id=project_id,
            data={"task_id": task_id}
        ))

        return {"message": "Task deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/projects/{project_id}/tasks/{task_id}/merge")
async def merge_task(project_id: str, task_id: str, force: bool = False):
    """Manually merge a completed task"""
    try:
        pm = ProjectManager(project_id)
        task = next((t for t in pm.get_tasks() if t.id == task_id), None)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.status != TaskStatus.COMPLETED and not force:
            raise HTTPException(
                status_code=400, detail="Task must be completed to merge")

        # Use the existing merge script
        import subprocess
        from pathlib import Path
        from datetime import datetime

        # Simple direct merge approach
        try:
            # Ensure we're on main branch
            checkout_main = subprocess.run(
                ["git", "checkout", "main"],
                cwd=str(pm.project_path),
                capture_output=True,
                text=True
            )

            if checkout_main.returncode != 0:
                raise Exception(
                    f"Failed to checkout main: {checkout_main.stderr}")

            # Pull latest main
            pull_result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=str(pm.project_path),
                capture_output=True,
                text=True
            )

            # Check if the branch exists locally
            branch_check = subprocess.run(
                ["git", "rev-parse", "--verify", task.branch],
                cwd=str(pm.project_path),
                capture_output=True,
                text=True
            )

            if branch_check.returncode != 0:
                # Branch doesn't exist, check in worktree
                worktree_path = pm.project_path / "worktrees" / task.branch
                if worktree_path.exists():
                    # Push the branch from worktree to main repo
                    push_result = subprocess.run(
                        ["git", "push", "origin", f"HEAD:{task.branch}"],
                        cwd=str(worktree_path),
                        capture_output=True,
                        text=True
                    )

                    if push_result.returncode != 0:
                        raise Exception(
                            f"Failed to push branch from worktree: {push_result.stderr}")

                    # Fetch the branch in main repo
                    fetch_result = subprocess.run(
                        ["git", "fetch", "origin", task.branch],
                        cwd=str(pm.project_path),
                        capture_output=True,
                        text=True
                    )
                else:
                    raise Exception(
                        f"Branch {task.branch} not found locally or in worktrees")

            # Now merge the branch
            merge_result = subprocess.run(
                ["git", "merge", task.branch, "--no-ff",
                    "-m", f"Merge task: {task.title}"],
                cwd=str(pm.project_path),
                capture_output=True,
                text=True
            )

            if merge_result.returncode == 0:
                result = merge_result
            else:
                raise Exception(f"Merge failed: {merge_result.stderr}")

        except Exception as e:
            # If direct merge fails, fall back to the auto-merge script
            result = subprocess.run([
                "python",
                str(Path(__file__).parent.parent.parent /
                    "scripts" / "auto-merge.py"),
                task.branch,
                "--strategy", "merge",
                "--json"
            ], cwd=str(pm.project_path), capture_output=True, text=True)

        if result.returncode == 0:
            # Update task status to merged
            pm.update_task(task.id, {
                "status": TaskStatus.MERGED,
                "merged_at": datetime.now()
            })

            # Notify via WebSocket
            await ws_manager.broadcast(WebSocketMessage(
                type="task_merged",
                project_id=project_id,
                data={
                    "task_id": task.id,
                    "branch": task.branch
                }
            ))

            return {"message": f"Task '{task.title}' merged successfully"}
        else:
            error_detail = result.stderr if result.stderr else result.stdout
            if not error_detail:
                error_detail = f"Unknown error (return code: {result.returncode})"
            raise HTTPException(
                status_code=500, detail=f"Merge failed: {error_detail}")

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Merge error details: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Merge error: {str(e)}")


# ============================================================================
# Agent Management Endpoints
# ============================================================================

@app.get("/api/projects/{project_id}/agents", response_model=List[Agent])
async def get_agents(project_id: str):
    """Get running agents for a project"""
    try:
        pm = ProjectManager(project_id)
        return pm.get_agents()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/projects/{project_id}/agents/{agent_id}/launch-iterm")
async def launch_iterm(project_id: str, agent_id: str):
    """Launch iTerm for a specific agent session"""
    try:
        import subprocess

        # The agent_id is the actual tmux session name (might be truncated)
        # AppleScript to open iTerm and attach to tmux session
        applescript = f'''
        tell application "iTerm"
            create window with default profile
            tell current session of current window
                write text "tmux attach -t {agent_id}"
            end tell
        end tell
        '''

        subprocess.run(['osascript', '-e', applescript])

        return {"message": f"Launched iTerm for session {agent_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_id}/agents/monitor")
async def launch_agent_monitor(project_id: str):
    """Launch tmux session with split panes showing all active agents"""
    try:
        import subprocess
        from pathlib import Path

        # Get the tmux viewer script path
        viewer_script = Path(__file__).parent / "tmux_viewer.py"

        # Check if any agents are running
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0 or not result.stdout:
            raise HTTPException(
                status_code=404, detail="No active agent sessions found")

        # Filter for this project's sessions
        sessions = [s for s in result.stdout.strip().split(
            '\n') if s.endswith(f"-{project_id}")]

        if not sessions:
            raise HTTPException(
                status_code=404, detail=f"No active sessions for project {project_id}")

        # Launch in iTerm
        applescript = f'''
        tell application "iTerm"
            activate
            
            -- Create new window
            create window with default profile
            
            tell current session of current window
                write text "cd {Path.cwd()}"
                write text "python {viewer_script} {project_id}"
            end tell
        end tell
        '''

        subprocess.run(["osascript", "-e", applescript])

        return {
            "message": f"Launched tmux monitor for {len(sessions)} active agents",
            "sessions": sessions
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_id}/reset-agent-tasks")
async def reset_agent_tasks(project_id: str):
    """Reset all claimed/in-progress tasks and kill their tmux sessions"""
    try:
        pm = ProjectManager(project_id)
        tasks = pm.get_tasks()
        agents = pm.get_agents()

        reset_count = 0
        killed_sessions = []

        # Kill all tmux sessions for this project
        for agent in agents:
            try:
                subprocess.run(
                    ["tmux", "kill-session", "-t", agent.session_name],
                    capture_output=True,
                    text=True
                )
                killed_sessions.append(agent.session_name)
            except:
                pass

        # Reset ALL tasks to unclaimed (except merged ones)
        for task in tasks:
            if task.status != TaskStatus.MERGED:
                pm.update_task(task.id, {
                    "status": TaskStatus.UNCLAIMED,
                    "session": None
                })
                reset_count += 1

        # Notify via WebSocket
        await ws_manager.broadcast(WebSocketMessage(
            type="tasks_reset",
            project_id=project_id,
            data={
                "reset_count": reset_count,
                "killed_sessions": killed_sessions
            }
        ))

        return {
            "success": True,
            "reset_count": reset_count,
            "killed_sessions": killed_sessions,
            "message": f"Reset {reset_count} tasks and killed {len(killed_sessions)} sessions"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Orchestrator Control Endpoints
# ============================================================================

@app.get("/api/orchestrator/config", response_model=OrchestratorConfig)
async def get_orchestrator_config():
    """Get orchestrator configuration"""
    return config_manager.get_orchestrator_config()


@app.put("/api/orchestrator/config", response_model=OrchestratorConfig)
async def update_orchestrator_config(config: OrchestratorConfig):
    """Update orchestrator configuration"""
    config_manager.update_orchestrator_config(config)
    orchestrator.update_config(config)
    return config


@app.post("/api/orchestrator/start")
async def start_orchestrator(project_id: str):
    """Start the orchestrator for a project"""
    try:
        await orchestrator.start(project_id)
        return {"message": "Orchestrator started"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/orchestrator/stop")
async def stop_orchestrator():
    """Stop the orchestrator"""
    await orchestrator.stop()
    return {"message": "Orchestrator stopped"}


@app.get("/api/orchestrator/status")
async def get_orchestrator_status():
    """Get orchestrator status"""
    return {
        "running": orchestrator.is_running(),
        "current_project": orchestrator.current_project_id
    }


@app.post("/api/orchestrator/check-tasks")
async def check_orchestrator_tasks():
    """Manually trigger task status check"""
    if orchestrator.current_project_id:
        await orchestrator._check_agent_status()
        return {"message": "Task check completed"}
    else:
        raise HTTPException(status_code=400, detail="No active project")


@app.get("/api/projects/{project_id}/coordination-stats")
async def get_coordination_stats(project_id: str):
    """Get A2AMCP coordination statistics for a project"""
    if hasattr(orchestrator, 'get_coordination_stats'):
        stats = await orchestrator.get_coordination_stats(project_id)
        return stats
    else:
        return {
            "enabled": False,
            "message": "A2AMCP coordination not available"
        }


# ============================================================================
# Plan Generation Endpoints
# ============================================================================

@app.post("/api/projects/{project_id}/generate-plan")
async def generate_plan(project_id: str, request: dict):
    """Generate a project plan using AI"""
    try:
        project = config_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        project_overview = request.get("project_overview", "")
        initial_prompt = request.get("initial_prompt", "")
        dart_workspace = request.get("dart_workspace", "")
        dart_dartboard = request.get("dart_dartboard", "")

        # Get orchestrator config for API key and model
        orch_config = config_manager.get_orchestrator_config()
        api_key = orch_config.api_key
        model = orch_config.api_model
        api_provider = orch_config.api_provider
        api_base_url = orch_config.api_base_url
        api_version = orch_config.api_version

        # For Aliyun, api_version stores the app_id
        app_id = api_version if api_provider == 'aliyun' else None

        # Use Claude integration to generate plan
        project_info = {
            "project_name": project.name,
            "project_path": project.path,
            "project_overview": project_overview,
            "initial_prompt": initial_prompt,
            "dart_workspace": dart_workspace,
            "dart_dartboard": dart_dartboard
        }

        # Generate plan using Generic API Client
        result = claude.generate_plan(
            project_info,
            api_key=api_key,
            model=model,
            api_provider=api_provider,
            api_base_url=api_base_url,
            api_version=api_version
        )

        # Check if generation was successful
        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to generate plan")
            )

        plan = result["plan"]
        suggested_tasks = result["suggested_tasks"]

        # Update project with overview, prompt, and plan
        updated_project = config_manager.update_project(project_id, {
            "project_overview": project_overview,
            "initial_prompt": initial_prompt,
            "plan": plan
        })

        # Create initial tasks based on the plan
        pm = ProjectManager(project_id)
        created_tasks = []

        # Create a mapping of task titles to their IDs for dependency resolution
        title_to_id = {}

        # First pass: Create all tasks without dependencies
        for task_info in suggested_tasks:
            task = pm.add_task(
                task_info["title"],
                task_info["description"],
                dependencies=[],  # Will update in second pass
                priority=task_info.get("priority", 5)
            )
            created_tasks.append(task)
            title_to_id[task_info["title"]] = task.id
            print(
                f"📝 Created task: {task_info['title']} (Priority: {task_info.get('priority', 5)})")

        # Second pass: Update dependencies by resolving task titles to IDs
        for i, task_info in enumerate(suggested_tasks):
            if task_info.get("dependencies"):
                dependency_ids = []
                for dep_title in task_info["dependencies"]:
                    if dep_title in title_to_id:
                        dependency_ids.append(title_to_id[dep_title])
                    else:
                        print(
                            f"Warning: Dependency '{dep_title}' not found for task '{task_info['title']}'")

                if dependency_ids:
                    # Update the task with resolved dependencies
                    pm.update_task(created_tasks[i].id, {
                                   "dependencies": dependency_ids})
                    print(
                        f"🔗 Updated dependencies for '{task_info['title']}': {len(dependency_ids)} dependencies")

        # Notify via WebSocket
        await ws_manager.broadcast(WebSocketMessage(
            type="plan_generated",
            project_id=project_id,
            data={
                "plan": plan,
                "tasks_created": len(created_tasks)
            }
        ))

        return {
            "plan": plan,
            "tasks_created": len(created_tasks),
            "message": "Plan generated successfully",
            "cost_info": result.get("cost_info", {}),
            "usage": result.get("usage", {})
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_id}/generate-task-breakdown")
async def generate_task_breakdown(project_id: str, request: dict):
    """Generate a structured task breakdown using Task Master AI"""
    try:
        project = config_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        project_overview = request.get("project_overview", "")
        initial_prompt = request.get("initial_prompt", "")

        # Get orchestrator config for API key and model
        orch_config = config_manager.get_orchestrator_config()
        api_key = orch_config.api_key
        model = orch_config.api_model
        api_provider = orch_config.api_provider
        api_base_url = orch_config.api_base_url
        api_version = orch_config.api_version

        # Use Claude integration to generate structured task breakdown
        project_info = {
            "project_name": project.name,
            "project_path": project.path,
            "project_overview": project_overview,
            "initial_prompt": initial_prompt
        }

        # Generate task breakdown using Generic API Client
        result = claude.generate_task_breakdown(
            project_info,
            api_key=api_key,
            model=model,
            api_provider=api_provider,
            api_base_url=api_base_url,
            api_version=api_version
        )

        # Check if generation was successful
        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to generate task breakdown")
            )

        plan = result["plan"]
        task_breakdown = result["task_breakdown"]
        suggested_tasks = result["suggested_tasks"]

        # Update project with overview, prompt, plan, and task breakdown
        updated_project = config_manager.update_project(project_id, {
            "project_overview": project_overview,
            "initial_prompt": initial_prompt,
            "plan": plan
        })

        # Create tasks from the structured breakdown
        pm = ProjectManager(project_id)
        created_tasks = []

        print(f"📋 Creating {len(suggested_tasks)} tasks from breakdown...")

        # Enhanced task creation with wave/priority information
        for i, task_info in enumerate(suggested_tasks):
            try:
                # Create custom prompt for each task based on the breakdown
                custom_prompt = f"""You are working on {project.name}.

Task Context:
{task_info["description"]}

Wave: {task_info.get("wave", 1)} | Agent Role: {task_info.get("agent", 1)}

Key Requirements:
- Follow the project's architecture and conventions
- Complete this specific task thoroughly
- Test your implementation
- Commit your changes with a clear message

This task is part of a structured development approach. Focus on delivering high-quality, production-ready code."""

                task = pm.add_task(
                    task_info["title"],
                    task_info["description"],
                    dependencies=[],  # Dependencies handled by wave structure
                    priority=task_info.get("priority", 5),
                    prompt=custom_prompt
                )

                created_tasks.append(task)
                print(
                    f"📝 Created task #{i+1}: {task.title} (ID: {task.id}, Wave: {task_info.get('wave', 1)}, Priority: {task_info.get('priority', 5)})")
            except Exception as e:
                print(
                    f"❌ Failed to create task '{task_info['title']}': {str(e)}")
                # Continue creating other tasks even if one fails
                continue

        # Notify via WebSocket
        await ws_manager.broadcast(WebSocketMessage(
            type="task_breakdown_generated",
            project_id=project_id,
            data={
                "plan": plan,
                "task_breakdown": task_breakdown,
                "tasks_created": len(created_tasks)
            }
        ))

        return {
            "plan": plan,
            "task_breakdown": task_breakdown,
            "tasks_created": len(created_tasks),
            "message": "Task breakdown generated successfully",
            "cost_info": result.get("cost_info", {}),
            "usage": result.get("usage", {})
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Git Management Endpoints
# ============================================================================

@app.get("/api/projects/{project_id}/git-status")
async def get_git_status(project_id: str):
    """Check if project path is a Git repository"""
    try:
        project = config_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        project_path = Path(project.path)
        if not project_path.exists():
            raise HTTPException(
                status_code=404, detail="Project path does not exist")

        # Check if .git directory exists
        git_dir = project_path / ".git"
        is_git_repo = git_dir.exists() and git_dir.is_dir()

        # Update project with Git status
        config_manager.update_project(project_id, {"is_git_repo": is_git_repo})

        # If it's a Git repo, get additional info
        git_info = {"is_git_repo": is_git_repo}

        if is_git_repo:
            try:
                # Get current branch
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=str(project_path),
                    capture_output=True,
                    text=True,
                    check=True
                )
                git_info["current_branch"] = result.stdout.strip()

                # Check for uncommitted changes
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=str(project_path),
                    capture_output=True,
                    text=True,
                    check=True
                )
                git_info["has_changes"] = bool(result.stdout.strip())

                # Get remote URL if exists
                try:
                    result = subprocess.run(
                        ["git", "remote", "get-url", "origin"],
                        cwd=str(project_path),
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    git_info["remote_url"] = result.stdout.strip()
                except subprocess.CalledProcessError:
                    git_info["remote_url"] = None

            except subprocess.CalledProcessError as e:
                git_info["error"] = f"Error getting Git info: {str(e)}"

        return git_info

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_id}/init-git")
async def init_git_repo(project_id: str):
    """Initialize Git repository in project path"""
    try:
        project = config_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        project_path = Path(project.path)
        if not project_path.exists():
            raise HTTPException(
                status_code=404, detail="Project path does not exist")

        # Check if already a Git repo
        git_dir = project_path / ".git"
        if git_dir.exists():
            raise HTTPException(
                status_code=400, detail="Already a Git repository")

        # Initialize Git repository
        result = subprocess.run(
            ["git", "init"],
            cwd=str(project_path),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Git: {result.stderr}"
            )

        # Update project status
        config_manager.update_project(project_id, {"is_git_repo": True})

        # Create initial .gitignore if it doesn't exist
        gitignore_path = project_path / ".gitignore"
        gitignore_created = False
        if not gitignore_path.exists():
            # Basic .gitignore content
            gitignore_content = """# Dependencies
node_modules/
venv/
env/
.env

# Build outputs
dist/
build/
*.pyc
__pycache__/

# IDE files
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Project specific
.splitmind/
worktrees/
"""
            gitignore_path.write_text(gitignore_content)
            gitignore_created = True

        # Notify via WebSocket
        await ws_manager.broadcast(WebSocketMessage(
            type="git_initialized",
            project_id=project_id,
            data={
                "project_id": project_id,
                "message": "Git repository initialized successfully"
            }
        ))

        return {
            "success": True,
            "message": "Git repository initialized successfully",
            "gitignore_created": gitignore_created
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except (WebSocketDisconnect, asyncio.CancelledError, Exception):
        ws_manager.disconnect(websocket)


# ============================================================================
# File System Endpoints
# ============================================================================

@app.get("/api/filesystem/browse")
async def browse_filesystem(path: Optional[str] = None):
    """Browse filesystem directories"""
    try:
        if not path:
            # Default to user's home directory
            path = str(Path.home())

        current_path = Path(path)

        # Security check - ensure path exists and is a directory
        if not current_path.exists():
            raise HTTPException(status_code=404, detail="Path not found")

        if not current_path.is_dir():
            # If it's a file, get its parent directory
            current_path = current_path.parent

        # Get directory contents
        directories = []
        try:
            for item in sorted(current_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    # Check if it's a git repository
                    is_git_repo = (item / '.git').exists()
                    directories.append({
                        "name": item.name,
                        "path": str(item),
                        "is_git_repo": is_git_repo
                    })
        except PermissionError:
            # Handle permission errors gracefully
            pass

        # Get parent directory (if not at root)
        parent_path = None
        if current_path != current_path.parent:
            parent_path = str(current_path.parent)

        # Common quick access paths
        quick_access = []
        home = Path.home()
        common_paths = [
            (home, "Home"),
            (home / "Desktop", "Desktop"),
            (home / "Documents", "Documents"),
            (home / "code", "Code"),
            (home / "projects", "Projects"),
            (home / "dev", "Dev"),
        ]

        for qpath, name in common_paths:
            if qpath.exists() and qpath.is_dir():
                quick_access.append({
                    "name": name,
                    "path": str(qpath)
                })

        return {
            "current_path": str(current_path),
            "parent_path": parent_path,
            "directories": directories,
            "quick_access": quick_access,
            "platform": platform.system()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/filesystem/create-folder")
async def create_folder(parent_path: str, folder_name: str):
    """Create a new folder in the filesystem"""
    try:
        if not parent_path or not folder_name:
            raise HTTPException(
                status_code=400, detail="Parent path and folder name are required")

        # Sanitize folder name
        folder_name = folder_name.strip()
        if not folder_name or '/' in folder_name or '\\' in folder_name:
            raise HTTPException(status_code=400, detail="Invalid folder name")

        parent = Path(parent_path)
        if not parent.exists() or not parent.is_dir():
            raise HTTPException(
                status_code=404, detail="Parent directory not found")

        new_folder = parent / folder_name

        # Check if folder already exists
        if new_folder.exists():
            raise HTTPException(
                status_code=409, detail="Folder already exists")

        # Create the folder
        new_folder.mkdir(parents=False, exist_ok=False)

        # Initialize as git repo if requested
        # For now, we'll just create the folder

        return {
            "success": True,
            "path": str(new_folder),
            "name": folder_name
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MCP Diagnostics Endpoints
# ============================================================================

@app.get("/api/mcp/check-cli")
async def check_claude_cli():
    """Check if Claude CLI is installed and available"""
    try:
        # Check if claude command exists
        result = subprocess.run(
            ["which", "claude"],
            capture_output=True,
            text=True
        )

        cli_installed = result.returncode == 0
        cli_path = result.stdout.strip() if cli_installed else None

        # Get version if installed
        version = None
        if cli_installed:
            try:
                version_result = subprocess.run(
                    ["claude", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if version_result.returncode == 0:
                    version = version_result.stdout.strip()
            except:
                pass

        return {
            "installed": cli_installed,
            "path": cli_path,
            "version": version
        }
    except Exception as e:
        return {
            "installed": False,
            "error": str(e)
        }


@app.get("/api/mcp/list")
async def list_mcps():
    """List installed MCP tools"""
    try:
        # Check if Claude CLI is installed first
        cli_check = await check_claude_cli()
        if not cli_check["installed"]:
            return {
                "success": False,
                "error": "Claude CLI is not installed",
                "mcps": []
            }

        # Run claude mcp list command
        result = subprocess.run(
            ["claude", "mcp", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Failed to list MCPs: {result.stderr}",
                "mcps": []
            }

        # Parse the output
        output = result.stdout.strip()
        mcps = []

        # Parse the MCP list output
        # Expected format: "name: transport command [args...]"
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('=') or 'MCP' in line:
                continue

            # Try to parse MCP info
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    details = parts[1].strip()

                    # Try to extract transport and command
                    transport = "unknown"
                    command = details

                    # Common patterns
                    if details.startswith("stdio"):
                        transport = "stdio"
                        command = details[5:].strip()
                    elif details.startswith("sse"):
                        transport = "sse"
                        command = details[3:].strip()
                    elif "npx" in details or "node" in details:
                        transport = "stdio"
                        command = details

                    mcps.append({
                        "name": name,
                        "transport": transport,
                        "command": command,
                        "global": True  # Assume global for now
                    })

        return {
            "success": True,
            "mcps": mcps,
            "raw_output": output
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out",
            "mcps": []
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "mcps": []
        }


@app.post("/api/mcp/install")
async def install_mcp(name: str, command: Optional[str] = None):
    """Install an MCP tool"""
    try:
        # Check if Claude CLI is installed first
        cli_check = await check_claude_cli()
        if not cli_check["installed"]:
            return {
                "success": False,
                "error": "Claude CLI is not installed"
            }

        # Build the install command based on the MCP name
        if name == "dart" and command:
            # Special handling for Dart with token
            cmd = ["claude", "mcp", "add-json", "dart", command]
        elif name == "browsermcp":
            cmd = ["claude", "mcp", "add-json", "browsermcp",
                   '{"command":"npx","args":["@browsermcp/mcp@latest"]}']
        elif name == "playwright":
            cmd = ["claude", "mcp", "add-json", "playwright",
                   '{"command":"npx","args":["@playwright/mcp"]}']
        elif name == "context7":
            cmd = ["claude", "mcp", "add", "--transport", "sse", "context7",
                   "https://mcp.context7.com/sse"]
        elif command:
            # Custom command provided
            cmd = ["claude", "mcp", "add-json", name, command]
        else:
            # Default to simple add
            cmd = ["claude", "mcp", "add", "-g", name]

        # Run the install command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Failed to install MCP: {result.stderr}"
            }

        return {
            "success": True,
            "message": f"Successfully installed {name} MCP",
            "output": result.stdout
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Installation timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Coordination Monitoring API
# ============================================================================

@app.get("/api/projects/{project_id}/coordination/status")
async def get_coordination_status(project_id: str):
    """Get real-time coordination status for a project"""
    try:
        from .coordination_monitor import coordination_monitor
        await coordination_monitor.initialize()
        stats = await coordination_monitor.get_project_stats(project_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}/coordination/events")
async def get_coordination_events(project_id: str, limit: int = 50):
    """Get recent coordination events for a project"""
    try:
        from .coordination_monitor import coordination_monitor
        await coordination_monitor.initialize()
        events = await coordination_monitor.detect_events(project_id)
        return {"events": events[-limit:]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/api/projects/{project_id}/coordination/live")
async def coordination_websocket(websocket: WebSocket, project_id: str):
    """WebSocket endpoint for live coordination updates"""
    await websocket.accept()

    try:
        from .coordination_monitor import coordination_monitor
        await coordination_monitor.initialize()

        # Subscribe to coordination events
        async def send_event(event):
            await websocket.send_json({
                "type": "coordination_event",
                "data": {
                    "event_type": event.event_type.value,
                    "project_id": event.project_id,
                    "agent_id": event.agent_id,
                    "timestamp": event.timestamp,
                    "data": event.data
                }
            })

        coordination_monitor.subscribe_to_events(send_event)

        # Start monitoring in background
        monitor_task = asyncio.create_task(
            coordination_monitor.monitor_project(project_id, interval=0.5)
        )

        # Send initial state
        stats = await coordination_monitor.get_project_stats(project_id)
        await websocket.send_json({
            "type": "coordination_state",
            "data": stats
        })

        # Keep connection alive and send periodic updates
        while True:
            # Send current state every 2 seconds
            stats = await coordination_monitor.get_project_stats(project_id)
            await websocket.send_json({
                "type": "coordination_update",
                "data": stats
            })
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        if 'monitor_task' in locals():
            monitor_task.cancel()
    except Exception as e:
        print(f"Coordination WebSocket error: {e}")
        if 'monitor_task' in locals():
            monitor_task.cancel()


# ============================================================================
# Static Files and Frontend
# ============================================================================

# Check if frontend is built
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    # Serve static files
    app.mount("/assets", StaticFiles(directory=frontend_path /
              "assets"), name="assets")

    # Catch-all route for React (must be last)
    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        """Serve React app"""
        # Don't intercept API routes
        if full_path.startswith("api/"):
            raise HTTPException(
                status_code=404, detail="API endpoint not found")

        file_path = frontend_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_path / "index.html")
else:
    @app.get("/")
    async def root():
        """API root when frontend is not built"""
        return {
            "message": "SplitMind API",
            "status": "Frontend not built",
            "docs": "/docs"
        }
