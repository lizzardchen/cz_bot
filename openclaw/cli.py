"""CLI entry point for OpenClaw Bot."""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="claw",
        description="🤖 OpenClaw Bot - 自主编码 Agent，一句话实现需求",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    sub.add_parser("init", help="初始化配置")

    # run: one-shot task
    run_p = sub.add_parser("run", help="执行一个编码任务")
    run_p.add_argument("task", nargs="*", help="任务描述 (自然语言)")
    run_p.add_argument("-p", "--project", default=".", help="项目目录 (默认当前目录)")

    # chat: interactive session
    chat_p = sub.add_parser("chat", help="交互式对话模式")
    chat_p.add_argument("-p", "--project", default=".", help="项目目录 (默认当前目录)")

    # telegram: start telegram bot
    tg_p = sub.add_parser("telegram", help="启动 Telegram Bot")
    tg_p.add_argument("-p", "--project", default=".", help="项目目录 (默认当前目录)")

    # status
    sub.add_parser("status", help="查看配置状态")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "init":
        from openclaw.config import init_config_interactive
        init_config_interactive()
        return

    if args.command == "status":
        _show_status()
        return

    # Commands that need config
    from openclaw.config import load_config
    config = load_config()

    if not config.llm.api_key:
        print("❌ 未配置 API Key。请先运行: claw init")
        print("   或设置环境变量: export OPENCLAW_API_KEY=your-key")
        sys.exit(1)

    # Override project root if specified
    if hasattr(args, "project"):
        config.project.root = str(Path(args.project).resolve())

    if args.command == "run":
        task = " ".join(args.task) if args.task else None
        if not task:
            print("❌ 请提供任务描述: claw run '添加一个登录功能'")
            sys.exit(1)

        from openclaw.agent import run_agent
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        console.print(Panel(
            f"📋 任务: {task}\n📁 项目: {config.project.root}\n🧠 模型: {config.llm.model}",
            title="🤖 OpenClaw",
            border_style="cyan",
        ))

        result = run_agent(task, config)
        console.print(Panel(f"✅ {result}", title="完成", border_style="green"))

    elif args.command == "chat":
        from openclaw.agent import chat_session
        chat_session(config)

    elif args.command == "telegram":
        if not config.telegram.enabled or not config.telegram.token:
            print("❌ Telegram Bot 未配置。请先运行 claw init 或编辑 ~/.openclaw/config.json")
            sys.exit(1)

        from openclaw.telegram_bot import TelegramBot
        bot = TelegramBot(config)
        bot.run()


def _show_status():
    from rich.console import Console
    from rich.panel import Panel
    from openclaw.config import load_config, get_config_path

    console = Console()
    config_path = get_config_path()

    lines = [f"📄 配置文件: {config_path} {'✅' if config_path.exists() else '❌ 未创建'}"]

    if config_path.exists():
        config = load_config()
        lines.append(f"🧠 Provider: {config.llm.provider}")
        lines.append(f"🧠 Model: {config.llm.model}")
        lines.append(f"🔑 API Key: {'✅ 已配置' if config.llm.api_key else '❌ 未配置'}")
        lines.append(f"📁 项目目录: {config.project.root}")
        lines.append(f"📱 Telegram: {'✅ 已启用' if config.telegram.enabled else '❌ 未启用'}")
    else:
        lines.append("\n运行 [bold]claw init[/bold] 初始化配置")

    console.print(Panel("\n".join(lines), title="🤖 OpenClaw Status", border_style="cyan"))


if __name__ == "__main__":
    main()
