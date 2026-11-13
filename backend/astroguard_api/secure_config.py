"""
AstroGuard secure configuration module.

Security properties:
- Standard-library-only implementation.
- Does not print environment values.
- Existing process environment takes precedence over .env.
- Does not overwrite existing environment variables by default.
- Validates production secret requirements.
- Provides safe redaction for logs.
- Does not expose secrets through repr().
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Tuple
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"

_SECRET_KEY_MARKERS = (
    "KEY",
    "TOKEN",
    "PASSWORD",
    "SECRET",
    "DSN",
    "CREDENTIAL",
    "PRIVATE",
)

_SECRET_ASSIGNMENT = re.compile(
    r"""(?i)\b([A-Z0-9_]*(?:API[_-]?KEY|ACCESS[_-]?TOKEN|REFRESH[_-]?TOKEN|PASSWORD|SECRET(?:[_-]?[A-Z0-9_]*)?|AUTHORIZATION|DATABASE[_-]?URL|REDIS[_-]?URL|DSN))\b(\s*[:=]\s*)("[^"]*"|'[^']*'|[^\s,;]+)"""
)

_BEARER_PATTERN = re.compile(
    r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"
)

_URL_CREDENTIAL_PATTERN = re.compile(
    r"(://[^:/@\s]+:)[^@\s]+(@)"
)


class ConfigurationError(ValueError):
    """Raised when AstroGuard configuration is invalid."""


def _is_secret_name(name: str) -> bool:
    normalized = name.upper()
    return any(marker in normalized for marker in _SECRET_KEY_MARKERS)


def _strip_inline_comment(value: str) -> str:
    """
    Remove unquoted inline comments.

    A # inside quoted strings is preserved.
    """
    quote = None
    escaped = False

    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue

        if character == "\\" and quote == '"':
            escaped = True
            continue

        if quote:
            if character == quote:
                quote = None
            continue

        if character in ("'", '"'):
            quote = character
            continue

        if character == "#" and (
            index == 0 or value[index - 1].isspace()
        ):
            return value[:index].rstrip()

    return value.rstrip()


def _decode_env_value(raw_value: str) -> str:
    value = _strip_inline_comment(raw_value.strip())

    if len(value) >= 2:
        if value[0] == value[-1] and value[0] in ("'", '"'):
            quote = value[0]
            value = value[1:-1]

            if quote == '"':
                value = (
                    value.replace("\\n", "\n")
                    .replace("\\r", "\r")
                    .replace('\\"', '"')
                    .replace("\\\\", "\\")
                )

    return value


def parse_env_file(path: Path) -> dict[str, str]:
    """
    Parse a dotenv-style file without displaying its contents.

    Supported:
    - KEY=value
    - export KEY=value
    - Single- and double-quoted values
    - Blank lines and comments
    - UTF-8 BOM

    Variable interpolation is intentionally not supported.
    """
    path = Path(path)

    if not path.exists():
        return {}

    if not path.is_file():
        raise ConfigurationError("Environment path is not a file.")

    parsed: dict[str, str] = {}

    try:
        content = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ConfigurationError(
            "Unable to read environment configuration file."
        ) from exc

    for line_number, original_line in enumerate(
        content.splitlines(), start=1
    ):
        line = original_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            raise ConfigurationError(
                f"Malformed environment entry at line {line_number}."
            )

        key, raw_value = line.split("=", 1)
        key = key.strip()

        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ConfigurationError(
                f"Invalid environment variable name at line {line_number}."
            )

        if key in parsed:
            raise ConfigurationError(
                f"Duplicate environment variable at line {line_number}."
            )

        parsed[key] = _decode_env_value(raw_value)

    return parsed


def load_environment_file(
    path: Optional[Path] = None,
    *,
    override: bool = False,
    environ: Optional[dict[str, str]] = None,
) -> int:
    """
    Load .env values into the process environment.

    Existing environment variables win unless override=True.
    Returns the number of variables loaded, never their values.
    """
    target = os.environ if environ is None else environ
    env_path = DEFAULT_ENV_FILE if path is None else Path(path)
    parsed = parse_env_file(env_path)

    loaded = 0

    for key, value in parsed.items():
        if override or key not in target:
            target[key] = value
            loaded += 1

    return loaded


def _get(
    source: Mapping[str, str],
    name: str,
    default: str = "",
) -> str:
    value = source.get(name, default)
    return str(value).strip()


def _parse_bool(value: str, name: str) -> bool:
    normalized = value.strip().lower()

    if normalized in ("1", "true", "yes", "on"):
        return True

    if normalized in ("0", "false", "no", "off", ""):
        return False

    raise ConfigurationError(
        f"{name} must be a valid boolean."
    )


def _parse_int(
    value: str,
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if not value:
        return default

    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"{name} must be an integer."
        ) from exc

    if not minimum <= parsed <= maximum:
        raise ConfigurationError(
            f"{name} is outside its permitted range."
        )

    return parsed


def _validate_http_url(value: str, name: str) -> str:
    if not value:
        return ""

    try:
        parts = urlsplit(value)
    except ValueError as exc:
        raise ConfigurationError(
            f"{name} is not a valid URL."
        ) from exc

    if parts.scheme not in ("http", "https"):
        raise ConfigurationError(
            f"{name} must use HTTP or HTTPS."
        )

    if not parts.netloc or not parts.hostname:
        raise ConfigurationError(
            f"{name} must contain a hostname."
        )

    if parts.username or parts.password:
        raise ConfigurationError(
            f"{name} must not embed credentials."
        )

    return value.rstrip("/")


def _parse_origins(value: str) -> Tuple[str, ...]:
    if not value:
        return ("http://localhost:3000",)

    origins = []

    for item in value.split(","):
        origin = item.strip()

        if not origin:
            continue

        validated = _validate_http_url(
            origin,
            "CORS_ALLOWED_ORIGINS",
        )

        parts = urlsplit(validated)

        if parts.path or parts.query or parts.fragment:
            raise ConfigurationError(
                "CORS origins must not contain paths or query strings."
            )

        if validated not in origins:
            origins.append(validated)

    return tuple(origins)


@dataclass(frozen=True)
class SecureSettings:
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_log_level: str = "INFO"

    nasa_api_key: str = field(default="", repr=False)
    nasa_api_base_url: str = "https://api.nasa.gov"

    database_url: str = field(default="", repr=False)
    redis_url: str = field(default="", repr=False)

    jwt_secret_key: str = field(default="", repr=False)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    cors_allowed_origins: Tuple[str, ...] = (
        "http://localhost:3000",
    )

    frontend_origin: str = "http://localhost:3000"
    public_api_base_url: str = "http://127.0.0.1:8000"

    space_track_api_username: str = field(default="", repr=False)
    space_track_api_password: str = field(default="", repr=False)

    sentry_dsn: str = field(default="", repr=False)
    aws_access_key_id: str = field(default="", repr=False)
    aws_secret_access_key: str = field(default="", repr=False)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def safe_summary(self) -> dict[str, object]:
        """
        Return non-secret configuration metadata only.
        """
        return {
            "app_env": self.app_env,
            "app_debug": self.app_debug,
            "app_host": self.app_host,
            "app_port": self.app_port,
            "app_log_level": self.app_log_level,
            "nasa_api_configured": bool(self.nasa_api_key),
            "database_configured": bool(self.database_url),
            "redis_configured": bool(self.redis_url),
            "jwt_secret_configured": bool(self.jwt_secret_key),
            "jwt_algorithm": self.jwt_algorithm,
            "cors_origin_count": len(self.cors_allowed_origins),
            "production": self.is_production,
        }


def build_settings(
    environ: Optional[Mapping[str, str]] = None,
    *,
    load_dotenv: bool = False,
    env_file: Optional[Path] = None,
) -> SecureSettings:
    """
    Build validated immutable application settings.

    For unit tests, pass environ explicitly.
    For application startup, call load_dotenv=True.
    """
    if environ is None:
        if load_dotenv:
            load_environment_file(env_file)
        source: Mapping[str, str] = os.environ
    else:
        source = environ

    app_env = _get(source, "APP_ENV", "development").lower()

    if app_env not in ("development", "test", "staging", "production"):
        raise ConfigurationError(
            "APP_ENV must be development, test, staging, or production."
        )

    app_debug = _parse_bool(
        _get(source, "APP_DEBUG", "false"),
        "APP_DEBUG",
    )

    if app_env == "production" and app_debug:
        raise ConfigurationError(
            "APP_DEBUG must be disabled in production."
        )

    app_port = _parse_int(
        _get(source, "APP_PORT", "8000"),
        "APP_PORT",
        8000,
        1,
        65535,
    )

    token_expiry = _parse_int(
        _get(source, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"),
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        30,
        1,
        10080,
    )

    log_level = _get(source, "APP_LOG_LEVEL", "INFO").upper()

    if log_level not in (
        "CRITICAL",
        "ERROR",
        "WARNING",
        "INFO",
        "DEBUG",
    ):
        raise ConfigurationError(
            "APP_LOG_LEVEL is not supported."
        )

    jwt_algorithm = _get(source, "JWT_ALGORITHM", "HS256")

    if jwt_algorithm not in ("HS256", "HS384", "HS512"):
        raise ConfigurationError(
            "JWT_ALGORITHM is not an approved HMAC algorithm."
        )

    jwt_secret = _get(source, "JWT_SECRET_KEY")

    if app_env == "production":
        if len(jwt_secret) < 32:
            raise ConfigurationError(
                "Production requires JWT_SECRET_KEY with at least 32 characters."
            )

    cors_origins = _parse_origins(
        _get(source, "CORS_ALLOWED_ORIGINS")
    )

    frontend_origin = _validate_http_url(
        _get(source, "FRONTEND_ORIGIN", "http://localhost:3000"),
        "FRONTEND_ORIGIN",
    )

    public_api_base_url = _validate_http_url(
        _get(
            source,
            "PUBLIC_API_BASE_URL",
            "http://127.0.0.1:8000",
        ),
        "PUBLIC_API_BASE_URL",
    )

    nasa_base_url = _validate_http_url(
        _get(
            source,
            "NASA_API_BASE_URL",
            "https://api.nasa.gov",
        ),
        "NASA_API_BASE_URL",
    )

    database_url = _get(source, "DATABASE_URL")
    redis_url = _get(source, "REDIS_URL")

    return SecureSettings(
        app_env=app_env,
        app_debug=app_debug,
        app_host=_get(source, "APP_HOST", "127.0.0.1"),
        app_port=app_port,
        app_log_level=log_level,
        nasa_api_key=_get(source, "NASA_API_KEY"),
        nasa_api_base_url=nasa_base_url,
        database_url=database_url,
        redis_url=redis_url,
        jwt_secret_key=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        jwt_access_token_expire_minutes=token_expiry,
        cors_allowed_origins=cors_origins,
        frontend_origin=frontend_origin,
        public_api_base_url=public_api_base_url,
        space_track_api_username=_get(
            source,
            "SPACE_TRACK_API_USERNAME",
        ),
        space_track_api_password=_get(
            source,
            "SPACE_TRACK_API_PASSWORD",
        ),
        sentry_dsn=_get(source, "SENTRY_DSN"),
        aws_access_key_id=_get(source, "AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=_get(
            source,
            "AWS_SECRET_ACCESS_KEY",
        ),
    )


def redact_secrets(message: object) -> str:
    """
    Redact common secret-bearing patterns before logging.

    This is a defensive helper, not a replacement for avoiding
    logging secret-bearing objects in the first place.
    """
    text = str(message)

    text = _BEARER_PATTERN.sub("Bearer [REDACTED]", text)
    text = _URL_CREDENTIAL_PATTERN.sub(
        r"\1[REDACTED]\2",
        text,
    )

    text = _SECRET_ASSIGNMENT.sub(
        lambda match: (
            match.group(1)
            + match.group(2)
            + "[REDACTED]"
        ),
        text,
    )

    return text


def validate_configuration(
    settings: SecureSettings,
) -> Tuple[str, ...]:
    """
    Return non-secret validation findings.

    Empty tuple means no additional configuration warnings.
    """
    warnings = []

    if settings.app_env == "development" and settings.app_debug:
        warnings.append(
            "Debug mode is enabled; disable it outside local development."
        )

    if settings.app_env == "production":
        if not settings.database_url:
            warnings.append(
                "Production database URL is not configured."
            )

        if settings.cors_allowed_origins == (
            "http://localhost:3000",
        ):
            warnings.append(
                "Production CORS still uses the local development origin."
            )

        if settings.public_api_base_url.startswith("http://"):
            warnings.append(
                "Production public API URL is not using HTTPS."
            )

    return tuple(warnings)
