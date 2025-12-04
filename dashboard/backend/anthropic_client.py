"""
Generic API Client for SplitMind

This module handles direct API calls to various AI providers for plan generation.
Supports Anthropic, OpenAI, Azure OpenAI, and other compatible providers.
"""
import os
import json
import httpx
from typing import Dict, List, Optional
from pathlib import Path


class GenericAPIClient:
    """Client for generic API interactions with various AI providers"""

    def __init__(self, api_key: Optional[str] = None, api_provider: str = "anthropic",
                 api_base_url: Optional[str] = None, api_version: Optional[str] = None):
        self.api_key = api_key or os.getenv("API_KEY")
        self.api_provider = api_provider.lower()
        self.api_version = api_version
        self.default_model = "claude-sonnet-4-20250514"  # Default model
        self.app_id = None  # For Aliyun provider

        # Set base URL based on provider
        if api_base_url:
            self.base_url = api_base_url.rstrip('/')
        elif self.api_provider == "anthropic":
            self.base_url = "https://api.anthropic.com/v1"
        elif self.api_provider == "openai":
            self.base_url = "https://api.openai.com/v1"
        elif self.api_provider == "azure":
            # For Azure, base URL needs to be provided explicitly
            self.base_url = api_base_url or "https://YOUR_RESOURCE_NAME.openai.azure.com"
        elif self.api_provider == "aliyun":
            self.base_url = "https://dashscope.aliyuncs.com/api/v1"
        else:
            # Default to Anthropic for unknown providers
            self.base_url = "https://api.anthropic.com/v1"

        # Pricing per million tokens (as of Jan 2025) - defaults to Anthropic pricing
        self.pricing = {
            "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
            "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
            "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
            "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
            "gpt-4": {"input": 30.00, "output": 60.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            # Aliyun pricing is based on app usage
            "aliyun-default": {"input": 0.0, "output": 0.0}
        }

    def _get_headers(self, model: Optional[str] = None) -> Dict[str, str]:
        """Get appropriate headers based on the API provider"""
        headers = {
            "content-type": "application/json"
        }

        if self.api_provider == "anthropic":
            headers.update({
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            })
        elif self.api_provider == "openai":
            headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
        elif self.api_provider == "azure":
            headers.update({
                "api-key": self.api_key
            })
            if self.api_version:
                headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.api_provider == "aliyun":
            headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "X-DashScope-DataInspection": "enable"
            })
        else:
            # Default to Anthropic-style headers
            headers.update({
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            })

        return headers

    def _get_endpoint(self, endpoint: str) -> str:
        """Get the full endpoint URL"""
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def generate_plan(self, project_info: Dict, model: Optional[str] = None) -> Dict:
        """
        Generate a project plan using the configured API provider

        Args:
            project_info: Dictionary containing:
                - project_name: Name of the project
                - project_overview: Detailed project description
                - initial_prompt: User's initial request

        Returns:
            Dictionary containing:
                - plan: Generated project plan
                - suggested_tasks: List of tasks with titles and descriptions
                - success: Boolean indicating if the request was successful
                - error: Error message if request failed
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "No API key configured. Please add it in Settings.",
                "plan": "",
                "suggested_tasks": []
            }

        # Prepare the prompt based on provider
        if self.api_provider in ["anthropic", "default"]:
            return self._generate_plan_anthropic(project_info, model)
        elif self.api_provider == "openai":
            return self._generate_plan_openai(project_info, model)
        elif self.api_provider == "azure":
            return self._generate_plan_azure(project_info, model)
        elif self.api_provider == "aliyun":
            # For Aliyun, app_id is stored in self.api_version
            return self._generate_plan_aliyun(project_info, model, self.api_version)
        else:
            # Default to Anthropic-style prompt
            return self._generate_plan_anthropic(project_info, model)

    def _generate_plan_anthropic(self, project_info: Dict, model: Optional[str] = None) -> Dict:
        """Generate plan using Anthropic-style API"""
        # Prepare the prompt
        system_prompt = """You are a project planning expert. You analyze project requirements and create comprehensive development plans with actionable tasks.

When creating tasks, you MUST format each one exactly as follows:
- **Task Title** - Brief description | Dependencies: [dep1, dep2] | Priority: X

Where:
- Dependencies are the titles of other tasks that must be completed first (use exact task titles, or "none" if no dependencies)
- Priority is a number from 1-10 where 1 is highest priority, 10 is lowest
- Tasks should follow a logical development order (e.g., setup before implementation, implementation before testing)

Example format:
- **Set up project structure** - Initialize Git repo and create basic folders | Dependencies: [none] | Priority: 1
- **Create database schema** - Design and implement database models | Dependencies: [Set up project structure] | Priority: 2
- **Implement API endpoints** - Create REST API for CRUD operations | Dependencies: [Create database schema] | Priority: 3
- **Write unit tests** - Add comprehensive test coverage | Dependencies: [Implement API endpoints] | Priority: 4

Make sure tasks are specific, have clear dependencies, and follow a logical implementation order."""

        user_prompt = f"""Please create a comprehensive project plan for the following project:

Project Name: {project_info.get('project_name', 'Unknown')}

Project Overview:
{project_info.get('project_overview', 'No overview provided')}

Initial Requirements/Prompt:
{project_info.get('initial_prompt', 'No initial prompt provided')}

Please provide:
1. A detailed project plan with:
   - Architecture decisions
   - Technology stack recommendations
   - Development phases with timelines
   - Risk factors and mitigation strategies
   
2. Generate 10-15 specific, actionable tasks with dependencies and priorities:
   - Use the EXACT format: **Task Title** - Brief description | Dependencies: [dep1, dep2] | Priority: X
   - List dependencies by exact task titles or use [none]
   - Assign priorities 1-10 (1=highest, 10=lowest) based on logical order
   - Ensure tasks follow natural development flow (setup → implementation → testing → deployment)

Make the tasks concrete and implementable by AI coding agents."""

        try:
            # Make API request
            headers = self._get_headers(model)

            data = {
                "model": model or self.default_model,
                "max_tokens": 4096,
                "temperature": 0.7,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            }

            with httpx.Client() as client:
                response = client.post(
                    self._get_endpoint("messages"),
                    headers=headers,
                    json=data,
                    timeout=30.0
                )

                if response.status_code != 200:
                    error_data = response.json()
                    return {
                        "success": False,
                        "error": f"API Error: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        "plan": "",
                        "suggested_tasks": []
                    }

                result = response.json()
                content = result.get('content', [{}])[0].get('text', '')

                # Calculate cost
                usage = result.get('usage', {})
                input_tokens = usage.get('input_tokens', 0)
                output_tokens = usage.get('output_tokens', 0)

                model_used = model or self.default_model
                cost_info = self._calculate_cost(
                    model_used, input_tokens, output_tokens)

                # Parse the response
                parsed = self._parse_response(content)
                parsed['cost_info'] = cost_info
                parsed['usage'] = usage

                return parsed

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timed out. Please try again.",
                "plan": "",
                "suggested_tasks": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error calling API: {str(e)}",
                "plan": "",
                "suggested_tasks": []
            }

    def _generate_plan_openai(self, project_info: Dict, model: Optional[str] = None) -> Dict:
        """Generate plan using OpenAI-style API"""
        # Prepare the prompt
        system_prompt = """You are a project planning expert. You analyze project requirements and create comprehensive development plans with actionable tasks.

When creating tasks, you MUST format each one exactly as follows:
- **Task Title** - Brief description | Dependencies: [dep1, dep2] | Priority: X

Where:
- Dependencies are the titles of other tasks that must be completed first (use exact task titles, or "none" if no dependencies)
- Priority is a number from 1-10 where 1 is highest priority, 10 is lowest
- Tasks should follow a logical development order (e.g., setup before implementation, implementation before testing)

Example format:
- **Set up project structure** - Initialize Git repo and create basic folders | Dependencies: [none] | Priority: 1
- **Create database schema** - Design and implement database models | Dependencies: [Set up project structure] | Priority: 2
- **Implement API endpoints** - Create REST API for CRUD operations | Dependencies: [Create database schema] | Priority: 3
- **Write unit tests** - Add comprehensive test coverage | Dependencies: [Implement API endpoints] | Priority: 4

Make sure tasks are specific, have clear dependencies, and follow a logical implementation order."""

        user_prompt = f"""Please create a comprehensive project plan for the following project:

Project Name: {project_info.get('project_name', 'Unknown')}

Project Overview:
{project_info.get('project_overview', 'No overview provided')}

Initial Requirements/Prompt:
{project_info.get('initial_prompt', 'No initial prompt provided')}

Please provide:
1. A detailed project plan with:
   - Architecture decisions
   - Technology stack recommendations
   - Development phases with timelines
   - Risk factors and mitigation strategies
   
2. Generate 10-15 specific, actionable tasks with dependencies and priorities:
   - Use the EXACT format: **Task Title** - Brief description | Dependencies: [dep1, dep2] | Priority: X
   - List dependencies by exact task titles or use [none]
   - Assign priorities 1-10 (1=highest, 10=lowest) based on logical order
   - Ensure tasks follow natural development flow (setup → implementation → testing → deployment)

Make the tasks concrete and implementable by AI coding agents."""

        try:
            # Make API request
            headers = self._get_headers(model)

            data = {
                "model": model or "gpt-4-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                "max_tokens": 4096,
                "temperature": 0.7
            }

            with httpx.Client() as client:
                response = client.post(
                    self._get_endpoint("chat/completions"),
                    headers=headers,
                    json=data,
                    timeout=30.0
                )

                if response.status_code != 200:
                    error_data = response.json()
                    return {
                        "success": False,
                        "error": f"API Error: {error_data.get('error', {}).get('message', 'Unknown error')}",
                        "plan": "",
                        "suggested_tasks": []
                    }

                result = response.json()
                content = result.get('choices', [{}])[0].get(
                    'message', {}).get('content', '')

                # Calculate cost (OpenAI-style)
                usage = result.get('usage', {})
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)

                model_used = model or "gpt-4-turbo"
                cost_info = self._calculate_cost(
                    model_used, input_tokens, output_tokens)

                # Parse the response
                parsed = self._parse_response(content)
                parsed['cost_info'] = cost_info
                parsed['usage'] = usage

                return parsed

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timed out. Please try again.",
                "plan": "",
                "suggested_tasks": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error calling API: {str(e)}",
                "plan": "",
                "suggested_tasks": []
            }

    def _generate_plan_azure(self, project_info: Dict, model: Optional[str] = None) -> Dict:
        """Generate plan using Azure OpenAI API"""
        # For Azure, we can use the same approach as OpenAI but with different endpoint
        return self._generate_plan_openai(project_info, model)

    def _generate_plan_aliyun(self, project_info: Dict, model: Optional[str] = None, app_id: Optional[str] = None) -> Dict:
        """Generate plan using Aliyun Bailian API

        Supports two modes:
        1. Model API: Use qwen-plus, qwen-turbo, etc. directly (if model is specified)
        2. App API: Use custom app with app_id (if app_id is specified)
        """
        # Determine which API endpoint to use
        use_app_api = app_id and app_id.strip()  # Use app API if app_id is provided
        actual_model = model or "qwen-plus"
        self.app_id = app_id if use_app_api else None

        # Prepare the prompt
        system_prompt = """You are a project planning expert. You analyze project requirements and create comprehensive development plans with actionable tasks.

When creating tasks, you MUST format each one exactly as follows:
- **Task Title** - Brief description | Dependencies: [dep1, dep2] | Priority: X

Where:
- Dependencies are the titles of other tasks that must be completed first (use exact task titles, or "none" if no dependencies)
- Priority is a number from 1-10 where 1 is highest priority, 10 is lowest
- Tasks should follow a logical development order (e.g., setup before implementation, implementation before testing)

Example format:
- **Set up project structure** - Initialize Git repo and create basic folders | Dependencies: [none] | Priority: 1
- **Create database schema** - Design and implement database models | Dependencies: [Set up project structure] | Priority: 2
- **Implement API endpoints** - Create REST API for CRUD operations | Dependencies: [Create database schema] | Priority: 3
- **Write unit tests** - Add comprehensive test coverage | Dependencies: [Implement API endpoints] | Priority: 4

Make sure tasks are specific, have clear dependencies, and follow a logical implementation order."""

        user_prompt = f"""Please create a comprehensive project plan for the following project:

Project Name: {project_info.get('project_name', 'Unknown')}

Project Overview:
{project_info.get('project_overview', 'No overview provided')}

Initial Requirements/Prompt:
{project_info.get('initial_prompt', 'No initial prompt provided')}

Please provide:
1. A detailed project plan with:
   - Architecture decisions
   - Technology stack recommendations
   - Development phases with timelines
   - Risk factors and mitigation strategies
   
2. Generate 10-15 specific, actionable tasks with dependencies and priorities:
   - Use the EXACT format: **Task Title** - Brief description | Dependencies: [dep1, dep2] | Priority: X
   - List dependencies by exact task titles or use [none]
   - Assign priorities 1-10 (1=highest, 10=lowest) based on logical order
   - Ensure tasks follow natural development flow (setup → implementation → testing → deployment)

Make the tasks concrete and implementable by AI coding agents."""

        try:
            # Make API request
            headers = self._get_headers(model)

            if use_app_api:
                # Use custom app API
                data = {
                    "input": {
                        "prompt": user_prompt
                    },
                    "parameters": {
                        "enable_moderation": True
                    }
                }

                endpoint = f"apps/{self.app_id}/completion"
            else:
                # Use model API directly
                data = {
                    "model": actual_model,
                    "input": {
                        "messages": [
                            {
                                "role": "system",
                                "content": system_prompt
                            },
                            {
                                "role": "user",
                                "content": user_prompt
                            }
                        ]
                    },
                    "parameters": {
                        "enable_moderation": True
                    }
                }

                endpoint = "services/aigc/text-generation/generation"

            with httpx.Client() as client:
                response = client.post(
                    self._get_endpoint(endpoint),
                    headers=headers,
                    json=data,
                    timeout=30.0
                )

                if response.status_code != 200:
                    error_data = response.json()
                    return {
                        "success": False,
                        "error": f"API Error: {error_data.get('message', 'Unknown error')}",
                        "plan": "",
                        "suggested_tasks": []
                    }

                result = response.json()

                # Extract content based on API type
                if use_app_api:
                    content = result.get('output', {}).get('text', '')
                else:
                    # Model API returns output.text
                    content = result.get('output', {}).get('text', '')

                # Calculate cost (Aliyun-style)
                usage = result.get('usage', {})
                input_tokens = usage.get('input_tokens', 0) or 0
                output_tokens = usage.get('output_tokens', 0) or 0

                cost_info = self._calculate_cost(
                    "aliyun-default", input_tokens, output_tokens)

                # Parse the response
                parsed = self._parse_response(content)
                parsed['cost_info'] = cost_info
                parsed['usage'] = usage

                return parsed

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timed out. Please try again.",
                "plan": "",
                "suggested_tasks": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error calling API: {str(e)}",
                "plan": "",
                "suggested_tasks": []
            }

    def generate_task_breakdown(self, project_info: Dict, model: Optional[str] = None) -> Dict:
        """
        Generate a structured task breakdown using the Task Master AI approach.

        Args:
            project_info: Dictionary containing project details
            model: Model to use (optional, will use default if not provided)

        Returns:
            Dictionary containing:
                - plan: Generated project plan
                - task_breakdown: Structured wave-based task breakdown
                - suggested_tasks: List of tasks for backward compatibility
                - success: Boolean indicating if the request was successful
                - error: Error message if request failed
        """
        # For now, we'll use the same approach as generate_plan but with a different prompt
        # In a future enhancement, we could customize this further for task breakdowns
        return self.generate_plan(project_info, model)

    def _parse_response(self, content: str) -> Dict:
        """Parse API response to extract plan and tasks with dependencies"""
        lines = content.split('\n')

        # Extract tasks
        tasks = []
        for line in lines:
            line = line.strip()
            if line.startswith('- **') and '**' in line[4:]:
                # Pattern: - **Title** - Description | Dependencies: [dep1, dep2] | Priority: X
                parts = line.split('**')
                if len(parts) >= 3:
                    title = parts[1].strip()
                    remaining = parts[2].strip()

                    # Remove leading dash if present
                    if remaining.startswith('-'):
                        remaining = remaining[1:].strip()

                    # Split by pipe to extract description, dependencies, and priority
                    sections = remaining.split('|')
                    description = sections[0].strip() if sections else ""

                    # Default values
                    dependencies = []
                    priority = 5  # Default middle priority

                    # Parse dependencies and priority from remaining sections
                    for section in sections[1:]:
                        section = section.strip()
                        if section.startswith('Dependencies:'):
                            deps_str = section[len('Dependencies:'):].strip()
                            # Remove brackets and split by comma
                            deps_str = deps_str.strip('[]')
                            if deps_str and deps_str.lower() != 'none':
                                dependencies = [
                                    dep.strip() for dep in deps_str.split(',') if dep.strip()]
                        elif section.startswith('Priority:'):
                            priority_str = section[len('Priority:'):].strip()
                            try:
                                priority = int(priority_str)
                            except ValueError:
                                priority = 5  # Default if parsing fails

                    tasks.append({
                        "title": title,
                        "description": description,
                        "dependencies": dependencies,
                        "priority": priority
                    })

        # If no tasks found with the specific format, try a simpler extraction
        if not tasks:
            tasks = self._extract_simple_tasks(content)

        return {
            "plan": content,
            "suggested_tasks": tasks,
            "success": True
        }

    def _extract_simple_tasks(self, content: str) -> List[Dict]:
        """Extract tasks using a simpler approach if the specific format isn't found"""
        tasks = []
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            # Look for lines that start with a dash and contain task-like content
            if line.startswith('- ') and ('task' in line.lower() or 'implement' in line.lower() or
                                          'create' in line.lower() or 'build' in line.lower()):
                # Simple extraction - take the whole line as title and create a generic description
                title = line[2:]  # Remove the "- " prefix
                if len(title) > 5:  # Only if it seems like a reasonable task title
                    tasks.append({
                        "title": title[:100],  # Limit length
                        "description": f"Complete the following task: {title}",
                        "dependencies": [],
                        "priority": 5
                    })

        # If still no tasks, create some default ones
        if not tasks:
            tasks = self._get_default_tasks()

        return tasks[:15]  # Limit to 15 tasks

    def _get_default_tasks(self) -> List[Dict]:
        """Get default tasks if parsing fails"""
        return [
            {
                "title": "Initialize Project Structure",
                "description": "Set up the project repository with proper folder structure and initial configuration",
                "dependencies": [],
                "priority": 1
            },
            {
                "title": "Create Development Environment",
                "description": "Configure development tools, linters, and local environment setup",
                "dependencies": ["Initialize Project Structure"],
                "priority": 2
            },
            {
                "title": "Design System Architecture",
                "description": "Plan and document the overall system architecture and component design",
                "dependencies": ["Create Development Environment"],
                "priority": 3
            },
            {
                "title": "Implement Core Features",
                "description": "Build the main functionality as specified in the project requirements",
                "dependencies": ["Design System Architecture"],
                "priority": 4
            },
            {
                "title": "Add Testing Suite",
                "description": "Create comprehensive unit and integration tests",
                "dependencies": ["Implement Core Features"],
                "priority": 5
            }
        ]

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Dict:
        """Calculate API cost based on token usage"""
        # Get pricing for the model, fallback to default if not found
        model_pricing = self.pricing.get(model, {"input": 0.0, "output": 0.0})

        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
        total_cost = input_cost + output_cost

        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": round(input_cost, 4),
            "output_cost": round(output_cost, 4),
            "total_cost": round(total_cost, 4)
        }


# Keep the existing anthropic_client instance for backward compatibility
anthropic_client = GenericAPIClient()
