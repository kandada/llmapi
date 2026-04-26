import os
from pathlib import Path
from typing import Optional

def _get_default_db_path() -> str:
    home = Path.home()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", home))
    else:
        base = home
    data_dir = base / ".llmapi"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "one-api.db")

class Config:
    # Server
    PORT: int = int(os.getenv("PORT", "3000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "change-this-in-production")
    THEME: str = os.getenv("THEME", "default")

    # Database
    SQL_DSN: Optional[str] = os.getenv("SQL_DSN")
    LOG_SQL_DSN: Optional[str] = os.getenv("LOG_SQL_DSN")
    SQLite_Path: str = os.getenv("SQLITE_PATH") or _get_default_db_path()
    SQLITE_BUSY_TIMEOUT: int = 3000
    SQL_MAX_IDLE_CONNS: int = 100
    SQL_MAX_OPEN_CONNS: int = 1000
    SQL_MAX_LIFETIME: int = 60

    # User & Quota
    QuotaForNewUser: int = int(os.getenv("QUOTA_FOR_NEW_USER", "0"))
    QuotaForInviter: int = int(os.getenv("QUOTA_FOR_INVITER", "0"))
    QuotaForInvitee: int = int(os.getenv("QUOTA_FOR_INVITEE", "0"))
    QuotaRemindThreshold: int = int(os.getenv("QUOTA_REMIND_THRESHOLD", "1000000"))
    PreConsumedQuota: int = int(os.getenv("PRE_CONSUMED_QUOTA", "100000"))

    # Sync Frequency (seconds)
    SyncFrequency: int = int(os.getenv("SYNC_FREQUENCY", "10"))

    # Channel Test Frequency (seconds)
    ChannelTestFrequency: int = int(os.getenv("CHANNEL_TEST_FREQUENCY", "0"))

    # Retry
    RetryTimes: int = int(os.getenv("RETRY_TIMES", "3"))

    # Cache
    MemoryCacheEnabled: bool = True

    # Batch Update
    BatchUpdateEnabled: bool = os.getenv("BATCH_UPDATE_ENABLED", "false").lower() == "true"
    BatchUpdateInterval: int = int(os.getenv("BATCH_UPDATE_INTERVAL", "60"))

    # Metrics
    EnableMetric: bool = os.getenv("ENABLE_METRIC", "false").lower() == "true"
    ChannelDisableThreshold: float = 0.25

    # Display
    DisplayInCurrencyEnabled: bool = False
    DisplayTokenStatEnabled: bool = False

    # Items per page
    ItemsPerPage: int = 25

    # Max recent items
    MaxRecentItems: int = 100

    # Quota per unit (for currency display)
    QuotaPerUnit: float = 1.0

    # Initial root token
    InitialRootToken: Optional[str] = os.getenv("INITIAL_ROOT_TOKEN")
    InitialRootAccessToken: Optional[str] = os.getenv("INITIAL_ROOT_ACCESS_TOKEN")

    # Frontend base URL
    FrontendBaseUrl: Optional[str] = os.getenv("FRONTEND_BASE_URL")

    # Server address (for email links)
    ServerAddress: str = os.getenv("SERVER_ADDRESS", "")

    # System name & logo
    SystemName: str = os.getenv("SYSTEM_NAME", "LLM API Gateway")
    Logo: str = os.getenv("LOGO", "")
    Footer: str = os.getenv("FOOTER", "")

    # Notice & About
    Notice: str = ""
    About: str = ""
    HomePageContent: str = ""

    # Top-up link & Chat link
    TopUpLink: str = ""
    ChatLink: str = ""

    # OAuth - GitHub
    GitHubClientId: str = os.getenv("GITHUB_CLIENT_ID", "")
    GitHubClientSecret: str = os.getenv("GITHUB_CLIENT_SECRET", "")

    # OAuth - Lark
    LarkClientId: str = os.getenv("LARK_CLIENT_ID", "")
    LarkClientSecret: str = os.getenv("LARK_CLIENT_SECRET", "")

    # OAuth - OIDC
    OidcClientId: str = os.getenv("OIDC_CLIENT_ID", "")
    OidcClientSecret: str = os.getenv("OIDC_CLIENT_SECRET", "")
    OidcWellKnown: str = os.getenv("OIDC_WELL_KNOWN", "")
    OidcAuthorizationEndpoint: str = ""
    OidcTokenEndpoint: str = ""
    OidcUserinfoEndpoint: str = ""

    # WeChat
    WeChatServerAddress: str = os.getenv("WECHAT_SERVER_ADDRESS", "")
    WeChatServerToken: str = os.getenv("WECHAT_SERVER_TOKEN", "")
    WeChatAccountQRCodeImageURL: str = ""

    # SMTP
    SMTPServer: str = os.getenv("SMTP_SERVER", "")
    SMTPPort: int = int(os.getenv("SMTP_PORT", "587"))
    SMTPAccount: str = os.getenv("SMTP_ACCOUNT", "")
    SMTPToken: str = os.getenv("SMTP_TOKEN", "")
    SMTPFrom: str = ""

    # Message Pusher
    MessagePusherAddress: str = os.getenv("MESSAGE_PUSHER_ADDRESS", "")
    MessagePusherToken: str = os.getenv("MESSAGE_PUSHER_TOKEN", "")

    # Turnstile
    TurnstileSiteKey: str = os.getenv("TURNSTILE_SITE_KEY", "")
    TurnstileSecretKey: str = os.getenv("TURNSTILE_SECRET_KEY", "")

    # Feature flags
    PasswordLoginEnabled: bool = True
    PasswordRegisterEnabled: bool = True
    RegisterEnabled: bool = True
    EmailVerificationEnabled: bool = False
    GitHubOAuthEnabled: bool = False
    OidcEnabled: bool = False
    WeChatAuthEnabled: bool = False
    TurnstileCheckEnabled: bool = False
    EmailDomainRestrictionEnabled: bool = False
    EmailDomainWhitelist: list = []
    AutomaticDisableChannelEnabled: bool = True
    AutomaticEnableChannelEnabled: bool = True
    ApproximateTokenEnabled: bool = True
    LogConsumeEnabled: bool = True

    # External App Integration
    # Comma-separated list of API tokens for external apps (aacode, fastclaw, etc.)
    SystemApiTokens: list = [t.strip() for t in os.getenv("SYSTEM_API_TOKENS", "").split(",") if t.strip()]
    # Allow external apps to auto-create users
    ExternalAppAutoCreateUser: bool = os.getenv("EXTERNAL_APP_AUTO_CREATE_USER", "true").lower() == "true"

    # Valid themes
    ValidThemes: dict = {
        "default": True,
        "air": True,
        "berry": True,
    }

    # Root user email (for notifications)
    RootUserEmail: str = ""


config = Config()
