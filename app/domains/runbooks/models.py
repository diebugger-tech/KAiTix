from datetime import datetime
from typing import List, Optional
from sqlalchemy import Integer, String, DateTime, Enum, DECIMAL, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Runbook(Base):
    __tablename__ = "runbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    typ: Mapped[str] = mapped_column(
        Enum("shutdown", "startup", "wartung", "notfall", "custom"), nullable=False
    )
    beschreibung: Mapped[Optional[str]] = mapped_column(Text)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    erstellt_von: Mapped[Optional[str]] = mapped_column(String(100))
    generated_from_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("runbooks.id", ondelete="SET NULL")
    )

    # Relationships
    layers: Mapped[List["RunbookLayer"]] = relationship(
        back_populates="runbook", cascade="all, delete-orphan", passive_deletes=True, order_by="RunbookLayer.position"
    )
    devices: Mapped[List["RunbookDevice"]] = relationship(
        back_populates="runbook", cascade="all, delete-orphan", passive_deletes=True
    )
    executions: Mapped[List["RunbookExecution"]] = relationship(
        back_populates="runbook", cascade="all, delete-orphan", passive_deletes=True
    )
    generated_from: Mapped[Optional["Runbook"]] = relationship(
        remote_side=[id]
    )

class RunbookLayer(Base):
    __tablename__ = "runbook_layers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    runbook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    markdown_note: Mapped[Optional[str]] = mapped_column(Text)
    shutdown_order: Mapped[Optional[int]] = mapped_column(Integer)
    startup_order: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    runbook: Mapped["Runbook"] = relationship(back_populates="layers")
    devices: Mapped[List["RunbookDevice"]] = relationship(
        back_populates="layer", cascade="all, delete-orphan", passive_deletes=True, order_by="RunbookDevice.position"
    )

class RunbookDevice(Base):
    __tablename__ = "runbook_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    runbook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False
    )
    layer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runbook_layers.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL")
    )
    vm_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("virtual_machines.id", ondelete="SET NULL")
    )
    freitext: Mapped[Optional[str]] = mapped_column(String(255))
    delay_seconds: Mapped[int] = mapped_column(Integer, default=30)
    responsible: Mapped[Optional[str]] = mapped_column(String(100))
    note: Mapped[Optional[str]] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    runbook: Mapped["Runbook"] = relationship(back_populates="devices")
    layer: Mapped["RunbookLayer"] = relationship(back_populates="devices")
    # To avoid circular import, we can import Device and VirtualMachine at the module level or specify as strings
    # "Device" and "VirtualMachine" will be resolved by SQLAlchemy's registry if they are imported elsewhere
    device = relationship("Device", foreign_keys=[device_id])
    vm = relationship("VirtualMachine", foreign_keys=[vm_id])
    
    execution_steps: Mapped[List["RunbookExecutionStep"]] = relationship(
        back_populates="runbook_device", cascade="all, delete-orphan", passive_deletes=True
    )

class RunbookExecution(Base):
    __tablename__ = "runbook_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    runbook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False
    )
    gestartet_am: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    gestartet_von: Mapped[Optional[str]] = mapped_column(String(100))
    modus: Mapped[str] = mapped_column(Enum("shutdown", "startup"), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("aktiv", "abgeschlossen", "abgebrochen"), nullable=False, default="aktiv"
    )

    # Relationships
    runbook: Mapped["Runbook"] = relationship(back_populates="executions")
    steps: Mapped[List["RunbookExecutionStep"]] = relationship(
        back_populates="execution", cascade="all, delete-orphan", passive_deletes=True
    )

class RunbookExecutionStep(Base):
    __tablename__ = "runbook_execution_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runbook_executions.id", ondelete="CASCADE"), nullable=False
    )
    runbook_device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runbook_devices.id", ondelete="CASCADE"), nullable=False
    )
    abgehakt_am: Mapped[Optional[datetime]] = mapped_column(DateTime)
    abgehakt_von: Mapped[Optional[str]] = mapped_column(String(100))
    note: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    execution: Mapped["RunbookExecution"] = relationship(back_populates="steps")
    runbook_device: Mapped["RunbookDevice"] = relationship(back_populates="execution_steps")
