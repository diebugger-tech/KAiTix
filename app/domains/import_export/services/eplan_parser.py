import csv
import io
import re
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Rack, Device, Cable


class EplanParser:
    @staticmethod
    def detect_delimiter(header_line: str) -> str:
        """
        Detects delimiter based on common separators.
        """
        delimiters = [";", ",", "\t", "|"]
        counts = {d: header_line.count(d) for d in delimiters}
        # Find the delimiter with the highest count, defaulting to ';'
        best_delim = max(counts, key=counts.get)  # type: ignore
        return best_delim if counts[best_delim] > 0 else ";"

    @classmethod
    def parse_csv(
        cls, file_content: bytes, mapping: Dict[str, str], encoding: str = "utf-8"
    ) -> List[Dict[str, Any]]:
        """
        Parses CSV byte content using mapping dict mapping fields to CSV header names (or column indices).
        Supported target fields in mapping:
          - cable_number (BMK/Kabelnummer)
          - cable_type (Kabeltyp, e.g. Cat6, LWL)
          - source_rack
          - source_device
          - source_port
          - target_rack
          - target_device
          - target_port
          - length (float)
          - color (Farbe)
        """
        # Decode content, try fallback to latin-1/iso-8859-1 if utf-8 fails
        try:
            decoded = file_content.decode(encoding)
        except UnicodeDecodeError:
            decoded = file_content.decode("latin-1")

        lines = [line.strip() for line in decoded.splitlines() if line.strip()]
        if not lines:
            return []

        delimiter = cls.detect_delimiter(lines[0])

        # Parse using csv.reader
        reader = csv.reader(io.StringIO(decoded), delimiter=delimiter)
        try:
            headers = next(reader)
        except StopIteration:
            return []

        headers = [h.strip() for h in headers]

        # Precompute mapping from field to CSV column index
        field_to_idx = {}
        for target_field, mapped_col in mapping.items():
            if not mapped_col:
                continue
            # Try to match by header name
            try:
                # Direct match or case-insensitive match
                idx = -1
                for i, h in enumerate(headers):
                    if h.lower() == str(mapped_col).lower():
                        idx = i
                        break
                if idx != -1:
                    field_to_idx[target_field] = idx
                else:
                    # Try interpreting as integer index
                    idx = int(mapped_col)
                    if 0 <= idx < len(headers):
                        field_to_idx[target_field] = idx
            except ValueError:
                # Column not found / not an integer index
                pass

        parsed_records = []
        for row_idx, row in enumerate(reader, start=2):
            if not row or all(not cell.strip() for cell in row):
                continue

            record = {"row_index": row_idx}
            for target_field, col_idx in field_to_idx.items():
                if col_idx < len(row):
                    val = row[col_idx].strip()
                    # Process numeric fields
                    if target_field == "length":
                        # Strip unit characters (like 'm', 'meter') and swap comma to dot
                        val_cleaned = re.sub(r"[^\d,\.]", "", val).replace(",", ".")
                        try:
                            record[target_field] = (
                                float(val_cleaned) if val_cleaned else None  # type: ignore
                            )
                        except ValueError:
                            record[target_field] = None  # type: ignore
                    else:
                        record[target_field] = val if val else None  # type: ignore
                else:
                    record[target_field] = None  # type: ignore

            # Skip records that have absolutely no cable number or connections
            if (
                record.get("cable_number")
                or record.get("source_device")
                or record.get("target_device")
            ):
                parsed_records.append(record)

        return parsed_records

    @classmethod
    async def preview_import(
        cls, parsed_data: List[Dict[str, Any]], db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Validates parsed records against the current database.
        Detects which racks, devices, and ports already exist vs which need to be created.
        """
        # Unique names we need to check in the database
        rack_names = set()
        device_names = set()
        cable_numbers = set()

        for row in parsed_data:
            if row.get("source_rack"):
                rack_names.add(row["source_rack"])
            if row.get("target_rack"):
                rack_names.add(row["target_rack"])
            if row.get("source_device"):
                device_names.add(row["source_device"])
            if row.get("target_device"):
                device_names.add(row["target_device"])
            if row.get("cable_number"):
                cable_numbers.add(row["cable_number"])

        # Query database for existing items
        racks_in_db = {}
        if rack_names:
            r_query = select(Rack).where(Rack.name.in_(list(rack_names)))
            r_result = await db.execute(r_query)
            for r in r_result.scalars().all():
                racks_in_db[r.name.lower()] = r

        devices_in_db = {}
        if device_names:
            # We fetch devices and eager load their ports to check existing ports
            from sqlalchemy.orm import selectinload

            d_query = (
                select(Device)
                .where(Device.hostname.in_(list(device_names)))
                .options(selectinload(Device.interfaces))
            )
            d_result = await db.execute(d_query)
            for d in d_result.scalars().all():
                devices_in_db[d.hostname.lower()] = d

        cables_in_db = {}
        if cable_numbers:
            c_query = select(Cable).where(Cable.kabel_nr.in_(list(cable_numbers)))
            c_result = await db.execute(c_query)
            for c in c_result.scalars().all():
                cables_in_db[c.kabel_nr.lower()] = c  # type: ignore

        preview_rows = []
        stats = {
            "total_rows": len(parsed_data),
            "new_cables": 0,
            "existing_cables": 0,
            "missing_racks": set(),
            "missing_devices": set(),
            "missing_ports": set(),
        }

        for row in parsed_data:
            cable_num = row.get("cable_number")
            cable_num_lower = cable_num.lower() if cable_num else None

            status = "new"
            cable_id = None
            if cable_num_lower and cable_num_lower in cables_in_db:
                status = "existing"
                cable_id = cables_in_db[cable_num_lower].id
                stats["existing_cables"] += 1  # type: ignore
            else:
                stats["new_cables"] += 1  # type: ignore

            # Helper to check if source/target entities exist
            def check_entity(rack_name, dev_name, port_name):
                rack_ok = True
                dev_ok = True
                port_ok = True

                if rack_name and rack_name.lower() not in racks_in_db:
                    rack_ok = False
                    stats["missing_racks"].add(rack_name)

                if dev_name:
                    dev_lower = dev_name.lower()
                    if dev_lower not in devices_in_db:
                        dev_ok = False
                        stats["missing_devices"].add(dev_name)
                        port_ok = False  # Port cannot exist if device doesn't
                    elif port_name:
                        dev_obj = devices_in_db[dev_lower]
                        port_exists = any(
                            p.port_name.lower() == port_name.lower()
                            for p in dev_obj.interfaces
                        )
                        if not port_exists:
                            port_ok = False
                            stats["missing_ports"].add(f"{dev_name} -> {port_name}")
                return rack_ok, dev_ok, port_ok

            s_rack_ok, s_dev_ok, s_port_ok = check_entity(
                row.get("source_rack"), row.get("source_device"), row.get("source_port")
            )
            t_rack_ok, t_dev_ok, t_port_ok = check_entity(
                row.get("target_rack"), row.get("target_device"), row.get("target_port")
            )

            preview_rows.append(
                {
                    "row_index": row.get("row_index"),
                    "cable_number": cable_num,
                    "cable_type": row.get("cable_type"),
                    "cable_status": status,
                    "cable_id": cable_id,
                    "length": row.get("length"),
                    "farbe": row.get("farbe") or row.get("color"),
                    "source": {
                        "rack": row.get("source_rack"),
                        "rack_exists": s_rack_ok,
                        "device": row.get("source_device"),
                        "device_exists": s_dev_ok,
                        "port": row.get("source_port"),
                        "port_exists": s_port_ok,
                    },
                    "target": {
                        "rack": row.get("target_rack"),
                        "rack_exists": t_rack_ok,
                        "device": row.get("target_device"),
                        "device_exists": t_dev_ok,
                        "port": row.get("target_port"),
                        "port_exists": t_port_ok,
                    },
                }
            )

        return {
            "stats": {
                "total_rows": stats["total_rows"],
                "new_cables": stats["new_cables"],
                "existing_cables": stats["existing_cables"],
                "missing_racks_count": len(stats["missing_racks"]),  # type: ignore
                "missing_devices_count": len(stats["missing_devices"]),  # type: ignore
                "missing_ports_count": len(stats["missing_ports"]),  # type: ignore
                "missing_racks": list(stats["missing_racks"]),  # type: ignore
                "missing_devices": list(stats["missing_devices"]),  # type: ignore
                "missing_ports": list(stats["missing_ports"]),  # type: ignore
            },
            "rows": preview_rows,
        }
