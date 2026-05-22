"""
KAiTix — Rack PDF Export Endpunkt
Ablegen unter: app/api/endpoints/rack_export.py

Einbinden in app/api/__init__.py oder main.py:
    from app.api.endpoints.rack_export import router as pdf_router
    app.include_router(pdf_router, prefix="/api/v1", tags=["export"])
"""

import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import (
    Rack as RackModel,
    Device as DeviceModel,
    Cable as CableModel,
)
from app.domains.import_export.services.rack_pdf import generate_rack_pdf

router = APIRouter()


def remove_file(path: str):
    """Löscht eine Datei vom Dateisystem, fängt Fehler ab."""
    try:
        os.unlink(path)
    except Exception:
        pass


async def _build_pdf_data(db: AsyncSession, rack_id: int | None = None) -> dict:
    """Lädt alle nötigen Daten aus der DB und baut das kanonische Dict."""

    # Racks
    rack_q = select(RackModel)
    if rack_id:
        rack_q = rack_q.where(RackModel.id == rack_id)
    rack_res = await db.execute(rack_q)
    racks = rack_res.scalars().all()

    if rack_id and not racks:
        raise HTTPException(status_code=404, detail="Rack nicht gefunden")

    # Devices mit Interfaces
    dev_res = await db.execute(
        select(DeviceModel).options(
            selectinload(DeviceModel.interfaces),
        )
    )
    devices = dev_res.scalars().all()

    # Cables
    cable_res = await db.execute(select(CableModel))
    cables = cable_res.scalars().all()

    # Ports aus interfaces aufbauen
    ports = []
    for dev in devices:
        for iface in dev.interfaces or []:
            ports.append(
                {
                    "id": iface.id,
                    "device_id": iface.device_id,
                    "port_name": iface.port_name,
                    "typ": iface.typ,
                    "kabel_id": iface.kabel_id,
                }
            )

    return {
        "racks": [
            {
                "id": r.id,
                "name": r.name,
                "standort": r.standort,
                "hoehe_u": r.hoehe_u,
            }
            for r in racks
        ],
        "devices": [
            {
                "id": d.id,
                "hostname": d.hostname,
                "typ": d.typ,
                "ip_adresse": d.ip_adresse,
                "rack_id": d.rack_id,
                "u_position": d.u_position,
                "u_hoehe": d.u_hoehe,
                "phase": d.phase,
                "tdp_watt": float(d.anschlussleistung_watt or d.tdp_watt or 0),
                "anschlussleistung_watt": float(d.anschlussleistung_watt or 0),
            }
            for d in devices
        ],
        "ports": ports,
        "cables": [
            {
                "id": c.id,
                "kabel_nr": c.kabel_nr,
                "typ": c.typ,
                "laenge_m": float(c.laenge_m or 0),
                "farbe": c.farbe,
                "von_device_id": c.von_device_id,
                "von_port": c.von_port,
                "nach_device_id": c.nach_device_id,
                "nach_port": c.nach_port,
            }
            for c in cables
        ],
    }


@router.get("/racks/{rack_id}/pdf")
async def export_rack_pdf(
    rack_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Einzelnes Rack als PDF exportieren."""
    data = await _build_pdf_data(db, rack_id=rack_id)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name

    rack_name = data["racks"][0]["name"] if data["racks"] else f"rack-{rack_id}"

    try:
        generate_rack_pdf(data, tmp_path, rack_id=rack_id)
    except Exception as e:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise HTTPException(
            status_code=500, detail=f"PDF-Generierung fehlgeschlagen: {e}"
        )

    filename = f"rack_{rack_name.replace(' ', '_')}.pdf"
    background_tasks.add_task(remove_file, tmp_path)
    return FileResponse(
        tmp_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/racks-pdf")
async def export_all_racks_pdf(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Alle Racks als ein PDF exportieren."""
    data = await _build_pdf_data(db)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name

    try:
        generate_rack_pdf(data, tmp_path)
    except Exception as e:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise HTTPException(
            status_code=500, detail=f"PDF-Generierung fehlgeschlagen: {e}"
        )

    background_tasks.add_task(remove_file, tmp_path)
    return FileResponse(
        tmp_path,
        media_type="application/pdf",
        filename="rack_dokumentation.pdf",
        headers={
            "Content-Disposition": 'attachment; filename="rack_dokumentation.pdf"'
        },
    )
