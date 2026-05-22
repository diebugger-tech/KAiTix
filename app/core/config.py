import os
from pydantic import BaseModel


def _parse_origins(raw: str) -> list[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]


class Settings(BaseModel):
    PROJECT_NAME: str = "KAiTix"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "mysql+aiomysql://root@127.0.0.1:3306/serverflow"
    )
    ALLOWED_ORIGINS: list[str] = _parse_origins(
        os.getenv("ALLOWED_ORIGINS", "http://localhost:5175,http://127.0.0.1:5175")
    )


settings = Settings()
