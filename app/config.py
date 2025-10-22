"""Configuration management with secure secrets handling."""

import os
from typing import Optional


class Config:
    """
    Application configuration with environment-based secrets.

    Secrets are loaded from environment variables to avoid hardcoding
    and support rotation without code changes.
    """

    def __init__(self):
        """Initialize configuration from environment variables."""
        # Optional: Database URL (not required for in-memory storage)
        self.database_url = self._get_secret("DATABASE_URL", required=False)

        # Optional: Secret key for signing/encryption
        self.secret_key = self._get_secret("SECRET_KEY", required=False)

        # Optional: API keys for external services
        self.external_api_key = self._get_secret("EXTERNAL_API_KEY", required=False)

        # Application settings (non-sensitive)
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")

    def _get_secret(self, key: str, required: bool = True) -> Optional[str]:
        """
        Retrieve secret from environment variables.

        Args:
            key: Environment variable name
            required: Whether the secret is mandatory

        Returns:
            Secret value or None if not required and not found

        Raises:
            ValueError: If required secret is not found
        """
        value = os.getenv(key)

        if required and not value:
            raise ValueError(
                f"Required secret '{key}' not found in environment variables. "
                f"Please set {key} environment variable."
            )

        return value

    def __repr__(self) -> str:
        """
        Safe representation that masks secrets.

        Returns:
            String representation with masked sensitive fields
        """
        return (
            f"Config("
            f"database_url={'***' if self.database_url else 'None'}, "
            f"secret_key={'***' if self.secret_key else 'None'}, "
            f"external_api_key={'***' if self.external_api_key else 'None'}, "
            f"debug={self.debug}, "
            f"environment='{self.environment}'"
            f")"
        )

    def validate_production_secrets(self) -> None:
        """
        Validate that all required secrets are present for production.

        Should be called during application startup in production environment.

        Raises:
            RuntimeError: If production-required secrets are missing
        """
        if self.environment == "production":
            missing = []

            # Add production-required secrets here
            # Example:
            # if not self.secret_key:
            #     missing.append("SECRET_KEY")

            if missing:
                raise RuntimeError(
                    f"Missing required secrets for production: {', '.join(missing)}"
                )


# Global config instance
config = Config()
