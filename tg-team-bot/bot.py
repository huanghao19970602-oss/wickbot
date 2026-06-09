"""
Telegram 团队管理 Bot —— 主程序入口

启动命令：
    python bot.py

使用前请：
    1. 复制 .env.example 为 .env 并填入真实配置
    2. pip install -r requirements.txt
    3. 确保 Bot Token 已从 @BotFather 获取
"""

import logging
import sys
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

from database import init_db
from bot_handlers import (
    start, help_command,
    report_start, report_cancel,
    handle_completed, handle_planned, handle_blockers,
    summary_command, all_reports, member_query, analyze_command,
    set_okr_command, view_okr_command, remind_command,
    WAITING_COMPLETED, WAITING_PLANNED, WAITING_BLOCKERS
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Bot 启动入口"""
    from decouple import config

    BOT_TOKEN = config("BOT_TOKEN", default=None)

    if not BOT_TOKEN:
        logger.error("BOT_TOKEN 未设置！请在 .env 文件中填入你的 Bot Token")
        sys.exit(1)

    init_db()
    logger.info("数据库已就绪")

    app = Application.builder().token(BOT_TOKEN).build()

    # ====================================================================
    # 注册所有命令
    # ====================================================================
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", report_cancel))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("all", all_reports))
    app.add_handler(CommandHandler("member", member_query))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("setokr", set_okr_command))
    app.add_handler(CommandHandler("okr", view_okr_command))
    app.add_handler(CommandHandler("remind", remind_command))

    # ====================================================================
    # 注册日报多步对话处理器
    # ====================================================================
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("report", report_start)],
        states={
            WAITING_COMPLETED: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_completed)
            ],
            WAITING_PLANNED: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_planned)
            ],
            WAITING_BLOCKERS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_blockers)
            ],
        },
        fallbacks=[CommandHandler("cancel", report_cancel)],
    )
    app.add_handler(conv_handler)

    logger.info("🤖 Bot 启动中...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
