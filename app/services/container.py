from __future__ import annotations

from app.config import Settings
from app.database import Database
from app.services.admin_service import AdminService
from app.services.feedback_service import FeedbackService
from app.services.stats_service import StatsService
from app.services.submission_service import SubmissionService


class ServiceContainer:
    """集中管理所有依赖与服务的容器。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database()
        self.stats_service = StatsService(self)
        self.admin_service = AdminService(self)
        self.submission_service = SubmissionService(self)
        self.feedback_service = FeedbackService(self)

