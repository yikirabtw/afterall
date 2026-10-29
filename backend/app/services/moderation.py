"""Решения по жалобам. Права проверяет тот, кто вызывает (бот — по роли и списку админов из настроек)."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ModerationActionKind, ReportStatus, UserRole
from app.db.models import ModerationAction, Report, User
from app.domain.safety import BAN_WEEK
from app.domain.time import as_utc

OPEN_STATUSES = (ReportStatus.OPEN, ReportStatus.IN_REVIEW)
RESOLUTIONS = {"ban7": "Бан на 7 дней", "ban": "Бан навсегда", "reject": "Жалоба отклонена"}


def can_moderate(user: User, admin_ids: frozenset[int]) -> bool:
    return user.role in (UserRole.MODERATOR, UserRole.ADMIN) or user.telegram_id in admin_ids


async def decide_report(session: AsyncSession, report: Report, action: str, moderator: User, now: datetime) -> None:
    """ban7 / ban — бан нарушителя и закрытие всех его открытых жалоб; reject — отклонить только эту."""
    resolution = RESOLUTIONS[action]
    if action == "reject":
        _close(report, ReportStatus.REJECTED, moderator, resolution, now)
        return

    target = await session.get(User, report.target_user_id)
    until = now + BAN_WEEK if action == "ban7" else None
    if target.is_banned and (target.banned_until is None or (until and as_utc(target.banned_until) > until)):
        until = target.banned_until  # уже забанен дольше — не сокращаем
    target.is_banned = True
    target.banned_until = until
    session.add(
        ModerationAction(
            moderator_id=moderator.id,
            target_user_id=target.id,
            report_id=report.id,
            action=ModerationActionKind.BAN,
            reason=f"{resolution} (жалоба #{report.id}: {report.reason})",
            expires_at=until,
        )
    )
    # Остальные жалобы на того же человека тоже решены этим баном
    others = await session.scalars(
        select(Report).where(Report.target_user_id == target.id, Report.status.in_(OPEN_STATUSES))
    )
    for item in {report, *others}:
        _close(item, ReportStatus.RESOLVED, moderator, resolution, now)


def _close(report: Report, status: ReportStatus, moderator: User, resolution: str, now: datetime) -> None:
    report.status = status
    report.moderator_id = moderator.id
    report.resolution = resolution
    report.resolved_at = now
