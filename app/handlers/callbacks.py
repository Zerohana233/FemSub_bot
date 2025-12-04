from __future__ import annotations

from telegram.ext import ContextTypes

from app.services.container import ServiceContainer
from app.handlers.commands import send_template_story


async def handle_callback_query(update, context: ContextTypes.DEFAULT_TYPE, services: ServiceContainer):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "tpl_story":
        await send_template_story(update, context)
    elif data.startswith("toggle_anonymous:"):
        submission_id = data.split(":")[1]
        await services.submission_service.toggle_anonymous(query, submission_id)
    elif data.startswith("confirm:"):
        submission_id = data.split(":")[1]
        await services.submission_service.confirm_submission(query, submission_id, context)
    elif data.startswith("cancel:"):
        await services.submission_service.cancel_submission(query)
    elif data.startswith("admin_") or data.startswith("confirm_ban:"):
        await services.admin_service.handle_callback(query, data, context)

