from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Rack, Device, Cable, PduOutlet

router = APIRouter()


@router.get("")
async def get_topology(db: AsyncSession = Depends(get_db)):
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
    rack_map = {r.id: r for r in racks}

    nodes = []
    for dev in all_devices:
        rack = rack_map.get(dev.rack_id) if dev.rack_id else None
        nodes.append(
            {
                "id": dev.id,
                "hostname": dev.hostname,
                "typ": dev.typ,
                "rack_id": dev.rack_id,
                "rack_name": rack.name if rack else None,
                "u_position": dev.u_position,
                "u_hoehe": dev.u_hoehe if dev.u_hoehe is not None else 1,
                "hersteller": dev.hersteller,
                "modell": dev.modell,
                "ip_adresse": dev.ip_adresse,
            }
        )

    edges = []

    # Kabel-Verbindungen
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

    # PDU-Stromverbindungen (Outlet → Gerät)
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
                    "laenge_m": None,
                    "farbe": None,
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

    return {"racks": racks_out, "nodes": nodes, "edges": edges}
