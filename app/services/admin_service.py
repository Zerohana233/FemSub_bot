from __future__ import annotations

import asyncio
import html
import logging
from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.models import Submission, SubmissionStatus
from app.services.state_store import TimedStateStore


class AdminService:
    """管理员审核、编辑与控制面板逻辑。"""

    def __init__(self, container):
        self.container = container
        self.db = container.db
        self.settings = container.settings
        self.edit_states: TimedStateStore[Dict] = TimedStateStore(ttl_seconds=600)
        self.tag_states: TimedStateStore[Dict] = TimedStateStore(ttl_seconds=600)

    def create_review_keyboard(self, submission: Submission) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("✅ 通过", callback_data=f"admin_approve:{submission.submission_id}"),
                InlineKeyboardButton("🚫 拒绝", callback_data=f"admin_reject:{submission.submission_id}"),
            ],
            [
                InlineKeyboardButton("✏️ 编辑文案", callback_data=f"admin_edit:{submission.submission_id}"),
                InlineKeyboardButton("🏷 添加 Tag", callback_data=f"admin_tags:{submission.submission_id}"),
            ],
            [
                InlineKeyboardButton("🛑 拉黑用户", callback_data=f"admin_ban:{submission.submission_id}"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    async def format_control_text(self, submission: Submission, context: ContextTypes.DEFAULT_TYPE) -> str:
        anonymous_status = "是" if submission.is_anonymous else "否"

        try:
            user = await context.bot.get_chat(submission.user_id)
            full_name = user.first_name
            if user.last_name:
                full_name += f" {user.last_name}"
        except Exception as exc:  # pylint: disable=broad-except
            logging.error("Error getting user info: %s", exc)
            full_name = submission.username

        escaped_full_name = html.escape(full_name)
        username_display = f" (@{submission.username})" if submission.username else ""

        return (
            f"""👤 用户: <a href="tg://user?id={submission.user_id}">{escaped_full_name}</a>{username_display}
🆔 ID: {submission.user_id}
🔔 匿名: {anonymous_status}"""
        )

    async def handle_callback(self, query, data: str, context: ContextTypes.DEFAULT_TYPE):
        if data.startswith("admin_approve:"):
            await self._handle_admin_approve(query, data, context)
        elif data.startswith("admin_reject:"):
            submission_id = data.split(":")[1]
            await self._handle_admin_reject_simple(query, submission_id, context)
        elif data.startswith("admin_edit:"):
            await self._handle_admin_edit(query, data, context)
        elif data.startswith("admin_tags:"):
            submission_id = data.split(":")[1]
            await self._handle_admin_tags_simple(query, submission_id, context)
        elif data.startswith("admin_ban:"):
            await self._handle_admin_ban(query, data)
        elif data.startswith("confirm_ban:"):
            await self._handle_confirm_ban(query, data)
        elif data.startswith("admin_back:"):
            await self._handle_admin_back(query, data, context)

    async def _handle_admin_approve(self, query, data: str, context: ContextTypes.DEFAULT_TYPE):
        submission_id = data.split(":")[1]
        submission = self.db.get_submission(submission_id)

        if not submission:
            await query.edit_message_text("❌ 投稿不存在", parse_mode=ParseMode.HTML)
            return

        final_caption = submission.caption_only or ""
        if submission.tags:
            final_caption = f"{final_caption}\n\n{submission.tags}" if final_caption else submission.tags

        if not submission.is_anonymous:
            try:
                user = await context.bot.get_chat(submission.user_id)
                full_name = user.first_name
                if user.last_name:
                    full_name += f" {user.last_name}"
            except Exception as exc:  # pylint: disable=broad-except
                logging.error("Error getting user info: %s", exc)
                full_name = submission.username

            escaped_full_name = html.escape(full_name)
            user_link = f"<a href='tg://user?id={submission.user_id}'>{escaped_full_name}</a>"
            footer_text = f"\n\nvia {user_link}"
            if self.settings.nav_channel_link:
                nav_link = f"<a href='{self.settings.nav_channel_link}'>𝔽𝕖𝕞𝕊𝕦𝕓</a>"
                footer_text += f"\n{nav_link}"
            final_caption += footer_text
        else:
            if self.settings.nav_channel_link:
                nav_link = f"<a href='{self.settings.nav_channel_link}'>𝔽𝕖𝕞𝕊𝕦𝕓</a>"
                final_caption += f"\n\n{nav_link}"

        try:
            if len(submission.media_files) > 1:
                media_group = []
                for i, media_file in enumerate(submission.media_files):
                    media_caption = final_caption if i == 0 else None
                    if media_file.file_type == "photo":
                        from telegram import InputMediaPhoto

                        media = InputMediaPhoto(media=media_file.file_id, caption=media_caption, parse_mode=ParseMode.HTML)
                    elif media_file.file_type == "video":
                        from telegram import InputMediaVideo

                        media = InputMediaVideo(media=media_file.file_id, caption=media_caption, parse_mode=ParseMode.HTML)
                    else:
                        from telegram import InputMediaDocument

                        media = InputMediaDocument(media=media_file.file_id, caption=media_caption, parse_mode=ParseMode.HTML)
                    media_group.append(media)

                await context.bot.send_media_group(chat_id=self.settings.channel_id, media=media_group)
            else:
                if submission.media_files:
                    media_file = submission.media_files[0]
                    if media_file.file_type == "photo":
                        await context.bot.send_photo(
                            chat_id=self.settings.channel_id,
                            photo=media_file.file_id,
                            caption=final_caption,
                            parse_mode=ParseMode.HTML,
                        )
                    elif media_file.file_type == "video":
                        await context.bot.send_video(
                            chat_id=self.settings.channel_id,
                            video=media_file.file_id,
                            caption=final_caption,
                            parse_mode=ParseMode.HTML,
                        )
                    else:
                        await context.bot.send_document(
                            chat_id=self.settings.channel_id,
                            document=media_file.file_id,
                            caption=final_caption,
                            parse_mode=ParseMode.HTML,
                        )
                else:
                    await context.bot.send_message(
                        chat_id=self.settings.channel_id,
                        text=final_caption,
                        parse_mode=ParseMode.HTML,
                    )

            submission.status = SubmissionStatus.APPROVED
            self.db.save_submission(submission)

            try:
                await context.bot.send_message(
                    chat_id=submission.user_id,
                    text="✅ 恭喜！您的投稿已被采纳。",
                    parse_mode=ParseMode.HTML,
                )
            except Exception as exc:  # pylint: disable=broad-except
                logging.error("Error notifying user about approval: %s", exc)

            admin_name = query.from_user.first_name
            if query.from_user.last_name:
                admin_name += f" {query.from_user.last_name}"

            await query.edit_message_text(
                f"✅ <b>已发布</b> (操作人: {admin_name})",
                reply_markup=None,
                parse_mode=ParseMode.HTML,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logging.error("Error publishing to channel: %s", exc)
            await query.edit_message_text(
                "❌ 发布失败，请检查频道设置",
                reply_markup=None,
                parse_mode=ParseMode.HTML,
            )

    async def _handle_admin_reject_simple(self, query, submission_id: str, context: ContextTypes.DEFAULT_TYPE):
        submission = self.db.get_submission(submission_id)

        if not submission:
            await query.edit_message_text("❌ 投稿不存在", parse_mode=ParseMode.HTML)
            return

        try:
            await context.bot.send_message(
                chat_id=submission.user_id,
                text="🚫 抱歉，您的投稿未通过审核。",
                parse_mode=ParseMode.HTML,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logging.error("Error notifying user about rejection: %s", exc)

        submission.status = SubmissionStatus.REJECTED
        self.db.save_submission(submission)

        admin_name = query.from_user.first_name
        if query.from_user.last_name:
            admin_name += f" {query.from_user.last_name}"

        await query.edit_message_text(
            f"🚫 <b>已拒绝</b> (操作人: {admin_name})",
            reply_markup=None,
            parse_mode=ParseMode.HTML,
        )

    async def _handle_admin_edit(self, query, data: str, context: ContextTypes.DEFAULT_TYPE):
        submission_id = data.split(":")[1]
        submission = self.db.get_submission(submission_id)

        if not submission:
            await query.answer("❌ 投稿不存在")
            return

        escaped_caption = html.escape(submission.caption_only or "无")
        prompt_message = await context.bot.send_message(
            chat_id=self.settings.admin_group_id,
            text=f"当前文案:\n{escaped_caption}\n\n请回复本条消息输入新的文案：",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("↩️ 返回", callback_data=f"admin_back:{submission_id}")]]
            ),
            parse_mode=ParseMode.HTML,
        )

        admin_id = query.from_user.id
        self.edit_states.set(
            admin_id,
            {
                "sub_id": submission_id,
                "prompt_msg_id": prompt_message.message_id,
            },
        )

        await query.answer()

    async def _handle_admin_tags_simple(self, query, submission_id: str, context: ContextTypes.DEFAULT_TYPE):
        submission = self.db.get_submission(submission_id)

        if not submission:
            await query.answer("❌ 投稿不存在")
            return

        escaped_tags = html.escape(submission.tags) if submission.tags else "无"
        prompt_message = await context.bot.send_message(
            chat_id=self.settings.admin_group_id,
            text=f"当前标签: {escaped_tags}\n\n<b>请回复本条消息输入您想添加的 Tag (例如 #Tag1 #Tag2)...</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("↩️ 返回", callback_data=f"admin_back:{submission_id}")]]
            ),
            parse_mode=ParseMode.HTML,
        )

        admin_id = query.from_user.id
        self.tag_states.set(
            admin_id,
            {
                "sub_id": submission_id,
                "prompt_msg_id": prompt_message.message_id,
            },
        )

        await query.answer()

    async def _handle_admin_ban(self, query, data: str):
        submission_id = data.split(":")[1]
        submission = self.db.get_submission(submission_id)

        if not submission:
            await query.edit_message_text("❌ 投稿不存在", parse_mode=ParseMode.HTML)
            return

        escaped_username = html.escape(submission.username)
        await query.edit_message_text(
            f"⚠️ 确认拉黑用户 @{escaped_username} ({submission.user_id})？",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✅ 确认拉黑", callback_data=f"confirm_ban:{submission_id}"),
                        InlineKeyboardButton("↩️ 返回", callback_data=f"admin_back:{submission_id}"),
                    ]
                ]
            ),
            parse_mode=ParseMode.HTML,
        )

    async def _handle_confirm_ban(self, query, data: str):
        submission_id = data.split(":")[1]
        submission = self.db.get_submission(submission_id)

        if not submission:
            await query.edit_message_text("❌ 投稿不存在", parse_mode=ParseMode.HTML)
            return

        escaped_username = html.escape(submission.username)
        await query.edit_message_text(
            f"✅ 用户 @{escaped_username} 已被拉黑",
            reply_markup=None,
            parse_mode=ParseMode.HTML,
        )

    async def _handle_admin_back(self, query, data: str, context: ContextTypes.DEFAULT_TYPE):
        submission_id = data.split(":")[1]
        submission = self.db.get_submission(submission_id)

        if not submission:
            await query.edit_message_text("❌ 投稿不存在", parse_mode=ParseMode.HTML)
            return

        control_text = await self.format_control_text(submission, context)
        keyboard = self.create_review_keyboard(submission)

        await query.edit_message_text(
            control_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )

    async def handle_admin_reply(self, update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        admin_id = message.from_user.id

        if admin_id in self.edit_states:
            await self._process_edit_reply(admin_id, message, context)
        elif admin_id in self.tag_states:
            await self._process_tag_reply(admin_id, message, context)

    async def _process_edit_reply(self, admin_id: int, message, context: ContextTypes.DEFAULT_TYPE):
        state_data = self.edit_states.get(admin_id)
        if not state_data:
            return
        submission_id = state_data["sub_id"]
        prompt_msg_id = state_data["prompt_msg_id"]

        submission = self.db.get_submission(submission_id)
        if not submission:
            await self._safe_delete_message(prompt_msg_id, context)
            self.edit_states.delete(admin_id)
            return

        new_caption = message.text
        if not new_caption:
            await self._safe_delete_message(prompt_msg_id, context)
            self.edit_states.delete(admin_id)
            return

        submission.caption_only = new_caption
        if submission.tags:
            submission.caption = new_caption + "\n\n" + submission.tags
        else:
            submission.caption = new_caption
        self.db.save_submission(submission)

        await self._update_preview_message(submission, context)

        await self._safe_delete_message(message.message_id, context)
        await self._safe_delete_message(prompt_msg_id, context)

        self.edit_states.delete(admin_id)

    async def _process_tag_reply(self, admin_id: int, message, context: ContextTypes.DEFAULT_TYPE):
        state_data = self.tag_states.get(admin_id)
        if not state_data:
            return
        submission_id = state_data["sub_id"]
        prompt_msg_id = state_data["prompt_msg_id"]

        submission = self.db.get_submission(submission_id)
        if not submission:
            await self._safe_delete_message(prompt_msg_id, context)
            self.tag_states.delete(admin_id)
            return

        new_tags = message.text
        if not new_tags:
            await self._safe_delete_message(prompt_msg_id, context)
            self.tag_states.delete(admin_id)
            return

        if submission.tags and new_tags in submission.tags:
            warning_msg = await context.bot.send_message(
                chat_id=self.settings.admin_group_id,
                text=f"⚠️ 标签 <code>{new_tags}</code> 已存在，无需重复添加。",
                parse_mode=ParseMode.HTML,
            )
            await asyncio.sleep(3)
            await self._safe_delete_message(warning_msg.message_id, context)
        else:
            submission.tags = f"{submission.tags} {new_tags}".strip() if submission.tags else new_tags
            if submission.caption_only:
                submission.caption = submission.caption_only
                if submission.tags:
                    submission.caption += "\n\n" + submission.tags
            else:
                submission.caption = submission.tags

            self.db.save_submission(submission)
            await self._update_preview_message(submission, context)

        await self._safe_delete_message(message.message_id, context)
        await self._safe_delete_message(prompt_msg_id, context)
        self.tag_states.delete(admin_id)

    async def _update_preview_message(self, submission: Submission, context: ContextTypes.DEFAULT_TYPE):
        try:
            final_caption = submission.caption_only or ""
            if submission.tags:
                final_caption = f"{final_caption}\n\n{submission.tags}" if final_caption else submission.tags

            if submission.preview_message_id:
                try:
                    await context.bot.edit_message_caption(
                        chat_id=self.settings.admin_group_id,
                        message_id=submission.preview_message_id,
                        caption=final_caption,
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    await context.bot.edit_message_text(
                        chat_id=self.settings.admin_group_id,
                        message_id=submission.preview_message_id,
                        text=final_caption,
                        parse_mode=ParseMode.HTML,
                    )
        except Exception as exc:  # pylint: disable=broad-except
            logging.error("Error updating preview message: %s", exc)

    async def _safe_delete_message(self, message_id: int, context: ContextTypes.DEFAULT_TYPE):
        try:
            await context.bot.delete_message(
                chat_id=self.settings.admin_group_id,
                message_id=message_id,
            )
        except Exception:
            pass

