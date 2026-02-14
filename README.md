# 🤖 OpenClaw Bot

**自主编码 Agent** — 一句话描述需求，它自动连接 LLM，读取/修改代码，实现功能。

可以在手机 (Android Termux) 或电脑上运行。

## 核心能力

- 📝 **自动读写代码** — 读取文件、搜索代码、创建/修改文件
- 🔧 **执行命令** — 运行 shell 命令、安装依赖、跑测试
- 📦 **Git 管理** — 自动提交变更
- 🧠 **多 LLM 支持** — DeepSeek、OpenAI、OpenRouter、Moonshot、通义千问
- 💬 **双交互模式** — CLI 命令行 + Telegram Bot
- 📱 **手机可用** — 通过 Termux 在 Android 上本地运行

## 快速开始

### 安装

```bash
git clone https://github.com/lizzardchen/cz_bot.git openclaw_bot
cd openclaw_bot
pip install -e .
```

### 初始化配置

```bash
claw init
```

按提示填入 API Key 和项目目录。

### 使用

```bash
# 交互式对话
claw chat

# 单次任务
claw run "给项目添加一个 README"

# 指定项目目录
claw run -p /path/to/your/project "添加用户登录功能"

# 启动 Telegram Bot
claw telegram
```

## 配置

配置文件位于 `~/.openclaw/config.json`：

```json
{
  "llm": {
    "provider": "deepseek",
    "api_key": "sk-xxx",
    "model": "deepseek-chat",
    "max_tokens": 4096,
    "temperature": 0.3
  },
  "telegram": {
    "enabled": true,
    "token": "your-telegram-bot-token",
    "allowed_users": ["your_telegram_user_id"]
  },
  "project": {
    "root": ".",
    "auto_commit": true
  }
}
```

### 支持的 LLM Provider

| Provider | provider 值 | model 值示例 | 注册地址 |
|----------|------------|-------------|---------|
| **DeepSeek** | `deepseek` | `deepseek-chat` | https://platform.deepseek.com |
| **智谱GLM** | `glm` | `glm-4-plus` | https://open.bigmodel.cn |
| **MiniMax** | `minimax` | `MiniMax-Text-01` | https://platform.minimaxi.com |
| **Moonshot/Kimi** | `moonshot` | `moonshot-v1-8k` | https://platform.moonshot.cn |
| **通义千问** | `dashscope` | `qwen-max` | https://dashscope.console.aliyun.com |
| **字节豆包** | `doubao` | `doubao-pro-256k` | https://console.volcengine.com/ark |
| **讯飞星火** | `spark` | `generalv3.5` | https://console.xfyun.cn |
| **百川** | `baichuan` | `Baichuan4` | https://platform.baichuan-ai.com |
| **零一万物** | `yi` | `yi-large` | https://platform.lingyiwanwu.com |
| **阶跃星辰** | `stepfun` | `step-2-16k` | https://platform.stepfun.com |
| OpenAI | `openai` | `gpt-4o` | https://platform.openai.com |
| OpenRouter | `openrouter` | `anthropic/claude-opus-4-5` | https://openrouter.ai |

> **注意**: 字节豆包需要在火山引擎控制台创建"推理接入点"后，用接入点 ID 作为 model 值。

### 环境变量

也可以通过环境变量配置（优先级高于配置文件）：

```bash
export OPENCLAW_API_KEY=sk-xxx
export OPENCLAW_MODEL=deepseek-chat
export OPENCLAW_TG_TOKEN=your-telegram-token
```

## 在手机上运行 (Android)

### 前置条件

- Android 7.0+ 手机
- 安装 [Termux](https://f-droid.org/packages/com.termux/)（**必须从 F-Droid 安装**，Google Play 版已停更）
- 一个 LLM API Key（推荐 DeepSeek，注册即送额度）

### 方法一：电脑开发，传到手机

在电脑上开发好代码后，把整个项目传到手机：

```bash
# USB 传输 (推荐)
# 1. 手机连电脑，把 openclaw_bot 文件夹复制到手机存储
# 2. 在 Termux 中:
cp -r /sdcard/openclaw_bot ~/openclaw_bot
bash ~/openclaw_bot/termux_setup.sh

# 局域网传输 (手机和电脑在同一 WiFi)
# 电脑上:
cd openclaw_bot
python -m http.server 8080
# 手机 Termux 中:
pkg install wget -y
wget -r -np http://电脑IP:8080/ -P ~/openclaw_bot
bash ~/openclaw_bot/termux_setup.sh

# Git 传输 (推荐，方便后续同步)
# 1. 电脑上 push 到 GitHub/Gitee
# 2. 手机 Termux 中:
pkg install git -y
git clone https://github.com/lizzardchen/cz_bot.git ~/openclaw_bot
bash ~/openclaw_bot/termux_setup.sh
```

### 方法二：手机上直接安装

如果代码已经在 GitHub/Gitee 上：

```bash
pkg install git -y
git clone https://github.com/lizzardchen/cz_bot.git ~/openclaw_bot
bash ~/openclaw_bot/termux_setup.sh
```

### 安装后使用

```bash
claw chat                          # 交互式对话
claw run '给项目加个日志功能'        # 单次任务
claw telegram                      # Telegram Bot 模式
bash ~/claw-chat.sh                # 快捷启动
```

### Termux 小技巧

- **后台运行 Telegram Bot**: `nohup claw telegram > ~/bot.log 2>&1 &`
- **防杀进程**: 手机设置 → 应用管理 → Termux → 电池优化 → 不优化
- **开机自启**: 安装 Termux:Boot，脚本自动创建在 `~/.shortcuts/`
- **桌面快捷方式**: 安装 Termux:Widget，添加小组件即可一键启动
- **同步代码回电脑**: `cd ~/openclaw_bot && git push`

## 工作原理

```
你的需求 (自然语言)
       ↓
   OpenClaw Agent
       ↓
   连接 LLM API (DeepSeek/OpenAI/...)
       ↓
   LLM 分析需求，调用工具:
     - read_file: 读取代码
     - search_code: 搜索代码
     - edit_file: 修改代码
     - write_file: 创建文件
     - run_command: 执行命令
     - git_commit: 提交变更
       ↓
   循环执行直到任务完成
       ↓
   返回结果摘要
```

## 项目结构

```
openclaw_bot/
├── openclaw/
│   ├── __init__.py      # 版本信息
│   ├── agent.py         # 核心 Agent 引擎 (LLM 循环)
│   ├── cli.py           # CLI 入口
│   ├── config.py        # 配置管理
│   ├── telegram_bot.py  # Telegram Bot 界面
│   └── tools.py         # Agent 工具 (文件/命令/Git)
├── pyproject.toml       # 依赖管理
├── termux_setup.sh      # Termux 安装脚本
└── README.md
```

## License

MIT
