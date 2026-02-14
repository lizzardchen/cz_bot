#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# OpenClaw Bot - Termux 一键安装脚本
# 在 Android 手机上运行自主编码 Agent
#
# 用法 (两种方式):
#   方式1: 已经把代码传到手机上了
#     cd ~/openclaw_bot && bash termux_setup.sh
#
#   方式2: 从零开始 (复制粘贴这一行到 Termux)
#     pkg install -y git && git clone https://github.com/YOUR_USERNAME/openclaw_bot.git ~/openclaw_bot && bash ~/openclaw_bot/termux_setup.sh
# ============================================================

set -e

echo "🤖 OpenClaw Bot Termux 安装"
echo "==========================="
echo ""

# 检测是否在 Termux 环境
if [ ! -d "/data/data/com.termux" ]; then
    echo "⚠️  检测到非 Termux 环境，继续安装..."
fi

# 确定项目目录 (脚本所在目录)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    BOT_DIR="$SCRIPT_DIR"
else
    BOT_DIR="$HOME/openclaw_bot"
fi

echo "📂 项目目录: $BOT_DIR"
echo ""

# 1. 更新包
echo "📦 [1/4] 更新 Termux..."
pkg update -y && pkg upgrade -y

# 2. 安装系统依赖
echo "🔧 [2/4] 安装 Python & Git..."
pkg install -y python git

# 3. 升级 pip & 安装项目
echo "� [3/4] 安装 OpenClaw Bot..."
pip install --upgrade pip setuptools wheel
cd "$BOT_DIR"
pip install -e .

# 4. 初始化配置
if [ ! -f "$HOME/.openclaw/config.json" ]; then
    echo ""
    echo "⚙️  [4/4] 首次运行，开始配置..."
    echo ""
    claw init
else
    echo "⚙️  [4/4] 配置已存在，跳过"
fi

# 创建快捷启动脚本
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

# Termux:Widget 快捷方式
mkdir -p "$HOME/.shortcuts"
cp "$HOME/claw-chat.sh" "$HOME/.shortcuts/OpenClaw-Chat"
cp "$HOME/claw-tg.sh" "$HOME/.shortcuts/OpenClaw-Telegram"
chmod +x "$HOME/.shortcuts/"*

echo ""
echo "============================================"
echo "🎉 安装完成！"
echo "============================================"
echo ""
echo "使用方法:"
echo "  claw chat                    # 交互式对话"
echo "  claw run '添加登录功能'       # 单次任务"
echo "  claw telegram                # 启动 Telegram Bot"
echo "  claw status                  # 查看状态"
echo ""
echo "快捷方式:"
echo "  bash ~/claw-chat.sh          # 一键启动对话"
echo "  bash ~/claw-tg.sh            # 一键启动 Telegram"
echo ""
echo "📱 安装 Termux:Widget 后可在桌面添加快捷方式"
echo ""
