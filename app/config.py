"""Configuration management with secure secrets handling."""

import os
from typing import Optional


class Config:
    def __init__(self):
        self.database_url = self._get_secret("DATABASE_URL", required=False)

        env = os.getenv("ENVIRONMENT", "development")
        self.secret_key = self._get_secret("SECRET_KEY", required=(env == "production"))
        self.secret_key_prev = self._get_secret("SECRET_KEY_PREV", required=False)

        self.external_api_key = self._get_secret("EXTERNAL_API_KEY", required=False)

        self.s3_bucket = os.getenv("S3_BUCKET", "highlights-uploads")
        self.s3_endpoint = os.getenv("S3_ENDPOINT")
        self.s3_access_key = self._get_secret("S3_ACCESS_KEY", required=False)
        self.s3_secret_key = self._get_secret("S3_SECRET_KEY", required=False)
        self.tmp_dir = os.getenv("TMP_DIR", "/tmp")

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
            f"secret_key_prev={'***' if self.secret_key_prev else 'None'}, "
            f"external_api_key={'***' if self.external_api_key else 'None'}, "
            f"s3_bucket='{self.s3_bucket}', "
            f"debug={self.debug}, "
            f"environment='{self.environment}'"
            f")"
        )

    def validate_production_secrets(self) -> None:
        if self.environment == "production":
            missing = []
            if not self.secret_key:
                missing.append("SECRET_KEY")
            if missing:
                raise RuntimeError(
                    f"Missing required secrets for production: {', '.join(missing)}"
                )


config = Config()
