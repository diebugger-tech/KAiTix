"""
KAiTix — Rack-Belegungsplan PDF Generator v2

Erwartet kanonisches Daten-Dict:
{
  "racks":   [{"id", "name", "standort", "hoehe_u"}],
  "devices": [{"id", "hostname", "typ", "ip_adresse", "rack_id",
               "u_position", "u_hoehe", "phase", "tdp_watt"}],
  "ports":   [{"id", "device_id", "port_name", "typ", "kabel_id"}],
  "cables":  [{"id", "kabel_nr", "typ", "laenge_m", "farbe",
               "von_device_id", "von_port", "nach_device_id", "nach_port"}],
}

Install: pip install reportlab
"""

from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4  # type: ignore
from reportlab.lib import colors  # type: ignore
from reportlab.lib.units import mm  # type: ignore
from reportlab.pdfgen import canvas as rl_canvas  # type: ignore
from reportlab.platypus import (  # type: ignore
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Flowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
from reportlab.lib.enums import TA_CENTER  # type: ignore

from app.core.constants import (
    C_SERVER,
    C_SWITCH,
    C_FIREWALL,
    C_STORAGE,
    C_PDU,
    C_KVM,
    C_KENTIX,
    C_BORDER,
    C_RAIL,
    C_TEXT,
    C_MUTED,
    C_XRACK,
    C_HEADER,
    C_STRIPE,
    PAGE_W,
    MARGIN,
    HEADER_STYLE,
    dev,
    rack as _rack,
    cable as get_cable,
    typ_color,
    typ_label,
    phase_load,
)


# ── Styles ───────────────────────────────────────────────────
def _make_styles() -> dict:
    base = getSampleStyleSheet()

    def s(name: str, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return {
        "title": s("sf_title", fontSize=16, textColor=C_TEXT, leading=20, spaceAfter=2),
        "subtitle": s(
            "sf_sub", fontSize=9, textColor=C_MUTED, leading=12, spaceAfter=8
        ),
        "h2": s(
            "sf_h2",
            fontSize=11,
            textColor=C_TEXT,
            leading=14,
            spaceBefore=10,
            spaceAfter=4,
            fontName="Helvetica-Bold",
        ),
        "cell": s("sf_cell", fontSize=8, textColor=C_TEXT, leading=10),
        "cell_m": s("sf_cell_m", fontSize=8, textColor=C_MUTED, leading=10),
        "footer": s(
            "sf_footer", fontSize=7, textColor=C_MUTED, leading=9, alignment=TA_CENTER
        ),
    }


# ── Rack-Frontansicht (canvas) ───────────────────────────────
def _draw_rack_front(
    c: rl_canvas.Canvas,
    data: dict,
    rack: dict,
    x: float,
    y: float,
    width: float,
    max_u: int = 24,
):
    hoehe_u = rack.get("hoehe_u", 42)
    show_u = min(hoehe_u, max_u)
    u_h_px = 5.5 * mm
    rack_h = show_u * u_h_px

    rail_w = 5 * mm  # Breite der seitlichen Schienen
    slot_x = x + rail_w
    slot_w = width - 2 * rail_w - 2 * mm

    # Rack-Gehäuse Außenrahmen
    c.setStrokeColor(colors.HexColor("#666666"))
    c.setLineWidth(1.2)
    c.setFillColor(colors.HexColor("#2a2a2a"))
    c.rect(x, y - rack_h, width - 1 * mm, rack_h, stroke=1, fill=1)

    # Linke Schiene
    c.setFillColor(C_RAIL)
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.3)
    c.rect(x + 0.5, y - rack_h + 0.5, rail_w - 1, rack_h - 1, stroke=1, fill=1)
    # Rechte Schiene
    c.rect(
        x + width - rail_w - 1.5,
        y - rack_h + 0.5,
        rail_w - 1,
        rack_h - 1,
        stroke=1,
        fill=1,
    )

    # Schraublöcher in Schienen (stilisiert)
    for i in range(show_u):
        sy = y - (i + 0.5) * u_h_px
        for sx in [x + rail_w / 2, x + width - rail_w / 2 - 1 * mm]:
            c.setFillColor(colors.HexColor("#888888"))
            c.circle(sx, sy, 0.8 * mm, fill=1, stroke=0)

    # Device-Map aufbauen
    devs = [d for d in data["devices"] if d.get("rack_id") == rack["id"]]
    dev_map: dict = {}
    for d in devs:
        pos = d.get("u_position") or 0
        uhe = max(d.get("u_hoehe", 1), 1)
        for u in range(pos, pos + uhe):
            dev_map[u] = d

    # Slots zeichnen (von oben = hohe HE-Nummer)
    for i, u in enumerate(range(hoehe_u, hoehe_u - show_u, -1)):
        slot_y = y - (i + 1) * u_h_px
        d = dev_map.get(u)

        # U-Nummer (in der Schiene)
        c.setFont("Helvetica", 4.5)
        c.setFillColor(C_TEXT)
        c.drawCentredString(x + rail_w / 2, slot_y + u_h_px / 2 - 1.5, str(u))

        if d and d.get("u_position") == u:
            uhe = max(d.get("u_hoehe", 1), 1)
            dev_h = uhe * u_h_px - 0.8
            col = typ_color(d.get("typ", "sonstige"))

            # Gerät-Block
            c.setFillColor(col)
            c.setStrokeColor(col.clone() if hasattr(col, "clone") else col)
            c.setLineWidth(0)
            c.rect(slot_x + 0.5, slot_y + 0.4, slot_w - 1, dev_h, stroke=0, fill=1)

            # Leichte Highlight-Linie oben
            c.setStrokeColor(colors.white)
            c.setLineWidth(0.5)
            c.line(
                slot_x + 1,
                slot_y + 0.4 + dev_h - 0.5,
                slot_x + slot_w - 1,
                slot_y + 0.4 + dev_h - 0.5,
            )

            # Hostname
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 5.5)
            max_chars = int(slot_w / 3.2)
            label = d["hostname"]
            if len(label) > max_chars:
                label = label[: max_chars - 1] + "…"
            c.drawString(slot_x + 2 * mm, slot_y + dev_h / 2 - 1.5, label)

            # Typ-Badge rechts
            c.setFont("Helvetica", 4.5)
            c.setFillColor(colors.white)
            c.drawRightString(
                slot_x + slot_w - 1.5 * mm,
                slot_y + dev_h / 2 - 1.5,
                typ_label(d.get("typ", "")),
            )

            # Watt-Anzeige (wenn vorhanden)
            watt = d.get("anschlussleistung_watt") or d.get("tdp_watt") or 0
            if watt and uhe >= 2:
                c.setFont("Helvetica", 4)
                c.setFillColor(colors.white)
                c.drawRightString(
                    slot_x + slot_w - 1.5 * mm, slot_y + dev_h / 2 - 5, f"{int(watt)}W"
                )

        elif not d:
            # Leerer Slot — dunkles Panel
            c.setFillColor(colors.HexColor("#1e1e1e"))
            c.rect(
                slot_x + 0.5, slot_y + 0.4, slot_w - 1, u_h_px - 0.8, stroke=0, fill=1
            )
            # Feine Trennlinie
            c.setStrokeColor(colors.HexColor("#333333"))
            c.setLineWidth(0.3)
            c.line(slot_x, slot_y + u_h_px, slot_x + slot_w, slot_y + u_h_px)

    # "Weitere HE" Hinweis
    if hoehe_u > max_u:
        extra = hoehe_u - max_u
        hidden_devs = [d for d in devs if (d.get("u_position") or 0) < hoehe_u - max_u]
        c.setFont("Helvetica", 5.5)
        c.setFillColor(C_MUTED)
        hint = f"… {extra} weitere HE"
        if hidden_devs:
            typen = {}  # type: ignore
            for d in hidden_devs:
                t = typ_label(d.get("typ", "–"))
                typen[t] = typen.get(t, 0) + 1
            detail = ", ".join(f"{v}× {k}" for k, v in typen.items())
            hint += f" (inkl. {detail})"
        c.drawCentredString(x + width / 2, y - rack_h - 3.5 * mm, hint)


class _RackDrawing(Flowable):
    """Reportlab Flowable-Wrapper für die canvas-basierte Rack-Zeichnung."""

    def __init__(self, data: dict, rack: dict, width: float = 60 * mm, max_u: int = 24):
        self._data = data
        self._rack = rack
        self._w = width
        self._max_u = max_u
        show_u = min(rack.get("hoehe_u", 42), max_u)
        extra = 8 * mm if rack.get("hoehe_u", 42) > max_u else 3 * mm
        self._h = show_u * 5.5 * mm + extra

    def wrap(self, aW, aH):
        return self._w, self._h

    def draw(self):
        _draw_rack_front(
            self.canv,
            self._data,
            self._rack,
            x=0,
            y=self._h - 3 * mm,
            width=self._w,
            max_u=self._max_u,
        )


# ── Tabellen ─────────────────────────────────────────────────
def _device_table(data: dict, rack: dict) -> Optional[Table]:
    devs = sorted(
        [d for d in data["devices"] if d.get("rack_id") == rack["id"]],
        key=lambda d: -(d.get("u_position") or 0),
    )
    if not devs:
        return None

    rows = [["U", "Hostname", "Typ", "IP-Adresse", "Phase", "Watt"]]
    for d in devs:
        u0 = d.get("u_position") or 0
        uhe = max(d.get("u_hoehe", 1), 1)
        u_str = f"U{u0}" if uhe == 1 else f"U{u0}–{u0 + uhe - 1}"
        power = d.get("anschlussleistung_watt") or d.get("tdp_watt") or 0
        rows.append(
            [
                u_str,
                d.get("hostname", "–"),
                d.get("typ", "–"),
                d.get("ip_adresse", "–") or "–",
                d.get("phase", "–") or "–",
                f"{int(power)} W",
            ]
        )

    t = Table(
        rows,
        colWidths=[12 * mm, 42 * mm, 22 * mm, 32 * mm, 12 * mm, 16 * mm],
        repeatRows=1,
    )
    t.setStyle(TableStyle(HEADER_STYLE))
    return t


def _port_table(data: dict, rack: dict) -> Optional[Table]:
    dev_ids = {d["id"] for d in data["devices"] if d.get("rack_id") == rack["id"]}
    ports = [p for p in data.get("ports", []) if p.get("device_id") in dev_ids]
    if not ports:
        return None

    rows = [["Gerät", "Port", "Typ", "Verbindung", "Kabel-Nr", "m", "★"]]
    for port in ports:
        src = dev(data, port.get("device_id"))
        cable = get_cable(data, port.get("kabel_id"))
        if not src:
            continue
        if cable:
            is_von = cable.get("von_device_id") == src["id"]
            dst_id = (
                cable.get("nach_device_id") if is_von else cable.get("von_device_id")
            )
            dst_port = cable.get("nach_port" if is_von else "von_port", "–")
            dst = dev(data, dst_id)
            dst_r = _rack(data, dst.get("rack_id")) if dst else None
            cross = dst and dst.get("rack_id") != rack["id"]
            ziel = f"{dst['hostname'] if dst else '?'} / {dst_port}"
            xmark = f"★ {dst_r['name']}" if cross and dst_r else ""
            kabel_nr = cable.get("kabel_nr", "–")
            laenge = str(cable.get("laenge_m", "–"))
        else:
            ziel = xmark = "–"
            kabel_nr = laenge = "–"

        rows.append(
            [
                src.get("hostname", "–"),
                port.get("port_name", "–"),
                port.get("typ", "–"),
                ziel,
                kabel_nr,
                laenge,
                xmark,
            ]
        )

    col_w = [30 * mm, 18 * mm, 14 * mm, 48 * mm, 18 * mm, 8 * mm, 14 * mm]
    cmds = list(HEADER_STYLE)
    for i, row in enumerate(rows[1:], 1):
        if row[-1] and row[-1] != "–":
            cmds += [
                ("TEXTCOLOR", (0, i), (-1, i), C_XRACK),
                ("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"),
            ]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle(cmds))
    return t


def _cable_table(data: dict, rack: dict) -> Optional[Table]:
    dev_ids = {d["id"] for d in data["devices"] if d.get("rack_id") == rack["id"]}
    cables = [
        c
        for c in data.get("cables", [])
        if c.get("von_device_id") in dev_ids or c.get("nach_device_id") in dev_ids
    ]
    if not cables:
        return None

    rows = [["Kabel-Nr", "Typ", "m", "Farbe", "Von", "Port", "Nach", "Port", "★"]]
    for c in cables:
        vd = dev(data, c.get("von_device_id"))
        nd = dev(data, c.get("nach_device_id"))
        vr = _rack(data, vd.get("rack_id") if vd else None)
        nr = _rack(data, nd.get("rack_id") if nd else None)
        cross = vd and nd and vd.get("rack_id") != nd.get("rack_id")
        xmark = ""
        if cross:
            other = nr if (vd and vd.get("rack_id") == rack["id"]) else vr
            xmark = f"★ {other['name']}" if other else "★"
        rows.append(
            [
                c.get("kabel_nr", "–"),
                c.get("typ", "–"),
                str(c.get("laenge_m", "–")),
                c.get("farbe", "–") or "–",
                vd["hostname"] if vd else "–",
                c.get("von_port", "–") or "–",
                nd["hostname"] if nd else "–",
                c.get("nach_port", "–") or "–",
                xmark,
            ]
        )

    col_w = [
        18 * mm,
        16 * mm,
        8 * mm,
        14 * mm,
        26 * mm,
        14 * mm,
        26 * mm,
        14 * mm,
        14 * mm,
    ]
    cmds = list(HEADER_STYLE)
    for i, row in enumerate(rows[1:], 1):
        if row[-1]:
            cmds += [
                ("TEXTCOLOR", (0, i), (-1, i), C_XRACK),
                ("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"),
            ]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle(cmds))
    return t


# ── Page-Template ────────────────────────────────────────────
class _PageTemplate:
    def __init__(self, generated: str):
        self._generated = generated

    def __call__(self, canvas, doc):
        canvas.saveState()
        w, h = A4

        # Header
        canvas.setFillColor(C_HEADER)
        canvas.setStrokeColor(C_HEADER)
        canvas.rect(0, h - 13 * mm, w, 13 * mm, stroke=0, fill=1)

        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(colors.white)
        canvas.drawString(MARGIN, h - 8.5 * mm, "KAiTix")

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#aaaaaa"))
        canvas.drawString(MARGIN + 22 * mm, h - 8.5 * mm, "Rack-Dokumentation")

        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(w - MARGIN, h - 8.5 * mm, f"Erstellt: {self._generated}")

        # Footer
        canvas.setStrokeColor(C_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 12 * mm, w - MARGIN, 12 * mm)

        canvas.setFont("Helvetica", 6)
        canvas.setFillColor(C_MUTED)
        canvas.drawString(MARGIN, 8 * mm, "★ = rack-übergreifende Verbindung")
        canvas.drawRightString(w - MARGIN, 8 * mm, f"Seite {doc.page}")

        canvas.restoreState()


# ── Farblegende ──────────────────────────────────────────────
def _legend_row() -> Table:
    """Kompakte Farblegende für Gerätetypen."""
    items = [
        ("SERVER", C_SERVER),
        ("SWITCH", C_SWITCH),
        ("FW", C_FIREWALL),
        ("STORAGE", C_STORAGE),
        ("PDU", C_PDU),
        ("KVM", C_KVM),
        ("KENTIX", C_KENTIX),
    ]
    cells = []
    for label, col in items:
        cells.append(f'<font color="white"> {label} </font>')

    row_data = [
        [
            Paragraph(
                f'<font color="white">{label}</font>',
                ParagraphStyle(
                    "leg", fontSize=6, leading=8, backColor=col, textColor=colors.white
                ),
            )
            for label, col in items
        ]
    ]
    t = Table(row_data, colWidths=[22 * mm] * len(items))
    t.setStyle(
        TableStyle(
            [("BACKGROUND", (i, 0), (i, 0), col) for i, (_, col) in enumerate(items)]
            + [
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("FONTSIZE", (0, 0), (-1, -1), 6),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    return t


# ── Haupt-Funktion ───────────────────────────────────────────
def generate_rack_pdf(
    data: dict, output_path: str, rack_id: Optional[int] = None
) -> str:
    """
    Generiert Rack-Dokumentation als PDF.

    Args:
        data:        Kanonisches Dict mit racks, devices, ports, cables.
        output_path: Ausgabepfad für die PDF-Datei.
        rack_id:     Wenn angegeben, nur diesen Rack exportieren.

    Returns:
        output_path
    """
    generated = datetime.now().strftime("%d.%m.%Y %H:%M")
    styles = _make_styles()

    racks = data["racks"]
    if rack_id is not None:
        racks = [r for r in racks if r["id"] == rack_id]

    story = []

    # ── Deckblatt ────────────────────────────────────────────
    story.append(Spacer(1, 35 * mm))
    story.append(Paragraph("Rack-Dokumentation", styles["title"]))
    story.append(
        Paragraph(
            f"Technische Bestandsaufnahme · Erstellt: {generated}",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(_legend_row())
    story.append(Spacer(1, 6 * mm))

    # Übersichtstabelle
    summary_rows = [
        ["Rack", "Standort", "HE", "Geräte", "Last L1", "Last L2", "Last L3"]
    ]
    for r in racks:
        devs = [d for d in data["devices"] if d.get("rack_id") == r["id"]]
        ph = phase_load(data, r["id"])
        summary_rows.append(
            [
                r["name"],
                r.get("standort", "–"),
                str(r.get("hoehe_u", 42)),
                str(len(devs)),
                f"{ph['L1'] / 1000:.2f} kW",
                f"{ph['L2'] / 1000:.2f} kW",
                f"{ph['L3'] / 1000:.2f} kW",
            ]
        )

    st = Table(
        summary_rows,
        colWidths=[28 * mm, 50 * mm, 12 * mm, 15 * mm, 22 * mm, 22 * mm, 22 * mm],
    )
    st.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_STRIPE]),
                ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(st)

    # ── Pro Rack ─────────────────────────────────────────────
    for rack in racks:
        story.append(PageBreak())
        ph = phase_load(data, rack["id"])
        devs = [d for d in data["devices"] if d.get("rack_id") == rack["id"]]

        story.append(Paragraph(rack["name"], styles["title"]))
        story.append(
            Paragraph(
                f"{rack.get('standort', '–')}  ·  {rack.get('hoehe_u', 42)} HE  ·  "
                f"{len(devs)} Geräte  ·  "
                f"L1: {ph['L1'] / 1000:.2f} kW  "
                f"L2: {ph['L2'] / 1000:.2f} kW  "
                f"L3: {ph['L3'] / 1000:.2f} kW",
                styles["subtitle"],
            )
        )

        dev_t = _device_table(data, rack)
        drawing = _RackDrawing(data, rack, width=62 * mm, max_u=24)

        if dev_t:
            combined = Table(
                [[drawing, dev_t]],
                colWidths=[65 * mm, PAGE_W - 2 * MARGIN - 67 * mm],
            )
            combined.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            story.append(combined)
        else:
            story.append(drawing)
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph("Keine Geräte eingebaut.", styles["cell_m"]))

        port_t = _port_table(data, rack)
        if port_t:
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("Portbelegung & Verbindungen", styles["h2"]))
            story.append(port_t)

        cable_t = _cable_table(data, rack)
        if cable_t:
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("Kabelliste", styles["h2"]))
            story.append(cable_t)

    # ── PDF bauen ─────────────────────────────────────────────
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title="Rack-Dokumentation",
        author="KAiTix",
    )
    template = _PageTemplate(generated)
    doc.build(story, onFirstPage=template, onLaterPages=template)
    return output_path
