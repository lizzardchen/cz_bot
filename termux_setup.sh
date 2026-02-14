#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# OpenClaw Bot - Termux 一键部署脚本
# 在 Android 手机上运行自主编码 Agent
#
# 一键部署 (在 Termux 中粘贴这一行):
#   curl -sL https://raw.githubusercontent.com/lizzardchen/cz_bot/main/termux_setup.sh | bash -s -- --key YOUR_API_KEY
#
# 或者分步:
#   pkg install -y git && git clone https://github.com/lizzardchen/cz_bot.git ~/openclaw_bot
#   bash ~/openclaw_bot/termux_setup.sh --key sk-xxx
#
# 参数:
#   --key KEY        API Key (必填，或设置环境变量 OPENCLAW_API_KEY)
#   --provider NAME  LLM 提供商 (默认: deepseek)
#   --model NAME     模型名 (默认: deepseek-chat)
#   --tg-token TOK   Telegram Bot Token (可选)
# ============================================================

set -e

# ---- 解析参数 ----
API_KEY="${OPENCLAW_API_KEY:-}"
PROVIDER="${OPENCLAW_PROVIDER:-deepseek}"
MODEL="${OPENCLAW_MODEL:-deepseek-chat}"
TG_TOKEN="${OPENCLAW_TG_TOKEN:-}"

while [ $# -gt 0 ]; do
    case "$1" in
        --key)      API_KEY="$2";    shift 2 ;;
        --provider) PROVIDER="$2";   shift 2 ;;
        --model)    MODEL="$2";      shift 2 ;;
        --tg-token) TG_TOKEN="$2";   shift 2 ;;
        *)          shift ;;
    esac
done

echo "🤖 OpenClaw Bot 一键部署"
echo "========================"
echo ""

# ---- 确定项目目录 ----
SCRIPT_DIR="$(cd "$(dirname "$0" 2>/dev/null)" 2>/dev/null && pwd 2>/dev/null || echo "")"
BOT_DIR="$HOME/openclaw_bot"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    BOT_DIR="$SCRIPT_DIR"
fi

# ---- 1. 安装系统依赖 ----
echo "📦 [1/5] 安装系统依赖..."
pkg update -y && pkg upgrade -y
pkg install -y python git

# ---- 2. 克隆代码 ----
if [ ! -f "$BOT_DIR/pyproject.toml" ]; then
    echo "� [2/5] 克隆代码..."
    git clone https://github.com/lizzardchen/cz_bot.git "$BOT_DIR"
else
    echo "📂 [2/5] 代码已存在，更新..."
    cd "$BOT_DIR" && git pull 2>/dev/null || true
fi

# ---- 3. 安装 Python 依赖 ----
echo "📥 [3/5] 安装 OpenClaw Bot..."
pip install --upgrade pip setuptools wheel
cd "$BOT_DIR"
pip install -e .

# ---- 4. 写入配置 ----
echo "⚙️  [4/5] 配置..."
CONFIG_DIR="$HOME/.openclaw"
CONFIG_FILE="$CONFIG_DIR/config.json"
mkdir -p "$CONFIG_DIR"

if [ -n "$API_KEY" ]; then
    # 有 API Key，直接写配置，无需交互
    TG_ENABLED="false"
    TG_SECTION=""
    if [ -n "$TG_TOKEN" ]; then
        TG_ENABLED="true"
    fi

    cat > "$CONFIG_FILE" << CONF_EOF
{
  "llm": {
    "provider": "$PROVIDER",
    "api_key": "$API_KEY",
    "model": "$MODEL",
    "max_tokens": 4096,
    "temperature": 0.3
  },
  "telegram": {
    "enabled": $TG_ENABLED,
    "token": "$TG_TOKEN",
    "allowed_users": []
  },
  "project": {
    "root": "$BOT_DIR",
    "auto_commit": true
  }
}
CONF_EOF
    echo "  ✅ 配置已自动生成"
elif [ ! -f "$CONFIG_FILE" ]; then
    # 没有 API Key 参数，进入交互式配置
    echo "  未检测到 --key 参数，进入交互式配置..."
    echo ""
    claw init
else
    echo "  ✅ 配置已存在，跳过"
fi

# ---- 5. 创建快捷方式 ----
echo "📱 [5/5] 创建快捷方式..."

cat > "$HOME/claw-chat.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/openclaw_bot
exec claw chat
EOF
chmod +x "$HOME/claw-chat.sh"

cat > "$HOME/claw-tg.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/openclaw_bot
exec claw telegram
EOF
chmod +x "$HOME/claw-tg.sh"

# Termux:Widget 桌面快捷方式
mkdir -p "$HOME/.shortcuts"
cp "$HOME/claw-chat.sh" "$HOME/.shortcuts/OpenClaw-Chat"
cp "$HOME/claw-tg.sh" "$HOME/.shortcuts/OpenClaw-Telegram"
chmod +x "$HOME/.shortcuts/"*

echo ""
echo "============================================"
echo "🎉 部署完成！"
echo "============================================"
echo ""
echo "现在可以直接使用:"
echo ""
echo "  claw chat                    # 交互式对话"
echo "  claw run '添加登录功能'       # 单次任务"
echo "  claw telegram                # 启动 Telegram Bot"
echo ""
echo "快捷方式:"
echo "  bash ~/claw-chat.sh          # 一键启动对话"
echo "  bash ~/claw-tg.sh            # 一键启动 Telegram"
echo ""

# 如果配置好了，直接启动对话
if [ -n "$API_KEY" ]; then
    echo "� 3 秒后自动进入对话模式... (Ctrl+C 取消)"
    sleep 3
    claw chat
fi
