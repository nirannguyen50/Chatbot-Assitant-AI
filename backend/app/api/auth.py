from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.email import send_reset_email

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email đã được đăng ký")

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password", status_code=200)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Luôn trả 200 dù email có tồn tại hay không — tránh lộ thông tin tài khoản.
    Email được gửi trong background để response không bị chậm.
    """
    user = db.query(User).filter(User.email == data.email).first()
    if user:
        # Vô hiệu hoá token cũ còn hiệu lực của user này
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,  # noqa: E712
            PasswordResetToken.expires_at > datetime.utcnow(),
        ).update({"used": True})

        raw_token, token_hash = PasswordResetToken.generate()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(reset_token)
        db.commit()

        background_tasks.add_task(send_reset_email, user.email, raw_token)

    return {"message": "Nếu email tồn tại, bạn sẽ nhận được link đặt lại mật khẩu."}


@router.post("/reset-password", status_code=200)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = PasswordResetToken.hash(data.token)
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash
    ).first()

    if not record or record.used:
        raise HTTPException(status_code=400, detail="Link đã được sử dụng hoặc không hợp lệ.")

    if datetime.utcnow() >= record.expires_at:
        raise HTTPException(status_code=400, detail="Link đã hết hạn. Vui lòng yêu cầu link mới.")

    record.user.hashed_password = hash_password(data.new_password)
    record.used = True
    db.commit()

    return {"message": "Mật khẩu đã được đặt lại thành công."}
