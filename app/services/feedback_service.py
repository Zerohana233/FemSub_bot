from __future__ import annotations

import logging
from typing import Dict

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from app.services.state_store import TimedStateStore


class FeedbackService:
    """管理员与用户之间的双向反馈通道。"""

    def __init__(self, container):
        self.container = container
        self.settings = container.settings
        self.admin_reply_states: TimedStateStore[int] = TimedStateStore(ttl_seconds=3600)

    async def start_admin_reply_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE, payload: str):
        try:
            target_user_id = int(payload.replace("reply_", ""))
        except ValueError:
            await update.message.reply_text("❌ 无效的用户ID格式。")
            return

        admin_id = update.message.from_user.id
        self.admin_reply_states.set(admin_id, target_user_id)

        try:
            user = await context.bot.get_chat(target_user_id)
            user_name = user.first_name
            if user.last_name:
                user_name += f" {user.last_name}"
            username = f" (@{user.username})" if user.username else ""
        except Exception as exc:  # pylint: disable=broad-except
            logging.error("Error getting user info: %s", exc)
            user_name = "未知用户"
            username = ""

        await update.message.reply_text(
            f"✅ 您现在可以回复用户 {user_name}{username}。发送的所有消息都将被转发。完成后请输入 /stop 结束。"
        )

    async def handle_admin_reply_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # 可能是普通消息 / 编辑消息等，这里统一用 effective_message 获取
        message = update.effective_message
        if message is None:
            return
        admin_id = message.from_user.id

        if admin_id not in self.admin_reply_states:
            return

        target_user_id = self.admin_reply_states.get(admin_id)
        if not target_user_id:
            return

        try:
            if message.text:
                await context.bot.send_message(chat_id=target_user_id, text=message.text)
            elif message.photo:
                await context.bot.send_photo(
                    chat_id=target_user_id,
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                )
            elif message.video:
                await context.bot.send_video(
                    chat_id=target_user_id,
                    video=message.video.file_id,
                    caption=message.caption,
                )
            elif message.document:
                await context.bot.send_document(
                    chat_id=target_user_id,
                    document=message.document.file_id,
                    caption=message.caption,
                )
            else:
                await message.reply_text("❌ 不支持的消息类型")
                return

            await message.reply_text("✅ 消息已转发")
            return ConversationHandler.END
        except Exception as exc:  # pylint: disable=broad-except
            logging.error("Error forwarding message: %s", exc)
            await message.reply_text("❌ 转发失败，用户可能已屏蔽机器人")

    async def stop_admin_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin_id = update.message.from_user.id

        if admin_id not in self.admin_reply_states:
            await update.message.reply_text("❌ 您当前不在回复模式中")
            return

        self.admin_reply_states.delete(admin_id)
        await update.message.reply_text("✅ 已退出回复模式")

