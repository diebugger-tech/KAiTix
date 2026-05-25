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

    async def export_pdf(self, id: int) -> bytes:
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

        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        story = []

        styles = getSampleStyleSheet()
        
        # Custom Typography Styles
        title_style = ParagraphStyle(
            'RunbookTitle',
            parent=styles['Heading1'],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=10
        )
        meta_style = ParagraphStyle(
            'RunbookMeta',
            parent=styles['Normal'],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#475569'),
            spaceAfter=15
        )
        layer_style = ParagraphStyle(
            'RunbookLayer',
            parent=styles['Heading2'],
            fontSize=13,
            leading=17,
            textColor=colors.HexColor('#1e3a8a'),
            spaceBefore=12,
            spaceAfter=6
        )
        item_style = ParagraphStyle(
            'RunbookItem',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#1e293b')
        )
        note_style = ParagraphStyle(
            'RunbookNote',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748b'),
            leftIndent=20
        )

        story.append(Paragraph(f"Runbook: {runbook.name}", title_style))
        
        typ_str = "Shutdown" if runbook.typ == "shutdown" else "Startup" if runbook.typ == "startup" else runbook.typ.capitalize()
        erstellt_am_str = runbook.erstellt_am.strftime('%Y-%m-%d %H:%M')
        story.append(Paragraph(f"<b>Typ:</b> {typ_str} | <b>Erstellt:</b> {erstellt_am_str} | <b>Erstellt von:</b> {runbook.erstellt_von or 'System'}", meta_style))
        
        if runbook.beschreibung:
            desc_style = ParagraphStyle(
                'RunbookDesc',
                parent=styles['Normal'],
                fontSize=10.5,
                leading=14,
                textColor=colors.HexColor('#334155'),
                spaceAfter=15
            )
            story.append(Paragraph(runbook.beschreibung, desc_style))
            
        story.append(Spacer(1, 10))
        
        sorted_layers = sorted(runbook.layers, key=lambda x: x.position)
        for layer in sorted_layers:
            story.append(Paragraph(f"Ebene {layer.position}: {layer.name}", layer_style))
            if layer.markdown_note:
                layer_note_style = ParagraphStyle(
                    'LayerNote',
                    parent=styles['Normal'],
                    fontSize=9,
                    leading=12,
                    textColor=colors.HexColor('#475569'),
                    backColor=colors.HexColor('#f1f5f9'),
                    borderColor=colors.HexColor('#cbd5e1'),
                    borderWidth=0.5,
                    borderPadding=6,
                    spaceAfter=8,
                    borderRadius=4
                )
                story.append(Paragraph(layer.markdown_note, layer_note_style))
            
            sorted_devices = sorted(layer.devices, key=lambda x: x.position)
            
            # Draw checklist table
            table_data = []
            for dev in sorted_devices:
                ident = dev.freitext or (dev.vm.name if dev.vm else (dev.device.hostname if dev.device else "Unknown"))
                resp_str = f" ({dev.responsible})" if dev.responsible else ""
                delay_str = f"{dev.delay_seconds}s"
                
                checkbox_html = "<b>[  ]</b>"
                info_html = f"<b>{ident}</b> ({delay_str}){resp_str}"
                
                row = [
                    Paragraph(checkbox_html, item_style),
                    Paragraph(info_html, item_style)
                ]
                table_data.append(row)
                
                if dev.note:
                    note_html = f"<i>Notiz: {dev.note}</i>"
                    table_data.append([Paragraph("", item_style), Paragraph(note_html, note_style)])
            
            if table_data:
                t = Table(table_data, colWidths=[24, 476])
                t.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(t)
            else:
                empty_style = ParagraphStyle('Empty', parent=styles['Normal'], fontSize=9.5, textColor=colors.HexColor('#94a3b8'), leftIndent=20)
                story.append(Paragraph("Keine Geräte in dieser Ebene.", empty_style))
                
            story.append(Spacer(1, 10))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
