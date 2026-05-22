from sqlalchemy import ForeignKey, Integer, String, DECIMAL, Enum, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
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

