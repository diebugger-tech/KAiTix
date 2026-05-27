from ._helpers import Format, Sheet, _ts
from .full_xlsx import _xlsx
from .full_ods import _ods
from .full_csv import _csv_zip
from .racks import _rack_xlsx, _rack_ods, _rack_csv
from .interfaces import _iface_xlsx, _iface_ods, _iface_csv
from .pdus import _pdu_xlsx, _pdu_ods, _pdu_csv
from .cables import _cable_xlsx, _cable_ods, _cable_csv

_MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_MIME_ODS = "application/vnd.oasis.opendocument.spreadsheet"


def build_export(data: dict, fmt: Format) -> tuple[bytes, str, str]:
    ts = _ts()
    if fmt == "xlsx":
        return (_xlsx(data), _MIME_XLSX, f"kaitix_dokumentation_{ts}.xlsx")
    if fmt == "ods":
        return (_ods(data), _MIME_ODS, f"kaitix_dokumentation_{ts}.ods")
    return (_csv_zip(data), "application/zip", f"kaitix_dokumentation_{ts}.zip")


def build_single_export(
    data: dict, sheet: Sheet, fmt: Format
) -> tuple[bytes, str, str]:
    ts = _ts()
    builders: dict[Sheet, dict[Format, tuple]] = {
        "racks": {
            "xlsx": (_rack_xlsx, _MIME_XLSX, f"kaitix_rack_inventar_{ts}.xlsx"),
            "ods": (_rack_ods, _MIME_ODS, f"kaitix_rack_inventar_{ts}.ods"),
            "csv": (_rack_csv, "text/csv", f"kaitix_rack_inventar_{ts}.csv"),
        },
        "interfaces": {
            "xlsx": (_iface_xlsx, _MIME_XLSX, f"kaitix_ports_interfaces_{ts}.xlsx"),
            "ods": (_iface_ods, _MIME_ODS, f"kaitix_ports_interfaces_{ts}.ods"),
            "csv": (_iface_csv, "text/csv", f"kaitix_ports_interfaces_{ts}.csv"),
        },
        "pdus": {
            "xlsx": (_pdu_xlsx, _MIME_XLSX, f"kaitix_pdu_belegung_{ts}.xlsx"),
            "ods": (_pdu_ods, _MIME_ODS, f"kaitix_pdu_belegung_{ts}.ods"),
            "csv": (_pdu_csv, "text/csv", f"kaitix_pdu_belegung_{ts}.csv"),
        },
        "cables": {
            "xlsx": (_cable_xlsx, _MIME_XLSX, f"kaitix_kabelliste_{ts}.xlsx"),
            "ods": (_cable_ods, _MIME_ODS, f"kaitix_kabelliste_{ts}.ods"),
            "csv": (_cable_csv, "text/csv", f"kaitix_kabelliste_{ts}.csv"),
        },
    }
    builder_fn, mime, fname = builders[sheet][fmt]
    return (builder_fn(data), mime, fname)
