"""
ServerFlow CLI
Stack: Python 3.11+, Typer, SQLAlchemy 2.x sync, PyMySQL
Install: pip install typer sqlalchemy pymysql rich python-dotenv
"""

import os
from datetime import date
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, DeclarativeBase, relationship
from sqlalchemy import Column, Integer, String, Numeric, Date, SmallInteger, ForeignKey

load_dotenv()

# ── DB-Verbindung ─────────────────────────────────────────────
DB_URL = os.getenv(
    "DATABASE_URL", "mysql+pymysql://serverflow:serverflow@localhost:3306/serverflow"
)
engine = create_engine(DB_URL, echo=False)
console = Console()
app = typer.Typer(help="ServerFlow — Serverraum Kabelliste & USV-Verwaltung")


# ── ORM Base ─────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


class Rack(Base):
    __tablename__ = "racks"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    standort = Column(String(100), nullable=False)
    hoehe_u = Column(SmallInteger, default=42)
    bemerkung = Column(String(255))
    devices = relationship("Device", back_populates="rack")


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True)
    typ = Column(String(50), nullable=False)
    hostname = Column(String(100), nullable=False)
    ip_adresse = Column(String(45))
    hersteller = Column(String(100))
    modell = Column(String(100))
    seriennummer = Column(String(100))
    rack_id = Column(Integer, ForeignKey("racks.id"))
    u_position = Column(SmallInteger)
    u_hoehe = Column(SmallInteger, default=1)
    circuit_id = Column(Integer, ForeignKey("distribution_circuits.id"))
    phase = Column(String(3))
    tdp_watt = Column(Numeric(8, 2))
    einschaltstrom_faktor = Column(Numeric(3, 1), default=2.5)
    api_url = Column(String(255))
    api_key = Column(String(255))
    bemerkung = Column(String(255))
    rack = relationship("Rack", back_populates="devices")
    interfaces = relationship("ServerInterface", back_populates="device")


class ServerInterface(Base):
    __tablename__ = "server_interfaces"
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    port_name = Column(String(50), nullable=False)
    typ = Column(String(20), nullable=False)
    mac_adresse = Column(String(17))
    switch_hostname = Column(String(100))
    switch_port = Column(String(50))
    kabel_id = Column(Integer, ForeignKey("cables.id"))
    device = relationship("Device", back_populates="interfaces")


class Cable(Base):
    __tablename__ = "cables"
    id = Column(Integer, primary_key=True)
    kabel_nr = Column(String(50), nullable=False)
    typ = Column(String(30), nullable=False)
    laenge_m = Column(Numeric(6, 2), nullable=False)
    farbe = Column(String(30))
    von_device = Column(Integer, ForeignKey("devices.id"))
    von_port = Column(String(50))
    nach_device = Column(Integer, ForeignKey("devices.id"))
    nach_port = Column(String(50))
    verlegt_am = Column(Date)
    verlegt_von = Column(String(100))
    bemerkung = Column(String(255))


class UsvUnit(Base):
    __tablename__ = "usv_units"
    id = Column(Integer, primary_key=True)
    bezeichnung = Column(String(100), nullable=False)
    hersteller = Column(String(100), default="Wöhrle SVS")
    rack_id = Column(Integer, ForeignKey("racks.id"))
    max_kw = Column(Numeric(6, 2), nullable=False)
    modules = relationship("UsvModule", back_populates="unit")


class UsvModule(Base):
    __tablename__ = "usv_modules"
    id = Column(Integer, primary_key=True)
    usv_unit_id = Column(Integer, ForeignKey("usv_units.id"), nullable=False)
    slot = Column(SmallInteger, nullable=False)
    leistung_kw = Column(Numeric(5, 2), nullable=False)
    status = Column(String(10), default="aktiv")
    seriennummer = Column(String(100))
    unit = relationship("UsvUnit", back_populates="modules")


class DistributionCircuit(Base):
    __tablename__ = "distribution_circuits"
    id = Column(Integer, primary_key=True)
    panel_id = Column(Integer, ForeignKey("distribution_panels.id"))
    bezeichnung = Column(String(50), nullable=False)
    phase = Column(String(3), nullable=False)
    absicherung_a = Column(Numeric(5, 1), nullable=False)


class DistributionPanel(Base):
    __tablename__ = "distribution_panels"
    id = Column(Integer, primary_key=True)
    bezeichnung = Column(String(100), nullable=False)
    rack_id = Column(Integer, ForeignKey("racks.id"))
    usv_unit_id = Column(Integer, ForeignKey("usv_units.id"))
    bemerkung = Column(String(255))


# ══════════════════════════════════════════════════════════════
# RACK COMMANDS
# ══════════════════════════════════════════════════════════════
rack_app = typer.Typer(help="Rack-Verwaltung")
app.add_typer(rack_app, name="rack")


@rack_app.command("add")
def rack_add(
    name: str = typer.Argument(..., help="z.B. RACK-01"),
    standort: str = typer.Argument(..., help="z.B. 'Serverraum EG'"),
    hoehe: int = typer.Option(42, help="Höhe in U"),
):
    """Rack anlegen."""
    with Session(engine) as s:
        s.add(Rack(name=name, standort=standort, hoehe_u=hoehe))
        s.commit()
    rprint(f"[green]✓ Rack '{name}' angelegt.[/green]")


@rack_app.command("list")
def rack_list():
    """Alle Racks anzeigen."""
    with Session(engine) as s:
        racks = s.query(Rack).all()
    t = Table("ID", "Name", "Standort", "Höhe U")
    for r in racks:
        t.add_row(str(r.id), r.name, r.standort, str(r.hoehe_u))
    console.print(t)


# ══════════════════════════════════════════════════════════════
# DEVICE COMMANDS
# ══════════════════════════════════════════════════════════════
device_app = typer.Typer(help="Geräte-Verwaltung (Server, Switch, Kentix, PDU)")
app.add_typer(device_app, name="device")


@device_app.command("add")
def device_add(
    hostname: str = typer.Argument(...),
    typ: str = typer.Option("server", help="server|switch|pdu|kentix_raconode|..."),
    ip: Optional[str] = typer.Option(None),
    rack: Optional[int] = typer.Option(None, help="Rack-ID"),
    u_pos: Optional[int] = typer.Option(None, help="U-Position (unterste)"),
    u_hoehe: int = typer.Option(1),
    watt: Optional[float] = typer.Option(None, help="TDP in Watt"),
    phase: Optional[str] = typer.Option(None, help="L1|L2|L3"),
    hersteller: Optional[str] = typer.Option(None),
    modell: Optional[str] = typer.Option(None),
    api_url: Optional[str] = typer.Option(None, help="Kentix/iDRAC API URL"),
    api_key: Optional[str] = typer.Option(None),
):
    """Gerät anlegen."""
    with Session(engine) as s:
        s.add(
            Device(
                hostname=hostname,
                typ=typ,
                ip_adresse=ip,
                rack_id=rack,
                u_position=u_pos,
                u_hoehe=u_hoehe,
                tdp_watt=watt,
                phase=phase,
                hersteller=hersteller,
                modell=modell,
                api_url=api_url,
                api_key=api_key,
            )
        )
        s.commit()
    rprint(f"[green]✓ Gerät '{hostname}' ({typ}) angelegt.[/green]")


@device_app.command("list")
def device_list(typ: Optional[str] = typer.Option(None, help="Filter nach Typ")):
    """Alle Geräte anzeigen."""
    with Session(engine) as s:
        q = s.query(Device)
        if typ:
            q = q.filter(Device.typ == typ)
        devices = q.all()
    t = Table("ID", "Hostname", "Typ", "IP", "Rack", "U", "Phase", "Watt")
    for d in devices:
        t.add_row(
            str(d.id),
            d.hostname,
            d.typ,
            d.ip_adresse or "-",
            str(d.rack_id or "-"),
            str(d.u_position or "-"),
            d.phase or "-",
            str(d.tdp_watt or "-"),
        )
    console.print(t)


# ══════════════════════════════════════════════════════════════
# INTERFACE COMMANDS
# ══════════════════════════════════════════════════════════════
iface_app = typer.Typer(help="Server-Interface Verwaltung")
app.add_typer(iface_app, name="iface")


@iface_app.command("add")
def iface_add(
    device_id: int = typer.Argument(..., help="Device-ID"),
    port_name: str = typer.Argument(..., help="z.B. eth0"),
    typ: str = typer.Option("1GbE"),
    mac: Optional[str] = typer.Option(None),
    switch_host: Optional[str] = typer.Option(None),
    switch_port: Optional[str] = typer.Option(None),
):
    """Interface zu einem Gerät hinzufügen."""
    with Session(engine) as s:
        s.add(
            ServerInterface(
                device_id=device_id,
                port_name=port_name,
                typ=typ,
                mac_adresse=mac,
                switch_hostname=switch_host,
                switch_port=switch_port,
            )
        )
        s.commit()
    rprint(
        f"[green]✓ Interface '{port_name}' ({typ}) zu Device {device_id} hinzugefügt.[/green]"
    )


@iface_app.command("list")
def iface_list(device_id: int = typer.Argument(...)):
    """Interfaces eines Geräts anzeigen."""
    with Session(engine) as s:
        ifaces = (
            s.query(ServerInterface)
            .filter(ServerInterface.device_id == device_id)
            .all()
        )
    t = Table("ID", "Port", "Typ", "MAC", "Switch", "Switch-Port", "Kabel-ID")
    for i in ifaces:
        t.add_row(
            str(i.id),
            i.port_name,
            i.typ,
            i.mac_adresse or "-",
            i.switch_hostname or "-",
            i.switch_port or "-",
            str(i.kabel_id or "-"),
        )
    console.print(t)


# ══════════════════════════════════════════════════════════════
# CABLE COMMANDS
# ══════════════════════════════════════════════════════════════
cable_app = typer.Typer(help="Kabelliste")
app.add_typer(cable_app, name="cable")


@cable_app.command("add")
def cable_add(
    typ: str = typer.Argument(..., help="Cat6|DAC|LC-LC|Strom-C13|..."),
    laenge: float = typer.Argument(..., help="Länge in Metern"),
    von: Optional[int] = typer.Option(None, help="Von Device-ID"),
    von_port: Optional[str] = typer.Option(None),
    nach: Optional[int] = typer.Option(None, help="Nach Device-ID"),
    nach_port: Optional[str] = typer.Option(None),
    farbe: Optional[str] = typer.Option(None),
    verlegt_von: Optional[str] = typer.Option(None),
):
    """Kabel anlegen (Nummer wird automatisch vergeben)."""
    with Session(engine) as s:
        count = s.query(Cable).count()
        kabel_nr = f"KAB-{count + 1:04d}"
        s.add(
            Cable(
                kabel_nr=kabel_nr,
                typ=typ,
                laenge_m=laenge,
                von_device=von,
                von_port=von_port,
                nach_device=nach,
                nach_port=nach_port,
                farbe=farbe,
                verlegt_am=date.today(),
                verlegt_von=verlegt_von,
            )
        )
        s.commit()
    rprint(f"[green]✓ Kabel '{kabel_nr}' ({typ}, {laenge}m) angelegt.[/green]")


@cable_app.command("list")
def cable_list():
    """Alle Kabel anzeigen."""
    with Session(engine) as s:
        cables = s.query(Cable).all()
    t = Table("Nr", "Typ", "Länge", "Von", "Von-Port", "Nach", "Nach-Port", "Farbe")
    for c in cables:
        t.add_row(
            c.kabel_nr,
            c.typ,
            f"{c.laenge_m}m",
            str(c.von_device or "-"),
            c.von_port or "-",
            str(c.nach_device or "-"),
            c.nach_port or "-",
            c.farbe or "-",
        )
    console.print(t)


# ══════════════════════════════════════════════════════════════
# USV COMMANDS
# ══════════════════════════════════════════════════════════════
usv_app = typer.Typer(help="USV-Verwaltung & Berechnung")
app.add_typer(usv_app, name="usv")


@usv_app.command("add-unit")
def usv_add_unit(
    bezeichnung: str = typer.Argument(...),
    max_kw: float = typer.Argument(..., help="Schrank-Maximum kW"),
    rack_id: int = typer.Argument(...),
    hersteller: str = typer.Option("Wöhrle SVS"),
):
    """USV-Schrank anlegen."""
    with Session(engine) as s:
        s.add(
            UsvUnit(
                bezeichnung=bezeichnung,
                max_kw=max_kw,
                rack_id=rack_id,
                hersteller=hersteller,
            )
        )
        s.commit()
    rprint(f"[green]✓ USV '{bezeichnung}' ({max_kw} kW) angelegt.[/green]")


@usv_app.command("add-module")
def usv_add_module(
    usv_id: int = typer.Argument(..., help="USV-Unit ID"),
    slot: int = typer.Argument(..., help="Slot 1-4"),
    leistung_kw: float = typer.Argument(..., help="Modul-Leistung kW"),
    seriennummer: Optional[str] = typer.Option(None),
):
    """Leistungsmodul zu USV hinzufügen."""
    with Session(engine) as s:
        s.add(
            UsvModule(
                usv_unit_id=usv_id,
                slot=slot,
                leistung_kw=leistung_kw,
                seriennummer=seriennummer,
            )
        )
        s.commit()
    rprint(
        f"[green]✓ Modul Slot {slot} ({leistung_kw} kW) zu USV {usv_id} hinzugefügt.[/green]"
    )


@usv_app.command("calc")
def usv_calc(usv_id: int = typer.Argument(..., help="USV-Unit ID")):
    """
    USV-Berechnung:
    - Σ TDP aller angeschlossenen Geräte
    - Peak (Einschaltstrom)
    - N+1 Kapazität
    - Kaltstart-Check
    """
    with Session(engine) as s:
        unit = s.get(UsvUnit, usv_id)
        if not unit:
            rprint(f"[red]USV {usv_id} nicht gefunden.[/red]")
            raise typer.Exit(1)

        modules = (
            s.query(UsvModule)
            .filter(UsvModule.usv_unit_id == usv_id, UsvModule.status == "aktiv")
            .all()
        )

        # Alle Geräte am gleichen Rack (vereinfacht — später circuit_id filtern)
        devices = (
            s.query(Device)
            .filter(Device.rack_id == unit.rack_id, Device.tdp_watt.isnot(None))
            .all()
        )

    if not modules:
        rprint("[red]Keine aktiven Module gefunden.[/red]")
        raise typer.Exit(1)

    last_watt = sum(float(d.tdp_watt) for d in devices)
    last_kw = last_watt / 1000

    # Peak: jedes Gerät × eigenen Faktor, dann summieren
    peak_watt = sum(
        float(d.tdp_watt) * float(d.einschaltstrom_faktor or 2.5) for d in devices
    )
    peak_kw = peak_watt / 1000

    module_kw = [float(m.leistung_kw) for m in modules]
    inst_kw = sum(module_kw)
    max_modul = max(module_kw)
    n1_kw = inst_kw - max_modul  # N+1: größtes Modul fällt aus
    reserve_kw = inst_kw - last_kw
    kaltstart_ok = peak_kw <= n1_kw

    # Ausgabe
    console.rule(f"[bold]USV Berechnung — {unit.bezeichnung}[/bold]")
    t = Table("Parameter", "Wert", show_header=True)
    t.add_row("Geräte (mit TDP)", str(len(devices)))
    t.add_row("Last (Σ TDP)", f"{last_kw:.2f} kW")
    t.add_row("Peak (Einschaltstrom)", f"[yellow]{peak_kw:.2f} kW[/yellow]")
    t.add_row("Aktive Module", f"{len(modules)} × Module")
    t.add_row("Installiert", f"{inst_kw:.2f} kW")
    t.add_row(
        "N+1 Kapazität", f"{n1_kw:.2f} kW  (ohne größtes Modul: {max_modul:.1f} kW)"
    )
    t.add_row("Reserve", f"{reserve_kw:.2f} kW")

    status = (
        "[green]✓ JA[/green]"
        if kaltstart_ok
        else "[red]✗ NEIN — Peak übersteigt N+1![/red]"
    )
    t.add_row("Kaltstart (N+1) OK", status)
    console.print(t)

    if not kaltstart_ok:
        fehlend = peak_kw - n1_kw
        rprint(
            f"[red]→ Fehlende Kapazität für sicheren Kaltstart: {fehlend:.2f} kW[/red]"
        )
        module_zusatz = -(-fehlend // max_modul)  # ceil
        rprint(
            f"[yellow]→ Empfehlung: {int(module_zusatz)} weiteres Modul(e) à {max_modul:.0f} kW hinzufügen.[/yellow]"
        )


# ══════════════════════════════════════════════════════════════
# PHASE CHECK
# ══════════════════════════════════════════════════════════════
@app.command("phase-check")
def phase_check(rack_id: int = typer.Argument(..., help="Rack-ID")):
    """
    Phasenverteilung prüfen.
    Zeigt Last je Phase und Ungleichgewicht in %.
    Ziel: max. 10% Imbalance.
    """
    with Session(engine) as s:
        devices = (
            s.query(Device)
            .filter(
                Device.rack_id == rack_id,
                Device.tdp_watt.isnot(None),
                Device.phase.isnot(None),
            )
            .all()
        )

    phasen = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
    for d in devices:
        if d.phase in phasen:
            phasen[d.phase] += float(d.tdp_watt)

    gesamt = sum(phasen.values())
    if gesamt == 0:
        rprint("[yellow]Keine Geräte mit Phase-Zuweisung gefunden.[/yellow]")
        raise typer.Exit()

    ideal = gesamt / 3
    max_abw = max(abs(w - ideal) for w in phasen.values())
    imbalance = (max_abw / ideal) * 100

    console.rule("[bold]Phasenverteilung[/bold]")
    t = Table("Phase", "Last (W)", "Last (kW)", "Anteil %")
    for phase, watt in phasen.items():
        t.add_row(
            phase, f"{watt:.0f}", f"{watt / 1000:.2f}", f"{watt / gesamt * 100:.1f}%"
        )
    console.print(t)

    farbe = "green" if imbalance <= 10 else "red"
    rprint(f"[{farbe}]Ungleichgewicht: {imbalance:.1f}%  (Ziel: ≤ 10%)[/{farbe}]")

    if imbalance > 10:
        # Empfehlung: welches Gerät wohin verschieben
        max_phase = max(phasen, key=phasen.get)
        min_phase = min(phasen, key=phasen.get)
        rprint(
            f"[yellow]→ Geräte von {max_phase} nach {min_phase} verschieben.[/yellow]"
        )


if __name__ == "__main__":
    app()
