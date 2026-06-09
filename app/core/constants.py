from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm


C_SERVER = colors.HexColor("#185FA5")
C_SWITCH = colors.HexColor("#0F6E56")
C_FIREWALL = colors.HexColor("#993C1D")
C_STORAGE = colors.HexColor("#854F0B")
C_PDU = colors.HexColor("#3B6D11")
C_KVM = colors.HexColor("#534AB7")
C_KENTIX = colors.HexColor("#5F5E5A")
C_EMPTY = colors.HexColor("#ECECEC")
C_BORDER = colors.HexColor("#B4B2A9")
C_RAIL = colors.HexColor("#D0CEC8")
C_TEXT = colors.HexColor("#2C2C2A")
C_MUTED = colors.HexColor("#888780")
C_XRACK = colors.HexColor("#D85A30")
C_HEADER = colors.HexColor("#1a1a1a")
C_STRIPE = colors.HexColor("#F7F6F2")

KATEGORIE_COLOR = {
    "server": C_SERVER,
    "switch": C_SWITCH,
    "firewall": C_FIREWALL,
    "storage": C_STORAGE,
    "pdu": C_PDU,
    "kvm": C_KVM,
    "kentix_raconode": C_KENTIX,
    "kentix_doormaster": C_KENTIX,
    "kentix_multisensor": C_KENTIX,
    "patchpanel": C_SWITCH,
    "sonstige": C_KENTIX,
}

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm

HEADER_STYLE = [
    ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
    ("LEADING", (0, 0), (-1, -1), 10),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_STRIPE]),
    ("GRID", (0, 0), (-1, -1), 0.3, C_BORDER),
    ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ("TOPPADDING", (0, 0), (-1, -1), 2),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
]


def dev(data: dict, did: Optional[int]):
    if did is None:
        return None
    return next((d for d in data["devices"] if d["id"] == did), None)


def rack(data: dict, rid: Optional[int]):
    if rid is None:
        return None
    return next((r for r in data["racks"] if r["id"] == rid), None)


def cable(data: dict, cid: Optional[int]):
    if cid is None:
        return None
    return next((c for c in data["cables"] if c["id"] == cid), None)


def typ_color(typ: str) -> colors.Color:
    return KATEGORIE_COLOR.get(typ, C_KENTIX)


def typ_label(typ: str) -> str:
    return {
        "server": "SRV",
        "switch": "SW",
        "firewall": "FW",
        "storage": "STOR",
        "pdu": "PDU",
        "kvm": "KVM",
        "kentix_raconode": "KTIX",
        "kentix_doormaster": "KTIX",
        "kentix_multisensor": "KTIX",
        "patchpanel": "PP",
        "sonstige": "–",
    }.get(typ, typ.upper()[:4])


def phase_load(data: dict, rack_id: int) -> dict:
    phasen: dict = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
    for d in data["devices"]:
        if d.get("rack_id") == rack_id and d.get("phase") in phasen:
            power = d.get("anschlussleistung_watt") or d.get("tdp_watt") or 0
            phasen[d["phase"]] += float(power)
    return phasen
