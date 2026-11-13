from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from astroguard_api import main
from astroguard_api.settings import (
    Settings,
    build_application_settings,
)


class TestRuntimeSettings:

    def test_default_application_settings(self):
        settings = build_application_settings(
            environ={}
        )

        assert settings.app_name == "AstroGuard API"
        assert settings.app_env == "development"
        assert settings.api_v1_prefix == "/api/v1"
        assert settings.cors_origins == [
            "http://localhost:3000"
        ]

    def test_legacy_cors_variable_remains_supported(self):
        settings = build_application_settings(
            environ={
                "CORS_ORIGINS": (
                    "https://frontend.example.com"
                )
            }
        )

        assert settings.cors_origins == [
            "https://frontend.example.com"
        ]

    def test_preferred_cors_variable_has_precedence(self):
        settings = build_application_settings(
            environ={
                "CORS_ALLOWED_ORIGINS": (
                    "https://new.example.com"
                ),
                "CORS_ORIGINS": (
                    "https://old.example.com"
                ),
            }
        )

        assert settings.cors_origins == [
            "https://new.example.com"
        ]

    def test_empty_preferred_cors_uses_legacy_variable(self):
        settings = build_application_settings(
            environ={
                "CORS_ALLOWED_ORIGINS": "",
                "CORS_ORIGINS": (
                    "https://legacy.example.com"
                ),
            }
        )

        assert settings.cors_origins == [
            "https://legacy.example.com"
        ]

    def test_app_name_is_preserved(self):
        settings = build_application_settings(
            environ={
                "APP_NAME": "AstroGuard Test API"
            }
        )

        assert settings.app_name == "AstroGuard Test API"

    def test_api_prefix_is_preserved(self):
        settings = build_application_settings(
            environ={
                "API_V1_PREFIX": "/custom/v1"
            }
        )

        assert settings.api_v1_prefix == "/custom/v1"

    def test_invalid_api_prefix_rejected(self):
        from astroguard_api.secure_config import ConfigurationError

        invalid_prefixes = [
            "",
            "api/v1",
            "/api/v1/",
            "/api//v1",
            "/api/v1?token=x",
            "/api/v1#fragment",
        ]

        for prefix in invalid_prefixes:
            try:
                build_application_settings(
                    environ={
                        "API_V1_PREFIX": prefix
                    }
                )
            except ConfigurationError:
                continue

            raise AssertionError(
                f"Invalid API prefix was accepted: {prefix!r}"
            )

    def test_empty_app_name_rejected(self):
        from astroguard_api.secure_config import ConfigurationError

        try:
            build_application_settings(
                environ={"APP_NAME": " "}
            )
        except ConfigurationError:
            return

        raise AssertionError("Empty APP_NAME was accepted.")

    def test_long_app_name_rejected(self):
        from astroguard_api.secure_config import ConfigurationError

        try:
            build_application_settings(
                environ={"APP_NAME": "A" * 101}
            )
        except ConfigurationError:
            return

        raise AssertionError("Overlong APP_NAME was accepted.")

    def test_safe_summary_contains_no_secrets(self):
        secret = "runtime-private-secret-marker"

        settings = build_application_settings(
            environ={
                "APP_ENV": "test",
                "NASA_API_KEY": secret,
                "JWT_SECRET_KEY": secret,
                "DATABASE_URL": (
                    "postgresql://user:" + secret + "@localhost/db"
                ),
                "REDIS_URL": (
                    "redis://:" + secret + "@localhost:6379/0"
                ),
                "AWS_SECRET_ACCESS_KEY": secret,
            }
        )

        output = json.dumps(settings.safe_summary())

        assert secret not in output
        assert "postgresql://" not in output
        assert "redis://" not in output

    def test_settings_repr_does_not_expose_secret(self):
        secret = "runtime-repr-private-secret"

        settings = build_application_settings(
            environ={
                "JWT_SECRET_KEY": secret,
                "NASA_API_KEY": secret,
            }
        )

        assert secret not in repr(settings)

    def test_production_debug_is_rejected(self):
        from astroguard_api.secure_config import ConfigurationError

        try:
            build_application_settings(
                environ={
                    "APP_ENV": "production",
                    "APP_DEBUG": "true",
                    "JWT_SECRET_KEY": "x" * 48,
                }
            )
        except ConfigurationError:
            return

        raise AssertionError(
            "Production debug mode was accepted."
        )

    def test_production_requires_jwt_secret(self):
        from astroguard_api.secure_config import ConfigurationError

        try:
            build_application_settings(
                environ={
                    "APP_ENV": "production",
                    "APP_DEBUG": "false",
                }
            )
        except ConfigurationError:
            return

        raise AssertionError(
            "Production without JWT secret was accepted."
        )


class TestRuntimeEndpoint:

    def test_root_endpoint_contract(self):
        with TestClient(main.app) as client:
            response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {
            "name": "AstroGuard",
            "service": "astroguard-api",
            "status": "online",
            "environment": main.settings.app_env,
        }

    def test_health_endpoint_contract(self):
        with TestClient(main.app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "astroguard-api",
        }

    def test_ready_endpoint_contract(self):
        with TestClient(main.app) as client:
            response = client.get("/ready")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ready",
            "database": "available",
            "native_engine": "phase_1_available",
        }

    def test_system_info_endpoint_contract(self):
        path = (
            main.settings.api_v1_prefix
            + "/system/info"
        )

        with TestClient(main.app) as client:
            response = client.get(path)

        assert response.status_code == 200
        assert response.json() == {
            "name": "AstroGuard",
            "version": "0.1.0",
            "backend_language": "Python",
            "native_language": "C++20",
            "mode": "historical_telemetry_replay",
            "safety_classification": "research_prototype_only",
        }

    def test_existing_routes_remain_registered(self):
        paths = {
            route.path
            for route in main.app.routes
            if hasattr(route, "path")
        }

        assert "/" in paths
        assert "/health" in paths
        assert "/ready" in paths

        assert (
            main.settings.api_v1_prefix + "/system/info"
        ) in paths

    def test_api_responses_do_not_expose_known_secret_markers(
        self,
        monkeypatch,
    ):
        from astroguard_api.settings import build_application_settings

        secret = "never-expose-this-runtime-marker"

        safe_settings = build_application_settings(
            environ={
                "APP_ENV": "test",
                "NASA_API_KEY": secret,
                "JWT_SECRET_KEY": secret,
                "DATABASE_URL": (
                    "postgresql://user:" + secret + "@localhost/db"
                ),
                "REDIS_URL": (
                    "redis://:" + secret + "@localhost:6379/0"
                ),
            }
        )

        monkeypatch.setattr(
            main,
            "settings",
            safe_settings,
        )

        with TestClient(main.app) as client:
            responses = [
                client.get("/"),
                client.get("/health"),
                client.get("/ready"),
                client.get(
                    safe_settings.api_v1_prefix
                    + "/system/info"
                ),
            ]

        for response in responses:
            assert response.status_code == 200
            assert secret not in response.text
            assert "postgresql://" not in response.text
            assert "redis://" not in response.text


class TestStartupLogging:

    def test_startup_log_uses_safe_summary(
        self,
        monkeypatch,
        caplog,
    ):
        from astroguard_api.settings import build_application_settings

        secret = "startup-log-private-marker"

        safe_settings = build_application_settings(
            environ={
                "APP_ENV": "test",
                "NASA_API_KEY": secret,
                "JWT_SECRET_KEY": secret,
            }
        )

        monkeypatch.setattr(
            main,
            "settings",
            safe_settings,
        )

        with caplog.at_level(
            logging.INFO,
            logger="astroguard.application",
        ):
            main._log_startup_configuration()

        output = caplog.text

        assert "AstroGuard application startup configuration" in output
        assert secret not in output
        assert "jwt_secret_configured" in output

    def test_startup_warning_does_not_contain_credentials(
        self,
        monkeypatch,
        caplog,
    ):
        from astroguard_api.settings import build_application_settings

        safe_settings = build_application_settings(
            environ={
                "APP_ENV": "development",
                "APP_DEBUG": "true",
                "JWT_SECRET_KEY": "private-warning-marker",
            }
        )

        monkeypatch.setattr(
            main,
            "settings",
            safe_settings,
        )

        with caplog.at_level(
            logging.WARNING,
            logger="astroguard.application",
        ):
            main._log_startup_configuration()

        assert "Debug mode" in caplog.text
        assert "private-warning-marker" not in caplog.text
