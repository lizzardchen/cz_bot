"""Configuration management."""

import json
import os
from pathlib import Path
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: str = "deepseek"  # deepseek, openai, openrouter, minimax, glm, moonshot, dashscope
    api_key: str = ""
    api_base: str | None = None
    model: str = "deepseek-chat"
    max_tokens: int = 4096
    temperature: float = 0.3


class TelegramConfig(BaseModel):
    """Telegram bot configuration."""
    enabled: bool = False
    token: str = ""
    allowed_users: list[str] = Field(default_factory=list)


def _detect_bot_dir() -> str:
    """Find the openclaw_bot install directory."""
    # Check common locations
    from pathlib import Path
    candidates = [
        Path.home() / "openclaw_bot",
        Path(__file__).resolve().parent.parent,  # ../openclaw/ -> ../
    ]
    for c in candidates:
        if (c / "pyproject.toml").exists():
            return str(c)
    return "."


class ProjectConfig(BaseModel):
    """Project/workspace configuration."""
    root: str = "."  # project root to operate on; defaults to bot's own repo
    auto_commit: bool = True
    branch: str = "main"


class Config(BaseModel):
    """Root configuration."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    project: ProjectConfig = Field(default_factory=ProjectConfig)


def get_config_dir() -> Path:
    """Get config directory path."""
    return Path.home() / ".openclaw"


def get_config_path() -> Path:
    """Get config file path."""
    return get_config_dir() / "config.json"


def load_config() -> Config:
    """Load config from file, env vars, or defaults."""
    path = get_config_path()
    data = {}

    if path.exists():
        with open(path) as f:
            data = json.load(f)

    # Environment variable overrides
    if api_key := os.environ.get("OPENCLAW_API_KEY"):
        data.setdefault("llm", {})["api_key"] = api_key
    if api_base := os.environ.get("OPENCLAW_API_BASE"):
        data.setdefault("llm", {})["api_base"] = api_base
    if model := os.environ.get("OPENCLAW_MODEL"):
        data.setdefault("llm", {})["model"] = model
    if tg_token := os.environ.get("OPENCLAW_TG_TOKEN"):
        data.setdefault("telegram", {})["token"] = tg_token
        data["telegram"]["enabled"] = True

    return Config.model_validate(data)


def save_config(config: Config) -> None:
    """Save config to file."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(config.model_dump(), f, indent=2, ensure_ascii=False)


def init_config_interactive() -> Config:
    """Interactive config setup."""
    print("🤖 OpenClaw Bot 初始化配置")
    print("=" * 40)

    config = Config()

    # LLM setup
    print("\n📡 LLM 配置")
    print("支持的 provider: deepseek, openai, openrouter")
    provider = input(f"Provider [{config.llm.provider}]: ").strip()
    if provider:
        config.llm.provider = provider

    api_key = input("API Key: ").strip()
    if api_key:
        config.llm.api_key = api_key

    model = input(f"Model [{config.llm.model}]: ").strip()
    if model:
        config.llm.model = model

    # Project setup
    default_root = _detect_bot_dir()
    print("\n📁 项目配置")
    print(f"  默认操作自己的代码仓库，也可以指定其他项目目录")
    root = input(f"项目根目录 [{default_root}]: ").strip()
    config.project.root = root if root else default_root

    # Telegram setup
    print("\n📱 Telegram Bot 配置 (可选, 回车跳过)")
    tg_token = input("Telegram Bot Token: ").strip()
    if tg_token:
        config.telegram.enabled = True
        config.telegram.token = tg_token
        users = input("允许的用户ID (逗号分隔, 空=所有人): ").strip()
        if users:
            config.telegram.allowed_users = [u.strip() for u in users.split(",")]

    save_config(config)
    print(f"\n✅ 配置已保存到 {get_config_path()}")
    return config
