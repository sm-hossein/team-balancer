from contextlib import asynccontextmanager
from itertools import combinations
import os
import random
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage

from .database import Base, engine, run_migrations, session_scope
from .models import (
    AuthToken,
    CategoryWeight,
    Comparison,
    ComparisonSkip,
    GoalkeeperWeight,
    Player,
    Skill,
    SkillTranslation,
    User,
)
from .schemas import (
    AdminPasswordResetRequest,
    AdminUserCreateResponse,
    AdminComparisonResponse,
    AuthResponse,
    ComparisonAnswerRequest,
    ComparisonAnswerResponse,
    ComparisonQuestionResponse,
    ComparisonSkipRequest,
    ComparisonSkipResponse,
    PasswordChangeRequest,
    PlayerCreateRequest,
    PlayerResponse,
    PlayerUpdateRequest,
    PendingRegistrationResponse,
    SelfProfileUpdateRequest,
    TeamGenerationRequest,
    UserLoginRequest,
    UserRegisterRequest,
)
from .ratings import compute_player_ratings
from .security import create_token, hash_password, verify_password
from .seed import seed_reference_data
from .team_generation import generate_balanced_teams


MAX_PLAYER_IMAGE_BYTES = 2 * 1024 * 1024
PLAYER_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
    with session_scope() as session:
        seed_reference_data(session)
    yield


app = FastAPI(
    title="Team Balancer API",
    version="0.1.0",
    lifespan=lifespan,
)

default_cors_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", ",".join(default_cors_origins)).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_user(authorization: str | None = Header(default=None)) -> User:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    token_value = authorization.removeprefix("Bearer ").strip()
    with session_scope() as session:
        auth_token = session.query(AuthToken).filter_by(token=token_value).one_or_none()
        if auth_token is None:
            raise HTTPException(status_code=401, detail="Invalid token.")

        user = session.query(User).filter_by(id=auth_token.user_id).one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found.")
        session.expunge(user)
        return user


def _require_admin(user: User = Depends(_require_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


def _serialize_user(user: User) -> dict[str, object]:
    return {
        "id": user.id,
        "username": user.username,
        "preferred_language": user.preferred_language,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "is_approved": user.is_approved,
    }


def _serialize_player(player: Player) -> dict[str, object]:
    return {
        "id": player.id,
        "display_name": player.display_name,
        "name_fa": player.name_fa,
        "name_en": player.name_en,
        "role_type": player.role_type,
        "appearance_score": player.appearance_score,
        "image_url": player.image_url,
        "is_active": player.is_active,
        "linked_user_id": player.linked_user_id,
    }


def _serialize_skill(session, skill: Skill) -> dict[str, object]:
    translations = (
        session.query(SkillTranslation)
        .filter(SkillTranslation.skill_id == skill.id)
        .order_by(SkillTranslation.language_code)
        .all()
    )
    return {
        "key": skill.key,
        "category_key": skill.category_key,
        "applies_to_role_group": skill.applies_to_role_group,
        "priority": skill.priority,
        "translations": [
            {
                "language_code": translation.language_code,
                "label": translation.label,
            }
            for translation in translations
        ],
    }


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/uploads/player-image")
async def upload_player_image(
    file: UploadFile = File(...),
    current_user: User = Depends(_require_user),
) -> dict[str, str]:
    _ = current_user
    bucket_name = os.getenv("PLAYER_IMAGE_BUCKET")
    if not bucket_name:
        raise HTTPException(status_code=503, detail="Image storage is not configured.")

    extension = PLAYER_IMAGE_CONTENT_TYPES.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WebP images are allowed.")

    data = await file.read(MAX_PLAYER_IMAGE_BYTES + 1)
    if len(data) > MAX_PLAYER_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 2 MB or smaller.")
    if not data:
        raise HTTPException(status_code=400, detail="Image file is empty.")

    blob_name = f"player-images/{uuid4().hex}{extension}"
    blob = storage.Client().bucket(bucket_name).blob(blob_name)
    blob.cache_control = "public, max-age=31536000"
    blob.upload_from_string(data, content_type=file.content_type)

    return {"image_url": f"https://storage.googleapis.com/{bucket_name}/{blob_name}"}


@app.get("/api/reference-data")
def get_reference_data() -> dict[str, list[dict[str, object]]]:
    with session_scope() as session:
        category_weights = session.query(CategoryWeight).order_by(CategoryWeight.category_key).all()
        goalkeeper_weights = session.query(GoalkeeperWeight).order_by(GoalkeeperWeight.skill_key).all()
        skills = session.query(Skill).order_by(Skill.priority.desc(), Skill.key).all()

        serialized_skills: list[dict[str, object]] = []
        for skill in skills:
            serialized_skills.append(_serialize_skill(session, skill))

        return {
            "category_weights": [
                {"category_key": item.category_key, "weight": item.weight}
                for item in category_weights
            ],
            "goalkeeper_weights": [
                {"skill_key": item.skill_key, "weight": item.weight}
                for item in goalkeeper_weights
            ],
            "skills": serialized_skills,
        }


@app.post("/api/admin/users", response_model=AdminUserCreateResponse, status_code=status.HTTP_201_CREATED)
def create_user_account(
    payload: UserRegisterRequest,
    current_user: User = Depends(_require_admin),
) -> AdminUserCreateResponse:
    _ = current_user
    with session_scope() as session:
        if session.query(User).filter_by(username=payload.username).one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Username already exists.")
        existing_player = (
            session.query(Player)
            .filter((Player.name_fa == payload.name_fa) | (Player.name_en == payload.name_en))
            .one_or_none()
        )
        if existing_player is not None:
            raise HTTPException(status_code=409, detail="Player name already exists.")

        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            preferred_language=payload.preferred_language,
            is_admin=False,
            is_active=True,
            is_approved=True,
        )
        session.add(user)
        session.flush()

        player = Player(
            display_name=payload.name_en,
            name_fa=payload.name_fa,
            name_en=payload.name_en,
            role_type=payload.role_type,
            appearance_score=payload.appearance_score,
            image_url=payload.image_url,
            is_active=True,
            linked_user_id=user.id,
        )
        session.add(player)
        session.flush()

        return AdminUserCreateResponse(
            user=_serialize_user(user),
            player=_serialize_player(player),
        )


@app.put("/api/admin/users/{username}/password")
def reset_user_password(
    username: str,
    payload: AdminPasswordResetRequest,
    current_user: User = Depends(_require_admin),
) -> dict[str, str]:
    _ = current_user
    with session_scope() as session:
        user = session.query(User).filter_by(username=username).one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")

        user.password_hash = hash_password(payload.new_password)
        session.query(AuthToken).filter_by(user_id=user.id).delete(synchronize_session=False)
        return {"status": "ok"}


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: UserLoginRequest) -> AuthResponse:
    with session_scope() as session:
        user = session.query(User).filter_by(username=payload.username).one_or_none()
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="This account is inactive.")
        if not user.is_approved:
            raise HTTPException(status_code=403, detail="This account is waiting for admin approval.")

        token_value = create_token()
        session.add(AuthToken(user_id=user.id, token=token_value))

        player = session.query(Player).filter_by(linked_user_id=user.id).one_or_none()
        return AuthResponse(
            token=token_value,
            user=_serialize_user(user),
            player=_serialize_player(player) if player else None,
        )


@app.get("/api/me")
def me(current_user: User = Depends(_require_user)) -> dict[str, object]:
    with session_scope() as session:
        player = session.query(Player).filter_by(linked_user_id=current_user.id).one_or_none()
        return {
            "user": _serialize_user(current_user),
            "player": _serialize_player(player) if player else None,
        }


@app.put("/api/me", response_model=AuthResponse)
def update_me(
    payload: SelfProfileUpdateRequest,
    authorization: str | None = Header(default=None),
    current_user: User = Depends(_require_user),
) -> AuthResponse:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token_value = authorization.removeprefix("Bearer ").strip()

    with session_scope() as session:
        user = session.query(User).filter_by(id=current_user.id).one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")

        player = session.query(Player).filter_by(linked_user_id=user.id).one_or_none()
        if player is None:
            raise HTTPException(status_code=404, detail="Linked player not found.")

        existing_player = (
            session.query(Player)
            .filter(
                Player.id != player.id,
                ((Player.name_fa == payload.name_fa) | (Player.name_en == payload.name_en)),
            )
            .one_or_none()
        )
        if existing_player is not None:
            raise HTTPException(status_code=409, detail="Player name already exists.")

        user.preferred_language = payload.preferred_language
        player.name_fa = payload.name_fa
        player.name_en = payload.name_en
        player.display_name = payload.name_en
        player.role_type = payload.role_type
        player.image_url = payload.image_url
        session.flush()

        return AuthResponse(
            token=token_value,
            user=_serialize_user(user),
            player=_serialize_player(player),
        )


@app.put("/api/me/password")
def change_password(
    payload: PasswordChangeRequest,
    authorization: str | None = Header(default=None),
    current_user: User = Depends(_require_user),
) -> dict[str, str]:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token_value = authorization.removeprefix("Bearer ").strip()

    with session_scope() as session:
        user = session.query(User).filter_by(id=current_user.id).one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        if not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect.")
        if payload.current_password == payload.new_password:
            raise HTTPException(status_code=400, detail="New password must be different from the current password.")

        user.password_hash = hash_password(payload.new_password)
        session.query(AuthToken).filter(
            AuthToken.user_id == user.id,
            AuthToken.token != token_value,
        ).delete(synchronize_session=False)

    return {"message": "Password updated."}


@app.get("/api/progress")
def get_progress(current_user: User = Depends(_require_user)) -> dict[str, int | float]:
    with session_scope() as session:
        evaluator_player = session.query(Player).filter_by(linked_user_id=current_user.id).one_or_none()
        active_players = session.query(Player).filter_by(is_active=True).all()
        skills = session.query(Skill).filter_by(is_active=True).all()
        own_player_id = evaluator_player.id if evaluator_player else None

        total_possible = 0
        for skill in skills:
            eligible_players = [
                player
                for player in active_players
                if skill.applies_to_role_group != "goalkeeper_only"
                or player.role_type in {"goalkeeper", "hybrid"}
            ]
            for first, second in combinations(eligible_players, 2):
                if own_player_id is not None and own_player_id in {first.id, second.id}:
                    continue
                total_possible += 1

        answered_count = session.query(Comparison).filter_by(evaluator_user_id=current_user.id).count()
        skipped_count = session.query(ComparisonSkip).filter_by(evaluator_user_id=current_user.id).count()
        completed = answered_count + skipped_count
        completion_percent = (completed * 100 / total_possible) if total_possible else 100.0
        return {
            "answered_count": answered_count,
            "skipped_count": skipped_count,
            "total_possible": total_possible,
            "completion_percent": round(completion_percent, 1),
        }


@app.get("/api/players", response_model=list[PlayerResponse])
def list_players(current_user: User = Depends(_require_user)) -> list[PlayerResponse]:
    with session_scope() as session:
        query = session.query(Player)
        if not current_user.is_admin:
            query = query.filter_by(is_active=True)
        players = query.order_by(Player.appearance_score.desc(), Player.display_name).all()
        return [PlayerResponse(**_serialize_player(player)) for player in players]


@app.get("/api/ratings")
def get_ratings(current_user: User = Depends(_require_user)) -> dict[str, object]:
    with session_scope() as session:
        ratings = compute_player_ratings(
            session,
            include_inactive=current_user.is_admin,
        )
        return {"items": ratings}


@app.get("/api/admin/comparisons", response_model=list[AdminComparisonResponse])
def list_admin_comparisons(current_user: User = Depends(_require_admin)) -> list[AdminComparisonResponse]:
    _ = current_user
    with session_scope() as session:
        comparisons = session.query(Comparison).order_by(Comparison.created_at.desc(), Comparison.id.desc()).all()
        users = {user.id: user for user in session.query(User).all()}
        players = {player.id: player for player in session.query(Player).all()}
        skills = {skill.id: skill for skill in session.query(Skill).all()}

        return [
            AdminComparisonResponse(
                id=comparison.id,
                created_at=comparison.created_at.isoformat(),
                evaluator_user=_serialize_user(users[comparison.evaluator_user_id]),
                skill=_serialize_skill(session, skills[comparison.skill_id]),
                player_a=_serialize_player(players[comparison.player_a_id]),
                player_b=_serialize_player(players[comparison.player_b_id]),
                winner_player_id=comparison.winner_player_id,
            )
            for comparison in comparisons
            if comparison.evaluator_user_id in users
            and comparison.skill_id in skills
            and comparison.player_a_id in players
            and comparison.player_b_id in players
        ]


@app.get("/api/admin/pending-registrations", response_model=list[PendingRegistrationResponse])
def list_pending_registrations(current_user: User = Depends(_require_admin)) -> list[PendingRegistrationResponse]:
    _ = current_user
    with session_scope() as session:
        users = (
            session.query(User)
            .filter_by(is_admin=False, is_approved=False)
            .order_by(User.id.desc())
            .all()
        )
        user_ids = [user.id for user in users]
        if not user_ids:
            return []
        players = {
            player.linked_user_id: player
            for player in session.query(Player).filter(Player.linked_user_id.in_(user_ids)).all()
        }
        return [
            PendingRegistrationResponse(
                user=_serialize_user(user),
                player=_serialize_player(players[user.id]),
            )
            for user in users
            if user.id in players
        ]


@app.post("/api/admin/registrations/{user_id}/approve", response_model=PendingRegistrationResponse)
def approve_registration(user_id: int, current_user: User = Depends(_require_admin)) -> PendingRegistrationResponse:
    _ = current_user
    with session_scope() as session:
        user = session.query(User).filter_by(id=user_id, is_admin=False).one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        player = session.query(Player).filter_by(linked_user_id=user.id).one_or_none()
        if player is None:
            raise HTTPException(status_code=404, detail="Linked player not found.")
        user.is_approved = True
        user.is_active = True
        player.is_active = True
        session.flush()
        return PendingRegistrationResponse(
            user=_serialize_user(user),
            player=_serialize_player(player),
        )


@app.delete("/api/admin/registrations/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def reject_registration(user_id: int, current_user: User = Depends(_require_admin)) -> None:
    _ = current_user
    with session_scope() as session:
        user = session.query(User).filter_by(id=user_id, is_admin=False, is_approved=False).one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="Pending user not found.")
        session.query(AuthToken).filter_by(user_id=user.id).delete(synchronize_session=False)
        session.query(Player).filter_by(linked_user_id=user.id).delete(synchronize_session=False)
        session.delete(user)


@app.post("/api/team-generation")
def create_balanced_teams(
    payload: TeamGenerationRequest,
    current_user: User = Depends(_require_admin),
) -> dict[str, object]:
    _ = current_user
    with session_scope() as session:
        try:
            result = generate_balanced_teams(
                session,
                selected_player_ids=payload.selected_player_ids,
                team_count=payload.team_count,
                goalkeeper_ids=payload.goalkeeper_ids,
                players_per_team=payload.players_per_team,
                previous_team_player_ids=payload.previous_team_player_ids,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return result


@app.post("/api/players", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
def create_player(payload: PlayerCreateRequest, current_user: User = Depends(_require_admin)) -> PlayerResponse:
    _ = current_user
    with session_scope() as session:
        existing = (
            session.query(Player)
            .filter((Player.name_fa == payload.name_fa) | (Player.name_en == payload.name_en))
            .one_or_none()
        )
        if existing is not None:
            raise HTTPException(status_code=409, detail="Player already exists.")

        if payload.linked_user_id is not None:
            linked_user = session.query(User).filter_by(id=payload.linked_user_id).one_or_none()
            if linked_user is None:
                raise HTTPException(status_code=404, detail="Linked user not found.")

        player = Player(
            display_name=payload.name_en,
            name_fa=payload.name_fa,
            name_en=payload.name_en,
            role_type=payload.role_type,
            appearance_score=payload.appearance_score,
            image_url=payload.image_url,
            linked_user_id=payload.linked_user_id,
            is_active=True,
        )
        session.add(player)
        session.flush()
        return PlayerResponse(**_serialize_player(player))


@app.put("/api/players/{player_id}", response_model=PlayerResponse)
def update_player(
    player_id: int,
    payload: PlayerUpdateRequest,
    current_user: User = Depends(_require_admin),
) -> PlayerResponse:
    _ = current_user
    with session_scope() as session:
        player = session.query(Player).filter_by(id=player_id).one_or_none()
        if player is None:
            raise HTTPException(status_code=404, detail="Player not found.")

        duplicate = (
            session.query(Player)
            .filter(
                ((Player.name_fa == payload.name_fa) | (Player.name_en == payload.name_en)),
                Player.id != player_id,
            )
            .one_or_none()
        )
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Player name already exists.")

        player.display_name = payload.name_en
        player.name_fa = payload.name_fa
        player.name_en = payload.name_en
        player.role_type = payload.role_type
        player.appearance_score = payload.appearance_score
        player.image_url = payload.image_url
        player.is_active = payload.is_active
        session.flush()
        return PlayerResponse(**_serialize_player(player))


@app.delete("/api/players/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_player(
    player_id: int,
    current_user: User = Depends(_require_admin),
) -> None:
    with session_scope() as session:
        player = session.query(Player).filter_by(id=player_id).one_or_none()
        if player is None:
            raise HTTPException(status_code=404, detail="Player not found.")

        linked_user_id = player.linked_user_id
        if linked_user_id == current_user.id:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own admin account.")

        player.is_active = False

        if linked_user_id is not None:
            linked_user = session.query(User).filter_by(id=linked_user_id).one_or_none()
            if linked_user is not None:
                linked_user.is_active = False
            session.query(AuthToken).filter_by(user_id=linked_user_id).delete(synchronize_session=False)


@app.get("/api/comparisons/next", response_model=ComparisonQuestionResponse | None)
def get_next_comparison(current_user: User = Depends(_require_user)) -> ComparisonQuestionResponse | None:
    with session_scope() as session:
        evaluator_player = session.query(Player).filter_by(linked_user_id=current_user.id).one_or_none()
        active_players = session.query(Player).filter_by(is_active=True).order_by(Player.id).all()
        skills = session.query(Skill).filter_by(is_active=True).order_by(Skill.priority.desc(), Skill.id).all()
        comparisons = session.query(Comparison).all()
        skips = session.query(ComparisonSkip).filter_by(evaluator_user_id=current_user.id).all()

        own_player_id = evaluator_player.id if evaluator_player else None

        answered_by_user = {
            (comparison.skill_id, comparison.player_a_id, comparison.player_b_id)
            for comparison in comparisons
            if comparison.evaluator_user_id == current_user.id
        }
        skipped_by_user = {
            (skip.skill_id, skip.player_a_id, skip.player_b_id)
            for skip in skips
        }
        user_skill_counts: dict[int, int] = {}
        for comparison in comparisons:
            if comparison.evaluator_user_id == current_user.id:
                user_skill_counts[comparison.skill_id] = user_skill_counts.get(comparison.skill_id, 0) + 1
        for skip in skips:
            user_skill_counts[skip.skill_id] = user_skill_counts.get(skip.skill_id, 0) + 1
        recent_skill_ids: list[int] = []
        recent_events = [
            (comparison.created_at, comparison.skill_id)
            for comparison in comparisons
            if comparison.evaluator_user_id == current_user.id
        ] + [
            (skip.created_at, skip.skill_id)
            for skip in skips
        ]
        recent_events.sort(key=lambda item: item[0], reverse=True)
        for _, skill_id in recent_events[:2]:
            recent_skill_ids.append(skill_id)

        player_exposure: dict[int, int] = {player.id: 0 for player in active_players}
        pair_stats: dict[tuple[int, int, int], list[Comparison]] = {}
        for comparison in comparisons:
            key = (comparison.skill_id, comparison.player_a_id, comparison.player_b_id)
            pair_stats.setdefault(key, []).append(comparison)
            player_exposure[comparison.player_a_id] = player_exposure.get(comparison.player_a_id, 0) + 1
            player_exposure[comparison.player_b_id] = player_exposure.get(comparison.player_b_id, 0) + 1

        candidate_pool: list[tuple[float, Skill, Player, Player, int, int]] = []

        for skill in skills:
            eligible_players = [
                player
                for player in active_players
                if skill.applies_to_role_group != "goalkeeper_only"
                or player.role_type in {"goalkeeper", "hybrid"}
            ]

            for first, second in combinations(eligible_players, 2):
                if own_player_id is not None and own_player_id in {first.id, second.id}:
                    continue

                player_a, player_b = sorted((first, second), key=lambda item: item.id)
                pair_key = (skill.id, player_a.id, player_b.id)
                if pair_key in answered_by_user or pair_key in skipped_by_user:
                    continue

                prior_answers = pair_stats.get(pair_key, [])
                answer_count = len(prior_answers)
                winner_counts: dict[int, int] = {}
                for answer in prior_answers:
                    winner_counts[answer.winner_player_id] = winner_counts.get(answer.winner_player_id, 0) + 1
                disagreement_count = 0
                if winner_counts:
                    disagreement_count = answer_count - max(winner_counts.values())

                appearance_signal = player_a.appearance_score + player_b.appearance_score
                exposure_gap = max(0, 8 - player_exposure.get(player_a.id, 0)) + max(
                    0, 8 - player_exposure.get(player_b.id, 0)
                )
                skill_familiarity_penalty = user_skill_counts.get(skill.id, 0) * 18
                score = (
                    skill.priority * 100
                    + appearance_signal * 2
                    + exposure_gap * 12
                    - answer_count * 40
                    + disagreement_count * 25
                    - skill_familiarity_penalty
                )

                candidate_pool.append(
                    (
                        score,
                        skill,
                        player_a,
                        player_b,
                        answer_count,
                        disagreement_count,
                    )
                )

        if not candidate_pool:
            return None

        candidates_by_skill: dict[int, list[tuple[float, Skill, Player, Player, int, int]]] = {}
        for candidate in candidate_pool:
            candidates_by_skill.setdefault(candidate[1].id, []).append(candidate)

        min_seen_count = min(user_skill_counts.get(skill_id, 0) for skill_id in candidates_by_skill)
        eligible_skill_groups = []
        for skill_id, skill_candidates in candidates_by_skill.items():
            seen_count = user_skill_counts.get(skill_id, 0)
            if seen_count == min_seen_count:
                skill_candidates.sort(key=lambda item: item[0], reverse=True)
                eligible_skill_groups.append(skill_candidates)

        if len(eligible_skill_groups) > 1 and recent_skill_ids:
            filtered_skill_groups = [
                skill_candidates
                for skill_candidates in eligible_skill_groups
                if skill_candidates[0][1].id != recent_skill_ids[0]
            ]
            if filtered_skill_groups:
                eligible_skill_groups = filtered_skill_groups

        if len(eligible_skill_groups) > 2 and len(recent_skill_ids) > 1:
            filtered_skill_groups = [
                skill_candidates
                for skill_candidates in eligible_skill_groups
                if skill_candidates[0][1].id != recent_skill_ids[1]
            ]
            if filtered_skill_groups:
                eligible_skill_groups = filtered_skill_groups

        chosen_skill_group = random.choice(eligible_skill_groups)

        top_skill_candidates = chosen_skill_group[: min(6, len(chosen_skill_group))]
        group_best_score = top_skill_candidates[0][0]
        candidate_weights = [
            1 / (group_best_score - candidate[0] + 1)
            for candidate in top_skill_candidates
        ]
        _, skill, player_a, player_b, answer_count, disagreement_count = random.choices(
            top_skill_candidates,
            weights=candidate_weights,
            k=1,
        )[0]
        return ComparisonQuestionResponse(
            skill=_serialize_skill(session, skill),
            player_a=_serialize_player(player_a),
            player_b=_serialize_player(player_b),
            existing_answer_count=answer_count,
            disagreement_count=disagreement_count,
        )


@app.post("/api/comparisons", response_model=ComparisonAnswerResponse, status_code=status.HTTP_201_CREATED)
def submit_comparison_answer(
    payload: ComparisonAnswerRequest,
    current_user: User = Depends(_require_user),
) -> ComparisonAnswerResponse:
    with session_scope() as session:
        skill = session.query(Skill).filter_by(key=payload.skill_key, is_active=True).one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found.")

        player_a = session.query(Player).filter_by(id=payload.player_a_id, is_active=True).one_or_none()
        player_b = session.query(Player).filter_by(id=payload.player_b_id, is_active=True).one_or_none()
        if player_a is None or player_b is None:
            raise HTTPException(status_code=404, detail="Player not found.")
        if player_a.id == player_b.id:
            raise HTTPException(status_code=400, detail="Comparison requires two distinct players.")

        evaluator_player = session.query(Player).filter_by(linked_user_id=current_user.id).one_or_none()
        if evaluator_player and evaluator_player.id in {player_a.id, player_b.id}:
            raise HTTPException(status_code=400, detail="You cannot evaluate yourself.")

        if payload.winner_player_id not in {player_a.id, player_b.id}:
            raise HTTPException(status_code=400, detail="Winner must be one of the compared players.")

        if skill.applies_to_role_group == "goalkeeper_only":
            valid_roles = {"goalkeeper", "hybrid"}
            if player_a.role_type not in valid_roles or player_b.role_type not in valid_roles:
                raise HTTPException(status_code=400, detail="Goalkeeper skills require goalkeeper-capable players.")

        ordered_a, ordered_b = sorted((player_a.id, player_b.id))
        existing = (
            session.query(Comparison)
            .filter_by(
                skill_id=skill.id,
                evaluator_user_id=current_user.id,
                player_a_id=ordered_a,
                player_b_id=ordered_b,
            )
            .one_or_none()
        )
        if existing is not None:
            raise HTTPException(status_code=409, detail="You already answered this comparison.")

        comparison = Comparison(
            skill_id=skill.id,
            evaluator_user_id=current_user.id,
            player_a_id=ordered_a,
            player_b_id=ordered_b,
            winner_player_id=payload.winner_player_id,
            comparison_value=1 if payload.winner_player_id == ordered_a else -1,
        )
        session.add(comparison)
        session.flush()

        answer_count = (
            session.query(Comparison)
            .filter_by(skill_id=skill.id, player_a_id=ordered_a, player_b_id=ordered_b)
            .count()
        )

        return ComparisonAnswerResponse(
            comparison_id=comparison.id,
            existing_answer_count=answer_count,
        )


@app.post("/api/comparisons/skip", response_model=ComparisonSkipResponse, status_code=status.HTTP_201_CREATED)
def skip_comparison(
    payload: ComparisonSkipRequest,
    current_user: User = Depends(_require_user),
) -> ComparisonSkipResponse:
    with session_scope() as session:
        skill = session.query(Skill).filter_by(key=payload.skill_key, is_active=True).one_or_none()
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found.")

        player_a = session.query(Player).filter_by(id=payload.player_a_id, is_active=True).one_or_none()
        player_b = session.query(Player).filter_by(id=payload.player_b_id, is_active=True).one_or_none()
        if player_a is None or player_b is None:
            raise HTTPException(status_code=404, detail="Player not found.")
        if player_a.id == player_b.id:
            raise HTTPException(status_code=400, detail="Comparison requires two distinct players.")

        ordered_a, ordered_b = sorted((player_a.id, player_b.id))
        existing_skip = (
            session.query(ComparisonSkip)
            .filter_by(
                skill_id=skill.id,
                evaluator_user_id=current_user.id,
                player_a_id=ordered_a,
                player_b_id=ordered_b,
            )
            .one_or_none()
        )
        if existing_skip is not None:
            return ComparisonSkipResponse(skip_id=existing_skip.id)

        skip = ComparisonSkip(
            skill_id=skill.id,
            evaluator_user_id=current_user.id,
            player_a_id=ordered_a,
            player_b_id=ordered_b,
        )
        session.add(skip)
        session.flush()
        return ComparisonSkipResponse(skip_id=skip.id)
