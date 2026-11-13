"""
AstroGuard application settings.

This module integrates the secure configuration engine with the
existing FastAPI application.

Compatibility:
- APP_NAME remains supported.
- APP_ENV remains supported.
- API_V1_PREFIX remains supported.
- CORS_ORIGINS remains supported.
- CORS_ALLOWED_ORIGINS is the preferred replacement.

Security:
- .env is loaded without overriding process environment variables.
- Secret-bearing values are not included in repr().
- safe_summary() returns metadata only.
- Production configuration is validated before application startup.
"""

from __future__ import annotations

import os
import re

from dataclasses import dataclass, field
from typing import Mapping, Optional

from astroguard_api.secure_config import (
    ConfigurationError,
    SecureSettings,
    build_settings,
    load_environment_file,
    validate_configuration,
)


_API_PREFIX_PATTERN = re.compile(
    r"^/(?:[A-Za-z0-9._~-]+(?:/[A-Za-z0-9._~-]+)*)?$"
)


def parse_origins(raw: str) -> list[str]:
    """
    Backward-compatible parser for the legacy CORS_ORIGINS variable.

    The secure configuration module performs the actual URL validation.
    """
    return [
        item.strip()
        for item in raw.split(",")
        if item.strip()
    ]


def _validate_api_prefix(value: str) -> str:
    prefix = value.strip()

    if not prefix:
        raise ConfigurationError(
            "API_V1_PREFIX must not be empty."
        )

    if not _API_PREFIX_PATTERN.fullmatch(prefix):
        raise ConfigurationError(
            "API_V1_PREFIX must be a valid absolute URL path prefix."
        )

    if prefix != "/" and prefix.endswith("/"):
        raise ConfigurationError(
            "API_V1_PREFIX must not end with a slash."
        )

    return prefix


def _validate_app_name(value: str) -> str:
    app_name = value.strip()

    if not app_name:
        raise ConfigurationError(
            "APP_NAME must not be empty."
        )

    if len(app_name) > 100:
        raise ConfigurationError(
            "APP_NAME exceeds the maximum permitted length."
        )

    return app_name


@dataclass(frozen=True)
class Settings:
    """
    Application-facing configuration.

    The original application-facing fields are retained so that
    existing imports and route definitions remain compatible.
    """

    app_name: str
    app_env: str
    api_v1_prefix: str
    cors_origins: list[str]

    secure: SecureSettings = field(
        repr=False,
        compare=False,
    )

    configuration_warnings: tuple[str, ...] = field(
        default_factory=tuple,
        repr=False,
        compare=False,
    )

    @property
    def debug(self) -> bool:
        return self.secure.app_debug

    @property
    def host(self) -> str:
        return self.secure.app_host

    @property
    def port(self) -> int:
        return self.secure.app_port

    @property
    def log_level(self) -> str:
        return self.secure.app_log_level

    @property
    def is_production(self) -> bool:
        return self.secure.is_production

    def safe_summary(self) -> dict[str, object]:
        """
        Return safe application configuration metadata.

        No API keys, passwords, database URLs, JWT secrets,
        tokens, or cloud credentials are returned.
        """
        secure_summary = self.secure.safe_summary()

        return {
            "app_name": self.app_name,
            "app_env": self.app_env,
            "api_v1_prefix": self.api_v1_prefix,
            "cors_origin_count": len(self.cors_origins),
            "debug": self.debug,
            "host": self.host,
            "port": self.port,
            "log_level": self.log_level,
            "production": self.is_production,
            "secret_configuration": {
                "nasa_api_configured":
                    secure_summary["nasa_api_configured"],
                "database_configured":
                    secure_summary["database_configured"],
                "redis_configured":
                    secure_summary["redis_configured"],
                "jwt_secret_configured":
                    secure_summary["jwt_secret_configured"],
            },
        }


def build_application_settings(
    environ: Optional[Mapping[str, str]] = None,
    *,
    load_dotenv: bool = False,
) -> Settings:
    """
    Build application settings with legacy compatibility.

    Precedence:
      1. Explicit process environment.
      2. .env values when load_dotenv=True and process values absent.
      3. Safe application defaults.

    CORS compatibility:
      CORS_ALLOWED_ORIGINS takes precedence.
      CORS_ORIGINS is used when the preferred variable is absent
      or empty.
    """

    if environ is None:
        if load_dotenv:
            load_environment_file()

        source = dict(os.environ)
    else:
        source = dict(environ)

    preferred_cors = source.get(
        "CORS_ALLOWED_ORIGINS",
        "",
    ).strip()

    legacy_cors = source.get(
        "CORS_ORIGINS",
        "",
    ).strip()

    if not preferred_cors and legacy_cors:
        source["CORS_ALLOWED_ORIGINS"] = legacy_cors

    secure = build_settings(environ=source)

    app_name = _validate_app_name(
        source.get("APP_NAME", "AstroGuard API")
    )

    api_prefix = _validate_api_prefix(
        source.get("API_V1_PREFIX", "/api/v1")
    )

    warnings = validate_configuration(secure)

    return Settings(
        app_name=app_name,
        app_env=secure.app_env,
        api_v1_prefix=api_prefix,
        cors_origins=list(secure.cors_allowed_origins),
        secure=secure,
        configuration_warnings=warnings,
    )


# Load .env once when the application configuration module initializes.
#
# Existing process environment values retain precedence.
# This operation never prints the contents of the environment file.
load_environment_file()

# Preserve the original public import:
#
# from astroguard_api.settings import settings
#
settings = build_application_settings(
    environ=os.environ,
    load_dotenv=False,
)
