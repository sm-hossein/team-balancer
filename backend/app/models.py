from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    preferred_language: Mapped[str] = mapped_column(String(5), default="fa")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True)


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name_fa: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    name_en: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    role_type: Mapped[str] = mapped_column(String(20), index=True)
    appearance_score: Mapped[float] = mapped_column(Float, default=0.0)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    linked_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class CategoryWeight(Base):
    __tablename__ = "category_weights"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_key: Mapped[str] = mapped_column(String(30), unique=True)
    weight: Mapped[int] = mapped_column(Integer)


class GoalkeeperWeight(Base):
    __tablename__ = "goalkeeper_weights"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_key: Mapped[str] = mapped_column(String(50), unique=True)
    weight: Mapped[int] = mapped_column(Integer)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    category_key: Mapped[str] = mapped_column(String(30), index=True)
    applies_to_role_group: Mapped[str] = mapped_column(String(20))
    priority: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SkillTranslation(Base):
    __tablename__ = "skill_translations"
    __table_args__ = (
        UniqueConstraint("skill_id", "language_code", name="uq_skill_translation_lang"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    language_code: Mapped[str] = mapped_column(String(5))
    label: Mapped[str] = mapped_column(String(120))


class Comparison(Base):
    __tablename__ = "comparisons"
    __table_args__ = (
        UniqueConstraint(
            "skill_id",
            "evaluator_user_id",
            "player_a_id",
            "player_b_id",
            name="uq_comparison_per_user_pair_skill",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), index=True)
    evaluator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    player_a_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    player_b_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    winner_player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    comparison_value: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ComparisonSkip(Base):
    __tablename__ = "comparison_skips"
    __table_args__ = (
        UniqueConstraint(
            "skill_id",
            "evaluator_user_id",
            "player_a_id",
            "player_b_id",
            name="uq_comparison_skip_per_user_pair_skill",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), index=True)
    evaluator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    player_a_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    player_b_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
