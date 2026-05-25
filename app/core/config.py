import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env from project root so os.getenv picks up DATABASE_URL etc.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _parse_origins(raw: str) -> list[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]


class Settings(BaseModel):
    PROJECT_NAME: str = "KAiTix"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "mysql+aiomysql://kaitix:kaitix@127.0.0.1:3306/kaitix"
    )
    ALLOWED_ORIGINS: list[str] = _parse_origins(
        os.getenv("ALLOWED_ORIGINS", "http://localhost:5175,http://127.0.0.1:5175")
    )


settings = Settings()
