import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import DB, CurrentUser, client_ip
from app.core.security import create_access_token, hash_password, verify_password
from app.models import AuditLog, Profile, User
from app.schemas.api import AuthOut, GoogleLoginIn, LoginIn, RegisterIn, UserOut
from app.services.usage import track

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue(response: Response, user: User, is_new: bool = False) -> AuthOut:
    s = get_settings()
    token = create_access_token(user.id, user.role)
    response.set_cookie(
        s.cookie_name, token, httponly=True, secure=s.cookie_secure, samesite="lax",
        max_age=s.access_token_minutes * 60, path="/",
    )
    return AuthOut(access_token=token, user=UserOut.model_validate(user), is_new=is_new)


def _create_user(db, email: str, *, name: str | None, locale: str, password: str | None, provider: str) -> User:
    s = get_settings()
    role = "admin" if s.admin_email and email.lower() == s.admin_email.lower() else "user"
    user = User(email=email.lower(), name=name, locale=locale, role=role, auth_provider=provider,
                password_hash=hash_password(password) if password else None)
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id, language=locale))
    track(db, user.id, "signed_up", provider=provider)
    return user


@router.post("/register", response_model=AuthOut, status_code=201)
def register(body: RegisterIn, response: Response, db: DB, request: Request):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = _create_user(db, body.email, name=body.name, locale=body.locale, password=body.password, provider="password")
    db.add(AuditLog(actor_id=user.id, action="auth.register", entity="user", entity_id=str(user.id), ip=client_ip(request)))
    db.commit()
    return _issue(response, user, is_new=True)


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, response: Response, db: DB, request: Request):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        db.add(AuditLog(actor_id=user.id if user else None, action="auth.login_failed", ip=client_ip(request)))
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    db.add(AuditLog(actor_id=user.id, action="auth.login", ip=client_ip(request)))
    db.commit()
    return _issue(response, user)


@router.post("/google", response_model=AuthOut)
def google_login(body: GoogleLoginIn, response: Response, db: DB, request: Request):
    s = get_settings()
    if not s.google_client_id:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Google sign-in is not configured")
    info = verify_google_id_token(body.id_token)
    if info.get("aud") != s.google_client_id or info.get("email_verified") not in ("true", True) or not info.get("email"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Google token")
    user = db.scalar(select(User).where(User.email == info["email"].lower()))
    is_new = user is None
    if is_new:
        user = _create_user(db, info["email"], name=info.get("name"), locale=body.locale, password=None, provider="google")
    elif not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    elif not user.name and info.get("name"):
        user.name = info["name"][:200]
    db.add(AuditLog(actor_id=user.id, action="auth.google", ip=client_ip(request)))
    db.commit()
    return _issue(response, user, is_new=is_new)


def verify_google_id_token(id_token: str) -> dict:
    """Validate a Google Identity Services ID token via Google's tokeninfo endpoint (checks signature & expiry)."""
    try:
        r = httpx.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token}, timeout=10)
    except httpx.HTTPError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Google is unreachable, try again") from e
    info = r.json() if r.status_code == 200 else {}
    if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        return {}
    return info


@router.post("/apple")
def apple_login():
    # Interface reserved: Sign in with Apple requires a Services ID, key and JWKS verification per deployment.
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Apple sign-in is not configured")


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(get_settings().cookie_name, path="/")
    return {"ok": True}


@router.get("/providers")
def providers():
    s = get_settings()
    return {"password": True, "google": bool(s.google_client_id), "google_client_id": s.google_client_id,
            "apple": False}


@router.get("/whoami", response_model=UserOut)
def whoami(user: CurrentUser):
    return user
