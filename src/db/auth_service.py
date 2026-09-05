import datetime
import hashlib
import hmac
import re
import secrets
from db.manager import DatabaseManager


class AuthService:
    """
    Cryptographic authentication & user management service for Space Shooters.
    
    Provides:
    - PBKDF2-HMAC-SHA256 password hashing (100,000 rounds with 16-byte random salts).
    - Constant-time password verification via hmac.compare_digest.
    - Input sanitization and credential validation.
    - User registration and authentication workflows.
    """

    PBKDF2_ITERATIONS = 100_000
    SALT_BYTES = 16

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    @staticmethod
    def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
        """
        Generates a PBKDF2-HMAC-SHA256 hash from a plaintext password.
        Returns (hash_hex, salt_hex).
        """
        if salt is None:
            salt = secrets.token_bytes(AuthService.SALT_BYTES)
        
        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            AuthService.PBKDF2_ITERATIONS,
        )
        return derived_key.hex(), salt.hex()

    @staticmethod
    def verify_password(password: str, salt_hex: str, stored_hash_hex: str) -> bool:
        """
        Verifies a plaintext password against a stored hash and salt in constant time.
        """
        try:
            salt = bytes.fromhex(salt_hex)
            computed_hash_hex, _ = AuthService.hash_password(password, salt=salt)
            return hmac.compare_digest(computed_hash_hex, stored_hash_hex)
        except Exception:
            return False

    @staticmethod
    def validate_username(username: str) -> tuple[bool, str or None]:
        """Validates format and constraints of a pilot callsign."""
        clean = (username or "").strip()
        if len(clean) < 3:
            return False, "Callsign must be at least 3 characters long."
        if len(clean) > 20:
            return False, "Callsign cannot exceed 20 characters."
        if not re.match(r"^[A-Za-z0-9_\-\. ]+$", clean):
            return False, "Callsign can only contain letters, numbers, dashes, underscores, and spaces."
        return True, None

    @staticmethod
    def validate_password(password: str) -> tuple[bool, str or None]:
        """Validates format and constraints of a security passcode."""
        if not password or len(password) < 4:
            return False, "Passcode must be at least 4 characters long."
        if len(password) > 64:
            return False, "Passcode cannot exceed 64 characters."
        return True, None

    def register_user(self, username: str, password: str) -> tuple[dict or None, str or None]:
        """
        Registers a new pilot profile with salted PBKDF2 hash.
        Returns (user_dict, None) on success, or (None, error_message) on failure.
        """
        valid_u, u_err = self.validate_username(username)
        if not valid_u:
            return None, u_err

        valid_p, p_err = self.validate_password(password)
        if not valid_p:
            return None, p_err

        clean_username = username.strip()
        pwd_hash, salt = self.hash_password(password)

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password_hash, salt, last_login) VALUES (?, ?, ?, ?)",
                    (clean_username, pwd_hash, salt, datetime.datetime.utcnow().isoformat()),
                )
                user_id = cursor.lastrowid

                # Auto-initialize level 1 unlocked in campaign progression
                cursor.execute(
                    """
                    INSERT INTO campaign_progress (user_id, level, stars, high_score, completed, unlocked)
                    VALUES (?, 1, 0, 0, 0, 1)
                    ON CONFLICT(user_id, level) DO NOTHING;
                    """,
                    (user_id,),
                )

                return {
                    "id": user_id,
                    "username": clean_username,
                    "is_guest": False,
                }, None
        except Exception as e:
            err_str = str(e).lower()
            if "unique" in err_str or "already exists" in err_str:
                return None, f"Pilot callsign '{clean_username}' is already registered."
            return None, f"Database error during registration: {e}"

    def authenticate_user(self, username: str, password: str) -> tuple[dict or None, str or None]:
        """
        Authenticates pilot credentials.
        Returns (user_dict, None) on success, or (None, error_message) on failure.
        """
        clean_username = (username or "").strip()
        if not clean_username or not password:
            return None, "Please provide both callsign and security passcode."

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password_hash, salt, created_at FROM users WHERE username = ?",
                (clean_username,),
            )
            row = cursor.fetchone()

            if not row:
                return None, "Pilot callsign not found."

            user_id = row["id"]
            db_username = row["username"]
            stored_hash = row["password_hash"]
            salt = row["salt"]

            if not self.verify_password(password, salt, stored_hash):
                return None, "Invalid security passcode."

            # Update last_login timestamp
            now_iso = datetime.datetime.utcnow().isoformat()
            cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_iso, user_id))

            return {
                "id": user_id,
                "username": db_username,
                "is_guest": False,
                "created_at": row["created_at"],
                "last_login": now_iso,
            }, None

    def get_user_by_id(self, user_id: int) -> dict or None:
        """Retrieves public user profile by ID."""
        if not user_id:
            return None
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, created_at, last_login FROM users WHERE id = ?",
                (user_id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "is_guest": False,
                    "created_at": row["created_at"],
                    "last_login": row["last_login"],
                }
            return None

    def get_user_by_username(self, username: str) -> dict or None:
        """Retrieves public user profile by username (case-insensitive)."""
        clean_username = (username or "").strip()
        if not clean_username:
            return None
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, created_at, last_login FROM users WHERE username = ?",
                (clean_username,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "username": row["username"],
                    "is_guest": False,
                    "created_at": row["created_at"],
                    "last_login": row["last_login"],
                }
            return None
