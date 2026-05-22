import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Rack, Device, Cable, PduOutlet
from app.domains.import_export.services.topology_pdf import generate_topology_pdf

router = APIRouter()


def remove_file(path: str):
    try:
        os.unlink(path)
    except Exception:
        pass


async def _build_pdf_data(db: AsyncSession) -> dict:
    racks = (
        (await db.execute(select(Rack).options(selectinload(Rack.devices))))
        .scalars()
        .all()
    )
    all_devices = (await db.execute(select(Device))).scalars().all()
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

    dev_map = {d.id: d for d in all_devices}

    nodes = []
    for dev in all_devices:
        nodes.append(
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
        )

    edges = []
    for cable in cables:
        if cable.von_device_id and cable.nach_device_id:
            vd = dev_map.get(cable.von_device_id)
            nd = dev_map.get(cable.nach_device_id)
            cross_rack = (
                vd and nd and vd.rack_id and nd.rack_id and vd.rack_id != nd.rack_id
            )
            edges.append(
                {
                    "id": f"cable-{cable.id}",
                    "edge_type": "cable",
                    "kabel_nr": cable.kabel_nr,
                    "typ": cable.typ,
                    "laenge_m": float(cable.laenge_m),
                    "farbe": cable.farbe,
                    "von_device_id": cable.von_device_id,
                    "von_port": cable.von_port,
                    "nach_device_id": cable.nach_device_id,
                    "nach_port": cable.nach_port,
                    "cross_rack": bool(cross_rack),
                }
            )

    for outlet in outlets:
        if outlet.pdu_id and outlet.connected_device_id:
            pdu = dev_map.get(outlet.pdu_id)
            dev = dev_map.get(outlet.connected_device_id)
            cross_rack = (
                pdu
                and dev
                and pdu.rack_id
                and dev.rack_id
                and pdu.rack_id != dev.rack_id
            )
            edges.append(
                {
                    "id": f"power-{outlet.id}",
                    "edge_type": "power",
                    "kabel_nr": outlet.outlet_name,
                    "typ": f"Strom-{outlet.steckdosentyp or 'PDU'}",
                    "von_device_id": outlet.pdu_id,
                    "von_port": outlet.outlet_name,
                    "nach_device_id": outlet.connected_device_id,
                    "nach_port": outlet.connected_port,
                    "cross_rack": bool(cross_rack),
                    "phase": outlet.phase,
                }
            )

    racks_out = [
        {
            "id": r.id,
            "name": r.name,
            "standort": r.standort,
            "hoehe_u": r.hoehe_u,
        }
        for r in racks
    ]

    return {"racks": racks_out, "devices": nodes, "edges": edges}


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
        filename="topologie.pdf",
        headers={"Content-Disposition": 'attachment; filename="topologie.pdf"'},
    )
