import io
import zipfile

from ._helpers import (
    _dev_map,
    _rack_map,
    _phase_loads,
    _rack_devices,
    _ifaces_for_device,
    _cable_for_iface,
    _pdu_outlets,
    _to_csv,
    _ts,
)


def _csv_zip(data: dict) -> bytes:
    dm = _dev_map(data)
    rm = _rack_map(data)

    ov = [
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
    ]

    dev_rows = []
    for r in data["racks"]:
        for d in _rack_devices(data, r["id"]):
            dev_rows.append(
                [
                    r["name"],
                    d.get("u_pos", ""),
                    d.get("u_h", 1),
                    d["hostname"],
                    d["typ"],
                    d.get("ip", ""),
                    d.get("phase", ""),
                    d.get("watt", ""),
                    d.get("hersteller", ""),
                    d.get("modell", ""),
                ]
            )

    port_rows = []
    for r in data["racks"]:
        for d in _rack_devices(data, r["id"]):
            for iface in _ifaces_for_device(data, d["id"]):
                cable = _cable_for_iface(data, iface.get("kabel_id"))
                if cable:
                    is_von = cable.get("von_dev") == d["id"]
                    dst_id = cable.get("nach_dev") if is_von else cable.get("von_dev")
                    dst_dev = dm.get(dst_id)
                    dst_port = cable.get("nach_port" if is_von else "von_port", "")
                    cross = (
                        "JA" if (dst_dev and dst_dev.get("rack_id") != r["id"]) else ""
                    )
                    port_rows.append(
                        [
                            r["name"],
                            d["hostname"],
                            iface.get("port", ""),
                            iface.get("typ", ""),
                            iface.get("mac", ""),
                            dst_dev["hostname"] if dst_dev else "",
                            dst_port,
                            cable["nr"],
                            cable["typ"],
                            cable["laenge"],
                            cable.get("farbe", ""),
                            cross,
                        ]
                    )
                else:
                    port_rows.append(
                        [
                            r["name"],
                            d["hostname"],
                            iface.get("port", ""),
                            iface.get("typ", ""),
                            iface.get("mac", ""),
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                        ]
                    )

    cable_rows = []
    for c in sorted(data.get("cables", []), key=lambda x: x["nr"]):
        vd = dm.get(c.get("von_dev"))
        nd = dm.get(c.get("nach_dev"))
        vr = rm.get(vd.get("rack_id") if vd else None, {}).get("name", "")
        nr = rm.get(nd.get("rack_id") if nd else None, {}).get("name", "")
        cross = "JA" if (vd and nd and vd.get("rack_id") != nd.get("rack_id")) else ""
        cable_rows.append(
            [
                c["nr"],
                c["typ"],
                c["laenge"],
                c.get("farbe", ""),
                vd["hostname"] if vd else "",
                vr,
                c.get("von_port", ""),
                nd["hostname"] if nd else "",
                nr,
                c.get("nach_port", ""),
                c.get("verlegt_am", ""),
                c.get("verlegt_von", ""),
                cross,
            ]
        )

    pdu_rows = []
    for pdu in [d for d in data["devices"] if d.get("typ") == "pdu"]:
        rn = rm.get(pdu.get("rack_id"), {}).get("name", "")
        for o in _pdu_outlets(data, pdu["id"]):
            dev = dm.get(o.get("connected_device_id"))
            pdu_rows.append(
                [
                    pdu["hostname"],
                    rn,
                    o.get("outlet_name", ""),
                    o.get("phase", ""),
                    o.get("steckdosentyp", ""),
                    o.get("max_watt", ""),
                    dev["hostname"] if dev else "frei",
                    o.get("connected_port", ""),
                    "JA" if o.get("schaltbar") else "NEIN",
                ]
            )

    stamp = _ts()
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            f"kaitix_{stamp}_uebersicht.csv",
            _to_csv(
                ["rack", "standort", "he", "geraete", "l1_kw", "l2_kw", "l3_kw"], ov
            ),
        )
        zf.writestr(
            f"kaitix_{stamp}_geraete.csv",
            _to_csv(
                [
                    "rack",
                    "u_position",
                    "u_hoehe",
                    "hostname",
                    "typ",
                    "ip",
                    "phase",
                    "anschlussleistung_w",
                    "hersteller",
                    "modell",
                ],
                dev_rows,
            ),
        )
        zf.writestr(
            f"kaitix_{stamp}_ports.csv",
            _to_csv(
                [
                    "rack",
                    "geraet",
                    "port",
                    "typ",
                    "mac",
                    "ziel_geraet",
                    "ziel_port",
                    "kabel_nr",
                    "kabel_typ",
                    "laenge_m",
                    "farbe",
                    "rack_uebergreifend",
                ],
                port_rows,
            ),
        )
        zf.writestr(
            f"kaitix_{stamp}_kabel.csv",
            _to_csv(
                [
                    "kabel_nr",
                    "typ",
                    "laenge_m",
                    "farbe",
                    "von_geraet",
                    "von_rack",
                    "von_port",
                    "nach_geraet",
                    "nach_rack",
                    "nach_port",
                    "verlegt_am",
                    "verlegt_von",
                    "rack_uebergreifend",
                ],
                cable_rows,
            ),
        )
        zf.writestr(
            f"kaitix_{stamp}_pdu.csv",
            _to_csv(
                [
                    "pdu",
                    "rack",
                    "steckdose",
                    "phase",
                    "steckdosentyp",
                    "max_watt",
                    "geraet",
                    "port",
                    "schaltbar",
                ],
                pdu_rows,
            ),
        )
    return zip_buf.getvalue()
