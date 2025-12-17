"""
title: AI Agent Orchestrator
version: 2.0.0
description: Delegate tasks to specialized AI models, run parallel queries, and chain workflows.
author: AI.STACK
author_url: https://github.com/Rinkatecam/aistack

# SYSTEM PROMPT FOR AI
# ====================
# Delegate tasks to OTHER AI models for multi-agent workflows.
#
# SPECIALISTS (configurable):
#   reasoning_model - Analysis, logic, debugging
#   coding_model    - Code writing/review
#   creative_model  - Writing, content
#   vision_model    - Image analysis
#
# USE ask_specialist(), ask_multiple(), chain_tasks()
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
DEFAULT_TIMEOUT = 120


class Tools:
    class Valves(BaseModel):
        ollama_url: str = Field(default="http://ollama:11434", description="Ollama API URL")
        reasoning_model: str = Field(default="deepseek-r1:8b", description="Model for analysis/reasoning")
        coding_model: str = Field(default="qwen2.5:7b", description="Model for code")
        creative_model: str = Field(default="mistral:7b", description="Model for creative writing")
        vision_model: str = Field(default="llava:7b", description="Model for image analysis")
        general_model: str = Field(default="mistral:7b", description="General purpose model")
        default_timeout: int = Field(default=120, description="Timeout in seconds")
        max_tokens: int = Field(default=2048, description="Max response tokens")
        temperature: float = Field(default=0.7, description="Temperature (0.0-1.0)")

    class UserValves(BaseModel):
        preferred_reasoning_model: str = Field(default="", description="Override reasoning model")
        preferred_coding_model: str = Field(default="", description="Override coding model")

    def __init__(self):
        self.citation = False
        self.file_handler = False
        self.valves = self.Valves()

    def _get_ollama_url(self) -> str:
        return getattr(self.valves, 'ollama_url', OLLAMA_URL)

    def _get_model(self, specialist: str) -> str:
        specialist = specialist.lower().strip()
        model_map = {
            "reasoning": getattr(self.valves, 'reasoning_model', 'deepseek-r1:8b'),
            "analysis": getattr(self.valves, 'reasoning_model', 'deepseek-r1:8b'),
            "logic": getattr(self.valves, 'reasoning_model', 'deepseek-r1:8b'),
            "coding": getattr(self.valves, 'coding_model', 'qwen2.5:7b'),
            "code": getattr(self.valves, 'coding_model', 'qwen2.5:7b'),
            "programming": getattr(self.valves, 'coding_model', 'qwen2.5:7b'),
            "creative": getattr(self.valves, 'creative_model', 'mistral:7b'),
            "writing": getattr(self.valves, 'creative_model', 'mistral:7b'),
            "vision": getattr(self.valves, 'vision_model', 'llava:7b'),
            "image": getattr(self.valves, 'vision_model', 'llava:7b'),
            "general": getattr(self.valves, 'general_model', 'mistral:7b'),
        }
        return model_map.get(specialist, getattr(self.valves, 'general_model', 'mistral:7b'))

    def _query_ollama(self, model: str, prompt: str, system: str = "", timeout: int = 0) -> Dict[str, Any]:
        url = f"{self._get_ollama_url()}/api/generate"
        timeout = timeout if timeout > 0 else getattr(self.valves, 'default_timeout', DEFAULT_TIMEOUT)

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": getattr(self.valves, 'max_tokens', 2048),
                "temperature": getattr(self.valves, 'temperature', 0.7),
            }
        }

        if system:
            payload["system"] = system

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url, data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                return {
                    "success": True,
                    "model": model,
                    "response": result.get("response", ""),
                    "total_duration": result.get("total_duration", 0) / 1e9,
                    "eval_count": result.get("eval_count", 0),
                }
        except urllib.error.URLError as e:
            return {"success": False, "model": model, "error": f"Connection error: {e.reason}"}
        except urllib.error.HTTPError as e:
            return {"success": False, "model": model, "error": f"HTTP error {e.code}: {e.reason}"}
        except Exception as e:
            return {"success": False, "model": model, "error": str(e)}

    def list_available_models(self) -> str:
        """List all models available on Ollama server."""
        url = f"{self._get_ollama_url()}/api/tags"

        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                models = result.get("models", [])

                if not models:
                    return "No models installed on Ollama server."

                lines = ["Available Models on Ollama:", "=" * 40]
                for m in models:
                    name = m.get("name", "unknown")
                    size_bytes = m.get("size", 0)
                    size_gb = size_bytes / (1024**3)
                    lines.append(f"  {name:<25} {size_gb:.1f} GB")

                lines.extend([
                    "", "Configured Specialists:",
                    f"  Reasoning: {getattr(self.valves, 'reasoning_model', '?')}",
                    f"  Coding:    {getattr(self.valves, 'coding_model', '?')}",
                    f"  Creative:  {getattr(self.valves, 'creative_model', '?')}",
                    f"  Vision:    {getattr(self.valves, 'vision_model', '?')}",
                    f"  General:   {getattr(self.valves, 'general_model', '?')}",
                ])

                return "\n".join(lines)

        except Exception as e:
            return f"Error listing models: {e}"

    def ask_specialist(self, specialist: str, prompt: str, system_prompt: str = "") -> str:
        """
        Ask a specialist AI model to handle a task.

        Args:
            specialist: Type - "reasoning", "coding", "creative", "vision", "general"
                       Or model name like "mistral:7b"
            prompt: Task or question
            system_prompt: Optional context/behavior

        Returns:
            Specialist's response.
        """
        if ':' in specialist:
            model = specialist
            specialist_name = specialist
        else:
            model = self._get_model(specialist)
            specialist_name = specialist.capitalize()

        default_systems = {
            "reasoning": "You are an expert analyst. Think step by step and provide thorough analysis.",
            "coding": "You are an expert programmer. Write clean, efficient, well-documented code.",
            "creative": "You are a creative writer. Be imaginative, engaging, and original.",
            "vision": "You are an image analysis expert. Describe what you see in detail.",
            "general": "You are a helpful AI assistant. Be clear, accurate, and helpful.",
        }

        if not system_prompt:
            system_prompt = default_systems.get(specialist.lower(), default_systems["general"])

        result = self._query_ollama(model, prompt, system_prompt)

        if result["success"]:
            duration = result.get("total_duration", 0)
            tokens = result.get("eval_count", 0)

            output = [
                f"=== {specialist_name} Response (Model: {model}) ===",
                "",
                result["response"],
                "",
                f"--- Stats: {duration:.1f}s, {tokens} tokens ---"
            ]
            return "\n".join(output)
        else:
            return f"Error from {specialist_name} ({model}): {result.get('error', 'Unknown error')}"

    def ask_model(self, model: str, prompt: str, system_prompt: str = "") -> str:
        """Ask a specific model by name."""
        return self.ask_specialist(model, prompt, system_prompt)

    def ask_multiple(self, specialists: str, prompt: str) -> str:
        """
        Ask the same question to multiple specialists.

        Args:
            specialists: Comma-separated list: "reasoning,coding,creative"
            prompt: Question to ask all

        Returns:
            All responses for comparison.
        """
        specialist_list = [s.strip() for s in specialists.split(",") if s.strip()]

        if not specialist_list:
            return "Error: Please provide at least one specialist"

        if len(specialist_list) > 5:
            return "Error: Maximum 5 specialists at once"

        results = []
        for i, spec in enumerate(specialist_list, 1):
            results.append(f"\n{'='*50}")
            results.append(f"RESPONSE {i}/{len(specialist_list)}: {spec.upper()}")
            results.append('='*50)
            response = self.ask_specialist(spec, prompt)
            results.append(response)

        results.append(f"\n{'='*50}")
        results.append(f"COMPARISON COMPLETE: {len(specialist_list)} responses above")
        results.append('='*50)

        return "\n".join(results)

    def chain_tasks(self, tasks_json: str) -> str:
        """
        Execute a chain of tasks where each output feeds the next.

        Args:
            tasks_json: JSON array: '[["coding", "Write function"], ["reasoning", "Review: {previous}"]]'
                       Use {previous} for previous response.

        Returns:
            Final output after all tasks.
        """
        try:
            tasks = json.loads(tasks_json)
        except json.JSONDecodeError as e:
            return f"Error parsing tasks JSON: {e}"

        if not isinstance(tasks, list) or not tasks:
            return "Error: tasks must be a non-empty array"

        results = []
        previous_response = ""

        for i, task in enumerate(tasks, 1):
            if not isinstance(task, list) or len(task) < 2:
                return f"Error: Task {i} must be [specialist, prompt]"

            specialist, prompt = task[0], task[1]

            if previous_response and "{previous}" in prompt:
                prompt = prompt.replace("{previous}", previous_response)
            elif previous_response and i > 1:
                prompt = f"{prompt}\n\nPrevious step output:\n{previous_response}"

            results.append(f"\n{'='*50}")
            results.append(f"STEP {i}/{len(tasks)}: {specialist.upper()}")
            results.append('='*50)

            model = self._get_model(specialist) if ':' not in specialist else specialist
            result = self._query_ollama(model, prompt)

            if result["success"]:
                previous_response = result["response"]
                results.append(f"Model: {model}")
                results.append("")
                results.append(previous_response)
            else:
                error_msg = f"Error: {result.get('error', 'Unknown')}"
                results.append(error_msg)
                previous_response = error_msg

        results.append(f"\n{'='*50}")
        results.append(f"CHAIN COMPLETE: {len(tasks)} steps executed")
        results.append('='*50)

        return "\n".join(results)

    def code_review(self, code: str, language: str = "auto") -> str:
        """
        Have the reasoning model review code.

        Args:
            code: Code to review
            language: Programming language

        Returns:
            Detailed code review.
        """
        prompt = f"""Please review this code thoroughly:

```{language}
{code}
```

Analyze for:
1. Bugs and logic errors
2. Security vulnerabilities
3. Performance issues
4. Code style and best practices
5. Edge cases

Provide specific line references and suggested fixes."""

        system = "You are a senior code reviewer. Be thorough, specific, and constructive."
        return self.ask_specialist("reasoning", prompt, system)

    def brainstorm(self, topic: str, perspectives: int = 3) -> str:
        """
        Get multiple creative perspectives on a topic.

        Args:
            topic: Topic to brainstorm
            perspectives: Number of perspectives (1-5)

        Returns:
            Multiple creative perspectives.
        """
        perspectives = max(1, min(5, perspectives))

        prompt = f"""Generate {perspectives} completely different creative perspectives for:

{topic}

For each:
1. Give it a creative name
2. Explain the core idea
3. List 2-3 actionable steps
4. Note potential challenges"""

        system = "You are a creative consultant. Generate diverse, innovative ideas."
        return self.ask_specialist("creative", prompt, system)

    def debug_help(self, error_message: str, code_context: str = "", language: str = "auto") -> str:
        """
        Get help debugging an error.

        Args:
            error_message: Error or stack trace
            code_context: Optional code that caused error
            language: Programming language

        Returns:
            Analysis and suggested fixes.
        """
        prompt = f"""Debug this error:

ERROR:
{error_message}
"""
        if code_context:
            prompt += f"""
CODE CONTEXT:
```{language}
{code_context}
```
"""
        prompt += """
Please:
1. Explain what this error means
2. Identify the likely cause
3. Provide a specific fix
4. Suggest how to prevent this"""

        system = "You are an expert debugger. Be precise about the cause and specific about the fix."
        return self.ask_specialist("reasoning", prompt, system)

    def summarize_for_role(self, content: str, role: str = "manager") -> str:
        """
        Summarize content tailored for a specific role.

        Args:
            content: Content to summarize
            role: Target role - manager, developer, client, executive, technical

        Returns:
            Summary tailored for the role.
        """
        role_guides = {
            "manager": "Focus on timelines, resources, risks, decisions. Skip technical details.",
            "developer": "Focus on implementation, dependencies, code changes.",
            "client": "Focus on business value, features. No jargon.",
            "executive": "Focus on ROI, strategic impact. Very brief.",
            "technical": "Include all technical details, architecture decisions.",
        }

        guide = role_guides.get(role.lower(), role_guides["manager"])

        prompt = f"""Summarize the following content for a {role}:

{guide}

CONTENT:
{content}

Provide a clear, actionable summary."""

        return self.ask_specialist("general", prompt)
