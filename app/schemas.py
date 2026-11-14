from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """JSON uses camelCase (userId, tokenType...) to match the original Java API."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RegisterRequest(CamelModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def bcrypt_limit(cls, v: str) -> str:
        if len(v.encode()) > 72:
            raise ValueError("password must be at most 72 bytes")
        return v

    @field_validator("username")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


class LoginRequest(CamelModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AuthResponse(CamelModel):
    token: str
    token_type: str = "Bearer"


class ScoreRequest(CamelModel):
    points: int = Field(ge=1, le=1_000_000)


class LeaderboardRow(CamelModel):
    rank: int
    user_id: int
    username: str
    score: float


class ScoreResponse(CamelModel):
    added: int
    total_score: float
    rank: int
    recorded_at: datetime
