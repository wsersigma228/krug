from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (
    Event, Project, ProjectMember, Team, TeamApplication, TeamEngagement, TeamMember, TeamOpening,
    User,
)
from backend.pagination import cursor_scope, decode_cursor, encode_cursor, make_page, seek_page
from backend.platform_schemas import (
    ApplicationInput, ApplicationResponse, ApplicationStatus, EngagementPatch, MemberResponse,
    OpeningInput, OpeningPatch, OpeningResponse, TeamInput, TeamParams, TeamPatch, TeamResponse,
)
from backend.project_access import canonical_project_url
from backend.project_schemas import InterestedUser, ProjectCreate, ProjectResponse
from backend.rate_limit import check_rate_limit
from backend.routes.platform_common import (
    _search_labels, joined_page, lock_actor, owned, page_response, visible,
)
from backend.schemas import Page, PageParams
from backend.security import get_current_user, get_optional_user


router = APIRouter()


DatabaseId = Annotated[int, Path(gt=0, le=2_147_483_647)]


async def team_responses(db, rows, user_id=None):
    rows = list(rows)
    if not rows:
        return []
    ids = [row.id for row in rows]
    members_counts = dict((await db.execute(
        select(TeamMember.team_id, func.count()).where(TeamMember.team_id.in_(ids))
        .group_by(TeamMember.team_id))).all())
    openings_counts = dict((await db.execute(
        select(TeamOpening.team_id, func.count()).where(TeamOpening.team_id.in_(ids),
            TeamOpening.status == "open").group_by(TeamOpening.team_id))).all())
    interested_counts = dict((await db.execute(
        select(TeamEngagement.team_id, func.count()).where(TeamEngagement.team_id.in_(ids),
            TeamEngagement.interested.is_(True), TeamEngagement.interested_visible.is_(True))
            .group_by(TeamEngagement.team_id))).all())
    members = {}
    engagement = {}
    if user_id is not None:
        members = dict((await db.execute(select(TeamMember.team_id, func.count()).where(
            TeamMember.team_id.in_(ids), TeamMember.user_id == user_id).group_by(TeamMember.team_id))).all())
        engagement = {key: {"saved": saved, "interested": interested, "interested_visible": visible}
                      for key, saved, interested, visible in (await db.execute(
            select(TeamEngagement.team_id, TeamEngagement.saved, TeamEngagement.interested,
                   TeamEngagement.interested_visible).where(TeamEngagement.user_id == user_id,
                                                              TeamEngagement.team_id.in_(ids)))).all()}
    return [TeamResponse.model_validate(row).model_copy(update={
        "member_count": members_counts.get(row.id, 0), "openings_count": openings_counts.get(row.id, 0),
        "interested_count": interested_counts.get(row.id, 0),
        "saved": engagement.get(row.id, {}).get("saved", False),
        "interested": engagement.get(row.id, {}).get("interested", False),
        "interested_visible": engagement.get(row.id, {}).get("interested_visible", False),
        "is_member": bool(members.get(row.id, 0)),
    }) for row in rows]


@router.get("/teams", response_model=Page[TeamResponse])
async def list_teams(params: Annotated[TeamParams, Query()], db: AsyncSession = Depends(get_db),
                     user: User | None = Depends(get_optional_user)):
    values = params.model_dump(exclude={"cursor", "limit"})
    if params.saved is not None and user is None:
        raise HTTPException(401, "Sign in to filter saved teams")
    scope = cursor_scope("teams", user_id=user.id if user else None, **values)
    cursor = decode_cursor(params.cursor, scope)
    query = select(Team).where(or_(Team.visibility == "public",
        Team.owner_id == (user.id if user else -1)))
    if params.saved is not None:
        query = query.outerjoin(TeamEngagement, (TeamEngagement.team_id == Team.id)
            & (TeamEngagement.user_id == user.id)).where(
                func.coalesce(TeamEngagement.saved, False).is_(params.saved))
    if params.search:
        terms = func.websearch_to_tsquery("pg_catalog.simple", params.search.strip())
        labels = _search_labels(params.search)
        query = query.where(or_(Team.search_vector.bool_op("@@")(terms),
                                Team.skills.overlap(labels), Team.topics.overlap(labels)))
    if params.skill:
        query = query.where(Team.skills.contains([params.skill.strip().lower()]))
    if params.topic:
        query = query.where(Team.topics.contains([params.topic.strip().lower()]))
    if params.language:
        query = query.where(Team.languages.contains([params.language.strip().lower()]))
    if params.format:
        query = query.where(Team.format == params.format)
    if params.status:
        query = query.where(Team.status == params.status)
    else:
        query = query.where(Team.status != "archived")
    if params.event_id:
        query = query.where(Team.event_id == params.event_id)
    rows = (await db.scalars(seek_page(query, Team, cursor, params.limit))).all()
    selected = rows[:params.limit]
    return page_response(await team_responses(db, selected, user.id if user else None), len(rows) > params.limit,
                         selected[-1] if selected else None, scope)


@router.post("/teams", response_model=TeamResponse, status_code=201)
async def create_team(body: TeamInput, request: Request, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "team-create", str(user.id))
    actor = await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    if body.event_id:
        event = await db.scalar(select(Event).where(Event.id == body.event_id))
        if event is None or (event.visibility != "public" and event.owner_id != user.id):
            raise HTTPException(404, "Event not found")
    team = Team(**body.model_dump(), owner_id=user.id)
    db.add(team)
    try:
        await db.flush()
        db.add(TeamMember(team_id=team.id, user_id=user.id, role="Owner"))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Team slug already exists") from None
    await db.refresh(team)
    return (await team_responses(db, [team], user.id if user else None))[0]


@router.get("/teams/{slug}", response_model=TeamResponse)
async def get_team(slug: str, db: AsyncSession = Depends(get_db),
                   user: User | None = Depends(get_optional_user)):
    team = await visible(db, Team, slug, user)
    return (await team_responses(db, [team], user.id if user else None))[0]


@router.patch("/teams/{slug}", response_model=TeamResponse)
async def patch_team(slug: str, body: TeamPatch, db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
    team = await owned(db, Team, slug, user.id, lock=True)
    values = body.model_dump(exclude_unset=True)
    if "event_id" in values and values["event_id"] is not None:
        event = await db.scalar(select(Event).where(Event.id == values["event_id"]))
        if event is None or (event.visibility != "public" and event.owner_id != user.id):
            raise HTTPException(404, "Event not found")
    for key, value in values.items():
        setattr(team, key, value)
    await db.commit()
    await db.refresh(team)
    return (await team_responses(db, [team], user.id))[0]


@router.delete("/teams/{slug}", status_code=204)
async def delete_team(slug: str, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    team = await owned(db, Team, slug, user.id, lock=True)
    key = team.cover_key
    await db.delete(team)
    await db.commit()
    from backend.media import delete_photo
    delete_photo(key)


@router.get("/teams/{slug}/members", response_model=Page[MemberResponse])
async def team_members(slug: str, params: Annotated[PageParams, Query()],
                       db: AsyncSession = Depends(get_db),
                       user: User | None = Depends(get_optional_user)):
    team = await visible(db, Team, slug, user)
    scope = cursor_scope("team_members", team_id=team.id,
                         owner=user.id if user and user.id == team.owner_id and team.visibility != "public" else None)
    cursor = decode_cursor(params.cursor, scope)
    query = select(TeamMember.id, TeamMember.user_id, User.username, User.display_name,
                   User.avatar_key, TeamMember.role, TeamMember.joined_at).join(
        User, User.id == TeamMember.user_id).where(TeamMember.team_id == team.id)
    if cursor:
        query = query.where(tuple_(TeamMember.joined_at, TeamMember.id) < tuple_(cursor.created_at, cursor.id))
    rows = (await db.execute(query.order_by(TeamMember.joined_at.desc(), TeamMember.id.desc()).limit(params.limit + 1))).all()
    selected, more = rows[:params.limit], len(rows) > params.limit
    return {"items": [{"id": row.id, "user_id": row.user_id, "username": row.username,
                       "display_name": row.display_name, "role": row.role,
                       "joined_at": row.joined_at,
                       "avatar_url": f"/users/{row.user_id}/avatar" if row.avatar_key else None}
                      for row in selected], "has_more": more,
            "next_cursor": encode_cursor(selected[-1].joined_at, selected[-1].id, scope) if more else None}


@router.get("/teams/{slug}/openings", response_model=Page[OpeningResponse])
async def list_team_openings(slug: str, params: Annotated[PageParams, Query()],
                             db: AsyncSession = Depends(get_db),
                             user: User | None = Depends(get_optional_user)):
    team = await visible(db, Team, slug, user)
    owner_view = user is not None and user.id == team.owner_id
    scope = cursor_scope("team_openings", team_id=team.id, owner=user.id if owner_view else None)
    cursor = decode_cursor(params.cursor, scope)
    query = select(TeamOpening).where(TeamOpening.team_id == team.id)
    if not owner_view:
        query = query.where(TeamOpening.status == "open")
    rows = (await db.scalars(seek_page(query,
                                        TeamOpening, cursor, params.limit))).all()
    return make_page(rows, params.limit, scope)


@router.post("/teams/{slug}/openings", response_model=OpeningResponse, status_code=201)
async def create_team_opening(slug: str, body: OpeningInput, db: AsyncSession = Depends(get_db),
                              user: User = Depends(get_current_user)):
    team = await owned(db, Team, slug, user.id, lock=True)
    opening = TeamOpening(team_id=team.id, **body.model_dump())
    db.add(opening)
    await db.commit()
    await db.refresh(opening)
    return opening


@router.patch("/team-openings/{opening_id}", response_model=OpeningResponse)
async def patch_team_opening(opening_id: DatabaseId, body: OpeningPatch,
                             db: AsyncSession = Depends(get_db),
                             user: User = Depends(get_current_user)):
    team_id = await db.scalar(select(TeamOpening.team_id).where(TeamOpening.id == opening_id))
    if team_id is None:
        raise HTTPException(404, "Opening not found")
    team = await db.scalar(select(Team).where(
        Team.id == team_id, Team.owner_id == user.id).with_for_update())
    if team is None:
        raise HTTPException(404, "Opening not found")
    opening = await db.scalar(select(TeamOpening).where(
        TeamOpening.id == opening_id, TeamOpening.team_id == team.id)
        .execution_options(populate_existing=True).with_for_update())
    if opening is None:
        raise HTTPException(404, "Opening not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(opening, key, value)
    await db.commit()
    await db.refresh(opening)
    return opening


@router.post("/team-openings/{opening_id}/applications", response_model=ApplicationResponse, status_code=201)
async def apply_to_team(opening_id: DatabaseId, body: ApplicationInput,
                        request: Request,
                        db: AsyncSession = Depends(get_db),
                        user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "team-application", str(user.id))
    await lock_actor(db, user.id)
    team_id = await db.scalar(select(TeamOpening.team_id).where(TeamOpening.id == opening_id))
    if team_id is None:
        raise HTTPException(404, "Opening not found")
    team = await db.scalar(select(Team).where(Team.id == team_id).with_for_update())
    if team is None:
        raise HTTPException(404, "Opening not found")
    opening = await db.scalar(select(TeamOpening).where(
        TeamOpening.id == opening_id, TeamOpening.team_id == team.id)
        .execution_options(populate_existing=True).with_for_update())
    if opening is None or team.visibility != "public" or team.status != "recruiting" or opening.status != "open":
        raise HTTPException(404, "Opening not found")
    if await db.scalar(select(TeamMember.id).where(TeamMember.team_id == opening.team_id,
                                                   TeamMember.user_id == user.id)):
        raise HTTPException(409, "Already a team member")
    application = TeamApplication(opening_id=opening.id, applicant_id=user.id, message=body.message)
    db.add(application)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Application already exists") from None
    await db.refresh(application)
    return application


@router.get("/team-applications", response_model=Page[dict])
async def my_team_applications(params: Annotated[PageParams, Query()],
                               db: AsyncSession = Depends(get_db),
                               user: User = Depends(get_current_user)):
    scope = cursor_scope("my_team_applications", user_id=user.id)
    cursor = decode_cursor(params.cursor, scope)
    query = select(TeamApplication, Team.slug, Team.title, TeamOpening.title).join(
        TeamOpening, TeamOpening.id == TeamApplication.opening_id).join(
        Team, Team.id == TeamOpening.team_id).where(TeamApplication.applicant_id == user.id)
    rows = (await db.execute(seek_page(query, TeamApplication, cursor, params.limit))).all()
    page = joined_page(rows, params.limit, scope)
    page["items"] = [{**ApplicationResponse.model_validate(row[0]).model_dump(),
                      "team_slug": row[1], "team_title": row[2], "opening_title": row[3]}
                     for row in page["items"]]
    return page


@router.get("/teams/{slug}/applications", response_model=Page[dict])
async def list_team_applications(slug: str, params: Annotated[PageParams, Query()],
                                 db: AsyncSession = Depends(get_db),
                                 user: User = Depends(get_current_user)):
    team = await owned(db, Team, slug, user.id)
    scope = cursor_scope("team_applications", team_id=team.id)
    cursor = decode_cursor(params.cursor, scope)
    query = select(TeamApplication, TeamOpening.title, User.username, User.display_name).join(
        TeamOpening, TeamOpening.id == TeamApplication.opening_id).join(
        User, User.id == TeamApplication.applicant_id).where(TeamOpening.team_id == team.id)
    rows = (await db.execute(seek_page(query, TeamApplication, cursor, params.limit))).all()
    page = joined_page(rows, params.limit, scope)
    page["items"] = [{**ApplicationResponse.model_validate(row[0]).model_dump(),
                      "opening_title": row[1], "applicant_username": row[2],
                      "applicant_display_name": row[3]} for row in page["items"]]
    return page


@router.patch("/team-applications/{application_id}", response_model=ApplicationResponse)
async def change_team_application(application_id: DatabaseId, body: ApplicationStatus,
                                  db: AsyncSession = Depends(get_db),
                                  user: User = Depends(get_current_user)):
    app = await db.scalar(select(TeamApplication).where(TeamApplication.id == application_id))
    if app is None:
        raise HTTPException(404, "Application not found")
    opening = await db.scalar(select(TeamOpening).where(TeamOpening.id == app.opening_id))
    if opening is None:
        raise HTTPException(404, "Application not found")
    owner_action = await db.scalar(select(Team.owner_id).where(Team.id == opening.team_id)) == user.id
    account_ids = sorted({user.id, app.applicant_id} if owner_action else {user.id})
    for account_id in account_ids:
        exists = await db.scalar(select(User.id).where(User.id == account_id)
                                 .with_for_update(read=True, key_share=True))
        if exists is None:
            raise HTTPException(404, "Application not found")
    team = await db.scalar(select(Team).where(Team.id == opening.team_id).with_for_update())
    if team is None:
        raise HTTPException(404, "Application not found")
    app = await db.scalar(select(TeamApplication).where(TeamApplication.id == application_id)
                          .execution_options(populate_existing=True).with_for_update())
    if app is None:
        raise HTTPException(404, "Application not found")
    owner_action = user.id == team.owner_id
    if owner_action:
        if body.status not in {"accepted", "rejected"}:
            raise HTTPException(422, "Owners can accept or reject applications")
    elif app.applicant_id == user.id and body.status == "withdrawn":
        pass
    else:
        raise HTTPException(404, "Application not found")
    if app.status != "pending":
        raise HTTPException(409, "Application is no longer pending")
    if body.status == "accepted":
        await db.execute(insert(TeamMember).values(team_id=team.id, user_id=app.applicant_id,
            role="Member").on_conflict_do_nothing(index_elements=["team_id", "user_id"]))
    app.status = body.status
    await db.commit()
    await db.refresh(app)
    return app


@router.post("/teams/{slug}/project", response_model=ProjectResponse, status_code=201)
async def transfer_team_to_project(slug: str, body: ProjectCreate,
                                   request: Request,
                                   db: AsyncSession = Depends(get_db),
                                   user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "project-create", str(user.id))
    await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    team = await owned(db, Team, slug, user.id, lock=True)
    if team.linked_project_id is not None:
        project = await db.get(Project, team.linked_project_id)
        if project is not None:
            return project
        raise HTTPException(409, "Team already transferred")
    if body.derived_from_project_id is not None:
        source = await db.scalar(select(Project).where(Project.id == body.derived_from_project_id,
            Project.origin == "external", Project.visibility == "public").with_for_update(read=True))
        if source is None:
            raise HTTPException(404, "Source project not found")
    project = Project(**body.model_dump(), owner_id=user.id, origin="native",
        canonical_url=None if body.derived_from_project_id else canonical_project_url(body.source_url),
        source_name=None, source_external_id=None, last_activity_at=datetime.now(timezone.utc))
    db.add(project)
    try:
        await db.flush()
        members = (await db.scalars(select(TeamMember).where(TeamMember.team_id == team.id)
                                    .order_by(TeamMember.user_id, TeamMember.id))).all()
        for member in members:
            db.add(ProjectMember(project_id=project.id, user_id=member.user_id, role=member.role,
                                 joined_at=member.joined_at))
        team.linked_project_id = project.id
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Project slug or source URL already exists") from None
    await db.refresh(project)
    return project


async def team_engagement(db, team, user_id, changes=None):
    if changes is not None:
        await lock_actor(db, user_id)
        await db.execute(insert(TeamEngagement).values(team_id=team.id, user_id=user_id)
            .on_conflict_do_nothing(constraint="uq_team_engagement_user"))
        row = await db.scalar(select(TeamEngagement).where(TeamEngagement.team_id == team.id,
            TeamEngagement.user_id == user_id).execution_options(populate_existing=True).with_for_update())
        if changes.get("interested_visible") is True and not changes.get("interested", row.interested):
            raise HTTPException(422, "Visible interest requires interested=true")
        for key, value in changes.items():
            setattr(row, key, value)
        if not row.interested:
            row.interested_visible = False
        await db.commit()
    else:
        row = await db.scalar(select(TeamEngagement).where(TeamEngagement.team_id == team.id,
            TeamEngagement.user_id == user_id))
    return {"saved": row.saved if row else False, "interested": row.interested if row else False,
            "interested_visible": row.interested_visible if row else False}


@router.get("/teams/{slug}/engagement")
async def get_team_engagement(slug: str, db: AsyncSession = Depends(get_db),
                              user: User = Depends(get_current_user)):
    team = await visible(db, Team, slug, user)
    return await team_engagement(db, team, user.id)


@router.get("/teams/{slug}/interested", response_model=Page[InterestedUser])
async def team_interested(slug: str, params: Annotated[PageParams, Query()],
                          db: AsyncSession = Depends(get_db),
                          user: User | None = Depends(get_optional_user)):
    team = await visible(db, Team, slug, user)
    scope = cursor_scope("team_interested", team_id=team.id)
    query = select(TeamEngagement, User.id.label("user_id"),
                   User.username, User.display_name, User.bio, User.avatar_key).join(
        User, User.id == TeamEngagement.user_id).where(
            TeamEngagement.team_id == team.id, TeamEngagement.interested.is_(True),
            TeamEngagement.interested_visible.is_(True))
    rows = (await db.execute(seek_page(query, TeamEngagement,
        decode_cursor(params.cursor, scope), params.limit))).all()
    page = joined_page(rows, params.limit, scope)
    page["items"] = [{"id": row.user_id, "username": row.username,
                      "display_name": row.display_name, "bio": row.bio,
                      "avatar_url": f"/users/{row.user_id}/avatar" if row.avatar_key else None}
                     for row in page["items"]]
    return page


@router.patch("/teams/{slug}/engagement")
async def patch_team_engagement(slug: str, body: EngagementPatch,
                                request: Request,
                                db: AsyncSession = Depends(get_db),
                                user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "team-engagement", str(user.id))
    await lock_actor(db, user.id)
    team = await visible(db, Team, slug, user, lock=True)
    return await team_engagement(db, team, user.id, body.model_dump(exclude_unset=True))
