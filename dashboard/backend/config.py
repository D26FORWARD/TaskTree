"""
Configuration management for SplitMind
"""
import json
import os
from pathlib import Path
from typing import List, Optional
from .models import Project, OrchestratorConfig


class ConfigManager:
    """Manages SplitMind configuration and projects"""

    def __init__(self):
        # Store config in the project root directory (cctg)
        # Go up from backend/config.py -> backend -> dashboard -> cctg
        self.config_dir = Path(__file__).parent.parent.parent
        self.config_file = self.config_dir / "config.json"
        self.projects_file = self.config_dir / "projects.json"
        self._ensure_config_dir()
        self._load_config()

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist"""
        self.config_dir.mkdir(exist_ok=True)

        # Create default config if not exists
        if not self.config_file.exists():
            default_config = {
                "orchestrator": {
                    "max_concurrent_agents": 5,
                    "auto_merge": False,
                    "merge_strategy": "merge",
                    "auto_spawn_interval": 60,
                    "enabled": False,
                    "api_provider": "anthropic",
                    "api_key": None,
                    "api_model": "claude-sonnet-4-20250514",
                    "api_base_url": None,
                    "api_version": None
                },
                "dashboard": {
                    "theme": "dark",
                    "notifications": True
                }
            }
            self._save_json(self.config_file, default_config)

        # Create empty projects file if not exists
        if not self.projects_file.exists():
            self._save_json(self.projects_file, {"projects": []})

    def _load_config(self):
        """Load configuration from disk"""
        self.config = self._load_json(self.config_file)
        self.projects_data = self._load_json(self.projects_file)

    def _load_json(self, file_path: Path) -> dict:
        """Load JSON file"""
        with open(file_path, 'r') as f:
            return json.load(f)

    def _save_json(self, file_path: Path, data: dict):
        """Save JSON file"""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def get_orchestrator_config(self) -> OrchestratorConfig:
        """Get orchestrator configuration"""
        return OrchestratorConfig(**self.config["orchestrator"])

    def update_orchestrator_config(self, config: OrchestratorConfig):
        """Update orchestrator configuration"""
        self.config["orchestrator"] = config.dict()
        self._save_json(self.config_file, self.config)

    def get_projects(self) -> List[Project]:
        """Get all projects"""
        return [Project(**p) for p in self.projects_data["projects"]]

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a specific project"""
        for p in self.projects_data["projects"]:
            if p["id"] == project_id:
                return Project(**p)
        return None

    def add_project(self, project: Project) -> Project:
        """Add a new project"""
        # Check if project already exists
        existing = self.get_project(project.id)
        if existing:
            raise ValueError(f"Project with id '{project.id}' already exists")

        # Ensure project directory exists
        project_path = Path(project.path)
        if not project_path.exists():
            raise ValueError(f"Project path '{project.path}' does not exist")

        # Create .splitmind directory in project
        splitmind_dir = project_path / ".splitmind"
        splitmind_dir.mkdir(exist_ok=True)

        # Create default tasks.md if not exists
        tasks_file = splitmind_dir / "tasks.md"
        if not tasks_file.exists():
            tasks_file.write_text("# tasks.md\n\n")

        # Add to projects - convert datetime to string
        project_dict = project.dict()
        project_dict['created_at'] = project.created_at.isoformat()
        project_dict['updated_at'] = project.updated_at.isoformat()
        self.projects_data["projects"].append(project_dict)
        self._save_json(self.projects_file, self.projects_data)

        return project

    def update_project(self, project_id: str, updates: dict) -> Project:
        """Update an existing project"""
        from datetime import datetime

        for i, p in enumerate(self.projects_data["projects"]):
            if p["id"] == project_id:
                # Handle datetime updates
                if 'updated_at' not in updates:
                    updates['updated_at'] = datetime.now().isoformat()

                self.projects_data["projects"][i].update(updates)
                self._save_json(self.projects_file, self.projects_data)
                return Project(**self.projects_data["projects"][i])
        raise ValueError(f"Project '{project_id}' not found")

    def delete_project(self, project_id: str):
        """Delete a project (doesn't delete actual files)"""
        self.projects_data["projects"] = [
            p for p in self.projects_data["projects"]
            if p["id"] != project_id
        ]
        self._save_json(self.projects_file, self.projects_data)

    def get_project_config_path(self, project_id: str) -> Optional[Path]:
        """Get the .splitmind directory path for a project"""
        project = self.get_project(project_id)
        if project:
            return Path(project.path) / ".splitmind"
        return None


# Global config manager instance
config_manager = ConfigManager()
