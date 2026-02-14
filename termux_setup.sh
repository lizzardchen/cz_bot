#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# OpenClaw Bot - Termux 一键安装脚本
# 在 Android 手机上运行自主编码 Agent
# ============================================================

set -e

echo "🤖 OpenClaw Bot Termux 安装"
echo "==========================="
echo ""

# 1. 更新包
echo "📦 [1/5] 更新 Termux..."
pkg update -y && pkg upgrade -y

# 2. 安装系统依赖
echo "🔧 [2/5] 安装 Python & Git..."
pkg install -y python git

# 3. 升级 pip
echo "🐍 [3/5] 升级 pip..."
pip install --upgrade pip setuptools wheel

# 4. 克隆或更新项目
BOT_DIR="$HOME/openclaw_bot"
if [ -d "$BOT_DIR" ]; then
    echo "📂 [4/5] 更新代码..."
    cd "$BOT_DIR" && git pull
else
    echo "📂 [4/5] 克隆代码..."
    git clone https://github.com/YOUR_USERNAME/openclaw_bot.git "$BOT_DIR"
    cd "$BOT_DIR"
fi

# 5. 安装
echo "📥 [5/5] 安装依赖..."
pip install -e .

# 初始化配置
if [ ! -f "$HOME/.openclaw/config.json" ]; then
    echo ""
    echo "⚙️  首次运行，开始配置..."
    claw init
fi

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
