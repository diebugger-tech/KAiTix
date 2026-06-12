from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Integer, String, DateTime, Enum, DECIMAL, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.domains.power.models import UsvUnit
    from app.domains.cabling.models import Cable, Interface


class Rack(Base):
    __tablename__ = "racks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    standort: Mapped[str] = mapped_column(String(100), nullable=False)
    rackreihe: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hoehe_u: Mapped[int] = mapped_column(Integer, nullable=False, default=42)
    breite_mm: Mapped[Optional[int]] = mapped_column(Integer, default=600)
    bemerkung: Mapped[Optional[str]] = mapped_column(String(255))
    hersteller: Mapped[Optional[str]] = mapped_column(String(100))
    modell: Mapped[Optional[str]] = mapped_column(String(100))
    hardware_type_id: Mapped[Optional[int]] = mapped_column(Integer)
    max_watt: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 2), nullable=True
    )  # Max. Gesamtleistung für Overload-Check
    cooling_capacity_w: Mapped[Optional[float]] = mapped_column(
        DECIMAL(10, 2), nullable=True
    )  # Max. Kühlleistung für das Rack in Watt
    usv_n1_redundant: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # USV N+1-Redundanz aktiviert
    geaendert_von: Mapped[Optional[str]] = mapped_column(String(100))
    geaendert_am: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    usv_units: Mapped[List["UsvUnit"]] = relationship(
        back_populates="rack", cascade="all, delete-orphan", passive_deletes=True
    )

    devices: Mapped[List["Device"]] = relationship(
        back_populates="rack", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def total_tdp_w(self) -> float:
        if not self.devices:
            return 0.0
        return sum(
            float(dev.tdp_watt) for dev in self.devices if dev.tdp_watt is not None
        )


class DeviceDependency(Base):
    __tablename__ = "device_dependencies"

    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
    depends_on_device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
    dependency_type: Mapped[Optional[str]] = mapped_column(
        String(50), default="service"
    )
    dependency_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    device: Mapped["Device"] = relationship(
        foreign_keys=[device_id], back_populates="dependencies"
    )
    depends_on_device: Mapped["Device"] = relationship(
        foreign_keys=[depends_on_device_id], back_populates="depended_by"
    )


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    typ: Mapped[str] = mapped_column(
        Enum(
            "server",
            "switch",
            "pdu",
            "storage",
            "firewall",
            "kentix_raconode",
            "kentix_doormaster",
            "kentix_multisensor",
            "usv",
            "patchpanel",
            "sonstige",
        ),
        nullable=False,
    )
    hostname: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    # NUR-DOKU: Keine Auflösung, kein Ping, kein Scan. Reine Dokumentation.
    ip_adresse: Mapped[Optional[str]] = mapped_column(
        String(45)
    )  # IPv4 (Konvention); IPv6 in ipv6_adresse
    ipv6_adresse: Mapped[Optional[str]] = mapped_column(
        String(45)
    )  # bewusste v1-Vereinfachung = eine Adresse je Gerät/VM; Mehrfachadressen je Interface (Link-Local/ULA/GUA) sind als spätere Kindtabelle möglich, hier absichtlich nicht umgesetzt.
    hersteller: Mapped[Optional[str]] = mapped_column(String(100))
    modell: Mapped[Optional[str]] = mapped_column(String(100))
    seriennummer: Mapped[Optional[str]] = mapped_column(String(100))
    rack_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("racks.id", ondelete="CASCADE")
    )
    u_position: Mapped[Optional[int]] = mapped_column(Integer)
    u_hoehe: Mapped[int] = mapped_column(Integer, default=1)
    side: Mapped[Optional[str]] = mapped_column(Enum("left", "right"), nullable=True)
    subnet_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("subnets.id", ondelete="SET NULL"), nullable=True
    )

    phase: Mapped[Optional[str]] = mapped_column(Enum("L1", "L2", "L3"))
    tdp_watt: Mapped[Optional[float]] = mapped_column(
        DECIMAL(8, 2)
    )  # CPU/Komponenten-TDP
    psu_count: Mapped[Optional[int]] = mapped_column(Integer)
    psu_nennwatt: Mapped[Optional[float]] = mapped_column(DECIMAL(8, 2))
    last_pct: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 1), default=60.0)
    anschlussleistung_watt: Mapped[Optional[float]] = mapped_column(
        DECIMAL(8, 2)
    )  # Netzteileingabe für USV
    einschaltstrom_faktor: Mapped[Optional[float]] = mapped_column(
        DECIMAL(3, 1), default=2.5
    )
    shutdown_delay_seconds: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    shutdown_priority: Mapped[Optional[int]] = mapped_column(Integer, default=2)
    shutdown_method: Mapped[Optional[str]] = mapped_column(
        Enum("ACPI_Graceful", "SSH_Script", "Hard_Power_Cut_PDU"),
        default="ACPI_Graceful",
    )

    bemerkung: Mapped[Optional[str]] = mapped_column(String(255))
    inventarnummer: Mapped[Optional[str]] = mapped_column(String(100))
    geaendert_von: Mapped[Optional[str]] = mapped_column(String(100))
    geaendert_am: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Power input documentation (for PDUs)
    strom_typ: Mapped[Optional[str]] = mapped_column(
        Enum("1-phasig", "3-phasig"), nullable=True
    )
    spannung_v: Mapped[Optional[int]] = mapped_column(Integer)  # 230 or 400
    absicherung_a: Mapped[Optional[float]] = mapped_column(
        DECIMAL(5, 1)
    )  # Absicherung je Stromkreis in A, z.B. 16.0 oder 32.0
    anschluss_stecker: Mapped[Optional[str]] = mapped_column(
        Enum(
            "CEE-16A-3P", "CEE-32A-3P", "CEE-63A-3P", "C14", "C20", "Schuko", "sonstige"
        ),
        nullable=True,
    )  # z.B. "CEE-16A-3P" (Kentix SmartPDU 16A), "CEE-32A-3P"
    redundancy_path: Mapped[Optional[str]] = mapped_column(
        Enum("A", "B"), nullable=True
    )  # Stromversorgungspfad A oder B (für A/B-Redundanzprüfung)
    min_rack_hoehe: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Minimale Rack-Höhe in HE für PDU-Kompatibilitätsprüfung (z.B. 40 für 40HE PDU)

    # Relationships
    rack: Mapped[Optional["Rack"]] = relationship(back_populates="devices")

    dependencies: Mapped[List["DeviceDependency"]] = relationship(
        foreign_keys="[DeviceDependency.device_id]",
        back_populates="device",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    depended_by: Mapped[List["DeviceDependency"]] = relationship(
        foreign_keys="[DeviceDependency.depends_on_device_id]",
        back_populates="depends_on_device",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )

    interfaces: Mapped[List["Interface"]] = relationship(
        back_populates="device", cascade="all, delete-orphan", passive_deletes=True
    )

    cables_from: Mapped[List["Cable"]] = relationship(
        foreign_keys="[Cable.von_device_id]", back_populates="von_device"
    )
    cables_to: Mapped[List["Cable"]] = relationship(
        foreign_keys="[Cable.nach_device_id]", back_populates="nach_device"
    )

    # PDU specific relationships
    pdu_outlets: Mapped[List["PduOutlet"]] = relationship(
        foreign_keys="[PduOutlet.pdu_id]",
        back_populates="pdu",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    connected_pdu_outlets: Mapped[List["PduOutlet"]] = relationship(
        foreign_keys="[PduOutlet.connected_device_id]",
        back_populates="connected_device",
        lazy="selectin",
    )

    virtual_machines: Mapped[List["VirtualMachine"]] = relationship(
        foreign_keys="[VirtualMachine.host_device_id]",
        back_populates="host_device",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def device_ports(self) -> List["Interface"]:
        return self.interfaces

    @property
    def server_interfaces(self) -> List["Interface"]:
        return self.interfaces


class PduOutlet(Base):
    __tablename__ = "pdu_outlets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pdu_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    outlet_name: Mapped[str] = mapped_column(String(50), nullable=False)
    phase: Mapped[Optional[str]] = mapped_column(Enum("L1", "L2", "L3"))
    steckdosentyp: Mapped[Optional[str]] = mapped_column(
        Enum("C13", "C19", "C14", "C20", "Schuko", "CEE-16A"), nullable=True
    )
    max_watt: Mapped[Optional[float]] = mapped_column(DECIMAL(8, 2))
    schaltbar: Mapped[bool] = mapped_column(default=False)
    redundancy_path: Mapped[Optional[str]] = mapped_column(
        Enum("A", "B"), nullable=True
    )  # Pfad-Zugehörigkeit der Steckdose: A = Primärpfad, B = Redundanzpfad
    connected_device_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL")
    )
    connected_port: Mapped[Optional[str]] = mapped_column(String(50))

    # Relationships
    pdu: Mapped["Device"] = relationship(
        foreign_keys=[pdu_id], back_populates="pdu_outlets"
    )
    connected_device: Mapped[Optional["Device"]] = relationship(
        foreign_keys=[connected_device_id], back_populates="connected_pdu_outlets"
    )

    @property
    def pdu_name(self) -> Optional[str]:
        return self.pdu.hostname if self.pdu else None


class VirtualMachine(Base):
    __tablename__ = "virtual_machines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    host_device_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL")
    )
    hypervisor_typ: Mapped[Optional[str]] = mapped_column(
        Enum("vmware", "hyper-v", "kvm", "xcpng", "sonstige")
    )
    vm_id_extern: Mapped[Optional[str]] = mapped_column(String(50))
    betriebssystem: Mapped[Optional[str]] = mapped_column(String(100))
    dienst: Mapped[Optional[str]] = mapped_column(String(255))
    # NUR-DOKU: Keine Auflösung, kein Ping, kein Scan. Reine Dokumentation.
    ip_adresse: Mapped[Optional[str]] = mapped_column(
        String(45)
    )  # IPv4 (Konvention); IPv6 in ipv6_adresse
    ipv6_adresse: Mapped[Optional[str]] = mapped_column(
        String(45)
    )  # bewusste v1-Vereinfachung = eine Adresse je Gerät/VM; Mehrfachadressen je Interface (Link-Local/ULA/GUA) sind als spätere Kindtabelle möglich, hier absichtlich nicht umgesetzt.
    depends_on_vm_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("virtual_machines.id", ondelete="SET NULL")
    )
    shutdown_priority: Mapped[Optional[int]] = mapped_column(Integer, default=5)
    responsible: Mapped[Optional[str]] = mapped_column(String(100))
    subnet_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("subnets.id", ondelete="SET NULL"), nullable=True
    )
    bemerkung: Mapped[Optional[str]] = mapped_column(String(1000))

    # Relationships
    host_device: Mapped[Optional["Device"]] = relationship(
        foreign_keys=[host_device_id], back_populates="virtual_machines"
    )
    depends_on_vm: Mapped[Optional["VirtualMachine"]] = relationship(
        foreign_keys=[depends_on_vm_id], remote_side=[id]
    )
