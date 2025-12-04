from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class DashboardStats:
    total: int
    status_counts: Dict[str, int]
    daily_counts: List[Tuple[str, int]]
    top_submitters: List[Tuple[str, int]]


@dataclass(frozen=True)
class UserSummary:
    username: str
    total: int
    status_counts: Dict[str, int]
    recent_submissions: List[Tuple[str, str, str, str]]


class StatsService:
    """封装统计相关的数据库查询，便于 handler 复用。"""

    def __init__(self, container):
        self.db_path = container.db.db_path

    def get_dashboard(self) -> DashboardStats:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM submissions")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT status, COUNT(*) FROM submissions GROUP BY status")
        status_counts = dict(cursor.fetchall())

        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        cursor.execute(
            """
            SELECT DATE(created_at) as date, COUNT(*)
            FROM submissions
            WHERE created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """,
            (seven_days_ago,),
        )
        daily_counts = cursor.fetchall()

        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        cursor.execute(
            """
            SELECT COALESCE(username, ''), COUNT(*) as count
            FROM submissions
            WHERE created_at >= ?
            GROUP BY user_id, username
            ORDER BY count DESC
            LIMIT 10
        """,
            (thirty_days_ago,),
        )
        top_submitters = cursor.fetchall()

        conn.close()

        return DashboardStats(
            total=total,
            status_counts=status_counts,
            daily_counts=daily_counts,
            top_submitters=top_submitters,
        )

    def get_user_summary(self, user_id: int, username: str) -> UserSummary:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT status, COUNT(*)
            FROM submissions
            WHERE user_id = ?
            GROUP BY status
        """,
            (user_id,),
        )
        status_counts = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM submissions WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT submission_id, caption_only, tags, status, created_at
            FROM submissions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        """,
            (user_id,),
        )
        recent = cursor.fetchall()

        conn.close()

        recent_compact = [
            (
                sub_id,
                caption_only or "",
                tags or "",
                status,
                created_at,
            )
            for sub_id, caption_only, tags, status, created_at in recent
        ]

        return UserSummary(
            username=username,
            total=total,
            status_counts=status_counts,
            recent_submissions=recent_compact,
        )

