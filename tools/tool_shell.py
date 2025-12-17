"""
title: Shell Command Tool
version: 2.0.0
description: Execute shell commands (bash/cmd/powershell) with safety controls.
author: Rinkatecam
author_url: https://github.com/Rinkatecam/AI.Stack

# SYSTEM PROMPT FOR AI
# ====================
# Execute shell commands inside a Docker container with safety controls.
#
# IMPORTANT PATHS (inside Docker):
#   /data/projects     - Writable projects folder
#   /data/user-files   - AI workspace (writable)
#   /data/home         - User's home (read-only)
#
# USE run_command() for shell operations, quick_search() for finding files.
"""

import os
import subprocess
import platform
import shlex
from typing import Optional
from pydantic import BaseModel, Field

SYSTEM = platform.system()
MAX_OUTPUT = int(os.getenv("SHELL_MAX_OUTPUT", "50000"))
TIMEOUT = int(os.getenv("SHELL_TIMEOUT", "30"))

BLOCKED_COMMANDS = {
    "rm -rf /", "rm -rf /*", "del /f /s /q c:\\",
    "format", "mkfs", "dd if=",
    "shutdown", "reboot", "halt", "init 0", "init 6",
    "nmap", "nikto", "sqlmap", "hydra",
    "sudo rm", "sudo dd",
}

WARN_PATTERNS = ["sudo", "admin", "password", "delete", "remove"]


def _is_docker_container() -> bool:
    return os.path.exists("/.dockerenv") or os.path.exists("/data/user-files")


def _get_shell():
    if SYSTEM == "Windows":
        if os.path.exists(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"):
            return ["powershell", "-NoProfile", "-Command"]
        return ["cmd", "/c"]
    else:
        if os.path.exists("/bin/bash"):
            return ["/bin/bash", "-c"]
        return ["/bin/sh", "-c"]


def _is_blocked(command: str) -> bool:
    cmd_lower = command.lower().strip()
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            return True
    return False


def _has_warnings(command: str) -> list:
    warnings = []
    cmd_lower = command.lower()
    for pattern in WARN_PATTERNS:
        if pattern in cmd_lower:
            warnings.append(f"Command contains '{pattern}'")
    return warnings


class Tools:
    class Valves(BaseModel):
        default_timeout: int = Field(default=30, description="Command timeout (1-120s)")
        max_output_kb: int = Field(default=50, description="Max output size in KB")
        allow_sudo: bool = Field(default=False, description="Allow sudo commands")
        blocked_commands: str = Field(
            default="rm -rf /,format,mkfs,dd if=,shutdown,reboot",
            description="Comma-separated blocked patterns"
        )
        default_working_dir: str = Field(default="/data/user-files", description="Default working directory")

    class UserValves(BaseModel):
        preferred_shell: str = Field(default="auto", description="Shell: auto, bash, sh, powershell")

    def __init__(self):
        self.citation = False
        self.file_handler = False
        self.valves = self.Valves()

    def _get_timeout(self, requested: int = 0) -> int:
        default = getattr(self.valves, 'default_timeout', TIMEOUT)
        timeout = requested if requested > 0 else default
        return max(1, min(120, timeout))

    def _get_max_output(self) -> int:
        kb = getattr(self.valves, 'max_output_kb', 50)
        return kb * 1024

    def run_command(self, command: str, working_dir: str = "", timeout: int = 0) -> str:
        """
        Execute a shell command and return output.

        Args:
            command: The command to execute
            working_dir: Optional directory (default: current)
            timeout: Timeout in seconds (default: 30, max: 120)

        Returns:
            Command output or error message.
        """
        if not command or not command.strip():
            return "Error: No command provided."

        if _is_blocked(command):
            return "Error: This command is blocked for safety reasons."

        warnings = _has_warnings(command)
        warning_msg = ""
        if warnings:
            warning_msg = f"[Warning: {'; '.join(warnings)}]\n\n"

        cmd_timeout = self._get_timeout(timeout)

        cwd = None
        if working_dir:
            if working_dir.startswith("~"):
                working_dir = os.path.expanduser(working_dir)
            if os.path.isdir(working_dir):
                cwd = working_dir
            else:
                return f"Error: Working directory not found: {working_dir}"

        try:
            shell_cmd = _get_shell()
            full_cmd = shell_cmd + [command]

            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=cmd_timeout,
                cwd=cwd,
                env={**os.environ, "LANG": "en_US.UTF-8"}
            )

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                if output:
                    output += "\n--- stderr ---\n"
                output += result.stderr

            if not output.strip():
                output = "(Command completed with no output)"

            max_out = self._get_max_output()
            if len(output) > max_out:
                output = output[:max_out] + f"\n\n[Output truncated at {max_out} characters]"

            if result.returncode != 0:
                output += f"\n\n[Exit code: {result.returncode}]"

            return warning_msg + output

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {cmd_timeout} seconds."
        except FileNotFoundError as e:
            return f"Error: Command not found - {e}"
        except PermissionError:
            return "Error: Permission denied."
        except Exception as e:
            return f"Error executing command: {str(e)}"

    def get_system_info(self) -> str:
        """Get information about the current system."""
        home = os.path.expanduser("~")
        cwd = os.getcwd()
        shell = _get_shell()[0]

        info = [
            "System Information:", "=" * 40,
            f"Operating System: {SYSTEM}",
            f"Platform: {platform.platform()}",
            f"Architecture: {platform.machine()}",
            f"Shell: {shell}",
            f"Home Directory: {home}",
            f"Current Directory: {cwd}",
            f"Python Version: {platform.python_version()}",
        ]
        return "\n".join(info)

    def quick_search(self, query: str, path: str = "~", file_type: str = "*") -> str:
        """
        Quick file search helper.

        Args:
            query: Search term (filename pattern)
            path: Where to search (default: home)
            file_type: File extension filter (default: all)

        Returns:
            Search results.
        """
        if path.startswith("~"):
            path = os.path.expanduser(path)

        if not os.path.exists(path):
            return f"Error: Path not found: {path}"

        if SYSTEM == "Windows":
            filter_ext = f"-Filter *.{file_type}" if file_type != "*" else ""
            cmd = f'Get-ChildItem -Path "{path}" -Recurse {filter_ext} -ErrorAction SilentlyContinue | Where-Object {{ $_.Name -like "*{query}*" }} | Select-Object -First 50 FullName, Length, LastWriteTime | Format-Table -AutoSize'
        else:
            ext_filter = f"-name '*.{file_type}'" if file_type != "*" else ""
            cmd = f"find '{path}' {ext_filter} -type f -iname '*{query}*' 2>/dev/null | head -50"

        return self.run_command(cmd)

    def search_content(self, pattern: str, path: str = ".", file_type: str = "*") -> str:
        """
        Search for content inside files.

        Args:
            pattern: Text pattern to search
            path: Directory to search
            file_type: File extension (e.g., "py", "txt")

        Returns:
            Matching lines with file paths.
        """
        if path.startswith("~"):
            path = os.path.expanduser(path)

        if not os.path.exists(path):
            return f"Error: Path not found: {path}"

        if SYSTEM == "Windows":
            filter_ext = f"-Include *.{file_type}" if file_type != "*" else ""
            cmd = f'Get-ChildItem -Path "{path}" -Recurse {filter_ext} -ErrorAction SilentlyContinue | Select-String -Pattern "{pattern}" | Select-Object -First 100 | Format-Table -AutoSize Path, LineNumber, Line'
        else:
            include = f"--include='*.{file_type}'" if file_type != "*" else ""
            cmd = f"grep -rn '{pattern}' '{path}' {include} 2>/dev/null | head -100"

        return self.run_command(cmd)

    def create_project_structure(self, project_name: str, template: str = "basic", base_path: str = "/data/projects") -> str:
        """
        Create a folder structure for a new project.

        Args:
            project_name: Name of the project
            template: Type: basic, python, web, nodejs, docker, data
            base_path: Where to create (default: /data/projects)

        Returns:
            Created folder structure.
        """
        safe_name = "".join(c for c in project_name if c.isalnum() or c in "-_").strip()
        if not safe_name:
            return "Error: Invalid project name."

        project_path = f"{base_path}/{safe_name}"

        templates = {
            "basic": ["src", "docs", "tests", "config"],
            "python": ["src", "src/__init__.py", "tests", "tests/__init__.py", "docs", "config", "scripts", "requirements.txt", "README.md", ".gitignore"],
            "web": ["src", "src/components", "src/pages", "src/utils", "public", "public/images", "public/css", "public/js", "assets", "docs", "README.md"],
            "nodejs": ["src", "src/routes", "src/controllers", "src/models", "src/middleware", "public", "public/css", "public/js", "config", "tests", "package.json", "README.md", ".gitignore"],
            "docker": ["app", "app/src", "config", "scripts", "data", "logs", "docker-compose.yml", "Dockerfile", ".env.example", "README.md"],
            "data": ["data", "data/raw", "data/processed", "data/external", "notebooks", "models", "models/trained", "models/evaluation", "reports", "reports/figures", "src", "src/data", "src/features", "src/models", "config", "requirements.txt", "README.md"],
        }

        if template not in templates:
            return f"Error: Unknown template '{template}'. Available: {', '.join(templates.keys())}"

        structure = templates[template]
        commands = [f"mkdir -p '{project_path}'"]

        for item in structure:
            full_path = f"{project_path}/{item}"
            if "." in item.split("/")[-1]:
                parent = "/".join(full_path.split("/")[:-1])
                commands.append(f"mkdir -p '{parent}'")
                commands.append(f"touch '{full_path}'")
            else:
                commands.append(f"mkdir -p '{full_path}'")

        full_script = " && ".join(commands)
        self.run_command(full_script)

        verify_cmd = f"find '{project_path}' -type d 2>/dev/null | head -30"
        structure_output = self.run_command(verify_cmd)

        return f"Project '{safe_name}' created with '{template}' template!\n\nLocation: {project_path}\n\nStructure:\n{structure_output}"

    def create_folder(self, folder_path: str, create_parents: bool = True) -> str:
        """Create a new folder."""
        if not folder_path.startswith("/"):
            folder_path = f"/data/projects/{folder_path}"

        if not (folder_path.startswith("/data/user-files") or folder_path.startswith("/data/projects")):
            return "Error: Can only create folders in writable areas"

        flag = "-p" if create_parents else ""
        result = self.run_command(f"mkdir {flag} '{folder_path}' && echo 'Folder created: {folder_path}'")
        return result

    def list_folder(self, path: str = "/data/user-files", show_hidden: bool = False, details: bool = True) -> str:
        """List contents of a folder."""
        flags = "-la" if details else "-1"
        if not show_hidden and details:
            flags = "-l"
        if details:
            flags += "h"

        cmd = f"ls {flags} '{path}' 2>/dev/null"
        result = self.run_command(cmd)

        if "No such file or directory" in result:
            return f"Error: Folder not found: {path}"

        return f"Contents of {path}:\n\n{result}"

    def check_disk_space(self) -> str:
        """Check disk space usage."""
        cmd = "df -h 2>/dev/null | grep -E '^/|Filesystem'"
        result = self.run_command(cmd)
        return f"Disk Space Usage:\n{'='*50}\n{result}"

    def check_memory(self) -> str:
        """Check memory (RAM) usage."""
        cmd = """grep -E '^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapTotal|SwapFree):' /proc/meminfo 2>/dev/null | awk '{
            val = $2/1024/1024;
            printf "%-15s %6.2f GB\\n", $1, val
        }'"""
        result = self.run_command(cmd)
        summary = self.run_command("awk '/MemTotal/{t=$2} /MemAvailable/{a=$2} END{printf \"Used: %.1fG / %.1fG (%.0f%%)\\n\", (t-a)/1024/1024, t/1024/1024, (t-a)/t*100}' /proc/meminfo 2>/dev/null").strip()
        return f"Memory Usage:\n{'='*50}\n{summary}\n\nDetails:\n{result}"

    def server_health(self) -> str:
        """Quick server health check."""
        checks = []

        uptime_raw = self.run_command("cat /proc/uptime 2>/dev/null | awk '{print int($1/86400)\"d \"int(($1%86400)/3600)\"h \"int(($1%3600)/60)\"m\"}'").strip()
        if uptime_raw and "Exit code" not in uptime_raw:
            checks.append(f"UPTIME: {uptime_raw}")

        disk = self.run_command("df -h / 2>/dev/null | tail -1 | awk '{print $5 \" used of \" $2}'").strip()
        checks.append(f"DISK: {disk}")

        mem_total = self.run_command("grep MemTotal /proc/meminfo 2>/dev/null | awk '{printf \"%.1fG\", $2/1024/1024}'").strip()
        mem_avail = self.run_command("grep MemAvailable /proc/meminfo 2>/dev/null | awk '{printf \"%.1fG\", $2/1024/1024}'").strip()
        if mem_total and mem_avail and "Exit code" not in mem_total:
            checks.append(f"MEMORY: {mem_avail} available of {mem_total}")

        load = self.run_command("cat /proc/loadavg 2>/dev/null | awk '{print $1, $2, $3}'").strip()
        if load and "Exit code" not in load:
            checks.append(f"LOAD: {load} (1m 5m 15m)")

        return f"Server Health Check\n{'='*50}\n" + "\n".join(checks) + f"\n{'='*50}\nAll checks complete."
