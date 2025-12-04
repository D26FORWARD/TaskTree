"""
Claude Integration for SplitMind

This module handles the integration between SplitMind and Claude Code for orchestration,
and uses the Generic API Client for plan generation with support for multiple providers.
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from .anthropic_client import GenericAPIClient

# Create a generic API client instance
generic_api_client = GenericAPIClient()


class ClaudeIntegration:
    """
    Handles integration with Claude Code for plan generation and task execution.

    Note: Claude Code doesn't have a CLI. Instead, this module:
    1. Generates prompts that can be used with Claude Code
    2. Provides instructions for manual integration
    3. Prepares command files that Claude Code can execute
    """

    def __init__(self):
        self.commands_dir = Path(
            __file__).parent.parent.parent / ".claude" / "commands"

    def generate_task_breakdown(self, project_info: Dict, api_key: Optional[str] = None,
                                model: Optional[str] = None, api_provider: str = "anthropic",
                                api_base_url: Optional[str] = None, api_version: Optional[str] = None) -> Dict:
        """
        Generate a structured task breakdown using the Task Master AI approach.

        Args:
            project_info: Dictionary containing project details
            api_key: API key (optional, will use default if not provided)
            model: Model to use (optional, will use default if not provided)
            api_provider: API provider (anthropic, openai, azure, etc.)
            api_base_url: Base URL for API endpoint (for custom/self-hosted providers)
            api_version: API version (for providers that require it)

        Returns:
            Dictionary containing:
                - plan: Generated project plan
                - task_breakdown: Structured wave-based task breakdown
                - suggested_tasks: List of tasks for backward compatibility
                - success: Boolean indicating if the request was successful
                - error: Error message if request failed
        """
        # Update the client with the API key and provider if provided
        if api_key:
            generic_api_client.api_key = api_key
        if api_provider:
            generic_api_client.api_provider = api_provider
        if api_base_url:
            generic_api_client.base_url = api_base_url
        if api_version:
            generic_api_client.api_version = api_version

        # Call the Generic API with task master prompt
        result = generic_api_client.generate_task_breakdown(
            project_info, model)

        # If successful, save both plan and task breakdown
        if result.get('success'):
            project_path = project_info.get('project_path', '')
            if project_path:
                prompt_dir = Path(project_path) / ".splitmind" / "plans"
                prompt_dir.mkdir(parents=True, exist_ok=True)

                plan_file = prompt_dir / "generated-plan.md"
                with open(plan_file, 'w') as f:
                    f.write(result['plan'])

                task_breakdown_file = prompt_dir / "task-breakdown.md"
                with open(task_breakdown_file, 'w') as f:
                    f.write(result.get('task_breakdown', ''))

                result['plan_file'] = str(plan_file)
                result['task_breakdown_file'] = str(task_breakdown_file)

        return result

    def generate_plan(self, project_info: Dict, api_key: Optional[str] = None,
                      model: Optional[str] = None, api_provider: str = "anthropic",
                      api_base_url: Optional[str] = None, api_version: Optional[str] = None) -> Dict:
        """
        Generate a project plan using the Generic API Client.

        Args:
            project_info: Dictionary containing project details
            api_key: API key (optional, will use default if not provided)
            model: Model to use (optional, will use default if not provided)
            api_provider: API provider (anthropic, openai, azure, etc.)
            api_base_url: Base URL for API endpoint (for custom/self-hosted providers)
            api_version: API version (for providers that require it)

        Returns:
            Dictionary containing:
                - plan: Generated project plan
                - suggested_tasks: List of tasks with titles and descriptions
                - success: Boolean indicating if the request was successful
                - error: Error message if request failed
        """
        # Update the client with the API key and provider if provided
        if api_key:
            generic_api_client.api_key = api_key
        if api_provider:
            generic_api_client.api_provider = api_provider
        if api_base_url:
            generic_api_client.base_url = api_base_url
        if api_version:
            generic_api_client.api_version = api_version

        # Call the Generic API
        result = generic_api_client.generate_plan(project_info, model)

        # If successful, also save the plan to a file for reference
        if result.get('success'):
            project_path = project_info.get('project_path', '')
            if project_path:
                prompt_dir = Path(project_path) / ".splitmind" / "plans"
                prompt_dir.mkdir(parents=True, exist_ok=True)

                plan_file = prompt_dir / "generated-plan.md"
                with open(plan_file, 'w') as f:
                    f.write(result['plan'])

                result['plan_file'] = str(plan_file)

        return result

    def _parse_claude_response(self, claude_output: str) -> Dict:
        """Parse Claude's response to extract plan and tasks"""
        # Extract the plan section
        plan_start = claude_output.find("# Project Plan:")
        if plan_start == -1:
            plan_start = claude_output.find("## Project Plan")
        if plan_start == -1:
            plan_start = 0

        plan = claude_output[plan_start:].strip()

        # Extract suggested tasks
        # Look for task patterns like "- Task: title" or "1. title"
        tasks = []
        lines = claude_output.split('\n')

        current_task = None
        for line in lines:
            # Check for task title patterns
            if line.strip().startswith('- **') and '**' in line[4:]:
                # Pattern: - **Title** - Description
                parts = line.split('**')
                if len(parts) >= 3:
                    title = parts[1].strip()
                    desc = parts[2].strip(' -:')
                    tasks.append({
                        "title": title,
                        "description": desc
                    })
            elif line.strip().startswith('- Task:') or line.strip().startswith('- Title:'):
                # Pattern: - Task: Title
                title = line.split(':', 1)[1].strip()
                current_task = {"title": title, "description": ""}
            elif current_task and line.strip().startswith('- Description:'):
                # Pattern: - Description: text
                current_task["description"] = line.split(':', 1)[1].strip()
                tasks.append(current_task)
                current_task = None

        # If we didn't find specific tasks, generate some based on the plan
        if not tasks:
            tasks = self._extract_tasks_from_plan(plan)

        return {
            "plan": plan,
            "suggested_tasks": tasks
        }

    def _extract_tasks_from_plan(self, plan: str) -> List[Dict[str, str]]:
        """Extract tasks from plan text if no specific task format found"""
        tasks = []

        # Look for phase or task indicators
        for line in plan.split('\n'):
            line = line.strip()
            if any(indicator in line.lower() for indicator in ['task:', 'implement', 'create', 'build', 'set up', 'configure']):
                if line.startswith('-') or line.startswith('*') or line[0].isdigit():
                    # Clean up the line
                    title = line.strip('- *123456789.')
                    tasks.append({
                        "title": title[:100],  # Limit title length
                        "description": f"Complete the following task: {title}"
                    })

        # Ensure we have at least some tasks
        if not tasks:
            tasks = self._get_default_tasks()

        return tasks[:15]  # Limit to 15 tasks

    def _get_default_tasks(self) -> List[Dict[str, str]]:
        """Get default tasks if parsing fails"""
        return [
            {
                "title": "Initialize Project Structure",
                "description": "Set up the project repository with proper folder structure and initial configuration"
            },
            {
                "title": "Create Development Environment",
                "description": "Configure development tools, linters, and local environment setup"
            },
            {
                "title": "Design System Architecture",
                "description": "Plan and document the overall system architecture and component design"
            },
            {
                "title": "Implement Core Features",
                "description": "Build the main functionality as specified in the project requirements"
            },
            {
                "title": "Add Testing Suite",
                "description": "Create comprehensive unit and integration tests"
            }
        ]

    def _generate_mock_plan(self, project_info: Dict) -> Dict:
        """Generate a mock plan when Claude is not available"""
        overview = project_info.get('project_overview', '')
        prompt = project_info.get('initial_prompt', '')
        project_name = project_info.get('project_name', 'Project')

        # Mock implementation - replace with actual Claude call
        plan = f"""# Project Plan: {project_name}

## Overview
Based on the provided overview and prompt, here's a comprehensive development plan.

## Project Context
{overview}

## Requirements Analysis
{prompt}

## Architecture Decisions
- Frontend: React with TypeScript for type safety
- Backend: FastAPI for high-performance API
- Database: PostgreSQL for relational data
- Authentication: JWT-based auth system
- Deployment: Docker containers with CI/CD

## Development Phases

### Phase 1: Foundation & Setup (Week 1)
**Goal**: Establish project structure and development environment

Tasks:
1. Initialize project repository and structure
2. Set up development environment and tooling
3. Configure CI/CD pipeline
4. Create basic documentation

### Phase 2: Core Infrastructure (Week 2-3)
**Goal**: Build the foundational components

Tasks:
1. Implement authentication system
2. Set up database models and migrations
3. Create API structure and routing
4. Build basic UI components library

### Phase 3: Feature Development (Week 4-6)
**Goal**: Implement main features

Tasks:
1. Build user management features
2. Implement core business logic
3. Create main UI views and flows
4. Add data validation and error handling

### Phase 4: Integration & Testing (Week 7)
**Goal**: Ensure quality and reliability

Tasks:
1. Write comprehensive test suite
2. Perform integration testing
3. Add monitoring and logging
4. Optimize performance

### Phase 5: Deployment & Launch (Week 8)
**Goal**: Deploy to production

Tasks:
1. Configure production environment
2. Set up monitoring and alerts
3. Perform security audit
4. Create user documentation

## Technical Specifications

### API Design
- RESTful endpoints with OpenAPI documentation
- Versioned API (v1, v2, etc.)
- Rate limiting and authentication
- Comprehensive error handling

### Database Schema
- User management tables
- Core business entities
- Audit and logging tables
- Performance indexes

### Security Considerations
- Input validation on all endpoints
- SQL injection prevention
- XSS protection
- CORS configuration
- Environment variable management

## Risk Mitigation
- Regular code reviews
- Automated testing pipeline
- Staging environment testing
- Incremental deployment strategy

## Success Metrics
- 95% test coverage
- <200ms API response time
- Zero critical security vulnerabilities
- Comprehensive documentation
"""

        # Generate suggested tasks based on the plan
        suggested_tasks = [
            {
                "title": "Initialize Project Structure",
                "description": "Set up the project repository with proper folder structure, initialize package managers, and configure development environment including linting, formatting, and git hooks."
            },
            {
                "title": "Set Up CI/CD Pipeline",
                "description": "Configure continuous integration and deployment using GitHub Actions or similar. Include automated testing, building, and deployment workflows."
            },
            {
                "title": "Implement Authentication System",
                "description": "Create a complete authentication system with user registration, login, JWT token management, and role-based access control."
            },
            {
                "title": "Design Database Schema",
                "description": "Create comprehensive database schema with all required tables, relationships, and indexes. Include migration scripts and seed data."
            },
            {
                "title": "Build API Structure",
                "description": "Implement the core API structure with proper routing, middleware, error handling, and OpenAPI documentation."
            },
            {
                "title": "Create UI Component Library",
                "description": "Build a reusable component library with common UI elements following the design system. Include proper TypeScript types and Storybook documentation."
            },
            {
                "title": "Implement Core Business Logic",
                "description": "Develop the main business logic and features based on the project requirements. Ensure proper separation of concerns and testability."
            },
            {
                "title": "Write Test Suite",
                "description": "Create comprehensive test coverage including unit tests, integration tests, and end-to-end tests. Aim for 95% code coverage."
            },
            {
                "title": "Configure Production Environment",
                "description": "Set up production infrastructure including servers, databases, monitoring, logging, and backup systems."
            },
            {
                "title": "Create Documentation",
                "description": "Write complete documentation including API docs, user guides, deployment instructions, and developer documentation."
            }
        ]

        return {
            "plan": plan,
            "suggested_tasks": suggested_tasks
        }

    def execute_command(self, command_name: str, variables: Dict) -> str:
        """
        Execute a Claude command file with variables

        Args:
            command_name: Name of the command file (without .md extension)
            variables: Dictionary of variables to replace in the command

        Returns:
            Command output
        """
        command_path = self.commands_dir / f"{command_name}.md"

        if not command_path.exists():
            raise ValueError(f"Command file {command_name}.md not found")

        # Read command file
        with open(command_path, 'r') as f:
            command_content = f.read()

        # Replace variables
        for key, value in variables.items():
            command_content = command_content.replace(
                f"{{{{{key}}}}}", str(value))

        # In production, this would call Claude CLI
        # For now, return a mock response
        return f"Executed command: {command_name} with variables: {variables}"

    def create_agent_prompt(self, task_title: str, task_description: str, project_context: Dict) -> str:
        """
        Create a prompt file for Claude Code to execute a specific task.

        This is how SplitMind orchestrates - by creating prompts that 
        Claude Code agents can execute in their worktrees.
        """
        prompt = f"""# Task: {task_title}

## Description
{task_description}

## Project Context
- Project: {project_context.get('name', 'Unknown')}
- Path: {project_context.get('path', 'Unknown')}
- Branch: {project_context.get('branch', 'Unknown')}

## Instructions
1. Implement this task according to the description
2. Follow project conventions and patterns
3. Write clean, documented code
4. Include tests where appropriate
5. Commit your changes with a descriptive message

## Acceptance Criteria
- Task requirements are fully implemented
- Code follows project standards
- Tests pass (if applicable)
- Changes are committed

Please proceed with implementing this task.
"""
        return prompt


# Global instance
claude = ClaudeIntegration()
