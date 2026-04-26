from typing import Optional, List
from sqlalchemy.orm import Session
import time
import random
import re

from models import user as user_model
from models.user import User, UserRole, UserStatus
from utils.hash import hash_password, verify_password
from utils.random import generate_uuid, get_random_string
from utils.time import get_timestamp
from config import config


# In-memory verification code storage
# Format: { email: { code, expires_at, type } }
_verification_codes = {}

# Login rate limiting
# Format: { username_or_ip: { last_attempt, failed_count, locked_until } }
_login_rate_limits = {}


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def send_verification_code(self, email: str, code_type: str = "register") -> tuple[bool, str]:
        """Send verification code to email"""
        # Validate email format
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return False, "Invalid email format"

        # Check based on type
        existing_user = self.get_user_by_email(email)

        if code_type == "register":
            if existing_user:
                return False, "Email already registered"
        elif code_type == "login":
            if not existing_user:
                return False, "Email not registered"

        # Generate 6-digit code
        code = str(random.randint(100000, 999999))
        expires_at = int(time.time()) + 300  # 5 minutes

        _verification_codes[email] = {
            "code": code,
            "expires_at": expires_at,
            "type": code_type,
        }

        # TODO: Integrate with actual email service
        # For now, just log to console (development mode)
        print(f"[DEV] Verification code for {email}: {code}")

        return True, "Verification code sent"

    def verify_code(self, email: str, code: str, code_type: str = "register") -> tuple[bool, str]:
        """Verify the code and return result"""
        if email not in _verification_codes:
            return False, "No verification code found"

        info = _verification_codes[email]

        # Check expiry
        if time.time() > info["expires_at"]:
            del _verification_codes[email]
            return False, "Verification code expired"

        # Check type
        if info["type"] != code_type:
            return False, "Invalid verification code type"

        # Check code
        if info["code"] != code:
            return False, "Invalid verification code"

        # Success - remove the code
        del _verification_codes[email]
        return True, "Code verified"

    def create_user_with_email(self, email: str, password: str = None, username: str = None, display_name: str = None) -> User:
        """Create user with email verification (password optional)"""
        # Generate username from email if not provided
        if not username:
            username = email.split("@")[0][:12]
            # Make sure username is unique
            base_username = username
            counter = 1
            while self.get_user_by_username(username):
                username = f"{base_username}{counter}"
                counter += 1

        user = User(
            username=username,
            password=hash_password(password) if password else "",
            display_name=display_name or username,
            role=UserRole.COMMON,
            status=UserStatus.ENABLED,
            email=email,
            quota=config.QuotaForNewUser,
            used_quota=0,
            request_count=0,
            group="default",
            access_token=generate_uuid(),
            aff_code=get_random_string(4),
            inviter_id=0,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_all_users(self, offset: int = 0, limit: int = 25, order: str = "id") -> List[User]:
        query = self.db.query(User).filter(User.status != UserStatus.DELETED)

        if order == "quota":
            query = query.order_by(User.quota.desc())
        elif order == "used_quota":
            query = query.order_by(User.used_quota.desc())
        elif order == "request_count":
            query = query.order_by(User.request_count.desc())
        else:
            query = query.order_by(User.id.desc())

        return query.limit(limit).offset(offset).all()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_access_token(self, token: str) -> Optional[User]:
        return self.db.query(User).filter(User.access_token == token).first()

    def get_user_by_github_id(self, github_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.github_id == github_id).first()

    def search_users(self, keyword: str) -> List[User]:
        try:
            uid = int(keyword)
            return self.db.query(User).filter(User.id == uid).all()
        except ValueError:
            return self.db.query(User).filter(
                User.username.like(f"{keyword}%") |
                User.email.like(f"{keyword}%") |
                User.display_name.like(f"{keyword}%")
            ).all()

    def create_user(self, user_data: dict, inviter_id: int = 0) -> User:
        hashed = hash_password(user_data["password"])

        user = User(
            username=user_data["username"],
            password=hashed,
            display_name=user_data.get("display_name", user_data["username"]),
            role=user_data.get("role", UserRole.COMMON),
            status=UserStatus.ENABLED,
            email=user_data.get("email"),
            quota=config.QuotaForNewUser,
            used_quota=0,
            request_count=0,
            group=user_data.get("group", "default"),
            access_token=generate_uuid(),
            aff_code=get_random_string(4),
            inviter_id=inviter_id,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_user_external(self, user_data: dict) -> User:
        user = User(
            username=user_data["username"],
            password="",  # No password for external users
            display_name=user_data.get("display_name", user_data["username"]),
            role=user_data.get("role", UserRole.COMMON),
            status=UserStatus.ENABLED,
            email=user_data.get("email"),
            quota=0,  # External users start with 0 quota
            used_quota=0,
            request_count=0,
            group=user_data.get("group", "default"),
            access_token=generate_uuid(),
            aff_code=get_random_string(4),
            inviter_id=0,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: int, update_data: dict) -> Optional[User]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        if "password" in update_data and update_data["password"]:
            update_data["password"] = hash_password(update_data["password"])

        for key, value in update_data.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: int) -> bool:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        user.username = f"deleted_{get_random_string(8)}"
        user.status = UserStatus.DELETED
        self.db.commit()
        return True

    def validate_login(self, username: str, password: str, ip: str = "") -> tuple[Optional[User], Optional[str]]:
        rate_key = username.lower() if username else ip

        if rate_key in _login_rate_limits:
            info = _login_rate_limits[rate_key]
            locked_until = info.get("locked_until", 0)
            if time.time() < locked_until:
                remaining = int(locked_until - time.time())
                return None, f"Account locked. Try again in {remaining} seconds"

            last_attempt = info.get("last_attempt", 0)
            if last_attempt > 0 and time.time() - last_attempt < 5:
                return None, "Please wait 5 seconds between login attempts"

        user = self.get_user_by_username(username)
        if not user:
            user = self.get_user_by_email(username)

        if not user:
            # Record failed attempt for non-existent user too
            if rate_key not in _login_rate_limits:
                _login_rate_limits[rate_key] = {"failed_count": 0, "last_attempt": 0, "locked_until": 0}
            _login_rate_limits[rate_key]["failed_count"] += 1
            _login_rate_limits[rate_key]["last_attempt"] = time.time()

            # Lock after 5 failed attempts (5 minutes)
            if _login_rate_limits[rate_key]["failed_count"] >= 5:
                _login_rate_limits[rate_key]["locked_until"] = time.time() + 300
                return None, "Too many failed attempts. Account locked for 5 minutes"

            return None, "Invalid username or password"

        if not verify_password(password, user.password):
            # Record failed attempt
            if rate_key not in _login_rate_limits:
                _login_rate_limits[rate_key] = {"failed_count": 0, "last_attempt": 0, "locked_until": 0}
            _login_rate_limits[rate_key]["failed_count"] += 1
            _login_rate_limits[rate_key]["last_attempt"] = time.time()

            # Lock after 5 failed attempts (5 minutes)
            if _login_rate_limits[rate_key]["failed_count"] >= 5:
                _login_rate_limits[rate_key]["locked_until"] = time.time() + 300
                return None, "Too many failed attempts. Account locked for 5 minutes"

            remaining = 5 - _login_rate_limits[rate_key]["failed_count"]
            return None, f"Invalid username or password. {remaining} attempts remaining"

        if user.status != UserStatus.ENABLED:
            return None, "User is disabled"

        # Successful login - clear rate limit
        if rate_key in _login_rate_limits:
            del _login_rate_limits[rate_key]

        return user, None

    def is_admin(self, user_id: int) -> bool:
        user = self.get_user_by_id(user_id)
        return user and user.role >= UserRole.ADMIN

    def is_root(self, user_id: int) -> bool:
        user = self.get_user_by_id(user_id)
        return user and user.role >= UserRole.ROOT

    def get_user_quota(self, user_id: int) -> int:
        user = self.get_user_by_id(user_id)
        return user.quota if user else 0

    def increase_quota(self, user_id: int, quota: int):
        self.db.query(User).filter(User.id == user_id).update({
            "quota": User.quota + quota,
        })
        self.db.commit()

    def decrease_quota(self, user_id: int, quota: int):
        result = self.db.query(User).filter(
            User.id == user_id,
            User.quota >= quota
        ).update({
            "quota": User.quota - quota,
            "used_quota": User.used_quota + quota,
        })
        self.db.commit()
        return result > 0

    def update_used_quota(self, user_id: int, quota: int):
        self.db.query(User).filter(User.id == user_id).update({
            "used_quota": User.used_quota + quota,
            "request_count": User.request_count + 1,
        })
        self.db.commit()

    def get_max_user_id(self) -> int:
        user = self.db.query(User).order_by(User.id.desc()).first()
        return user.id if user else 0
