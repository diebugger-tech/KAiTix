from app.core.database import Base
from datetime import date, datetime
from sqlalchemy import ForeignKey, Integer, String, DECIMAL, Enum, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.domains.hardware.models import Device


class Cable(Base):
    __tablename__ = "cables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kabel_nr: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, unique=True
    )
    typ: Mapped[str] = mapped_column(
        Enum(
            "Cat6",
            "Cat6A",
            "Cat7",
            "DAC",
            "LC-LC",
            "SC-SC",
            "SFP+",
            "Strom-C13",
            "Strom-C19",
            "Strom-Schuko",
            "Strom-CEE-16A-3P",
            "Strom-CEE-32A-3P",
            "Strom-CEE-63A-3P",
            "sonstige",
        ),
        nullable=False,
    )
    laenge_m: Mapped[float] = mapped_column(DECIMAL(6, 2), nullable=False)
    farbe: Mapped[Optional[str]] = mapped_column(String(30))
    von_device_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL")
    )
    von_port: Mapped[Optional[str]] = mapped_column(String(50))
    nach_device_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL")
    )
    nach_port: Mapped[Optional[str]] = mapped_column(String(50))
    verlegt_am: Mapped[Optional[date]] = mapped_column(Date)
    verlegt_von: Mapped[Optional[str]] = mapped_column(String(100))
    bemerkung: Mapped[Optional[str]] = mapped_column(String(255))
    geaendert_von: Mapped[Optional[str]] = mapped_column(String(100))
    geaendert_am: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    von_device: Mapped[Optional["Device"]] = relationship(
        foreign_keys=[von_device_id], back_populates="cables_from"
    )
    nach_device: Mapped[Optional["Device"]] = relationship(
        foreign_keys=[nach_device_id], back_populates="cables_to"
    )
    interfaces: Mapped[List["Interface"]] = relationship(back_populates="cable")
    cable_strands: Mapped[List["CableStrand"]] = relationship(
        back_populates="cable", cascade="all, delete-orphan", passive_deletes=True
    )


class CableStrand(Base):
    __tablename__ = "cable_strands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cable_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cables.id", ondelete="CASCADE"), nullable=False
    )
    strand_number: Mapped[int] = mapped_column(Integer, nullable=False)
    farbe: Mapped[Optional[str]] = mapped_column(String(30))
    von_port_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("interfaces.id", ondelete="SET NULL")
    )
    nach_port_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("interfaces.id", ondelete="SET NULL")
    )
    bemerkung: Mapped[Optional[str]] = mapped_column(String(255))

    # Relationships
    cable: Mapped["Cable"] = relationship(back_populates="cable_strands")
    von_port: Mapped[Optional["Interface"]] = relationship(foreign_keys=[von_port_id])
    nach_port: Mapped[Optional["Interface"]] = relationship(foreign_keys=[nach_port_id])


class Interface(Base):
    __tablename__ = "interfaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    port_name: Mapped[str] = mapped_column(String(50), nullable=False)
    typ: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # z.B. 10GbE, RJ45, LC, SC, etc.
    mac_adresse: Mapped[Optional[str]] = mapped_column(String(17))
    status: Mapped[str] = mapped_column(
        Enum("frei", "belegt", "defekt"), nullable=False, default="frei"
    )

    kabel_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("cables.id", ondelete="SET NULL")
    )

    # Relationships
    device: Mapped["Device"] = relationship(back_populates="interfaces")
    cable: Mapped[Optional["Cable"]] = relationship(back_populates="interfaces")
