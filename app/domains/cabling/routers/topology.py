from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.cabling.services import CablingService
from app.domains.simulation.services import AnomalyScorer
from app.domains.power.models import UsvUnit

router = APIRouter()


@router.get("")
async def get_topology(db: AsyncSession = Depends(get_db)):
    """
    Get full topology including nodes, edges, and racks.
    """
    service = CablingService(db)
    raw = await service.load_topology()

    nodes = [
        {
            "id": dev.id,
            "hostname": dev.hostname,
            "typ": dev.typ,
            "rack_id": dev.rack_id,
            "rack_name": raw.rack_map[dev.rack_id].name if dev.rack_id else None,
            "u_position": dev.u_position,
            "u_hoehe": dev.u_hoehe if dev.u_hoehe is not None else 1,
            "hersteller": dev.hersteller,
            "modell": dev.modell,
            "ip_adresse": dev.ip_adresse,
        }
        for dev in raw.devices
    ]

    return {
        "racks": CablingService.build_racks_out(raw),
        "nodes": nodes,
        "edges": CablingService.build_edges(raw),
    }


@router.get("/anomaly-scores")
async def get_anomaly_scores(db: AsyncSession = Depends(get_db)):
    """
    Returns anomaly scores for all racks.
    """
    service = CablingService(db)
    raw = await service.load_topology()
    usv_rack_ids = set(
        (await db.execute(select(UsvUnit.rack_id))).scalars().all()
    )
    return AnomalyScorer.score_all_racks(
        racks=raw.racks,
        devices=raw.devices,
        outlets=raw.outlets,
        usv_rack_ids=usv_rack_ids,
    )
