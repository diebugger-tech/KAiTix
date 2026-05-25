from typing import List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domains.runbooks.models import (
    Runbook as RunbookModel,
    RunbookLayer as RunbookLayerModel,
    RunbookDevice as RunbookDeviceModel,
)
from app.domains.hardware.models import Device, PduOutlet

def _runbook_options():
    return [
        selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices).selectinload(RunbookDeviceModel.device).selectinload(Device.connected_pdu_outlets).selectinload(PduOutlet.pdu),
        selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices).selectinload(RunbookDeviceModel.vm),
    ]

class RunbookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_startup(self, id: int) -> RunbookModel:
        result = await self.db.execute(
            select(RunbookModel)
            .where(RunbookModel.id == id)
            .options(selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices))
        )
        shutdown_runbook = result.scalar_one_or_none()
        if not shutdown_runbook or shutdown_runbook.typ != "shutdown":
            raise HTTPException(status_code=400, detail="Must generate from a 'shutdown' runbook")

        startup_runbook = RunbookModel(
            name=f"{shutdown_runbook.name} — Startup",
            typ="startup",
            beschreibung=shutdown_runbook.beschreibung,
            generated_from_id=id
        )
        self.db.add(startup_runbook)
        await self.db.flush() # get id

        # reverse layers
        sorted_layers = sorted(shutdown_runbook.layers, key=lambda x: x.position, reverse=True)
        
        for layer_idx, old_layer in enumerate(sorted_layers):
            new_layer = RunbookLayerModel(
                runbook_id=startup_runbook.id,
                position=layer_idx + 1,
                name=old_layer.name,
                markdown_note=None 
            )
            self.db.add(new_layer)
            await self.db.flush()

            for old_dev in old_layer.devices:
                new_dev = RunbookDeviceModel(
                    runbook_id=startup_runbook.id,
                    layer_id=new_layer.id,
                    device_id=old_dev.device_id,
                    vm_id=old_dev.vm_id,
                    freitext=old_dev.freitext,
                    delay_seconds=old_dev.delay_seconds,
                    responsible=old_dev.responsible,
                    position=old_dev.position,
                    note=None
                )
                self.db.add(new_dev)

        await self.db.commit()
        
        # reload with options to match the response_model format
        reloaded = await self.db.execute(
            select(RunbookModel)
            .where(RunbookModel.id == startup_runbook.id)
            .options(*_runbook_options())
        )
        return reloaded.scalar_one()

    async def export_markdown(self, id: int) -> str:
        result = await self.db.execute(
            select(RunbookModel)
            .where(RunbookModel.id == id)
            .options(
                selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices).selectinload(RunbookDeviceModel.device),
                selectinload(RunbookModel.layers).selectinload(RunbookLayerModel.devices).selectinload(RunbookDeviceModel.vm),
            )
        )
        runbook = result.scalar_one_or_none()
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")

        lines = []
        lines.append(f"# Runbook: {runbook.name}")
        lines.append(f"**Typ:** {runbook.typ} | **Erstellt:** {runbook.erstellt_am.strftime('%Y-%m-%d %H:%M')} | **Von:** {runbook.erstellt_von or 'System'}")
        if runbook.beschreibung:
            lines.append(runbook.beschreibung)
        
        lines.append("\n---\n")
        lines.append("## " + ("SHUTDOWN-SEQUENZ" if runbook.typ == "shutdown" else "STARTUP-SEQUENZ (umgekehrt)" if runbook.typ == "startup" else f"{runbook.typ.upper()}-SEQUENZ"))
        
        sorted_layers = sorted(runbook.layers, key=lambda x: x.position)
        
        for layer in sorted_layers:
            lines.append(f"\n### Ebene {layer.position}: {layer.name}")
            if layer.markdown_note:
                lines.append(f"> {layer.markdown_note}")
            lines.append("")
            
            sorted_devices = sorted(layer.devices, key=lambda x: x.position)
            for dev in sorted_devices:
                ident = dev.freitext or (dev.vm.name if dev.vm else (dev.device.hostname if dev.device else "Unknown"))
                resp = f" — {dev.responsible}" if dev.responsible else ""
                lines.append(f"- [ ] {ident} ({dev.delay_seconds}s){resp}")
                if dev.note:
                    lines.append(f"      _Notiz: {dev.note}_")

        return "\n".join(lines)
