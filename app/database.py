from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional

from app.models import MediaFile, Submission, SubmissionStatus


class Database:
    """SQLite 数据访问封装"""

    def __init__(self, db_path: str = "femsub.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                media_files TEXT NOT NULL,
                caption TEXT,
                caption_only TEXT,
                is_anonymous BOOLEAN DEFAULT 0,
                tags TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                media_group_id TEXT,
                admin_message_id INTEGER,
                preview_message_id INTEGER,
                decision_by INTEGER
            )
        """
        )

        try:
            cursor.execute("ALTER TABLE submissions ADD COLUMN decision_by INTEGER")
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()

    def save_submission(self, submission: Submission):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO submissions
            (submission_id, user_id, username, media_files, caption, caption_only,
             is_anonymous, tags, status, created_at, media_group_id,
             admin_message_id, preview_message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                submission.submission_id,
                submission.user_id,
                submission.username,
                json.dumps(
                    [
                        {"file_id": m.file_id, "file_type": m.file_type, "caption": m.caption}
                        for m in submission.media_files
                    ]
                ),
                submission.caption,
                submission.caption_only,
                submission.is_anonymous,
                submission.tags,
                submission.status.value,
                submission.created_at.isoformat(),
                submission.media_group_id,
                submission.admin_message_id,
                submission.preview_message_id,
            ),
        )

        conn.commit()
        conn.close()

    def get_submission(self, submission_id: str) -> Optional[Submission]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM submissions WHERE submission_id = ?", (submission_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        if len(row) <= 12:
            caption_only = row[4]
            tags = row[6] if row[6] else ""
        else:
            caption_only = row[5] if row[5] else row[4]
            tags = row[7] if row[7] else ""

        try:
            media_files_data = json.loads(row[3])
        except json.JSONDecodeError as exc:
            logging.error("Invalid media_files JSON for submission %s: %s", submission_id, exc)
            media_files_data = []

        media_files = [MediaFile(**m) for m in media_files_data]

        return Submission(
            submission_id=row[0],
            user_id=row[1],
            username=row[2],
            media_files=media_files,
            caption=row[4],
            caption_only=caption_only,
            is_anonymous=bool(row[5] if len(row) <= 12 else row[6]),
            tags=tags,
            status=SubmissionStatus(row[7] if len(row) <= 12 else row[8]),
            created_at=datetime.fromisoformat(row[8] if len(row) <= 12 else row[9]),
            media_group_id=row[9] if len(row) <= 12 else row[10],
            admin_message_id=row[10] if len(row) <= 12 else row[11],
            preview_message_id=row[11] if len(row) <= 12 else row[12],
        )

    def update_submission_status(self, submission_id: str, status: SubmissionStatus):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE submissions SET status = ? WHERE submission_id = ?", (status.value, submission_id))
        conn.commit()
        conn.close()

    def update_submission_caption(self, submission_id: str, caption: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE submissions SET caption = ? WHERE submission_id = ?", (caption, submission_id))
        conn.commit()
        conn.close()

    def update_submission_tags(self, submission_id: str, tags: List[str]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE submissions SET tags = ? WHERE submission_id = ?", (" ".join(tags), submission_id))
        conn.commit()
        conn.close()

