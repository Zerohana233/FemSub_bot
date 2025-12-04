from __future__ import annotations

from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.services.container import ServiceContainer
from app.templates import STORY_TEMPLATE


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE, services: ServiceContainer):
    payload = context.args[0] if context.args else None

    if payload and payload.startswith("reply_"):
        await services.feedback_service.start_admin_reply_mode(update, context, payload)
        return

    help_text = """🐾 <b>欢迎来到 FemSub 投稿狗窝</b>

你现在是<b>雌畜 / 母狗 / 下贱玩物候选人</b>，
想被看见、被评头论足、被人拿着你的故事打胶，就把自己乖乖写清楚扔过来。

<b>怎么投？</b>
• 直接发文字、小作文、照片、视频、相册都可以
• 想写得更下贱一点，可以先点“获取投稿模板”照着填

<b>几点约定</b>
• 你发给我的东西，默认是为了<b>给别人爽</b>，而不是给你树立人设
• 你可以选择匿名，也可以选择用某种下贱身份署名
• 想清楚再发，一旦上墙，就当是送出去的肉

<i>如果只是想当个安静的变态，也可以先潜水看别人怎么烂掉的。</i>"""

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔞 进接待处（Lobby）", url="https://t.me/FemSubLobby")],
            [InlineKeyboardButton("📝 获取投稿模板", callback_data="tpl_story")],
        ]
    )

    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, services: ServiceContainer):
    await start(update, context, services)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE, services: ServiceContainer):
    if update.message.chat.id != services.settings.admin_group_id:
        await update.message.reply_text("❌ 此命令仅限管理员使用。")
        return

    dashboard = services.stats_service.get_dashboard()

    stats_text = f"📊 <b>FemSub 统计面板</b>\n\n"
    stats_text += f"📤 <b>总投稿数</b>: {dashboard.total}\n"
    stats_text += f"⏳ <b>待审核</b>: {dashboard.status_counts.get('pending', 0)}\n"
    stats_text += f"✅ <b>已通过</b>: {dashboard.status_counts.get('approved', 0)}\n"
    stats_text += f"🚫 <b>已拒绝</b>: {dashboard.status_counts.get('rejected', 0)}\n\n"

    stats_text += "<b>📈 最近7天投稿趋势</b>\n"
    if dashboard.daily_counts:
        for date, count in dashboard.daily_counts[-5:]:
            stats_text += f"  {date}: {count} 条\n"
    else:
        stats_text += "  暂无数据\n"

    stats_text += "\n<b>🏆 活跃投稿人 (最近30天)</b>\n"
    if dashboard.top_submitters:
        for i, (username, count) in enumerate(dashboard.top_submitters[:5], 1):
            display_name = f"@{username}" if username else "匿名用户"
            stats_text += f"  {i}. {display_name}: {count} 条\n"
    else:
        stats_text += "  暂无数据\n"

    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)


async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE, services: ServiceContainer):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name

    summary = services.stats_service.get_user_summary(user_id, username)

    my_text = f"👤 <b>{summary.username} 的个人中心</b>\n\n"
    my_text += f"📤 <b>总投稿数</b>: {summary.total}\n"
    my_text += f"⏳ <b>待审核</b>: {summary.status_counts.get('pending', 0)}\n"
    my_text += f"✅ <b>已通过</b>: {summary.status_counts.get('approved', 0)}\n"
    my_text += f"🚫 <b>已拒绝</b>: {summary.status_counts.get('rejected', 0)}\n\n"

    if summary.recent_submissions:
        my_text += "<b>📝 最近投稿记录</b>\n"
        for _, caption_only, tags, status, created_at in summary.recent_submissions[:5]:
            base_text = caption_only or tags or "无文案"
            short_caption = base_text[:30] + "..." if len(base_text) > 30 else base_text
            status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "🚫"}.get(status, "❓")
            created_date = datetime.fromisoformat(created_at).strftime("%m-%d %H:%M")
            my_text += f"{status_emoji} {created_date}: {short_caption}\n"
    else:
        my_text += "📝 <b>投稿记录</b>: 暂无投稿记录\n"

    my_text += "\n💡 <i>继续投稿来丰富您的记录吧！</i>"

    await update.message.reply_text(my_text, parse_mode=ParseMode.HTML)


async def stop_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, services: ServiceContainer):
    await services.feedback_service.stop_admin_reply(update, context)


async def send_template_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """用于 CallbackQuery 直接发送故事模板（不经 ServiceContainer）"""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(STORY_TEMPLATE, parse_mode=ParseMode.HTML)

