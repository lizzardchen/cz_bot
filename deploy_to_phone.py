"""
在电脑上运行此脚本，生成手机一键部署命令。
用法: python deploy_to_phone.py
"""

import sys


def main():
    print("🤖 OpenClaw Bot - 生成手机部署命令")
    print("=" * 45)
    print()

    # 收集信息
    print("请输入以下信息 (直接回车使用默认值):")
    print()

    api_key = input("API Key (必填): ").strip()
    if not api_key:
        print("❌ API Key 不能为空！")
        print("   去 https://platform.deepseek.com 注册获取")
        sys.exit(1)

    provider = input("Provider [deepseek]: ").strip() or "deepseek"
    model_defaults = {
        "deepseek": "deepseek-chat",
        "glm": "glm-4-plus",
        "minimax": "MiniMax-Text-01",
        "moonshot": "moonshot-v1-8k",
        "dashscope": "qwen-max",
        "doubao": "doubao-pro-256k",
        "spark": "generalv3.5",
        "baichuan": "Baichuan4",
        "yi": "yi-large",
        "stepfun": "step-2-16k",
        "openai": "gpt-4o",
        "openrouter": "anthropic/claude-opus-4-5",
    }
    default_model = model_defaults.get(provider, "deepseek-chat")
    model = input(f"Model [{default_model}]: ").strip() or default_model
    tg_token = input("Telegram Bot Token (可选, 回车跳过): ").strip()

    # 构建命令
    args = f'--key {api_key} --provider {provider} --model {model}'
    if tg_token:
        args += f' --tg-token {tg_token}'

    # 方式1: curl 一键命令
    curl_cmd = f'pkg install -y curl && curl -sL https://raw.githubusercontent.com/lizzardchen/cz_bot/main/termux_setup.sh | bash -s -- {args}'

    # 方式2: git clone 方式
    git_cmd = f'pkg install -y git && git clone https://github.com/lizzardchen/cz_bot.git ~/openclaw_bot && bash ~/openclaw_bot/termux_setup.sh {args}'

    print()
    print("=" * 45)
    print("📱 在手机 Termux 中粘贴以下任一命令:")
    print("=" * 45)
    print()
    print("方式一 (推荐，最短):")
    print()
    print(f"  {curl_cmd}")
    print()
    print("方式二 (git clone):")
    print()
    print(f"  {git_cmd}")
    print()
    print("=" * 45)
    print("粘贴后全自动完成: 安装依赖 → 克隆代码 → 配置 → 启动对话")
    print()

    # 复制到剪贴板
    try:
        import subprocess
        subprocess.run(["clip"], input=curl_cmd.encode(), check=True)
        print("✅ 方式一的命令已复制到剪贴板！直接去手机 Termux 粘贴即可。")
    except Exception:
        print("💡 手动复制上面的命令到手机 Termux 中粘贴运行。")


if __name__ == "__main__":
    main()
