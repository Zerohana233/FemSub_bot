from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.database import Database
from app.models import MediaFile, Submission, SubmissionStatus


def _create_submission(submission_id: str) -> Submission:
    return Submission(
        submission_id=submission_id,
        user_id=12345,
        username="tester",
        media_files=[MediaFile(file_id="file_1", file_type="photo")],
        caption="hello world",
        caption_only="hello world",
        is_anonymous=False,
        tags="#tag1",
        status=SubmissionStatus.PENDING,
        created_at=datetime.utcnow(),
    )


def test_save_and_load_submission(tmp_path: Path):
    db_path = tmp_path / "test.db"
    database = Database(db_path=str(db_path))

    submission = _create_submission("test_1")
    database.save_submission(submission)

    loaded = database.get_submission("test_1")
    assert loaded is not None
    assert loaded.submission_id == "test_1"
    assert loaded.caption_only == "hello world"
    assert loaded.media_files[0].file_id == "file_1"


def test_update_status_and_tags(tmp_path: Path):
    db_path = tmp_path / "test2.db"
    database = Database(db_path=str(db_path))

    submission = _create_submission("test_2")
    database.save_submission(submission)

    database.update_submission_status("test_2", SubmissionStatus.APPROVED)
    database.update_submission_tags("test_2", ["#a", "#b"])

    loaded = database.get_submission("test_2")
    assert loaded is not None
    assert loaded.status == SubmissionStatus.APPROVED
    assert loaded.tags == "#a #b"

