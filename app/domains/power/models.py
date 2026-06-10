from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    DECIMAL,
    Enum,
    DateTime,
    Text,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from decimal import Decimal
import json
from app.core.database import Base


if TYPE_CHECKING:
    from app.domains.hardware.models import Rack


class UsvUnit(Base):
    __tablename__ = "usv_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bezeichnung: Mapped[str] = mapped_column(String(100), nullable=False)
    hersteller: Mapped[str] = mapped_column(
        String(100), nullable=False, default="Wöhrle SVS"
    )
    rack_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("racks.id", ondelete="CASCADE"), nullable=False
    )
    max_kw: Mapped[float] = mapped_column(DECIMAL(6, 2), nullable=False)
    battery_strings: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    blocks_per_string: Mapped[int] = mapped_column(Integer, nullable=False, default=32)
    block_voltage_v: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2), nullable=False, default=Decimal("12.00")
    )
    block_capacity_ah: Mapped[Decimal] = mapped_column(
        DECIMAL(7, 2), nullable=False, default=Decimal("100.00")
    )
    has_bypass_switch: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    redundancy_path: Mapped[Optional[str]] = mapped_column(
        Enum("A", "B"), nullable=True
    )
    geaendert_von: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Relationships
    rack: Mapped["Rack"] = relationship(back_populates="usv_units")
    modules: Mapped[List["UsvModule"]] = relationship(
        back_populates="usv_unit", cascade="all, delete-orphan", passive_deletes=True
    )
    simulation_events: Mapped[List["UsvSimulationEvent"]] = relationship(
        back_populates="usv_unit", cascade="all, delete-orphan", passive_deletes=True
    )


class UsvModule(Base):
    __tablename__ = "usv_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usv_unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usv_units.id", ondelete="CASCADE"), nullable=False
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    leistung_kw: Mapped[float] = mapped_column(DECIMAL(5, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("aktiv", "reserve", "defekt"), nullable=False, default="aktiv"
    )
    seriennummer: Mapped[Optional[str]] = mapped_column(String(100))
    geaendert_von: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    usv_unit: Mapped["UsvUnit"] = relationship(back_populates="modules")


class UsvSimulationEvent(Base):
    __tablename__ = "usv_simulation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(
        Enum("info", "warning", "critical"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    usv_unit_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("usv_units.id", ondelete="CASCADE"), nullable=True
    )
    snapshot_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    usv_unit: Mapped[Optional["UsvUnit"]] = relationship(
        back_populates="simulation_events"
    )

    @property
    def snapshot(self) -> Optional[Dict[str, Any]]:
        if self.snapshot_json:
            return json.loads(self.snapshot_json)
        return None

    @snapshot.setter
    def snapshot(self, value: Optional[Dict[str, Any]]) -> None:
        self.snapshot_json = json.dumps(value, default=str) if value else None


class DistributionPanel(Base):
    __tablename__ = "distribution_panels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bezeichnung: Mapped[str] = mapped_column(String(100), nullable=False)
    rack_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("racks.id", ondelete="CASCADE"), nullable=True
    )
    usv_unit_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("usv_units.id", ondelete="SET NULL"), nullable=True
    )
    bemerkung: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    has_epo_contact: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    redundancy_path: Mapped[Optional[str]] = mapped_column(
        Enum("A", "B"), nullable=True
    )
    geaendert_von: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    circuits: Mapped[List["DistributionCircuit"]] = relationship(
        back_populates="panel", cascade="all, delete-orphan", passive_deletes=True
    )


class DistributionCircuit(Base):
    __tablename__ = "distribution_circuits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    panel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("distribution_panels.id", ondelete="CASCADE"),
        nullable=False,
    )
    bezeichnung: Mapped[str] = mapped_column(String(50), nullable=False)
    phase: Mapped[str] = mapped_column(Enum("L1", "L2", "L3"), nullable=False)
    absicherung_a: Mapped[float] = mapped_column(DECIMAL(5, 1), nullable=False)
    max_watt: Mapped[Optional[float]] = mapped_column(
        DECIMAL(8, 2), nullable=True
    )  # Usually Generated Column

    # Relationships
    panel: Mapped["DistributionPanel"] = relationship(back_populates="circuits")


class UsvCalculation(Base):
    __tablename__ = "usv_calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    berechnet_am: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    usv_unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("usv_units.id", ondelete="CASCADE"), nullable=False
    )
    last_kw: Mapped[float] = mapped_column(DECIMAL(8, 2), nullable=False)
    peak_kw: Mapped[float] = mapped_column(DECIMAL(8, 2), nullable=False)
    installiert_kw: Mapped[float] = mapped_column(DECIMAL(8, 2), nullable=False)
    reserve_kw: Mapped[float] = mapped_column(DECIMAL(8, 2), nullable=False)
    n1_kw: Mapped[float] = mapped_column(DECIMAL(8, 2), nullable=False)
    kaltstart_ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    bemerkung: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
