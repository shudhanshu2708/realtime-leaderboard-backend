from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import AppUser
from ..schemas import AuthResponse, LoginRequest, RegisterRequest
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, response_model_by_alias=True,
             status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, session: AsyncSession = Depends(get_session)):
    exists = (await session.execute(select(AppUser.id).where(AppUser.username == req.username))).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
    session.add(AppUser(username=req.username, password=hash_password(req.password)))
    try:
        await session.commit()
    except IntegrityError:  # race: two registrations with the same name
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
    return AuthResponse(token=create_token(req.username))


@router.post("/login", response_model=AuthResponse, response_model_by_alias=True)
async def login(req: LoginRequest, session: AsyncSession = Depends(get_session)):
    user = (await session.execute(select(AppUser).where(AppUser.username == req.username))).scalar_one_or_none()
    if user is None or not verify_password(req.password, user.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return AuthResponse(token=create_token(user.username))
