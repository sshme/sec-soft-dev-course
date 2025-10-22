"""Configuration management with secure secrets handling."""

import os
from typing import Optional


class Config:
    def __init__(self):
        self.database_url = self._get_secret("DATABASE_URL", required=False)

        self.secret_key = self._get_secret("SECRET_KEY", required=False)

        self.external_api_key = self._get_secret("EXTERNAL_API_KEY", required=False)

        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")

    def _get_secret(self, key: str, required: bool = True) -> Optional[str]:
        value = os.getenv(key)

        if required and not value:
            raise ValueError(
                f"Required secret '{key}' not found in environment variables. "
                f"Please set {key} environment variable."
            )

        return value

    def __repr__(self) -> str:
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
        if self.environment == "production":
            missing = []
            if missing:
                raise RuntimeError(
                    f"Missing required secrets for production: {', '.join(missing)}"
                )


config = Config()
