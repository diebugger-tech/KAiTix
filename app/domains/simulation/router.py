from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

from app.domains.simulation.schemas import SimulationScenario, SimulationResult
from app.domains.simulation.services import run_simulation

router = APIRouter(
    prefix="",
    tags=["simulation"],
    responses={404: {"description": "Not found"}},
)

@router.post("/run", response_model=SimulationResult)
async def api_run_simulation(scenario: SimulationScenario, db: AsyncSession = Depends(get_db)):
    """Run a power failure and shutdown/boot sequence simulation based on a specific scenario."""
    try:
        result = await run_simulation(db, scenario)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
