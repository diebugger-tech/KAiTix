from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.models import Device, Cable, Rack

router = APIRouter()

MAX_RESULTS = 8


@router.get("")
async def search(q: str = "", db: AsyncSession = Depends(get_db)):
    q = q.strip()
    if len(q) < 2:
        return {"devices": [], "cables": [], "racks": []}

    term = f"%{q}%"

    devs_res = await db.execute(
        select(Device)
        .where(
            or_(
                Device.hostname.ilike(term),
                Device.ip_adresse.ilike(term),
                Device.seriennummer.ilike(term),
                Device.inventarnummer.ilike(term),
                Device.hersteller.ilike(term),
                Device.modell.ilike(term),
            )
        )
        .limit(MAX_RESULTS)
    )
    devs = devs_res.scalars().all()

    cables_res = await db.execute(
        select(Cable)
        .where(
            or_(
                Cable.kabel_nr.ilike(term),
                Cable.farbe.ilike(term),
                Cable.von_port.ilike(term),
                Cable.nach_port.ilike(term),
                Cable.bemerkung.ilike(term),
            )
        )
        .limit(MAX_RESULTS)
    )
    cables = cables_res.scalars().all()

    racks_res = await db.execute(
        select(Rack)
        .where(or_(Rack.name.ilike(term), Rack.standort.ilike(term)))
        .limit(MAX_RESULTS)
    )
    racks = racks_res.scalars().all()

    return {
        "devices": [
            {
                "id": d.id,
                "hostname": d.hostname,
                "typ": d.typ,
                "rack_id": d.rack_id,
                "ip_adresse": d.ip_adresse,
                "hersteller": d.hersteller,
                "modell": d.modell,
            }
            for d in devs
        ],
        "cables": [
            {
                "id": c.id,
                "kabel_nr": c.kabel_nr,
                "typ": c.typ,
                "farbe": c.farbe,
                "von_port": c.von_port,
                "nach_port": c.nach_port,
            }
            for c in cables
        ],
        "racks": [{"id": r.id, "name": r.name, "standort": r.standort} for r in racks],
    }
