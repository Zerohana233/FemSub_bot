#!/usr/bin/env python3
"""
FemSub - Telegram Submission Bot
模块化重构版本：拆分配置、服务与处理器。
"""

import logging
from functools import partial

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.config import settings
from app.handlers import callbacks, commands, messages
from app.services import ServiceContainer

# Handler groups for priority-based message processing
GROUP_FEEDBACK = 0
GROUP_SUBMISSION = 1


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext").setLevel(logging.WARNING)

    services = ServiceContainer(settings)
    application = Application.builder().token(settings.bot_token).build()

    # ===== GROUP_FEEDBACK =====
    application.add_handler(
        CommandHandler("stop", partial(commands.stop_reply, services=services)),
        group=GROUP_FEEDBACK,
    )
    application.add_handler(
        MessageHandler(filters.ChatType.PRIVATE, partial(messages.feedback_bridge, services=services)),
        group=GROUP_FEEDBACK,
    )

    # ===== GROUP_SUBMISSION =====
    application.add_handler(
        CommandHandler("start", partial(commands.start, services=services)),
        group=GROUP_SUBMISSION,
    )
    application.add_handler(
        CommandHandler("help", partial(commands.help_command, services=services)),
        group=GROUP_SUBMISSION,
    )
    application.add_handler(
        CommandHandler("stats", partial(commands.stats, services=services)),
        group=GROUP_SUBMISSION,
    )
    application.add_handler(
        CommandHandler("my", partial(commands.my_command, services=services)),
        group=GROUP_SUBMISSION,
    )
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL)
            & ~filters.COMMAND,
            partial(messages.user_submission, services=services),
        ),
        group=GROUP_SUBMISSION,
    )

    # ===== Other handlers =====
    application.add_handler(
        MessageHandler(
            filters.Chat(settings.admin_group_id) & filters.REPLY,
            partial(messages.admin_group_reply, services=services),
        )
    )
    application.add_handler(CallbackQueryHandler(partial(callbacks.handle_callback_query, services=services)))

    print("🤖 FemSub Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()

