import os
from getpass import getpass


def ask_secret(label, env_name, required=True):
    value = getpass(label).strip()
    if required and not value:
        raise RuntimeError(f"{env_name} is required")
    if value:
        os.environ[env_name] = value
    return value


def main():
    print("=" * 60)
    print("POCKET OTC AI ANALYZER — GOOGLE COLAB")
    print("READ-ONLY: لا يتم تنفيذ أي صفقة")
    print("=" * 60)

    ask_secret("🔐 أدخل Telegram Bot Token: ", "TELEGRAM_BOT_TOKEN")
    ask_secret("🔐 أدخل Pocket Option SSID: ", "POCKET_OPTION_SSID")

    use_openrouter = input("🧠 تفعيل OpenRouter؟ [y/N]: ").strip().lower() == "y"
    if use_openrouter:
        ask_secret("🔐 أدخل OpenRouter API Key: ", "OPENROUTER_API_KEY")
        model = input(
            "🤖 اسم الموديل [openai/gpt-oss-120b:free]: "
        ).strip() or "openai/gpt-oss-120b:free"
        os.environ["OPENROUTER_MODEL"] = model

    print("\n🚀 بدء بوت Telegram...")
    from telegram_bot import run
    run()


if __name__ == "__main__":
    main()
