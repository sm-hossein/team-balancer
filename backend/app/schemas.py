from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    preferred_language: str = Field(default="fa", pattern="^(fa|en)$")
    name_fa: str = Field(min_length=2, max_length=100)
    name_en: str = Field(min_length=2, max_length=100)
    role_type: str = Field(pattern="^(goalkeeper|hybrid|outfield)$")
    appearance_score: float = Field(default=0, ge=0, le=100)
    image_url: str | None = None


class UserLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class AuthResponse(BaseModel):
    token: str
    user: dict
    player: dict | None


class RegistrationResponse(BaseModel):
    user: dict
    player: dict
    message: str


class PlayerCreateRequest(BaseModel):
    name_fa: str = Field(min_length=2, max_length=100)
    name_en: str = Field(min_length=2, max_length=100)
    role_type: str = Field(pattern="^(goalkeeper|hybrid|outfield)$")
    appearance_score: float = Field(default=0, ge=0, le=100)
    image_url: str | None = None
    linked_user_id: int | None = None


class PlayerResponse(BaseModel):
    id: int
    display_name: str
    name_fa: str | None
    name_en: str | None
    role_type: str
    appearance_score: float
    image_url: str | None
    is_active: bool
    linked_user_id: int | None


class PlayerUpdateRequest(BaseModel):
    name_fa: str = Field(min_length=2, max_length=100)
    name_en: str = Field(min_length=2, max_length=100)
    role_type: str = Field(pattern="^(goalkeeper|hybrid|outfield)$")
    appearance_score: float = Field(default=0, ge=0, le=100)
    image_url: str | None = None
    is_active: bool = True


class SelfProfileUpdateRequest(BaseModel):
    name_fa: str = Field(min_length=2, max_length=100)
    name_en: str = Field(min_length=2, max_length=100)
    role_type: str = Field(pattern="^(goalkeeper|hybrid|outfield)$")
    image_url: str | None = None
    preferred_language: str = Field(default="fa", pattern="^(fa|en)$")


class UserResponse(BaseModel):
    id: int
    username: str
    preferred_language: str
    is_admin: bool


class AdminUserCreateResponse(BaseModel):
    user: dict
    player: dict


class ComparisonQuestionResponse(BaseModel):
    skill: dict
    player_a: dict
    player_b: dict
    existing_answer_count: int
    disagreement_count: int


class ComparisonAnswerRequest(BaseModel):
    skill_key: str
    player_a_id: int
    player_b_id: int
    winner_player_id: int


class ComparisonAnswerResponse(BaseModel):
    comparison_id: int
    existing_answer_count: int


class ComparisonSkipRequest(BaseModel):
    skill_key: str
    player_a_id: int
    player_b_id: int


class ComparisonSkipResponse(BaseModel):
    skip_id: int


class AdminComparisonResponse(BaseModel):
    id: int
    created_at: str
    evaluator_user: dict
    skill: dict
    player_a: dict
    player_b: dict
    winner_player_id: int


class PendingRegistrationResponse(BaseModel):
    user: dict
    player: dict


class TeamGenerationRequest(BaseModel):
    team_count: int = Field(ge=2, le=8)
    players_per_team: int = Field(ge=1, le=10)
    selected_player_ids: list[int] = Field(min_length=4)
    goalkeeper_ids: list[int] = Field(default_factory=list)
    previous_team_player_ids: list[list[int]] = Field(default_factory=list)
