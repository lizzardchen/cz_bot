"""Core agent engine: connects to LLM, orchestrates tool calls in a loop."""

import json
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from openclaw.config import Config
from openclaw.tools import TOOLS_SCHEMA, ToolExecutor

console = Console()

SYSTEM_PROMPT = """\
You are OpenClaw, an autonomous coding agent. You operate on a real codebase.
Your job is to fulfill the user's request by reading, writing, and modifying code files.

## Capabilities
- Read files, list directories, search code
- Write new files, edit existing files (find-and-replace)
- Run shell commands (install packages, run tests, build, etc.)
- Create git commits

## Rules
1. ALWAYS read relevant files before modifying them.
2. Make minimal, focused changes. Don't rewrite entire files unless necessary.
3. After making changes, verify them (re-read the file, run tests if applicable).
4. When the task is complete, call task_done with a summary.
5. If you need clarification, ask in your response text — but try to be autonomous.
6. Write clean, idiomatic code following the project's existing style.
7. Create directories and files as needed.
8. If the project has tests, run them after changes to verify nothing broke.

## Important
- File paths are relative to the project root.
- You can call multiple tools in sequence within one turn.
- Be thorough but efficient. Read what you need, change what you need, verify, done.
"""


def _build_client(config: Config) -> OpenAI:
    """Build OpenAI-compatible client based on provider config."""
    provider = config.llm.provider.lower()

    base_urls = {
        # 国际
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        # 国产
        "deepseek": "https://api.deepseek.com",
        "glm": "https://open.bigmodel.cn/api/paas/v4",             # 智谱GLM
        "minimax": "https://api.minimax.chat/v1",                   # MiniMax
        "moonshot": "https://api.moonshot.cn/v1",                   # Moonshot/Kimi
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",  # 阿里通义千问
        "doubao": "https://ark.cn-beijing.volces.com/api/v3",       # 字节豆包(火山引擎)
        "spark": "https://spark-api-open.xf-yun.com/v1",            # 讯飞星火
        "baichuan": "https://api.baichuan-ai.com/v1",               # 百川
        "yi": "https://api.lingyiwanwu.com/v1",                     # 零一万物
        "stepfun": "https://api.stepfun.com/v1",                    # 阶跃星辰
    }

    api_base = config.llm.api_base or base_urls.get(provider, base_urls["openai"])

    return OpenAI(api_key=config.llm.api_key, base_url=api_base)


def run_agent(task: str, config: Config, on_message=None) -> str:
    """
    Run the agent loop for a given task.

    Args:
        task: The user's natural language request
        config: Application config
        on_message: Optional callback(role, content) for streaming output

    Returns:
        Final summary string
    """
    client = _build_client(config)
    executor = ToolExecutor(config.project.root)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    max_iterations = 30
    iteration = 0

    def emit(role: str, content: str):
        if on_message:
            on_message(role, content)
        elif role == "assistant":
            console.print(Panel(Markdown(content), title="🤖 Agent", border_style="cyan"))
        elif role == "tool_call":
            console.print(f"  🔧 [dim]{content}[/dim]")
        elif role == "tool_result":
            # Show truncated result
            lines = content.splitlines()
            preview = "\n".join(lines[:10])
            if len(lines) > 10:
                preview += f"\n  ... ({len(lines) - 10} more lines)"
            console.print(f"  📋 [dim]{preview}[/dim]")

    while iteration < max_iterations:
        iteration += 1

        try:
            response = client.chat.completions.create(
                model=config.llm.model,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                max_tokens=config.llm.max_tokens,
                temperature=config.llm.temperature,
            )
        except Exception as e:
            error_msg = f"LLM API error: {e}"
            emit("error", error_msg)
            return error_msg

        choice = response.choices[0]
        msg = choice.message

        # Add assistant message to history
        messages.append(msg.model_dump(exclude_none=True))

        # If there's text content, show it
        if msg.content:
            emit("assistant", msg.content)

        # If no tool calls, we're done
        if not msg.tool_calls:
            return msg.content or "(no response)"

        # Execute each tool call
        task_summary = None
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            try:
                fn_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            emit("tool_call", f"{fn_name}({json.dumps(fn_args, ensure_ascii=False)[:200]})")

            result = executor.execute(fn_name, fn_args)

            emit("tool_result", result)

            # Check if task is done
            if result.startswith("__TASK_DONE__:"):
                task_summary = result[len("__TASK_DONE__:"):]

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        if task_summary:
            # Auto-commit if configured
            if config.project.auto_commit:
                commit_result = executor.execute("git_commit", {"message": f"feat: {task_summary[:72]}"})
                emit("tool_result", commit_result)
            return task_summary

    return "Agent reached maximum iterations without completing the task."


def chat_session(config: Config):
    """Interactive multi-turn chat session with the agent."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

    history_file = config.project.root + "/.openclaw_history"
    session = PromptSession(history=FileHistory(history_file))

    console.print(Panel(
        "[bold cyan]🤖 OpenClaw Bot[/bold cyan]\n"
        "自主编码 Agent — 告诉我你想要什么，我来实现。\n\n"
        f"项目目录: [green]{config.project.root}[/green]\n"
        f"模型: [yellow]{config.llm.model}[/yellow]\n\n"
        "[dim]输入 exit/quit 退出, clear 清屏[/dim]",
        border_style="cyan",
    ))

    while True:
        try:
            user_input = session.prompt("\n🧑 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n👋 再见!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
            console.print("👋 再见!")
            break
        if user_input.lower() == "clear":
            console.clear()
            continue

        console.print()
        result = run_agent(user_input, config)
        console.print(Panel(f"✅ {result}", title="完成", border_style="green"))
