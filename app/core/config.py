import os
from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "KAiTix"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "mysql+aiomysql://root@127.0.0.1:3306/serverflow"
    )


settings = Settings()
