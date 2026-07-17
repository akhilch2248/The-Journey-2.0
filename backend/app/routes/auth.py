from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models.user import User
from ..schemas.auth import DevLoginRequest, TokenResponse, UserRead
from ..utils.auth_tokens import create_access_token
from ..utils.provider_tokens import ProviderTokenError, verify_provider_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_or_create_user(db: Session, provider: str, provider_id: str, email: str | None) -> User:
    user = (
        db.query(User)
        .filter(User.provider == provider, User.provider_id == provider_id)
        .first()
    )
    if user is None:
        user = User(provider=provider, provider_id=provider_id, email=email)
        db.add(user)
    elif email and user.email != email:
        user.email = email
    db.commit()
    db.refresh(user)
    return user


def _login(provider: str, payload: DevLoginRequest, db: Session) -> TokenResponse:
    settings = get_settings()
    id_token = payload.id_token.strip()
    if not id_token:
        raise HTTPException(status_code=400, detail="id_token must not be empty")

    if settings.auth_mode == "dev":
        # DEV MODE: the raw string IS the identity. Local testing only.
        identity = {"provider_id": id_token, "email": None}
    else:
        audience = settings.apple_audience if provider == "apple" else settings.google_audience
        if not audience:
            raise HTTPException(
                status_code=500,
                detail=f"{provider}_audience is not configured for production auth",
            )
        try:
            identity = verify_provider_token(provider, id_token, audience)
        except ProviderTokenError as exc:
            raise HTTPException(status_code=401, detail=str(exc))

    user = _get_or_create_user(db, provider, identity["provider_id"], identity["email"])
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.get("/config")
def auth_config():
    """Lets clients adapt their sign-in UI (dev identity field vs real SDKs)."""
    return {"mode": get_settings().auth_mode}


@router.post("/apple", response_model=TokenResponse)
def login_apple(payload: DevLoginRequest, db: Session = Depends(get_db)):
    return _login("apple", payload, db)


@router.post("/google", response_model=TokenResponse)
def login_google(payload: DevLoginRequest, db: Session = Depends(get_db)):
    return _login("google", payload, db)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user
