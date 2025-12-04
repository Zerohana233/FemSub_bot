from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.services.container import ServiceContainer


async def feedback_bridge(update: Update, context: ContextTypes.DEFAULT_TYPE, services: ServiceContainer):
    await services.feedback_service.handle_admin_reply_messages(update, context)


async def user_submission(update: Update, context: ContextTypes.DEFAULT_TYPE, services: ServiceContainer):
    await services.submission_service.handle_message(update, context)


async def admin_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, services: ServiceContainer):
    await services.admin_service.handle_admin_reply(update, context)

