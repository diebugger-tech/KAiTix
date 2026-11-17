"""Regeln für Breakout-Stränge. Reine Funktionen ohne Datenbankzugriff.

Regel: Kabeltyp mit enden_b = 1 hat keine Stränge, das B-Ende steht am Kabel
(nach_device_id/nach_port). Bei enden_b > 1 bleiben diese Felder leer; die B-Enden
sind genau enden_b Stränge mit strand_number 1..n, je nach_device_id + nach_port.
"""

from typing import Any, Iterable, Mapping, Sequence

from fastapi import HTTPException

Endpunkt = tuple[int | None, str | None]


def pruefe_straenge(
    kabeltyp_name: str, enden_b: int, straenge: Sequence[Mapping[str, Any]]
) -> None:
    """422, wenn Anzahl oder Nummerierung der Stränge nicht zum Kabeltyp passt."""
    if enden_b <= 1:
        if straenge:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Kabeltyp '{kabeltyp_name}' hat nur ein B-Ende und keine "
                    "Stränge. Das Ziel steht am Kabel."
                ),
            )
        return

    if len(straenge) != enden_b:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Kabeltyp '{kabeltyp_name}' braucht genau {enden_b} Stränge, "
                f"übergeben wurden {len(straenge)}"
            ),
        )
    nummern = sorted(strang["strand_number"] for strang in straenge)
    if nummern != list(range(1, enden_b + 1)):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Die Stränge müssen von 1 bis {enden_b} durchnummeriert sein, "
                f"übergeben wurden die Nummern {nummern}"
            ),
        )


def pruefe_kein_ziel_am_kabel(
    kabeltyp_name: str, nach_device_id: int | None, nach_port: str | None
) -> None:
    """422, wenn ein Breakout-Kabel zusätzlich ein Ziel am Kabel selbst trägt."""
    if nach_device_id is not None or nach_port:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Bei Kabeltyp '{kabeltyp_name}' stehen die B-Enden an den Strängen. "
                "Zielgerät und Zielport am Kabel müssen leer bleiben."
            ),
        )


def doppelter_endpunkt(endpunkte: Iterable[Endpunkt]) -> Endpunkt | None:
    """Erster Endpunkt (Gerät, Port), der im selben Kabel mehrfach vorkommt."""
    gesehen: set[Endpunkt] = set()
    for device_id, port in endpunkte:
        if not device_id or not port:
            continue
        if (device_id, port) in gesehen:
            return (device_id, port)
        gesehen.add((device_id, port))
    return None


def strang_schluessel(
    straenge: Iterable[Mapping[str, Any]],
) -> list[tuple[int, int | None, str | None, str | None]]:
    """Vergleichbare Darstellung einer Strangliste, sortiert nach Nummer."""
    return sorted(
        (
            strang["strand_number"],
            strang.get("nach_device_id"),
            strang.get("nach_port"),
            strang.get("farbe"),
        )
        for strang in straenge
    )
