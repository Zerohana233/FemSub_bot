from __future__ import annotations

import asyncio
import html
from datetime import datetime
from typing import Dict, List, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.models import MediaFile, Submission, SubmissionStatus


class SubmissionService:
    """用户投稿与媒体组处理逻辑。"""

    def __init__(self, container):
        self.container = container
        self.db = container.db
        self.settings = container.settings
        self.pending_media_groups: Dict[str, Dict] = {}
        self.media_group_tasks: Dict[str, asyncio.Task] = {}

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # 只处理真正的消息更新，忽略回调 / 其它类型
        message = update.effective_message
        if message is None:
            return

        if message.media_group_id:
            await self._handle_media_group_message(update, context)
            return

        await self._process_single_submission(update, context)

    async def toggle_anonymous(self, query, submission_id: str):
        submission = self.db.get_submission(submission_id)

        if not submission:
            await query.edit_message_text("❌ 投稿不存在或已过期", parse_mode=ParseMode.HTML)
            return

        submission.is_anonymous = not submission.is_anonymous
        self.db.save_submission(submission)

        preview_text = self._format_preview_text(submission)
        keyboard = self._create_user_control_keyboard(submission)

        if query.message.caption is not None:
            await query.edit_message_caption(
                caption=preview_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
        else:
            await query.edit_message_text(
                text=preview_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )

    async def confirm_submission(self, query, submission_id: str, context: ContextTypes.DEFAULT_TYPE):
        submission = self.db.get_submission(submission_id)

        if not submission:
            await query.edit_message_text("❌ 投稿不存在或已过期", parse_mode=ParseMode.HTML)
            return

        await self._send_to_admin_group(submission, context)

        if query.message.caption is not None:
            await query.edit_message_caption(
                caption="✅ 投稿已提交，等待管理员审核",
                reply_markup=None,
                parse_mode=ParseMode.HTML,
            )
        else:
            await query.edit_message_text(
                text="✅ 投稿已提交，等待管理员审核",
                reply_markup=None,
                parse_mode=ParseMode.HTML,
            )

    async def cancel_submission(self, query):
        if query.message.caption is not None:
            await query.edit_message_caption(
                caption="❌ 投稿已取消",
                reply_markup=None,
                parse_mode=ParseMode.HTML,
            )
        else:
            await query.edit_message_text(
                text="❌ 投稿已取消",
                reply_markup=None,
                parse_mode=ParseMode.HTML,
            )

    async def _handle_media_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        media_group_id = message.media_group_id

        if media_group_id not in self.pending_media_groups:
            self.pending_media_groups[media_group_id] = {
                "messages": [],
                "user_id": message.from_user.id,
                "username": message.from_user.username or message.from_user.first_name,
                "caption": message.caption or "",
                "created_at": datetime.now(),
            }

            self.media_group_tasks[media_group_id] = asyncio.create_task(
                self._process_media_group_after_timeout(media_group_id, context)
            )

        self.pending_media_groups[media_group_id]["messages"].append(message)

        if message.caption:
            self.pending_media_groups[media_group_id]["caption"] = message.caption

    async def _process_media_group_after_timeout(self, media_group_id: str, context: ContextTypes.DEFAULT_TYPE):
        await asyncio.sleep(self.settings.media_group_timeout)

        if media_group_id not in self.pending_media_groups:
            return

        media_group = self.pending_media_groups.pop(media_group_id)
        if media_group_id in self.media_group_tasks:
            del self.media_group_tasks[media_group_id]

        await self._create_submission_from_media_group(media_group, context)

    async def _create_submission_from_media_group(self, media_group: Dict, context: ContextTypes.DEFAULT_TYPE):
        messages = media_group["messages"]
        if not messages:
            return

        media_files: List[MediaFile] = []
        for message in messages:
            if message.photo:
                file_id = message.photo[-1].file_id
                media_files.append(MediaFile(file_id=file_id, file_type="photo"))
            elif message.video:
                file_id = message.video.file_id
                media_files.append(MediaFile(file_id=file_id, file_type="video"))
            elif message.document:
                file_id = message.document.file_id
                media_files.append(MediaFile(file_id=file_id, file_type="document"))

        submission_id = f"mg_{media_group['user_id']}_{int(datetime.now().timestamp())}"
        submission = Submission(
            submission_id=submission_id,
            user_id=media_group["user_id"],
            username=media_group["username"],
            media_files=media_files,
            caption=media_group["caption"],
            caption_only=media_group["caption"],
            is_anonymous=False,
            tags="",
            status=SubmissionStatus.PENDING,
            created_at=media_group["created_at"],
            media_group_id=messages[0].media_group_id,
        )

        self.db.save_submission(submission)
        await self._send_submission_preview(messages[0], submission)

    async def _process_single_submission(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        media_files: List[MediaFile] = []
        caption = message.caption or ""

        if message.photo:
            file_id = message.photo[-1].file_id
            media_files.append(MediaFile(file_id=file_id, file_type="photo"))
        elif message.video:
            file_id = message.video.file_id
            media_files.append(MediaFile(file_id=file_id, file_type="video"))
        elif message.document:
            file_id = message.document.file_id
            media_files.append(MediaFile(file_id=file_id, file_type="document"))
        elif message.text:
            caption = message.text
        else:
            await message.reply_text("❌ 不支持的文件类型，请发送文本、图片、视频或文件。")
            return

        submission_id = f"single_{message.from_user.id}_{int(datetime.now().timestamp())}"
        submission = Submission(
            submission_id=submission_id,
            user_id=message.from_user.id,
            username=message.from_user.username or message.from_user.first_name,
            media_files=media_files,
            caption=caption,
            caption_only=caption,
            is_anonymous=False,
            tags="",
            status=SubmissionStatus.PENDING,
            created_at=datetime.now(),
        )

        self.db.save_submission(submission)
        await self._send_submission_preview(message, submission)

    async def _send_submission_preview(self, message, submission: Submission):
        preview_text = self._format_preview_text(submission)
        keyboard = self._create_user_control_keyboard(submission)

        if submission.media_files:
            first_media = submission.media_files[0]
            if first_media.file_type == "photo":
                await message.reply_photo(
                    photo=first_media.file_id,
                    caption=preview_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML,
                )
            elif first_media.file_type == "video":
                await message.reply_video(
                    video=first_media.file_id,
                    caption=preview_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML,
                )
            else:
                await message.reply_document(
                    document=first_media.file_id,
                    caption=preview_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML,
                )
        else:
            await message.reply_text(
                preview_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )

    def _format_preview_text(self, submission: Submission) -> str:
        media_count = len(submission.media_files)

        if media_count > 1:
            media_info = f"📷 组图 ({media_count}张)"
        elif media_count == 1:
            media_info = "📷 单图"
        else:
            media_info = "📝 纯文本"

        escaped_caption = self._escape_html(submission.caption or "无")

        return f"""📤 <b>投稿预览</b>

{media_info}
💬 文案: {escaped_caption}
🔕 匿名: {'开启' if submission.is_anonymous else '关闭'}

请确认投稿内容："""

    def _create_user_control_keyboard(self, submission: Submission) -> InlineKeyboardMarkup:
        anonymous_text = "🔔 匿名: 开启" if submission.is_anonymous else "🔕 匿名: 关闭"

        keyboard = [
            [InlineKeyboardButton(anonymous_text, callback_data=f"toggle_anonymous:{submission.submission_id}")],
            [
                InlineKeyboardButton("✅ 确认投稿", callback_data=f"confirm:{submission.submission_id}"),
                InlineKeyboardButton("❌ 取消", callback_data=f"cancel:{submission.submission_id}"),
            ],
        ]

        return InlineKeyboardMarkup(keyboard)

    async def _send_to_admin_group(self, submission: Submission, context: ContextTypes.DEFAULT_TYPE):
        admin_service = self.container.admin_service
        keyboard = admin_service.create_review_keyboard(submission)

        try:
            if len(submission.media_files) > 1:
                media_group = []
                for i, media_file in enumerate(submission.media_files):
                    media_caption = submission.caption if i == 0 and submission.caption else None

                    if media_file.file_type == "photo":
                        media = InputMediaPhoto(media=media_file.file_id, caption=media_caption)
                    elif media_file.file_type == "video":
                        media = InputMediaVideo(media=media_file.file_id, caption=media_caption)
                    else:
                        media = InputMediaDocument(media=media_file.file_id, caption=media_caption)

                    media_group.append(media)

                preview_messages = await context.bot.send_media_group(
                    chat_id=self.settings.admin_group_id,
                    media=media_group,
                )

                control_text = await admin_service.format_control_text(submission, context)
                control_message = await context.bot.send_message(
                    chat_id=self.settings.admin_group_id,
                    text=control_text,
                    reply_markup=keyboard,
                    reply_to_message_id=preview_messages[0].message_id,
                    parse_mode=ParseMode.HTML,
                )

                submission.preview_message_id = preview_messages[0].message_id
                submission.admin_message_id = control_message.message_id
            else:
                if submission.media_files:
                    media_file = submission.media_files[0]
                    if media_file.file_type == "photo":
                        preview_message = await context.bot.send_photo(
                            chat_id=self.settings.admin_group_id,
                            photo=media_file.file_id,
                            caption=submission.caption,
                        )
                    elif media_file.file_type == "video":
                        preview_message = await context.bot.send_video(
                            chat_id=self.settings.admin_group_id,
                            video=media_file.file_id,
                            caption=submission.caption,
                        )
                    else:
                        preview_message = await context.bot.send_document(
                            chat_id=self.settings.admin_group_id,
                            document=media_file.file_id,
                            caption=submission.caption,
                        )
                else:
                    preview_message = await context.bot.send_message(
                        chat_id=self.settings.admin_group_id,
                        text=submission.caption,
                    )

                control_text = await admin_service.format_control_text(submission, context)
                control_message = await context.bot.send_message(
                    chat_id=self.settings.admin_group_id,
                    text=control_text,
                    reply_markup=keyboard,
                    reply_to_message_id=preview_message.message_id,
                    parse_mode=ParseMode.HTML,
                )

                submission.preview_message_id = preview_message.message_id
                submission.admin_message_id = control_message.message_id

            self.db.save_submission(submission)
        except Exception as exc:  # pylint: disable=broad-except
            # 使用 logging，在 main 中已配置默认 logger
            import logging

            logging.error("Error sending to admin group: %s", exc)

    @staticmethod
    def _escape_html(text: Optional[str]) -> str:
        if not text:
            return ""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#39;")
        return text

