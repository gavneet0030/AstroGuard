from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from astroguard_api.secure_config import (
    ConfigurationError,
    SecureSettings,
    build_settings,
    load_environment_file,
    parse_env_file,
    redact_secrets,
    validate_configuration,
)


class EnvParserTests(unittest.TestCase):

    def test_parses_basic_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "APP_ENV=test\nAPP_PORT=9000\n",
                encoding="utf-8",
            )

            values = parse_env_file(path)

            self.assertEqual(values["APP_ENV"], "test")
            self.assertEqual(values["APP_PORT"], "9000")

    def test_parses_export_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "export APP_ENV=staging\n",
                encoding="utf-8",
            )

            self.assertEqual(
                parse_env_file(path)["APP_ENV"],
                "staging",
            )

    def test_preserves_hash_inside_quotes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                'NASA_API_KEY="abc#123"\n',
                encoding="utf-8",
            )

            self.assertEqual(
                parse_env_file(path)["NASA_API_KEY"],
                "abc#123",
            )

    def test_removes_unquoted_inline_comment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "APP_ENV=test # local test\n",
                encoding="utf-8",
            )

            self.assertEqual(
                parse_env_file(path)["APP_ENV"],
                "test",
            )

    def test_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "APP_ENV=test\nAPP_ENV=production\n",
                encoding="utf-8",
            )

            with self.assertRaises(ConfigurationError):
                parse_env_file(path)

    def test_rejects_malformed_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "THIS_LINE_HAS_NO_EQUALS_SIGN\n",
                encoding="utf-8",
            )

            with self.assertRaises(ConfigurationError):
                parse_env_file(path)

    def test_missing_file_returns_empty_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.env"
            self.assertEqual(parse_env_file(path), {})


class EnvironmentLoadingTests(unittest.TestCase):

    def test_existing_environment_wins_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "APP_ENV=production\n",
                encoding="utf-8",
            )

            target = {"APP_ENV": "test"}

            loaded = load_environment_file(
                path,
                environ=target,
            )

            self.assertEqual(target["APP_ENV"], "test")
            self.assertEqual(loaded, 0)

    def test_override_can_be_explicitly_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "APP_ENV=production\n",
                encoding="utf-8",
            )

            target = {"APP_ENV": "test"}

            load_environment_file(
                path,
                override=True,
                environ=target,
            )

            self.assertEqual(target["APP_ENV"], "production")


class SettingsTests(unittest.TestCase):

    def test_default_settings(self):
        settings = build_settings(environ={})

        self.assertEqual(settings.app_env, "development")
        self.assertEqual(settings.app_port, 8000)
        self.assertFalse(settings.app_debug)

    def test_custom_settings(self):
        settings = build_settings(
            environ={
                "APP_ENV": "test",
                "APP_PORT": "9000",
                "APP_LOG_LEVEL": "WARNING",
            }
        )

        self.assertEqual(settings.app_env, "test")
        self.assertEqual(settings.app_port, 9000)
        self.assertEqual(settings.app_log_level, "WARNING")

    def test_invalid_environment_rejected(self):
        with self.assertRaises(ConfigurationError):
            build_settings(
                environ={"APP_ENV": "unknown"}
            )

    def test_invalid_port_rejected(self):
        with self.assertRaises(ConfigurationError):
            build_settings(
                environ={"APP_PORT": "99999"}
            )

    def test_non_integer_port_rejected(self):
        with self.assertRaises(ConfigurationError):
            build_settings(
                environ={"APP_PORT": "not-a-port"}
            )

    def test_invalid_boolean_rejected(self):
        with self.assertRaises(ConfigurationError):
            build_settings(
                environ={"APP_DEBUG": "sometimes"}
            )

    def test_production_requires_long_jwt_secret(self):
        with self.assertRaises(ConfigurationError):
            build_settings(
                environ={
                    "APP_ENV": "production",
                    "JWT_SECRET_KEY": "short",
                }
            )

    def test_production_rejects_debug_mode(self):
        with self.assertRaises(ConfigurationError):
            build_settings(
                environ={
                    "APP_ENV": "production",
                    "APP_DEBUG": "true",
                    "JWT_SECRET_KEY": "x" * 48,
                }
            )

    def test_production_accepts_valid_jwt_secret(self):
        settings = build_settings(
            environ={
                "APP_ENV": "production",
                "APP_DEBUG": "false",
                "JWT_SECRET_KEY": "x" * 48,
                "CORS_ALLOWED_ORIGINS": "https://example.com",
                "PUBLIC_API_BASE_URL": "https://api.example.com",
                "FRONTEND_ORIGIN": "https://example.com",
            }
        )

        self.assertTrue(settings.is_production)

    def test_invalid_jwt_algorithm_rejected(self):
        with self.assertRaises(ConfigurationError):
            build_settings(
                environ={"JWT_ALGORITHM": "none"}
            )

    def test_cors_origins_are_deduplicated(self):
        settings = build_settings(
            environ={
                "CORS_ALLOWED_ORIGINS": (
                    "https://example.com,"
                    "https://example.com"
                )
            }
        )

        self.assertEqual(
            settings.cors_allowed_origins,
            ("https://example.com",),
        )

    def test_cors_origin_with_path_rejected(self):
        with self.assertRaises(ConfigurationError):
            build_settings(
                environ={
                    "CORS_ALLOWED_ORIGINS": (
                        "https://example.com/api"
                    )
                }
            )

    def test_credential_embedded_url_rejected(self):
        with self.assertRaises(ConfigurationError):
            build_settings(
                environ={
                    "PUBLIC_API_BASE_URL": (
                        "https://user:password@example.com"
                    )
                }
            )

    def test_settings_repr_does_not_show_jwt_secret(self):
        secret = "never-print-this-secret-value"
        settings = build_settings(
            environ={"JWT_SECRET_KEY": secret}
        )

        self.assertNotIn(secret, repr(settings))

    def test_safe_summary_does_not_expose_secret(self):
        secret = "never-print-this-secret-value"
        settings = build_settings(
            environ={
                "JWT_SECRET_KEY": secret,
                "NASA_API_KEY": "private-nasa-key",
            }
        )

        summary = str(settings.safe_summary())

        self.assertNotIn(secret, summary)
        self.assertNotIn("private-nasa-key", summary)
        self.assertTrue(
            settings.safe_summary()["jwt_secret_configured"]
        )


class RedactionTests(unittest.TestCase):

    def test_redacts_api_key_assignment(self):
        output = redact_secrets(
            "NASA_API_KEY=super-secret-value"
        )

        self.assertNotIn("super-secret-value", output)
        self.assertIn("[REDACTED]", output)

    def test_redacts_bearer_token(self):
        output = redact_secrets(
            "Authorization: Bearer abc.def.ghi"
        )

        self.assertNotIn("abc.def.ghi", output)
        self.assertIn("[REDACTED]", output)

    def test_redacts_url_password(self):
        output = redact_secrets(
            "postgresql://admin:secret123@localhost/db"
        )

        self.assertNotIn("secret123", output)
        self.assertIn("[REDACTED]", output)

    def test_redacts_prefixed_nasa_api_key(self):
        output = redact_secrets(
            "NASA_API_KEY=super-secret-value"
        )
        self.assertNotIn("super-secret-value", output)
        self.assertIn("[REDACTED]", output)

    def test_redacts_jwt_secret_key(self):
        output = redact_secrets(
            "JWT_SECRET_KEY=jwt-private-value"
        )
        self.assertNotIn("jwt-private-value", output)
        self.assertIn("[REDACTED]", output)

    def test_redacts_aws_secret_access_key(self):
        output = redact_secrets(
            "AWS_SECRET_ACCESS_KEY=aws-private-value"
        )
        self.assertNotIn("aws-private-value", output)
        self.assertIn("[REDACTED]", output)

    def test_redacts_quoted_api_key(self):
        output = redact_secrets(
            'NASA_API_KEY="quoted-private-value"'
        )
        self.assertNotIn("quoted-private-value", output)
        self.assertIn("[REDACTED]", output)

    def test_redacts_database_url_assignment(self):
        output = redact_secrets(
            "DATABASE_URL=postgresql://admin:privatepass@localhost/db"
        )
        self.assertNotIn("privatepass", output)
        self.assertIn("[REDACTED]", output)

    def test_redacts_redis_url_assignment(self):
        output = redact_secrets(
            "REDIS_URL=redis://:privatepass@localhost:6379/0"
        )
        self.assertNotIn("privatepass", output)
        self.assertIn("[REDACTED]", output)

    def test_does_not_change_safe_text(self):
        safe = "AstroGuard API started successfully"
        self.assertEqual(redact_secrets(safe), safe)


class ConfigurationWarningTests(unittest.TestCase):

    def test_development_debug_warning(self):
        settings = build_settings(
            environ={
                "APP_ENV": "development",
                "APP_DEBUG": "true",
            }
        )

        warnings = validate_configuration(settings)

        self.assertTrue(any("Debug mode" in item for item in warnings))

    def test_production_configuration_warnings(self):
        settings = build_settings(
            environ={
                "APP_ENV": "production",
                "JWT_SECRET_KEY": "x" * 48,
            }
        )

        warnings = validate_configuration(settings)

        self.assertTrue(
            any("database" in item.lower() for item in warnings)
        )


if __name__ == "__main__":
    unittest.main()
