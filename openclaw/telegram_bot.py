"""Telegram bot interface for OpenClaw agent."""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from openclaw.config import Config
from openclaw.agent import run_agent

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot that forwards messages to the coding agent."""

    def __init__(self, config: Config):
        self.config = config
        self._running = False

    def _is_allowed(self, user_id: str, username: str | None) -> bool:
        """Check if user is allowed to use the bot."""
        allowed = self.config.telegram.allowed_users
        if not allowed:
            return True  # No restrictions
        return str(user_id) in allowed or (username and username in allowed)

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not self._is_allowed(str(user.id), user.username):
            await update.message.reply_text("⛔ 你没有权限使用此 Bot。")
            return

        await update.message.reply_text(
            "🤖 *OpenClaw Bot*\n\n"
            "我是你的自主编码 Agent。\n"
            "直接发消息告诉我你想要什么功能，我会自动修改代码来实现。\n\n"
            f"📁 项目目录: `{self.config.project.root}`\n"
            f"🧠 模型: `{self.config.llm.model}`\n\n"
            "命令:\n"
            "/status - 查看状态\n"
            "/project - 查看项目结构",
            parse_mode="Markdown",
        )

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not self._is_allowed(str(user.id), user.username):
            return

        from openclaw.tools import ToolExecutor
        executor = ToolExecutor(self.config.project.root)
        tree = executor.execute("list_dir", {"path": "."})

        await update.message.reply_text(
            f"🤖 *OpenClaw Bot Status*\n\n"
            f"📁 项目: `{self.config.project.root}`\n"
            f"🧠 模型: `{self.config.llm.model}`\n"
            f"🔑 Provider: `{self.config.llm.provider}`\n"
            f"📝 Auto-commit: `{self.config.project.auto_commit}`\n",
            parse_mode="Markdown",
        )

    async def _cmd_project(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not self._is_allowed(str(user.id), user.username):
            return

        from openclaw.tools import ToolExecutor
        executor = ToolExecutor(self.config.project.root)
        tree = executor.execute("list_dir", {"path": "."})

        await update.message.reply_text(f"```\n{tree}\n```", parse_mode="Markdown")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages as agent tasks."""
        user = update.effective_user
        if not self._is_allowed(str(user.id), user.username):
            await update.message.reply_text("⛔ 你没有权限使用此 Bot。")
            return

        task = update.message.text
        if not task:
            return

        # Send "working" indicator
        thinking_msg = await update.message.reply_text("🔄 正在分析需求并执行...")

        # Collect agent output
        output_lines = []

        def on_message(role: str, content: str):
            if role == "tool_call":
                output_lines.append(f"🔧 {content[:100]}")
            elif role == "assistant":
                output_lines.append(content)

        # Run agent in thread to avoid blocking
        try:
            result = await asyncio.to_thread(run_agent, task, self.config, on_message)
        except Exception as e:
            await thinking_msg.edit_text(f"❌ 执行出错: {e}")
            return

        # Build response
        response_parts = []
        if output_lines:
            # Show last few tool calls as context
            tool_calls = [l for l in output_lines if l.startswith("🔧")]
            if tool_calls:
                response_parts.append("*执行步骤:*\n" + "\n".join(tool_calls[-5:]))

        response_parts.append(f"\n✅ *完成:* {result}")

        response_text = "\n".join(response_parts)

        # Telegram has a 4096 char limit
        if len(response_text) > 4000:
            response_text = response_text[:2000] + "\n\n...(truncated)...\n\n" + response_text[-1500:]

        try:
            await thinking_msg.edit_text(response_text, parse_mode="Markdown")
        except Exception:
            # Fallback without markdown if parsing fails
            await thinking_msg.edit_text(response_text)

    def run(self):
        """Start the Telegram bot (blocking)."""
        if not self.config.telegram.token:
            raise ValueError("Telegram bot token not configured. Set it in ~/.openclaw/config.json")

        print(f"🤖 OpenClaw Telegram Bot 启动中...")
        print(f"📁 项目目录: {self.config.project.root}")
        print(f"🧠 模型: {self.config.llm.model}")

        app = Application.builder().token(self.config.telegram.token).build()

        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("status", self._cmd_status))
        app.add_handler(CommandHandler("project", self._cmd_project))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        print("✅ Bot 已启动，等待消息...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
