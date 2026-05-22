from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.cabling.services.topology_loader import load_topology, build_edges, build_racks_out

router = APIRouter()


@router.get("")
async def get_topology(db: AsyncSession = Depends(get_db)):
    raw = await load_topology(db)

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

    return {"racks": build_racks_out(raw), "nodes": nodes, "edges": build_edges(raw)}
