from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from decimal import Decimal
from datetime import datetime


# === USV MODULE SCHEMAS ===
class UsvModuleBase(BaseModel):
    usv_unit_id: int
    slot: int = Field(..., ge=0)
    leistung_kw: Decimal = Field(..., gt=0)
    status: str = "aktiv"
    seriennummer: Optional[str] = None


class UsvModuleCreate(UsvModuleBase):
    pass


class UsvModuleUpdate(BaseModel):
    slot: Optional[int] = Field(None, ge=0)
    leistung_kw: Optional[Decimal] = Field(None, gt=0)
    status: Optional[str] = None
    seriennummer: Optional[str] = None


class UsvModule(UsvModuleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# === USV UNIT SCHEMAS ===
class UsvUnitBase(BaseModel):
    bezeichnung: str
    hersteller: str = "Wöhrle SVS"
    rack_id: int
    max_kw: Decimal = Field(..., gt=0)
    battery_strings: int = 2
    blocks_per_string: int = 32
    block_voltage_v: Decimal = Decimal("12.00")
    block_capacity_ah: Decimal = Decimal("100.00")


class UsvUnitCreate(UsvUnitBase):
    pass


class UsvUnitUpdate(BaseModel):
    bezeichnung: Optional[str] = None
    hersteller: Optional[str] = None
    rack_id: Optional[int] = None
    max_kw: Optional[Decimal] = Field(None, gt=0)
    battery_strings: Optional[int] = None
    blocks_per_string: Optional[int] = None
    block_voltage_v: Optional[Decimal] = None
    block_capacity_ah: Optional[Decimal] = None


class UsvUnit(UsvUnitBase):
    id: int
    modules: List[UsvModule] = []
    model_config = ConfigDict(from_attributes=True)


# === USV SIMULATION EVENT SCHEMAS ===
class UsvSimulationEventResponse(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    severity: str
    description: str
    usv_unit_id: Optional[int] = None
    snapshot_json: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# === POWER AUDIT SCHEMAS ===
class UsvCalculationResponse(BaseModel):
    id: int
    berechnet_am: datetime
    usv_unit_id: int
    last_kw: Decimal
    peak_kw: Decimal
    installiert_kw: Decimal
    reserve_kw: Decimal
    n1_kw: Decimal
    kaltstart_ok: bool
    bemerkung: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class VdeAuditResult(BaseModel):
    rule: str
    status: str  # "ok" | "warning" | "error"
    message: str


class PowerAuditResponse(BaseModel):
    usv_unit_id: int
    audit_results: List[VdeAuditResult]
    calculations: List[UsvCalculationResponse]


# ──────────────────────────────────────────────────────────────
# SETUP SCHEMAS
# ──────────────────────────────────────────────────────────────
Phase = Literal["L1", "L2", "L3"]

class UsvSystemSetupRequest(BaseModel):
    """
    Eingabe für POST /api/v1/power/usv/setup.

    Erzeugt in einer Transaktion: UsvUnit + UsvModule(s) + DistributionPanel
    + DistributionCircuit(s). Reine Doku-Records, kein Hardware-Control.
    """

    # ── USV-Schrank ────────────────────────────────────────────
    usv_bezeichnung: str = Field(
        ..., min_length=1, max_length=100,
        examples=["Wöhrle 40kW Schrank"],
    )
    usv_kw: Decimal = Field(
        ..., gt=0, le=2000,
        description="Schrank-Maximum in kW (UsvUnit.max_kw)",
        examples=[40.0],
    )
    rack_id: int = Field(..., gt=0, description="Ziel-Rack (Upsert-Key Teil 2)")
    hersteller: str = Field(default="Wöhrle SVS", max_length=100)

    # ── Leistungsmodule ────────────────────────────────────────
    module_kw: Decimal = Field(
        ..., gt=0, le=500,
        description="Nennleistung je Modul in kW (symmetrische Auslegung lt. LB)",
        examples=[10.0],
    )
    module_count: int = Field(
        ..., ge=1, le=12,
        description="Anzahl aktiver Module bei Inbetriebnahme",
        examples=[4],
    )
    reserve_module_count: int = Field(
        default=0, ge=0, le=12,
        description="Zusätzliche Module mit Status 'reserve' (N+1-Redundanz)",
    )

    # ── Unterverteilung / Stromkreise ──────────────────────────
    panel_bezeichnung: str = Field(
        ..., min_length=1, max_length=100,
        examples=["UV-RZ-01"],
    )
    phases: list[Phase] = Field(
        default_factory=lambda: ["L1", "L2", "L3"],
        description="Phasen, für die je ein Stromkreis erzeugt wird",
    )
    absicherung_a: Decimal = Field(
        ..., gt=0, le=630,
        description="Absicherung je Stromkreis in Ampere",
        examples=[16.0],
    )

    # ── Audit (Punkt 6) ────────────────────────────────────────
    geaendert_von: str = Field(
        ..., min_length=1, max_length=100,
        description="Freitext-Audit: wer legt das System an",
    )

    # ── Validatoren ────────────────────────────────────────────
    @field_validator("phases")
    @classmethod
    def _phases_unique_and_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Mindestens eine Phase erforderlich (L1/L2/L3).")
        if len(set(v)) != len(v):
            raise ValueError("Phasen müssen eindeutig sein (keine Duplikate).")
        return v

    @model_validator(mode="after")
    def _slots_fit(self) -> "UsvSystemSetupRequest":
        total = self.module_count + self.reserve_module_count
        if total > 12:
            raise ValueError(
                f"Gesamtzahl Module ({total}) übersteigt max. 12 Slots."
            )
        return self


class PowerMetrics(BaseModel):
    """Ergebnis der geretteten Berechnung (siehe metrics.calculate_power_metrics)."""
    last_kw: float
    peak_kw: float
    installiert_kw: float
    n1_kw: float
    reserve_kw: float
    groesstes_modul_kw: float
    kaltstart_ok: bool
    phasen_last_kw: dict[str, float]
    phasen_imbalance_pct: float


class UsvSystemSetupResponse(BaseModel):
    """Was beim Setup erzeugt wurde + abgeleitete Kennzahlen + Hinweise."""
    usv_unit_id: int
    module_ids: list[int]
    panel_id: int
    circuit_ids: list[int]
    metrics: PowerMetrics
    warnings: list[str] = Field(
        default_factory=list,
        description="Nicht-blockierende Hinweise (z.B. N+1 nicht erfüllt)",
    )
