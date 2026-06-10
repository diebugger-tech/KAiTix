import io

from ._helpers import (
    _dev_map,
    _rack_map,
    _phase_loads,
    _rack_devices,
    _ifaces_for_device,
    _cable_for_iface,
    _pdu_outlets,
    _make_ods_mkrow,
)


def _ods(data: dict) -> bytes:
    from odf.opendocument import OpenDocumentSpreadsheet  # type: ignore
    from odf.table import Table  # type: ignore

    doc = OpenDocumentSpreadsheet()
    mkrow = _make_ods_mkrow()
    dm = _dev_map(data)
    rm = _rack_map(data)

    def add_sheet(name, header, rows_fn):
        t = Table(name=name)
        t.addElement(mkrow(header))
        for row in rows_fn():
            t.addElement(mkrow(row))
        doc.spreadsheet.addElement(t)

    add_sheet(
        "Übersicht",
        ["Rack", "Standort", "HE", "Geräte", "L1 kW", "L2 kW", "L3 kW"],
        lambda: [
            [
                r["name"],
                r["standort"],
                r["hoehe_u"],
                len(_rack_devices(data, r["id"])),
                round(_phase_loads(data, r["id"])["L1"] / 1000, 2),
                round(_phase_loads(data, r["id"])["L2"] / 1000, 2),
                round(_phase_loads(data, r["id"])["L3"] / 1000, 2),
            ]
            for r in data["racks"]
        ],
    )

    def rack_rows():
        rows = []
        for r in data["racks"]:
            for d in _rack_devices(data, r["id"]):
                rows.append(
                    [
                        r["name"],
                        r["standort"],
                        d.get("u_pos", "–"),
                        (d.get("u_pos") or 0) + (d.get("u_h") or 1) - 1,
                        d["hostname"],
                        d["typ"],
                        d.get("ip", "–"),
                        d.get("phase", "–"),
                        d.get("watt", "–"),
                        d.get("hersteller", "–"),
                        d.get("modell", "–"),
                    ]
                )
        return rows

    add_sheet(
        "Rack-Belegung",
        [
            "Rack",
            "Standort",
            "U-von",
            "U-bis",
            "Hostname",
            "Typ",
            "IP",
            "Phase",
            "Anschlussleistung (W)",
            "Hersteller",
            "Modell",
        ],
        rack_rows,
    )

    def iface_rows():
        rows = []
        for r in data["racks"]:
            for d in _rack_devices(data, r["id"]):
                for iface in _ifaces_for_device(data, d["id"]):
                    cable = _cable_for_iface(data, iface.get("kabel_id"))
                    if cable:
                        is_von = cable.get("von_dev") == d["id"]
                        dst_id = (
                            cable.get("nach_dev") if is_von else cable.get("von_dev")
                        )
                        dst_dev = dm.get(dst_id)
                        dst_port = cable.get("nach_port" if is_von else "von_port", "–")
                        cross = (
                            "★"
                            if (dst_dev and dst_dev.get("rack_id") != r["id"])
                            else ""
                        )
                        rows.append(
                            [
                                r["name"],
                                d["hostname"],
                                iface.get("port", "–"),
                                iface.get("typ", "–"),
                                iface.get("mac", "–"),
                                dst_dev["hostname"] if dst_dev else "–",
                                dst_port,
                                cable["nr"],
                                cable["typ"],
                                cable["laenge"],
                                cable.get("farbe", "–"),
                                cross,
                            ]
                        )
                    else:
                        rows.append(
                            [
                                r["name"],
                                d["hostname"],
                                iface.get("port", "–"),
                                iface.get("typ", "–"),
                                iface.get("mac", "–"),
                                "–",
                                "–",
                                "–",
                                "–",
                                "–",
                                "–",
                                "",
                            ]
                        )
        return rows

    add_sheet(
        "Ports & Interfaces",
        [
            "Rack",
            "Gerät",
            "Port",
            "Typ",
            "MAC",
            "Verbunden mit",
            "Ziel-Port",
            "Kabel-Nr",
            "Kabel-Typ",
            "m",
            "Farbe",
            "★",
        ],
        iface_rows,
    )

    def cable_rows():
        rows = []
        for c in sorted(data.get("cables", []), key=lambda x: x["nr"]):
            vd = dm.get(c.get("von_dev"))
            nd = dm.get(c.get("nach_dev"))
            vr = rm.get(vd.get("rack_id") if vd else None, {}).get("name", "–")
            nr = rm.get(nd.get("rack_id") if nd else None, {}).get("name", "–")
            cross = (
                "★" if (vd and nd and vd.get("rack_id") != nd.get("rack_id")) else ""
            )
            rows.append(
                [
                    c["nr"],
                    c["typ"],
                    c["laenge"],
                    c.get("farbe", "–"),
                    vd["hostname"] if vd else "–",
                    vr,
                    c.get("von_port", "–"),
                    nd["hostname"] if nd else "–",
                    nr,
                    c.get("nach_port", "–"),
                    cross,
                ]
            )
        return rows

    add_sheet(
        "Kabelliste",
        [
            "Kabel-Nr",
            "Typ",
            "m",
            "Farbe",
            "Von-Gerät",
            "Von-Rack",
            "Von-Port",
            "Nach-Gerät",
            "Nach-Rack",
            "Nach-Port",
            "★",
        ],
        cable_rows,
    )

    def pdu_rows():
        rows = []
        for pdu in [d for d in data["devices"] if d.get("typ") == "pdu"]:
            rn = rm.get(pdu.get("rack_id"), {}).get("name", "–")
            for o in _pdu_outlets(data, pdu["id"]):
                dev = dm.get(o.get("connected_device_id"))
                rows.append(
                    [
                        pdu["hostname"],
                        rn,
                        o.get("outlet_name", "–"),
                        o.get("phase", "–"),
                        o.get("steckdosentyp", "–"),
                        o.get("max_watt", "–"),
                        dev["hostname"] if dev else "frei",
                        o.get("connected_port", "–"),
                        "JA" if o.get("schaltbar") else "NEIN",
                    ]
                )
        return rows

    add_sheet(
        "PDU-Belegung",
        [
            "PDU",
            "Rack",
            "Steckdose",
            "Phase",
            "Typ",
            "Max W",
            "Gerät",
            "Port",
            "Schaltbar",
        ],
        pdu_rows,
    )

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
