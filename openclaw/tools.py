"""Tools that the AI agent can call to interact with the codebase."""

import os
import subprocess
import json
from pathlib import Path


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Returns the file content with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to project root"},
                    "start_line": {"type": "integer", "description": "Start line (1-indexed, optional)"},
                    "end_line": {"type": "integer", "description": "End line (1-indexed, optional)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with the given content. Parent directories are created automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to project root"},
                    "content": {"type": "string", "description": "Full file content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific string in a file. The old_string must match exactly (including whitespace).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to project root"},
                    "old_string": {"type": "string", "description": "Exact string to find and replace"},
                    "new_string": {"type": "string", "description": "Replacement string"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories at the given path. Returns names with type indicators (/ for dirs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path relative to project root. Use '.' for root."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a pattern in project files using grep. Returns matching lines with file paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex supported)"},
                    "path": {"type": "string", "description": "Directory or file to search in (default: '.')"},
                    "include": {"type": "string", "description": "File glob pattern to include, e.g. '*.py'"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command in the project directory. Use for running tests, installing packages, git operations, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Stage all changes and create a git commit with the given message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_done",
            "description": "Call this when the task is fully completed. Provide a summary of what was done.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Summary of what was accomplished"},
                },
                "required": ["summary"],
            },
        },
    },
]


class ToolExecutor:
    """Executes tool calls from the LLM against the project filesystem."""

    def __init__(self, project_root: str):
        self.root = Path(project_root).resolve()

    def _resolve(self, path: str) -> Path:
        """Resolve a relative path against project root, with safety check."""
        resolved = (self.root / path).resolve()
        if not str(resolved).startswith(str(self.root)):
            raise ValueError(f"Path escapes project root: {path}")
        return resolved

    def execute(self, name: str, args: dict) -> str:
        """Execute a tool by name and return the result string."""
        try:
            handler = getattr(self, f"_tool_{name}", None)
            if not handler:
                return f"Error: Unknown tool '{name}'"
            return handler(**args)
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    def _tool_read_file(self, path: str, start_line: int | None = None, end_line: int | None = None) -> str:
        fp = self._resolve(path)
        if not fp.exists():
            return f"Error: File not found: {path}"
        if not fp.is_file():
            return f"Error: Not a file: {path}"

        lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
        start = (start_line or 1) - 1
        end = end_line or len(lines)
        selected = lines[start:end]

        numbered = [f"{i + start + 1:4d} | {line}" for i, line in enumerate(selected)]
        return f"File: {path} ({len(lines)} lines total)\n" + "\n".join(numbered)

    def _tool_write_file(self, path: str, content: str) -> str:
        fp = self._resolve(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        return f"OK: Wrote {lines} lines to {path}"

    def _tool_edit_file(self, path: str, old_string: str, new_string: str) -> str:
        fp = self._resolve(path)
        if not fp.exists():
            return f"Error: File not found: {path}"

        text = fp.read_text(encoding="utf-8")
        count = text.count(old_string)
        if count == 0:
            return f"Error: old_string not found in {path}"
        if count > 1:
            return f"Error: old_string found {count} times in {path}, must be unique. Provide more context."

        new_text = text.replace(old_string, new_string, 1)
        fp.write_text(new_text, encoding="utf-8")
        return f"OK: Replaced 1 occurrence in {path}"

    def _tool_list_dir(self, path: str = ".") -> str:
        dp = self._resolve(path)
        if not dp.exists():
            return f"Error: Directory not found: {path}"
        if not dp.is_dir():
            return f"Error: Not a directory: {path}"

        entries = sorted(dp.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        result = []
        for entry in entries:
            rel = entry.relative_to(self.root)
            if entry.name.startswith(".") and entry.name in (".git", "__pycache__", ".venv", "venv"):
                continue
            suffix = "/" if entry.is_dir() else f"  ({entry.stat().st_size} bytes)"
            result.append(f"  {rel}{suffix}")

        return f"Directory: {path}\n" + "\n".join(result) if result else f"Directory: {path} (empty)"

    def _tool_search_code(self, pattern: str, path: str = ".", include: str | None = None) -> str:
        dp = self._resolve(path)
        cmd = ["grep", "-rn", "--color=never"]
        if include:
            cmd.extend(["--include", include])
        cmd.extend([pattern, str(dp)])

        # Try grep first, fall back to findstr on Windows
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=str(self.root))
            output = result.stdout
        except FileNotFoundError:
            # Windows fallback: use Python-based search
            output = self._python_search(pattern, dp, include)

        if not output.strip():
            return f"No matches found for '{pattern}'"

        # Make paths relative
        lines = output.strip().splitlines()[:50]  # cap at 50 results
        cleaned = []
        for line in lines:
            line = line.replace(str(self.root) + os.sep, "").replace(str(self.root) + "/", "")
            cleaned.append(line)

        return "\n".join(cleaned)

    def _python_search(self, pattern: str, search_path: Path, include: str | None = None) -> str:
        """Fallback search using Python when grep is not available."""
        import re
        import fnmatch

        results = []
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error:
            compiled = re.compile(re.escape(pattern), re.IGNORECASE)

        skip_dirs = {".git", "__pycache__", ".venv", "venv", "node_modules", ".mypy_cache"}

        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in files:
                if include and not fnmatch.fnmatch(fname, include):
                    continue
                fpath = Path(root) / fname
                try:
                    text = fpath.read_text(encoding="utf-8", errors="ignore")
                    for i, line in enumerate(text.splitlines(), 1):
                        if compiled.search(line):
                            rel = fpath.relative_to(self.root)
                            results.append(f"{rel}:{i}:{line}")
                            if len(results) >= 50:
                                return "\n".join(results)
                except (OSError, UnicodeDecodeError):
                    continue

        return "\n".join(results)

    def _tool_run_command(self, command: str, timeout: int = 60) -> str:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.root),
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += ("\n" if output else "") + result.stderr

            # Truncate very long output
            if len(output) > 8000:
                output = output[:4000] + "\n\n... (truncated) ...\n\n" + output[-2000:]

            status = "OK" if result.returncode == 0 else f"FAILED (exit code {result.returncode})"
            return f"[{status}]\n{output}" if output else f"[{status}]"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout}s"

    def _tool_git_commit(self, message: str) -> str:
        try:
            subprocess.run(["git", "add", "-A"], cwd=str(self.root), capture_output=True, timeout=10)
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return f"OK: Committed: {message}"
            return f"Git commit output: {result.stdout}\n{result.stderr}"
        except Exception as e:
            return f"Error: {e}"

    def _tool_task_done(self, summary: str) -> str:
        return f"__TASK_DONE__:{summary}"
