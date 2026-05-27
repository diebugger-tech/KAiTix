import logging
import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.cabling.services import CablingService
from app.domains.import_export.services.topology_pdf import generate_topology_pdf

logger = logging.getLogger(__name__)
router = APIRouter()


def remove_file(path: str):
    try:
        os.unlink(path)
    except OSError:
        pass


async def _build_pdf_data(db: AsyncSession) -> dict:
    service = CablingService(db)
    raw = await service.load_topology()

    devices = [
        {
            "id": dev.id,
            "hostname": dev.hostname,
            "typ": dev.typ,
            "rack_id": dev.rack_id,
            "u_position": dev.u_position,
            "u_hoehe": dev.u_hoehe or 1,
            "hersteller": dev.hersteller,
            "modell": dev.modell,
            "phase": dev.phase,
            "tdp_watt": float(dev.tdp_watt) if dev.tdp_watt else None,
            "anschlussleistung_watt": float(dev.anschlussleistung_watt)
            if dev.anschlussleistung_watt
            else None,
        }
        for dev in raw.devices
    ]

    return {
        "racks": CablingService.build_racks_out(raw),
        "devices": devices,
        "edges": CablingService.build_edges(raw),
    }


@router.get("/pdf")
async def export_topology_pdf(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    data = await _build_pdf_data(db)
    if not data["racks"]:
        raise HTTPException(status_code=404, detail="Keine Racks vorhanden")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name

    try:
        generate_topology_pdf(data, tmp_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        logger.exception("Topologie-PDF-Generierung fehlgeschlagen")
        raise HTTPException(status_code=500, detail="PDF-Generierung fehlgeschlagen")

    background_tasks.add_task(remove_file, tmp_path)
    return FileResponse(
        tmp_path,
        media_type="application/pdf",
        filename="topologie.pdf",
        headers={"Content-Disposition": 'attachment; filename="topologie.pdf"'},
    )
