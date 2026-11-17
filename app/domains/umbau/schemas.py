from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

UmbauStatus = Literal[
    "erfassung", "rueckbau", "umbau", "wiederaufbau", "abgeschlossen", "verworfen"
]


# === Eingaben ================================================================
class UmbauCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    beschreibung: Optional[str] = None
    rack_ids: List[int] = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def _name_nicht_leer(cls, wert: str) -> str:
        wert = wert.strip()
        if not wert:
            raise ValueError("Der Name darf nicht leer sein")
        return wert


class StatusWechsel(BaseModel):
    ziel: UmbauStatus


class AnklemmenEingabe(BaseModel):
    angeklemmt: bool
    # Nur bei Abweichung vom Soll: wo das Ende tatsächlich steckt und warum.
    ist_device_id: Optional[int] = None
    ist_port: Optional[str] = Field(None, max_length=50)
    grund: Optional[str] = Field(None, max_length=255)

    @field_validator("ist_port", "grund")
    @classmethod
    def _leer_ist_none(cls, wert: Optional[str]) -> Optional[str]:
        if wert is None:
            return None
        return wert.strip() or None


# === Ausgaben ================================================================
class RackKurz(BaseModel):
    id: int
    name: str


class FortschrittZahlen(BaseModel):
    """Zählung der Enden. angeklemmt enthält auch abweichend angeklemmte Enden."""

    enden_gesamt: int = 0
    gesteckt: int = 0
    abgeklemmt: int = 0
    angeklemmt: int = 0
    abweichend: int = 0


class UmbauListe(BaseModel):
    id: int
    name: str
    beschreibung: Optional[str] = None
    status: UmbauStatus
    erstellt_am: datetime
    erstellt_von: Optional[str] = None
    eingefroren_am: Optional[datetime] = None
    abgeschlossen_am: Optional[datetime] = None
    racks: List[RackKurz] = []
    geraete_gesamt: int = 0
    geraete_bestaetigt: int = 0
    fortschritt: FortschrittZahlen = FortschrittZahlen()


class GeraetErfassung(BaseModel):
    """Erfassungsfortschritt eines Geräts im Umfang."""

    device_id: int
    hostname: str
    typ: str
    rack_id: Optional[int] = None
    rack_name: Optional[str] = None
    kabel_gesamt: int = 0
    kabel_unvollstaendig: int = 0
    bestaetigt: bool = False
    bestaetigt_am: Optional[datetime] = None
    bestaetigt_von: Optional[str] = None


class EndeOut(BaseModel):
    id: int
    cable_id: Optional[int] = None
    strand_number: Optional[int] = None
    seite: str
    ende_nr: int
    soll_device_id: Optional[int] = None
    soll_device_name: str
    soll_rack_name: Optional[str] = None
    soll_port: str
    kabel_nr: Optional[str] = None
    kabeltyp_name: str
    kategorie: str
    farbe: Optional[str] = None
    status: str
    abgeklemmt_am: Optional[datetime] = None
    abgeklemmt_von: Optional[str] = None
    angeklemmt_am: Optional[datetime] = None
    angeklemmt_von: Optional[str] = None
    ist_device_id: Optional[int] = None
    ist_device_name: Optional[str] = None
    ist_port: Optional[str] = None
    abweichung_grund: Optional[str] = None
    # Abgeleitet, nicht gespeichert:
    gegenseite: List[str] = []
    sperrgrund: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class GeraetFortschritt(BaseModel):
    device_name: str
    fortschritt: FortschrittZahlen


class RackFortschritt(BaseModel):
    rack_name: str
    fortschritt: FortschrittZahlen
    geraete: List[GeraetFortschritt] = []


class StatusZiel(BaseModel):
    """Ein möglicher Statuswechsel samt Sperrgrund (None = jetzt möglich)."""

    ziel: UmbauStatus
    sperrgrund: Optional[str] = None


class EreignisOut(BaseModel):
    id: int
    ende_id: Optional[int] = None
    von_status: Optional[str] = None
    nach_status: str
    grund: Optional[str] = None
    benutzer: Optional[str] = None
    zeitpunkt: datetime
    model_config = ConfigDict(from_attributes=True)


class UmbauDetail(BaseModel):
    id: int
    name: str
    beschreibung: Optional[str] = None
    status: UmbauStatus
    erstellt_am: datetime
    erstellt_von: Optional[str] = None
    eingefroren_am: Optional[datetime] = None
    eingefroren_von: Optional[str] = None
    abgeschlossen_am: Optional[datetime] = None
    abgeschlossen_von: Optional[str] = None
    racks: List[RackKurz] = []
    # Erfassung
    geraete: List[GeraetErfassung] = []
    einfrier_sperren: List[str] = []
    # Rückbau / Wiederaufbau
    enden: List[EndeOut] = []
    fortschritt: FortschrittZahlen = FortschrittZahlen()
    fortschritt_racks: List[RackFortschritt] = []
    naechste_status: List[StatusZiel] = []
    ereignisse: List[EreignisOut] = []
