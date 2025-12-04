from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class SubmissionStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class MediaFile:
    file_id: str
    file_type: str  # 'photo', 'video', 'document'
    caption: Optional[str] = None


@dataclass
class Submission:
    submission_id: str
    user_id: int
    username: str
    media_files: List[MediaFile]
    caption: str  # 显示时的完整文案（caption_only + tags）
    caption_only: str  # 原始文案（不包含tags）
    is_anonymous: bool
    tags: str  # 标签字符串（例如 "#Tag1 #Tag2"）
    status: SubmissionStatus
    created_at: datetime
    media_group_id: Optional[str] = None
    admin_message_id: Optional[int] = None
    preview_message_id: Optional[int] = None

