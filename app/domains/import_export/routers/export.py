"""
KAiTix — Export Endpunkt
Ablegen: app/api/endpoints/export.py  (ersetzt oder ergänzt die bestehende export.py)

In app/api/router.py einbinden (falls noch nicht):
    from app.api.endpoints import export
    router.include_router(export.router, prefix="/export", tags=["export"])

Install: pip install openpyxl odfpy
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Rack, Device, Cable, PduOutlet
from app.domains.import_export.services.export_service import (
    build_export,
    build_single_export,
)

router = APIRouter()


async def _load_data(db: AsyncSession) -> dict:
    """Alle Export-relevanten Daten aus DB laden."""
    racks = (
        (await db.execute(select(Rack).options(selectinload(Rack.devices))))
        .scalars()
        .all()
    )

    devices = (
        (
            await db.execute(
                select(Device).options(
                    selectinload(Device.interfaces),
                    selectinload(Device.pdu_outlets),
                )
            )
        )
        .scalars()
        .all()
    )

    cables = (
        (
            await db.execute(
                select(Cable).options(
                    selectinload(Cable.von_device),
                    selectinload(Cable.nach_device),
                )
            )
        )
        .scalars()
        .all()
    )

    outlets = (await db.execute(select(PduOutlet))).scalars().all()

    def r2d(r):
        return {
            "id": r.id,
            "name": r.name,
            "standort": r.standort,
            "hoehe_u": r.hoehe_u,
        }

    def d2d(d):
        return {
            "id": d.id,
            "typ": d.typ,
            "hostname": d.hostname,
            "ip": d.ip_adresse or "–",
            "rack_id": d.rack_id,
            "u_pos": d.u_position or 0,
            "u_h": d.u_hoehe or 1,
            "phase": d.phase or "–",
            "watt": float(d.anschlussleistung_watt or d.tdp_watt or 0),
            "hersteller": d.hersteller or "–",
            "modell": d.modell or "–",
            "bemerkung": d.bemerkung or "",
        }

    def c2d(c):
        return {
            "id": c.id,
            "nr": c.kabel_nr,
            "typ": c.typ,
            "laenge": float(c.laenge_m),
            "farbe": c.farbe or "–",
            "von_dev": c.von_device_id,
            "von_port": c.von_port or "–",
            "nach_dev": c.nach_device_id,
            "nach_port": c.nach_port or "–",
            "verlegt_am": str(c.verlegt_am) if c.verlegt_am else "–",
            "verlegt_von": c.verlegt_von or "–",
        }

    def o2d(o):
        return {
            "id": o.id,
            "pdu_id": o.pdu_id,
            "outlet_name": o.outlet_name,
            "phase": o.phase or "–",
            "steckdosentyp": o.steckdosentyp or "–",
            "max_watt": float(o.max_watt) if o.max_watt else "–",
            "schaltbar": o.schaltbar,
            "connected_device_id": o.connected_device_id,
            "connected_port": o.connected_port or "–",
        }

    ifaces = []
    for d in devices:
        for i in d.interfaces or []:
            ifaces.append(
                {
                    "dev_id": d.id,
                    "port": i.port_name,
                    "typ": i.typ,
                    "mac": i.mac_adresse or "–",
                    "kabel_id": i.kabel_id,
                }
            )

    return {
        "racks": [r2d(r) for r in racks],
        "devices": [d2d(d) for d in devices],
        "interfaces": ifaces,
        "cables": [c2d(c) for c in cables],
        "pdu_outlets": [o2d(o) for o in outlets],
    }


@router.get("/xlsx")
async def export_xlsx(db: AsyncSession = Depends(get_db)):
    """Vollständige Dokumentation als Excel (.xlsx) mit allen Sheets."""
    data = await _load_data(db)
    raw, mime, fname = build_export(data, "xlsx")
    return Response(
        content=raw,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.get("/ods")
async def export_ods(db: AsyncSession = Depends(get_db)):
    """Vollständige Dokumentation als ODS (LibreOffice)."""
    data = await _load_data(db)
    raw, mime, fname = build_export(data, "ods")
    return Response(
        content=raw,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.get("/csv")
async def export_csv(db: AsyncSession = Depends(get_db)):
    """Kabelliste + Geräte + PDU als CSV-ZIP (5 Dateien)."""
    data = await _load_data(db)
    raw, mime, fname = build_export(data, "csv")
    return Response(
        content=raw,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.get("/racks")
async def export_racks(
    fmt: str = Query("xlsx", pattern="^(xlsx|ods|csv)$"),
    db: AsyncSession = Depends(get_db),
):
    """Rack-Inventar als Einzel-Export."""
    data = await _load_data(db)
    raw, mime, fname = build_single_export(data, "racks", fmt)  # type: ignore[arg-type]
    return Response(
        content=raw,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.get("/interfaces")
async def export_interfaces(
    fmt: str = Query("xlsx", pattern="^(xlsx|ods|csv)$"),
    db: AsyncSession = Depends(get_db),
):
    """Ports & Interfaces als Einzel-Export."""
    data = await _load_data(db)
    raw, mime, fname = build_single_export(data, "interfaces", fmt)  # type: ignore[arg-type]
    return Response(
        content=raw,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.get("/pdus")
async def export_pdus(
    fmt: str = Query("xlsx", pattern="^(xlsx|ods|csv)$"),
    db: AsyncSession = Depends(get_db),
):
    """PDU-Belegung als Einzel-Export."""
    data = await _load_data(db)
    raw, mime, fname = build_single_export(data, "pdus", fmt)  # type: ignore[arg-type]
    return Response(
        content=raw,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@router.get("/cables")
async def export_cables(
    fmt: str = Query("xlsx", pattern="^(xlsx|ods|csv)$"),
    db: AsyncSession = Depends(get_db),
):
    """Kabelliste als Einzel-Export."""
    data = await _load_data(db)
    raw, mime, fname = build_single_export(data, "cables", fmt)  # type: ignore[arg-type]
    return Response(
        content=raw,
        media_type=mime,
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )
