import ipaddress
from typing import Optional


def normalize_ipv6(ip_str: Optional[str]) -> Optional[str]:
    """
    NUR-DOKU: Reine String-Kanonisierung für Dedup.
    Bringt einen IPv6-String in die kanonische RFC-5952-Form (Kleinschreibung,
    kürzeste :: Schreibweise). Führt ausdrücklich keine Gültigkeitsprüfung gegen
    reale Adressräume oder Erreichbarkeitsprüfung durch.

    Ist der String nicht parsebar (z.B. weil es reiner Text oder versehentlich
    eine IPv4-Adresse ist), wird er unverändert zurückgegeben.
    Bewusste v1-Toleranz: Fehleinträge oder IPv4 im IPv6-Feld crashen nicht,
    sondern werden stillschweigend durchgewunken, da die Dokumentation
    auch unfertige oder unvollständige Einträge enthalten darf.
    """
    if not ip_str:
        return ip_str

    try:
        # Konstruktor normalisiert automatisch nach RFC 5952
        # (Kleinschreibung, Komprimierung der längsten Null-Sequenz)
        addr = ipaddress.IPv6Address(ip_str.strip())
        return str(addr)
    except ValueError:
        # Fängt ValueError (inkl. AddressValueError) und alle anderen Typ-Fehler bei der Initialisierung.
        # Nicht parsebar -> unverändert zurückgeben (Doku-Toleranz)
        return ip_str
