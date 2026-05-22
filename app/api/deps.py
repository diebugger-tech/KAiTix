from fastapi import Header
from typing import Annotated


async def get_username(
    x_username: Annotated[str | None, Header()] = None,
) -> str | None:
    return x_username
