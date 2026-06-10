from datetime import datetime

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
    C_KENTIX,
    C_BORDER,
    C_RAIL,
    C_TEXT,
    C_MUTED,
    C_HEADER,
    C_STRIPE,
    KATEGORIE_COLOR,
    PAGE_W,
    MARGIN,
)

C_POWER_L1 = colors.HexColor("#D6EAF8")
C_POWER_L2 = colors.HexColor("#D5F5E3")
C_POWER_L3 = colors.HexColor("#FDEBD0")
C_CAT = colors.HexColor("#3b82f6")
C_LWL = colors.HexColor("#d946ef")
C_SFP = colors.HexColor("#06b6d4")
C_STROM = colors.HexColor("#ef4444")


class _RackElevation(Flowable):
    def __init__(self, data: dict, rack: dict, width: float):
        Flowable.__init__(self)
        self.data = data
        self.rack = rack
        self.width = width
        self.hoehe_u = rack.get("hoehe_u", 42)
        self.u_h_px = 4.5 * mm
        self.rack_h = self.hoehe_u * self.u_h_px
        self.height = self.rack_h + 20 * mm

    def _rack_devices(self):
        return sorted(
            [d for d in self.data["devices"] if d.get("rack_id") == self.rack["id"]],
            key=lambda d: -(d.get("u_position") or 0),
        )

    def draw(self):
        c = self.canv
        x = 10 * mm
        y = self.height - 8 * mm
        w = self.width - 20 * mm
        u_h = self.u_h_px
        rail_w = 4 * mm
        slot_x = x + rail_w
        slot_w = w - 2 * rail_w - 2 * mm

        c.setStrokeColor(colors.HexColor("#666666"))
        c.setLineWidth(1.2)
        c.setFillColor(colors.HexColor("#2a2a2a"))
        c.rect(x, y - self.rack_h, w - 0.5 * mm, self.rack_h, stroke=1, fill=1)

        c.setFillColor(C_RAIL)
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.3)
        c.rect(
            x + 0.5,
            y - self.rack_h + 0.5,
            rail_w - 1,
            self.rack_h - 1,
            stroke=1,
            fill=1,
        )
        c.rect(
            x + w - rail_w - 1,
            y - self.rack_h + 0.5,
            rail_w - 1,
            self.rack_h - 1,
            stroke=1,
            fill=1,
        )

        for u in range(1, self.hoehe_u + 1):
            uy = y - (self.hoehe_u - u + 1) * u_h
            if u % 2 == 0:
                c.setFillColor(colors.HexColor("#333333"))
                c.rect(slot_x, uy, slot_w, u_h, stroke=0, fill=1)
            if u % 5 == 0 or u == 1:
                c.setStrokeColor(C_BORDER)
                c.setLineWidth(0.2)
                c.line(x, uy, x + w, uy)
                c.setFillColor(C_MUTED)
                c.setFont("Helvetica", 5)
                c.drawString(x + 0.5, uy + 0.5, str(u))

        for dev in self._rack_devices():
            u_pos = dev.get("u_position")
            u_hoehe = dev.get("u_hoehe") or 1
            if u_pos is None:
                continue
            dy = y - (self.hoehe_u - u_pos + 1) * u_h
            dh = max(u_hoehe * u_h - 0.5, u_h)
            color = KATEGORIE_COLOR.get(dev.get("typ", ""), C_KENTIX)
            c.setFillColor(color)
            c.roundRect(
                slot_x + 0.3,
                dy + 0.3,
                slot_w - 0.6,
                dh - 0.6,
                0.8 * mm,
                stroke=0,
                fill=1,
            )
            c.setFillColor(colors.white)
            c.setFont("Helvetica", 5.5)
            label = dev.get("hostname", "")
            c.drawString(slot_x + 1.5 * mm, dy + dh / 2 - 2, label)

    def wrap(self, avail_width, avail_height):
        return (self.width, self.height)


def _make_styles() -> dict:
    base = getSampleStyleSheet()

    def s(name: str, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return {
        "title": s("tp_title", fontSize=16, textColor=C_TEXT, leading=20, spaceAfter=2),
        "subtitle": s(
            "tp_sub", fontSize=9, textColor=C_MUTED, leading=12, spaceAfter=8
        ),
        "h2": s(
            "tp_h2",
            fontSize=11,
            textColor=C_TEXT,
            leading=14,
            spaceBefore=10,
            spaceAfter=4,
            fontName="Helvetica-Bold",
        ),
        "cell": s("tp_cell", fontSize=7.5, textColor=C_TEXT, leading=10),
        "cell_bold": s(
            "tp_cell_b",
            fontSize=7.5,
            textColor=C_TEXT,
            leading=10,
            fontName="Helvetica-Bold",
        ),
        "cell_m": s("tp_cell_m", fontSize=7.5, textColor=C_MUTED, leading=10),
        "footer": s(
            "tp_footer", fontSize=7, textColor=C_MUTED, leading=9, alignment=TA_CENTER
        ),
    }


def _build_nav(data: dict) -> dict:
    racks = {r["id"]: r for r in data["racks"]}
    devices = {d["id"]: d for d in data["devices"]}
    return {"racks": racks, "devices": devices}


def _edge_color(edge: dict):
    if edge.get("edge_type") == "power":
        phase = edge.get("phase")
        if phase == "L1":
            return C_POWER_L1
        if phase == "L2":
            return C_POWER_L2
        if phase == "L3":
            return C_POWER_L3
        return C_STROM
    t = (edge.get("typ") or "").lower()
    if "lc" in t or "sc" in t or "lwl" in t:
        return C_LWL
    if t.startswith("cat"):
        return C_CAT
    if t == "dac":
        return C_MUTED
    if "sfp" in t:
        return C_SFP
    if t.startswith("strom") or t.startswith("cee"):
        return C_STROM
    return C_MUTED


def _build_title_page(story, styles: dict, data: dict):
    ts = datetime.now().strftime("%d.%m.%Y %H:%M")
    edges = data.get("edges", [])
    cables_only = [e for e in edges if e.get("edge_type") != "power"]
    power = [e for e in edges if e.get("edge_type") == "power"]
    cross = [e for e in edges if e.get("cross_rack")]
    typ_count: dict = {}
    for d in data["devices"]:
        t = d.get("typ", "sonstige")
        typ_count[t] = typ_count.get(t, 0) + 1
    typ_list = ", ".join(f"{c}× {t}" for t, c in sorted(typ_count.items()))

    story.append(Paragraph("KAiTix — Topologie-Dokumentation", styles["title"]))
    story.append(Paragraph(f"Erstellt: {ts}", styles["subtitle"]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Übersicht", styles["h2"]))

    summary = [
        ["Racks", str(len(data.get("racks", [])))],
        ["Geräte", str(len(data.get("devices", [])))],
        ["Davon", typ_list],
        ["Kabel-Verbindungen", str(len(cables_only))],
        ["Strom-Verbindungen (PDU)", str(len(power))],
        ["Rack-übergreifend", str(len(cross))],
    ]
    t = Table(summary, colWidths=[50 * mm, 100 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 14),
                ("TEXTCOLOR", (0, 0), (-1, -1), C_TEXT),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, C_STRIPE]),
                ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t)

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Legende", styles["h2"]))
    legend = [
        ["Farbe", "Bedeutung"],
        [_swatch(C_SERVER), "Server"],
        [_swatch(C_SWITCH), "Switch"],
        [_swatch(C_FIREWALL), "Firewall"],
        [_swatch(C_STORAGE), "Storage"],
        [_swatch(C_PDU), "PDU"],
    ]
    lt = Table(legend, colWidths=[10 * mm, 50 * mm])
    lt.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, -1), C_TEXT),
                ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(lt)
    story.append(PageBreak())


def _swatch(color: colors.Color) -> str:
    return f'<font color="{color.hexval()}">■</font>'


def _build_rack_pages(story, styles: dict, data: dict, content_w: float):
    for rack in data.get("racks", []):
        rack_devices = [d for d in data["devices"] if d.get("rack_id") == rack["id"]]

        story.append(
            Paragraph(
                f"Rack: {rack['name']} ({rack.get('standort', '–')}) — {rack.get('hoehe_u', 42)} HE",
                styles["h2"],
            )
        )
        story.append(Spacer(1, 2 * mm))

        elev = _RackElevation(data, rack, content_w)
        story.append(elev)
        story.append(Spacer(1, 4 * mm))

        phase_data = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
        for d in rack_devices:
            ph = d.get("phase")
            if ph in phase_data:
                phase_data[ph] += float(
                    d.get("anschlussleistung_watt") or d.get("tdp_watt") or 0
                )

        dev_rows = [
            [
                Paragraph("U", styles["cell_bold"]),
                Paragraph("Hostname", styles["cell_bold"]),
                Paragraph("Typ", styles["cell_bold"]),
                Paragraph("Phase", styles["cell_bold"]),
                Paragraph("Watt", styles["cell_bold"]),
                Paragraph("Hersteller", styles["cell_bold"]),
                Paragraph("Modell", styles["cell_bold"]),
            ]
        ]
        for d in sorted(rack_devices, key=lambda x: -(x.get("u_position") or 9999)):
            u_pos = d.get("u_position")
            u_bis = (u_pos or 0) + (d.get("u_hoehe") or 1) - 1
            u_label = f"{u_pos}" if u_pos else "0U"
            if u_pos and d.get("u_hoehe", 1) > 1:
                u_label = f"{u_pos}–{u_bis}"
            dev_rows.append(
                [
                    Paragraph(u_label, styles["cell"]),
                    Paragraph(d.get("hostname", "–"), styles["cell"]),
                    Paragraph(d.get("typ", "–"), styles["cell"]),
                    Paragraph(d.get("phase") or "–", styles["cell"]),
                    Paragraph(
                        str(
                            int(
                                d.get("tdp_watt")
                                or d.get("anschlussleistung_watt")
                                or 0
                            )
                        ),
                        styles["cell"],
                    ),
                    Paragraph(d.get("hersteller") or "–", styles["cell"]),
                    Paragraph(d.get("modell") or "–", styles["cell"]),
                ]
            )

        if len(dev_rows) > 1:
            dt = Table(
                dev_rows,
                colWidths=[
                    10 * mm,
                    35 * mm,
                    16 * mm,
                    12 * mm,
                    14 * mm,
                    22 * mm,
                    25 * mm,
                ],
                repeatRows=1,
            )
            dt.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_STRIPE]),
                        ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.append(dt)

        phase_total = sum(phase_data.values())
        if phase_total > 0:
            story.append(Spacer(1, 2 * mm))
            story.append(
                Paragraph(
                    f"Phasenlast: L1={phase_data['L1']:.0f}W  L2={phase_data['L2']:.0f}W  "
                    f"L3={phase_data['L3']:.0f}W  Gesamt={phase_total:.0f}W",
                    styles["cell"],
                )
            )

        story.append(PageBreak())


def _build_connection_pages(story, styles: dict, data: dict):
    nav = _build_nav(data)
    edges = data.get("edges", [])

    story.append(Paragraph("Verbindungen", styles["h2"]))
    story.append(Spacer(1, 2 * mm))

    edge_rows = [
        [
            Paragraph("Kabel-Nr", styles["cell_bold"]),
            Paragraph("Typ", styles["cell_bold"]),
            Paragraph("Von", styles["cell_bold"]),
            Paragraph("Port", styles["cell_bold"]),
            Paragraph("Nach", styles["cell_bold"]),
            Paragraph("Port", styles["cell_bold"]),
            Paragraph("★", styles["cell_bold"]),
        ]
    ]

    for edge in sorted(edges, key=lambda e: e.get("kabel_nr", "")):
        is_power = edge.get("edge_type") == "power"
        vd = nav["devices"].get(edge.get("von_device_id"))
        nd = nav["devices"].get(edge.get("nach_device_id"))
        von_name = vd["hostname"] if vd else f"#{edge.get('von_device_id')}"
        nach_name = nd["hostname"] if nd else f"#{edge.get('nach_device_id')}"
        cross = "★" if edge.get("cross_rack") else ""
        typ_label = edge.get("typ", "–")
        if is_power:
            ph = edge.get("phase", "")
            if ph:
                typ_label += f" ({ph})"
        edge_rows.append(
            [
                Paragraph(edge.get("kabel_nr", "–"), styles["cell"]),
                Paragraph(typ_label, styles["cell"]),
                Paragraph(von_name, styles["cell"]),
                Paragraph(edge.get("von_port") or "–", styles["cell"]),
                Paragraph(nach_name, styles["cell"]),
                Paragraph(edge.get("nach_port") or "–", styles["cell"]),
                Paragraph(cross, styles["cell"]),
            ]
        )

    if len(edge_rows) > 1:
        et = Table(
            edge_rows,
            colWidths=[22 * mm, 26 * mm, 30 * mm, 20 * mm, 30 * mm, 20 * mm, 8 * mm],
            repeatRows=1,
        )
        et.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_STRIPE]),
                    ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(et)

    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("★ = Rack-übergreifend", styles["cell_m"]))


def generate_topology_pdf(data: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=20 * mm,
        bottomMargin=15 * mm,
    )
    styles = _make_styles()
    content_w = PAGE_W - 2 * MARGIN
    story = []  # type: ignore

    _build_title_page(story, styles, data)
    _build_rack_pages(story, styles, data, content_w)
    _build_connection_pages(story, styles, data)

    def add_page_number(canvas_obj: rl_canvas.Canvas, _doc):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.setFillColor(C_MUTED)
        page_num = canvas_obj.getPageNumber()
        text = f"KAiTix Topologie — Seite {page_num}"
        canvas_obj.drawCentredString(PAGE_W / 2, 10 * mm, text)
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
