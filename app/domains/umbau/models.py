"""Serverraum-Umbau: Soll-Stand einfrieren, Enden abklemmen, nach Soll wieder anklemmen.

Die Kabelliste bleibt die Tabelle `cables`. Beim Einfrieren entsteht je physischem
Stecker-Ende eine Zeile `umbau_enden` mit einer TEXTKOPIE des Solls. Ab dann liest der
Umbau `cables`, `cable_strands` und `interfaces` nicht mehr schreibend.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

UMBAU_STATUS = (
    "erfassung",
    "rueckbau",
    "umbau",
    "wiederaufbau",
    "abgeschlossen",
    "verworfen",
)
ENDE_STATUS = ("gesteckt", "abgeklemmt", "angeklemmt", "angeklemmt_abweichend")
ENDE_SEITEN = ("A", "B")


def jetzt() -> datetime:
    """Aktuelle Zeit als naive UTC, wie in den übrigen Domänen gespeichert."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Umbau(Base):
    __tablename__ = "umbauten"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    beschreibung: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Enum(*UMBAU_STATUS), nullable=False, default="erfassung"
    )
    erstellt_am: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=jetzt
    )
    erstellt_von: Mapped[Optional[str]] = mapped_column(String(100))
    eingefroren_am: Mapped[Optional[datetime]] = mapped_column(DateTime)
    eingefroren_von: Mapped[Optional[str]] = mapped_column(String(100))
    abgeschlossen_am: Mapped[Optional[datetime]] = mapped_column(DateTime)
    abgeschlossen_von: Mapped[Optional[str]] = mapped_column(String(100))

    # Umfang des Umbaus: die gewählten Racks
    racks: Mapped[List["UmbauRack"]] = relationship(
        back_populates="umbau", cascade="all, delete-orphan", passive_deletes=True
    )


class UmbauRack(Base):
    __tablename__ = "umbau_racks"

    umbau_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("umbauten.id", ondelete="CASCADE"), primary_key=True
    )
    rack_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("racks.id", ondelete="CASCADE"), primary_key=True
    )

    umbau: Mapped["Umbau"] = relationship(back_populates="racks")


class UmbauGeraetepruefung(Base):
    """„Gerät vollständig erfasst“ — Bestätigung je Gerät im Umfang."""

    __tablename__ = "umbau_geraetepruefungen"
    __table_args__ = (
        UniqueConstraint(
            "umbau_id", "device_id", name="uq_umbau_geraetepruefungen_umbau_device"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    umbau_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("umbauten.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL")
    )
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bestaetigt_am: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=jetzt
    )
    bestaetigt_von: Mapped[Optional[str]] = mapped_column(String(100))


class UmbauEnde(Base):
    """Ein physisches Stecker-Ende. Entsteht nur beim Einfrieren.

    Die soll_*-Felder sowie kabel_nr, kabeltyp_name, kategorie und farbe sind eine
    Textkopie und nach dem Einfrieren unveränderlich.
    """

    __tablename__ = "umbau_enden"
    __table_args__ = (
        UniqueConstraint(
            "umbau_id",
            "cable_id",
            "seite",
            "ende_nr",
            name="uq_umbau_enden_umbau_cable_seite_nr",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    umbau_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("umbauten.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cable_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("cables.id", ondelete="SET NULL")
    )
    strand_number: Mapped[Optional[int]] = mapped_column(Integer)
    seite: Mapped[str] = mapped_column(Enum(*ENDE_SEITEN), nullable=False)
    ende_nr: Mapped[int] = mapped_column(Integer, nullable=False)

    # Soll (Textkopie)
    soll_device_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL")
    )
    soll_device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    soll_rack_name: Mapped[Optional[str]] = mapped_column(String(100))
    soll_port: Mapped[str] = mapped_column(String(50), nullable=False)
    kabel_nr: Mapped[Optional[str]] = mapped_column(String(50))
    kabeltyp_name: Mapped[str] = mapped_column(String(100), nullable=False)
    kategorie: Mapped[str] = mapped_column(String(20), nullable=False)
    farbe: Mapped[Optional[str]] = mapped_column(String(30))

    # Fortschritt
    status: Mapped[str] = mapped_column(
        Enum(*ENDE_STATUS), nullable=False, default="gesteckt"
    )
    abgeklemmt_am: Mapped[Optional[datetime]] = mapped_column(DateTime)
    abgeklemmt_von: Mapped[Optional[str]] = mapped_column(String(100))
    angeklemmt_am: Mapped[Optional[datetime]] = mapped_column(DateTime)
    angeklemmt_von: Mapped[Optional[str]] = mapped_column(String(100))

    # Ist beim Wiederanklemmen (nur bei Abweichung vom Soll befüllt)
    ist_device_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL")
    )
    ist_device_name: Mapped[Optional[str]] = mapped_column(String(100))
    ist_port: Mapped[Optional[str]] = mapped_column(String(50))
    abweichung_grund: Mapped[Optional[str]] = mapped_column(String(255))


class UmbauEreignis(Base):
    """Protokoll des Umbaus. Wird nur angehängt, nie geändert."""

    __tablename__ = "umbau_ereignisse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    umbau_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("umbauten.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ende_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("umbau_enden.id", ondelete="SET NULL")
    )
    von_status: Mapped[Optional[str]] = mapped_column(String(30))
    nach_status: Mapped[str] = mapped_column(String(30), nullable=False)
    grund: Mapped[Optional[str]] = mapped_column(String(255))
    benutzer: Mapped[Optional[str]] = mapped_column(String(100))
    zeitpunkt: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=jetzt)
