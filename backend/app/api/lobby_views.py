"""Сборка ответов о пати. Здесь решается, кто какие данные видит."""

from datetime import datetime

from sqlalchemy.orm import selectinload

from app.api.schemas import LobbyDetailOut, LobbyMemberOut, LobbyOut, LobbyOwnerOut
from app.db.enums import MemberStatus
from app.db.models import Lobby, LobbyMember, User, UserGame
from app.domain.lobbies import effective_status

# Что подгружать вместе с пати: для ленты — без участников-людей, для карточки — с их анкетами и играми
FEED_OPTIONS = (
    selectinload(Lobby.members),
    selectinload(Lobby.owner).selectinload(User.profile),
)
DETAIL_OPTIONS = (
    selectinload(Lobby.owner).selectinload(User.profile),
    selectinload(Lobby.members).selectinload(LobbyMember.user).selectinload(User.profile),
    selectinload(Lobby.members)
    .selectinload(LobbyMember.user)
    .selectinload(User.games)
    .selectinload(UserGame.roles),
)


def _my_membership(lobby: Lobby, viewer_id: int) -> LobbyMember | None:
    return next((member for member in lobby.members if member.user_id == viewer_id), None)


def _sees_contacts(membership: LobbyMember | None) -> bool:
    return membership is not None and membership.status == MemberStatus.ACCEPTED


def lobby_out(lobby: Lobby, viewer_id: int, now: datetime) -> LobbyOut:
    membership = _my_membership(lobby, viewer_id)
    owner_profile = lobby.owner.profile
    return LobbyOut(
        id=lobby.id,
        kind=lobby.kind,
        game_id=lobby.game_id,
        title=lobby.title,
        description=lobby.description,
        slots_total=lobby.slots_total,
        slots_taken=sum(member.status == MemberStatus.ACCEPTED for member in lobby.members),
        rank_min_id=lobby.rank_min_id,
        rank_max_id=lobby.rank_max_id,
        need_mic=lobby.need_mic,
        play_style=lobby.play_style,
        language=lobby.language,
        starts_at=lobby.starts_at,
        expires_at=lobby.expires_at,
        status=effective_status(lobby.status, lobby.expires_at, now),
        owner=LobbyOwnerOut(
            user_id=lobby.owner_id,
            display_name=owner_profile.display_name if owner_profile else lobby.owner.first_name,
            avatar_url=owner_profile.avatar_url if owner_profile else None,
            reputation=owner_profile.reputation if owner_profile else 0,
        ),
        is_owner=lobby.owner_id == viewer_id,
        my_status=membership.status if membership else None,
        contact_link=lobby.contact_link if _sees_contacts(membership) else None,
        is_private=lobby.is_private,
    )


def _member_out(member: LobbyMember, game_id: int | None, with_contacts: bool) -> LobbyMemberOut:
    user = member.user
    profile = user.profile
    user_game = next((game for game in user.games if game.game_id == game_id), None)
    show_contacts = with_contacts and member.status == MemberStatus.ACCEPTED
    return LobbyMemberOut(
        user_id=user.id,
        display_name=profile.display_name if profile else user.first_name,
        avatar_url=profile.avatar_url if profile else None,
        reputation=profile.reputation if profile else 0,
        has_mic=profile.has_mic if profile else False,
        rank_id=user_game.rank_id if user_game else None,
        role_ids=user_game.role_ids if user_game else [],
        faceit_elo=user_game.faceit_elo if user_game else None,
        status=member.status,
        is_owner=member.is_owner,
        note=member.note,
        username=user.username if show_contacts and profile and profile.show_telegram else None,
        discord_tag=profile.discord_tag if show_contacts and profile else None,
    )


def lobby_detail_out(lobby: Lobby, viewer_id: int, now: datetime) -> LobbyDetailOut:
    membership = _my_membership(lobby, viewer_id)
    if lobby.owner_id == viewer_id:
        visible_statuses = {MemberStatus.PENDING, MemberStatus.ACCEPTED}
    elif _sees_contacts(membership):
        visible_statuses = {MemberStatus.ACCEPTED}
    else:
        visible_statuses = set()

    members = [
        _member_out(member, lobby.game_id, with_contacts=_sees_contacts(membership))
        for member in sorted(lobby.members, key=lambda m: (not m.is_owner, m.id))
        if member.status in visible_statuses
    ]
    return LobbyDetailOut(
        **lobby_out(lobby, viewer_id, now).model_dump(),
        members=members,
        # Пригласить в закрытую пати может только создатель — код видит только он
        invite_code=lobby.invite_code if lobby.owner_id == viewer_id else None,
    )
