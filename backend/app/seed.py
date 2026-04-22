from sqlalchemy.orm import Session

from .models import CategoryWeight, GoalkeeperWeight, Skill, SkillTranslation, User
from .security import hash_password


CATEGORY_WEIGHTS = {
    "attacking": 28,
    "possession": 34,
    "defensive": 20,
    "physical": 18,
}

GOALKEEPER_WEIGHTS = {
    "shot_stopping": 55,
    "restart_distribution": 25,
    "sweeper_keeper_ability": 20,
}

SKILLS = [
    ("finishing", "attacking", "both", 100, "\u062a\u0645\u0627\u0645\u200c\u06a9\u0646\u0646\u062f\u06af\u06cc", "Finishing"),
    ("shot_power", "attacking", "both", 96, "\u0642\u062f\u0631\u062a \u0634\u0648\u062a", "Shot Power"),
    ("shot_accuracy", "attacking", "both", 95, "\u062f\u0642\u062a \u0634\u0648\u062a", "Shot Accuracy"),
    ("dribbling", "attacking", "both", 90, "\u062f\u0631\u06cc\u0628\u0644", "Dribbling"),
    ("passing", "possession", "both", 98, "\u067e\u0627\u0633\u200c\u062f\u0647\u06cc", "Passing"),
    ("ball_control", "possession", "both", 97, "\u06a9\u0646\u062a\u0631\u0644 \u062a\u0648\u067e", "Ball Control"),
    ("playmaking", "possession", "both", 99, "\u0628\u0627\u0632\u06cc\u200c\u0633\u0627\u0632\u06cc", "Playmaking"),
    ("defending", "defensive", "both", 88, "\u062f\u0641\u0627\u0639", "Defending"),
    ("positioning_game_intelligence", "defensive", "both", 92, "\u062c\u0627\u06cc\u200c\u06af\u06cc\u0631\u06cc \u0648 \u062f\u0631\u06a9 \u0628\u0627\u0632\u06cc", "Positioning and Game Intelligence"),
    ("work_rate", "physical", "both", 87, "\u062f\u0648\u0646\u062f\u06af\u06cc", "Work Rate"),
    ("stamina", "physical", "both", 86, "\u0627\u0633\u062a\u0642\u0627\u0645\u062a", "Stamina"),
    ("physical_strength", "physical", "both", 84, "\u0642\u062f\u0631\u062a \u0628\u062f\u0646\u06cc", "Physical Strength"),
    ("shot_stopping", "goalkeeping", "goalkeeper_only", 110, "\u062a\u0648\u0627\u0646\u0627\u06cc\u06cc \u0645\u0647\u0627\u0631 \u0634\u0648\u062a", "Shot Stopping"),
    ("restart_distribution", "goalkeeping", "goalkeeper_only", 108, "\u0634\u0631\u0648\u0639 \u0645\u062c\u062f\u062f \u062e\u0648\u0628", "Restart Distribution"),
    ("sweeper_keeper_ability", "goalkeeping", "goalkeeper_only", 106, "\u062a\u0648\u0627\u0646\u0627\u06cc\u06cc \u062c\u0644\u0648 \u0622\u0645\u062f\u0646 \u0648 \u0628\u0627\u0632\u06cc \u062f\u0631 \u062e\u0627\u0631\u062c \u0627\u0632 \u0645\u062d\u0648\u0637\u0647", "Sweeper Keeper Ability"),
]

ADMIN_USER = {
    "username": "admin",
    "password": "admin123",
    "preferred_language": "fa",
    "is_admin": True,
    "is_active": True,
}


def seed_reference_data(session: Session) -> None:
    for category_key, weight in CATEGORY_WEIGHTS.items():
        existing = session.query(CategoryWeight).filter_by(category_key=category_key).one_or_none()
        if existing is None:
            session.add(CategoryWeight(category_key=category_key, weight=weight))
        else:
            existing.weight = weight

    for skill_key, weight in GOALKEEPER_WEIGHTS.items():
        existing = session.query(GoalkeeperWeight).filter_by(skill_key=skill_key).one_or_none()
        if existing is None:
            session.add(GoalkeeperWeight(skill_key=skill_key, weight=weight))
        else:
            existing.weight = weight

    for key, category_key, applies_to_role_group, priority, label_fa, label_en in SKILLS:
        existing_skill = session.query(Skill).filter_by(key=key).one_or_none()
        if existing_skill is None:
            existing_skill = Skill(
                key=key,
                category_key=category_key,
                applies_to_role_group=applies_to_role_group,
                priority=priority,
                is_active=True,
            )
            session.add(existing_skill)
            session.flush()
        else:
            existing_skill.category_key = category_key
            existing_skill.applies_to_role_group = applies_to_role_group
            existing_skill.priority = priority
            existing_skill.is_active = True

        _upsert_translation(session, existing_skill.id, "fa", label_fa)
        _upsert_translation(session, existing_skill.id, "en", label_en)

    _seed_admin_user(session)


def _seed_admin_user(session: Session) -> None:
    existing = session.query(User).filter_by(username=ADMIN_USER["username"]).one_or_none()
    if existing is None:
        session.add(
            User(
                username=ADMIN_USER["username"],
                password_hash=hash_password(ADMIN_USER["password"]),
                preferred_language=ADMIN_USER["preferred_language"],
                is_admin=ADMIN_USER["is_admin"],
                is_active=ADMIN_USER["is_active"],
                is_approved=True,
            )
        )
    else:
        existing.is_active = True
        existing.is_approved = True


def _upsert_translation(session: Session, skill_id: int, language_code: str, label: str) -> None:
    existing_translation = (
        session.query(SkillTranslation)
        .filter_by(skill_id=skill_id, language_code=language_code)
        .one_or_none()
    )
    if existing_translation is None:
        session.add(SkillTranslation(skill_id=skill_id, language_code=language_code, label=label))
    else:
        existing_translation.label = label
