"""
app/domains/power/metrics.py

Reine, seiteneffektfreie Strom-Mathematik für KAiTix.

Gerettet aus cli.py (usv_calc / phase_check) und dem alten audit_vde_compliance().
Eine Quelle der Wahrheit — wird sowohl vom USV-Setup-Service als auch vom
geplanten Phasen-Imbalance-Tab aufgerufen.

WICHTIG — Charakter dieser Funktion:
Dies ist ein KONZEPT-/SIMULATIONSwerkzeug. Die Kennzahlen (N+1, Kaltstart-Peak,
Imbalance, kaltstart_ok) beschreiben eine *gerechnete* Konfiguration. Sie sind
KEINE VDE-Abnahme und KEIN Zertifikat. Die formale Abnahme der realen Anlage
erfolgt unter realen Bedingungen durch qualifizierte Prüfer mit Messung und
Haftung. Diese Funktion plant und dokumentiert — sie zertifiziert nicht.

Keine DB, kein ORM, kein I/O. Nimmt einfache Datenklassen, gibt Zahlen zurück.
Damit trivial testbar und unabhängig vom async-Stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Einschaltstrom-Faktor: in der Leistungsbeschreibung explizit gefordert
# (2,5 × Nennleistung je Gerät, sofern nicht herstellerseitig abweichend).
DEFAULT_EINSCHALTSTROM_FAKTOR = 2.5

# Zielwert Phasen-Imbalance laut LB (Abschnitt 3.3): ≤ 10 %.
IMBALANCE_ZIEL_PCT = 10.0


@dataclass(frozen=True)
class DeviceLoad:
    """Last-Beitrag eines Geräts. Entkoppelt von der ORM-Device-Klasse."""
    tdp_watt: float
    phase: str | None = None
    einschaltstrom_faktor: float = DEFAULT_EINSCHALTSTROM_FAKTOR


@dataclass(frozen=True)
class ModuleSpec:
    """Ein aktives Leistungsmodul."""
    leistung_kw: float


@dataclass(frozen=True)
class PowerMetricsResult:
    """
    Ergebnis der Simulation. Reine Kennzahlen.

    kaltstart_ok ist ein Simulations-Ergebnis ("reicht die N+1-Kapazität
    rechnerisch für den Kaltstart-Peak"), kein Freigabe-Stempel.
    """
    last_kw: float
    peak_kw: float
    installiert_kw: float
    groesstes_modul_kw: float
    n1_kw: float
    reserve_kw: float
    kaltstart_reserve_kw: float          # n1_kw - peak_kw (kann negativ sein)
    kaltstart_ok: bool                   # Simulation: peak_kw <= n1_kw
    phasen_last_kw: dict[str, float]
    phasen_imbalance_pct: float
    hinweise: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = {
            "last_kw": round(self.last_kw, 3),
            "peak_kw": round(self.peak_kw, 3),
            "installiert_kw": round(self.installiert_kw, 3),
            "groesstes_modul_kw": round(self.groesstes_modul_kw, 3),
            "n1_kw": round(self.n1_kw, 3),
            "reserve_kw": round(self.reserve_kw, 3),
            "kaltstart_reserve_kw": round(self.kaltstart_reserve_kw, 3),
            "kaltstart_ok": self.kaltstart_ok,
            "phasen_last_kw": {k: round(v, 3) for k, v in self.phasen_last_kw.items()},
            "phasen_imbalance_pct": round(self.phasen_imbalance_pct, 1),
            "hinweise": list(self.hinweise),
        }
        return d


def calculate_power_metrics(
    devices: list[DeviceLoad],
    modules: list[ModuleSpec],
) -> PowerMetricsResult:
    """
    Berechnet die USV-Simulations-Kennzahlen für eine Konfiguration.

    Formeln (gerettet aus cli.py):
      last_kw         = Σ TDP / 1000
      peak_kw         = Σ (TDP × Einschaltstrom-Faktor) / 1000
      installiert_kw  = Σ aktive Modulleistungen
      n1_kw           = installiert_kw − größtes Modul        (N+1: größtes fällt aus)
      reserve_kw      = installiert_kw − last_kw
      kaltstart_reserve_kw = n1_kw − peak_kw
      kaltstart_ok    = peak_kw ≤ n1_kw                       (Simulation, kein Zertifikat)
      imbalance_pct   = max|phase − ideal| / ideal × 100      (ideal = gesamt / 3)

    Robust gegen leere Eingaben: ohne Module ist n1_kw = 0, kaltstart_ok = False.
    Wirft nicht — ein Planungstool soll auch Teil-Konfigurationen rechnen können.
    """
    hinweise: list[str] = []

    # ── Last & Peak ────────────────────────────────────────────
    last_watt = sum(d.tdp_watt for d in devices)
    last_kw = last_watt / 1000.0

    peak_watt = sum(
        d.tdp_watt * (d.einschaltstrom_faktor or DEFAULT_EINSCHALTSTROM_FAKTOR)
        for d in devices
    )
    peak_kw = peak_watt / 1000.0

    # ── Modulkapazität & N+1 ───────────────────────────────────
    module_kw = [m.leistung_kw for m in modules]
    installiert_kw = sum(module_kw)
    groesstes_modul_kw = max(module_kw) if module_kw else 0.0
    # N+1: das leistungsstärkste Einzelmodul fällt aus (LB Abschnitt 2.2)
    n1_kw = installiert_kw - groesstes_modul_kw
    reserve_kw = installiert_kw - last_kw
    kaltstart_reserve_kw = n1_kw - peak_kw
    kaltstart_ok = bool(module_kw) and peak_kw <= n1_kw

    if not module_kw:
        hinweise.append("Keine aktiven Module übergeben — N+1-Kapazität = 0 kW.")
    elif not kaltstart_ok:
        # Tatsachenbeschreibung, kein Verdikt. Inkl. Empfehlung wie im alten Tool,
        # aber als Planungs-Hinweis formuliert.
        fehlend = peak_kw - n1_kw
        hinweise.append(
            f"Kaltstart-Peak ({peak_kw:.2f} kW) liegt rechnerisch über der "
            f"N+1-Kapazität ({n1_kw:.2f} kW) — Differenz {fehlend:.2f} kW."
        )
        if groesstes_modul_kw > 0:
            zusatz = int(-(-fehlend // groesstes_modul_kw))  # ceil
            hinweise.append(
                f"Zur Deckung in der Simulation: +{zusatz} Modul(e) "
                f"à {groesstes_modul_kw:.0f} kW."
            )

    if reserve_kw < 0:
        hinweise.append(
            f"Last ({last_kw:.2f} kW) übersteigt installierte Kapazität "
            f"({installiert_kw:.2f} kW)."
        )

    # ── Phasen-Imbalance ───────────────────────────────────────
    phasen: dict[str, float] = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
    for d in devices:
        if d.phase in phasen and d.tdp_watt:
            phasen[d.phase] += d.tdp_watt / 1000.0  # in kW

    gesamt = sum(phasen.values())
    if gesamt > 0:
        ideal = gesamt / 3.0
        max_abw = max(abs(w - ideal) for w in phasen.values())
        imbalance_pct = (max_abw / ideal) * 100.0
        if imbalance_pct > IMBALANCE_ZIEL_PCT:
            max_phase = max(phasen, key=phasen.get)
            min_phase = min(phasen, key=phasen.get)
            hinweise.append(
                f"Phasen-Imbalance {imbalance_pct:.1f} % über Zielwert "
                f"{IMBALANCE_ZIEL_PCT:.0f} % — Last von {max_phase} nach "
                f"{min_phase} verschieben (Simulation)."
            )
    else:
        imbalance_pct = 0.0

    return PowerMetricsResult(
        last_kw=last_kw,
        peak_kw=peak_kw,
        installiert_kw=installiert_kw,
        groesstes_modul_kw=groesstes_modul_kw,
        n1_kw=n1_kw,
        reserve_kw=reserve_kw,
        kaltstart_reserve_kw=kaltstart_reserve_kw,
        kaltstart_ok=kaltstart_ok,
        phasen_last_kw=phasen,
        phasen_imbalance_pct=imbalance_pct,
        hinweise=hinweise,
    )
