"""Regeln des Serverraum-Umbaus. Reine Funktionen ohne Datenbankzugriff.

Hier steht, was fachlich gilt: welche Enden ein Kabel hat, welche Kabel zum Umfang
gehören, wann eingefroren werden darf und welche Statuswechsel erlaubt sind. Service
und Oberfläche fragen dieselben Funktionen, damit Anzeige und Server nie auseinanderlaufen.
"""

from dataclasses import dataclass
from typing import Collection, Iterable, Mapping, Sequence

# --- Status -----------------------------------------------------------------
ERFASSUNG = "erfassung"
RUECKBAU = "rueckbau"
UMBAU = "umbau"
WIEDERAUFBAU = "wiederaufbau"
ABGESCHLOSSEN = "abgeschlossen"
VERWORFEN = "verworfen"

GESTECKT = "gesteckt"
ABGEKLEMMT = "abgeklemmt"
ANGEKLEMMT = "angeklemmt"
ANGEKLEMMT_ABWEICHEND = "angeklemmt_abweichend"

UMBAU_STATUS_LABEL: Mapping[str, str] = {
    ERFASSUNG: "Erfassung",
    RUECKBAU: "Rückbau",
    UMBAU: "Umbau",
    WIEDERAUFBAU: "Wiederaufbau",
    ABGESCHLOSSEN: "abgeschlossen",
    VERWORFEN: "verworfen",
}

# --- Aktionen an einem Ende ---------------------------------------------------
ABKLEMMEN = "abklemmen"
ABKLEMMEN_ZURUECK = "abklemmen_zurueck"
ANKLEMMEN = "anklemmen"
ANKLEMMEN_ABWEICHEND = "anklemmen_abweichend"
ANKLEMMEN_ZURUECK = "anklemmen_zurueck"

# Jede Aktion gehört zu genau einer Phase des Umbaus.
AKTION_PHASE: Mapping[str, str] = {
    ABKLEMMEN: RUECKBAU,
    ABKLEMMEN_ZURUECK: RUECKBAU,
    ANKLEMMEN: WIEDERAUFBAU,
    ANKLEMMEN_ABWEICHEND: WIEDERAUFBAU,
    ANKLEMMEN_ZURUECK: WIEDERAUFBAU,
}

# (Aktion, Status des Endes vorher) → Status des Endes nachher.
# Rücknahmen gehen genau eine Stufe zurück.
ENDE_UEBERGAENGE: Mapping[tuple[str, str], str] = {
    (ABKLEMMEN, GESTECKT): ABGEKLEMMT,
    (ABKLEMMEN_ZURUECK, ABGEKLEMMT): GESTECKT,
    (ANKLEMMEN, ABGEKLEMMT): ANGEKLEMMT,
    (ANKLEMMEN_ABWEICHEND, ABGEKLEMMT): ANGEKLEMMT_ABWEICHEND,
    (ANKLEMMEN_ZURUECK, ANGEKLEMMT): ABGEKLEMMT,
    (ANKLEMMEN_ZURUECK, ANGEKLEMMT_ABWEICHEND): ABGEKLEMMT,
}

# Zielstatus je Aktion (unabhängig vom Ausgangsstatus), für die Idempotenzprüfung.
AKTION_ZIEL: Mapping[str, str] = {
    ABKLEMMEN: ABGEKLEMMT,
    ABKLEMMEN_ZURUECK: GESTECKT,
    ANKLEMMEN: ANGEKLEMMT,
    ANKLEMMEN_ABWEICHEND: ANGEKLEMMT_ABWEICHEND,
    ANKLEMMEN_ZURUECK: ABGEKLEMMT,
}

Endpunkt = tuple[int | None, str | None]


# --- Sicht auf ein Kabel ------------------------------------------------------
@dataclass(frozen=True)
class StrangSicht:
    strand_number: int
    device_id: int | None
    port: str | None
    farbe: str | None = None


@dataclass(frozen=True)
class KabelSicht:
    """Was die Regeln von einem Kabel wissen müssen."""

    id: int
    kabel_nr: str | None
    typ: str
    kategorie: str | None  # None = Kabel ohne Kabeltyp
    kabeltyp_name: str | None
    enden_a: int
    enden_b: int
    farbe: str | None
    von: Endpunkt
    nach: Endpunkt
    straenge: tuple[StrangSicht, ...] = ()

    @property
    def bezeichnung(self) -> str:
        return self.kabel_nr or f"#{self.id}"


@dataclass(frozen=True)
class EndeSoll:
    """Ein physisches Stecker-Ende, wie es beim Einfrieren festgehalten wird."""

    cable_id: int
    seite: str
    ende_nr: int
    strand_number: int | None
    device_id: int | None
    port: str | None
    farbe: str | None


# --- Kabel: Strom, Enden, Vollständigkeit, Umfang -----------------------------
def ist_strom(kabel: KabelSicht) -> bool:
    """Stromkabel gehören in dieser Version nicht zum Umbau.

    Maßgeblich ist die Kategorie des Kabeltyps. Ein Kabel ohne Kabeltyp gilt als
    Strom, wenn sein bisheriger typ mit "Strom" beginnt (gleiche Regel wie die
    Belegungsprüfung).
    """
    if kabel.kategorie is not None:
        return kabel.kategorie == "strom"
    return kabel.typ.startswith("Strom")


def enden_fuer_kabel(kabel: KabelSicht) -> list[EndeSoll]:
    """Alle Enden eines Kabels: A = 1 Ende, B = 1 Ende oder je Strang ein Ende."""
    if ist_strom(kabel):
        return []
    enden = [
        EndeSoll(
            cable_id=kabel.id,
            seite="A",
            ende_nr=1,
            strand_number=None,
            device_id=kabel.von[0],
            port=kabel.von[1],
            farbe=kabel.farbe,
        )
    ]
    if kabel.enden_b <= 1:
        enden.append(
            EndeSoll(
                cable_id=kabel.id,
                seite="B",
                ende_nr=1,
                strand_number=None,
                device_id=kabel.nach[0],
                port=kabel.nach[1],
                farbe=kabel.farbe,
            )
        )
        return enden
    for strang in sorted(kabel.straenge, key=lambda s: s.strand_number):
        enden.append(
            EndeSoll(
                cable_id=kabel.id,
                seite="B",
                ende_nr=strang.strand_number,
                strand_number=strang.strand_number,
                device_id=strang.device_id,
                port=strang.port,
                farbe=strang.farbe or kabel.farbe,
            )
        )
    return enden


def _endpunkt_fehlt(endpunkt: Endpunkt) -> bool:
    return not endpunkt[0] or not endpunkt[1]


def unvollstaendig(kabel: KabelSicht) -> list[str]:
    """Gründe, warum ein Kabel noch nicht eingefroren werden kann (leer = vollständig)."""
    if ist_strom(kabel):
        return []
    gruende: list[str] = []
    if kabel.kategorie is None:
        gruende.append("Kabeltyp fehlt")
    if kabel.enden_a != 1:
        gruende.append(
            f"Kabeltyp mit {kabel.enden_a} A-Enden wird im Umbau nicht unterstützt"
        )
    if _endpunkt_fehlt(kabel.von):
        gruende.append("A-Ende fehlt (Gerät oder Port)")
    if kabel.enden_b <= 1:
        if _endpunkt_fehlt(kabel.nach):
            gruende.append("Gegenstelle fehlt (Gerät oder Port)")
        return gruende

    if len(kabel.straenge) != kabel.enden_b:
        gruende.append(
            f"B-Enden fehlen ({len(kabel.straenge)} von {kabel.enden_b} Strängen)"
        )
    offene = sorted(
        strang.strand_number
        for strang in kabel.straenge
        if _endpunkt_fehlt((strang.device_id, strang.port))
    )
    if offene:
        nummern = ", ".join(str(nummer) for nummer in offene)
        gruende.append(f"B-Enden fehlen (Gerät oder Port an Ende {nummern})")
    return gruende


def geraete_eines_kabels(kabel: KabelSicht) -> set[int]:
    """Alle Geräte, an denen irgendein Ende des Kabels steckt."""
    kandidaten = [kabel.von[0], kabel.nach[0], *(s.device_id for s in kabel.straenge)]
    return {device_id for device_id in kandidaten if device_id}


def im_umfang(kabel: KabelSicht, geraete_im_umfang: Collection[int]) -> bool:
    """Nicht-Strom-Kabel mit mindestens einem Ende an einem Gerät im Umfang."""
    if ist_strom(kabel):
        return False
    return bool(geraete_eines_kabels(kabel) & set(geraete_im_umfang))


def einfrier_sperren(
    kabel_im_umfang: Iterable[KabelSicht],
    geraete_im_umfang: Sequence[tuple[int, str]],
    bestaetigte_geraete: Collection[int],
) -> list[str]:
    """Jeder Grund, der das Einfrieren verhindert, namentlich. Leer = Einfrieren erlaubt."""
    sperren: list[str] = []
    for kabel in sorted(kabel_im_umfang, key=lambda k: k.bezeichnung):
        gruende = unvollstaendig(kabel)
        if gruende:
            sperren.append(f"Kabel {kabel.bezeichnung}: {'; '.join(gruende)}")
    bestaetigt = set(bestaetigte_geraete)
    for device_id, name in sorted(geraete_im_umfang, key=lambda g: g[1]):
        if device_id not in bestaetigt:
            sperren.append(f"Gerät {name}: nicht als vollständig erfasst bestätigt")
    return sperren


# --- Enden: Aktionen und Sperrgründe ------------------------------------------
def aktion_sperrgrund(aktion: str, ende_status: str, umbau_status: str) -> str | None:
    """Warum diese Aktion an diesem Ende jetzt nicht geht. None = erlaubt.

    Ist das Ziel der Aktion schon erreicht, ist das kein Sperrgrund: der Aufrufer
    antwortet dann ohne Änderung (siehe ziel_schon_erreicht).
    """
    phase = AKTION_PHASE[aktion]
    if umbau_status != phase:
        return (
            f"{_aktion_label(aktion)} ist nur im Status "
            f"„{UMBAU_STATUS_LABEL[phase]}“ möglich, der Umbau ist im Status "
            f"„{UMBAU_STATUS_LABEL.get(umbau_status, umbau_status)}“."
        )
    if (aktion, ende_status) in ENDE_UEBERGAENGE:
        return None
    if ende_status == AKTION_ZIEL[aktion]:
        return None
    return _falscher_ende_status(aktion, ende_status)


def ziel_schon_erreicht(aktion: str, ende_status: str) -> bool:
    return ende_status == AKTION_ZIEL[aktion]


def ziel_status(aktion: str, ende_status: str) -> str | None:
    """Status des Endes nach der Aktion; None, wenn der Übergang nicht existiert."""
    return ENDE_UEBERGAENGE.get((aktion, ende_status))


def sperrgrund(ende_status: str, umbau_status: str) -> str | None:
    """Warum an diesem Ende gerade gar nichts gebucht werden kann. None = buchbar.

    EINE Regel für Anzeige und Server: Ein Ende ist buchbar, wenn im aktuellen
    Status des Umbaus mindestens eine Aktion von seinem Status aus existiert.
    """
    if umbau_status == ERFASSUNG:
        return "Der Umbau ist noch in der Erfassung. Enden entstehen beim Einfrieren."
    if umbau_status == UMBAU:
        return (
            "Im Status „Umbau“ wird nichts gebucht. Zum Anklemmen in den "
            "Wiederaufbau wechseln."
        )
    if umbau_status in (ABGESCHLOSSEN, VERWORFEN):
        return f"Der Umbau ist {UMBAU_STATUS_LABEL[umbau_status]}."
    for (aktion, von_status), _ in ENDE_UEBERGAENGE.items():
        if von_status == ende_status and AKTION_PHASE[aktion] == umbau_status:
            return None
    if umbau_status == WIEDERAUFBAU and ende_status == GESTECKT:
        return "Das Ende wurde nicht abgeklemmt und kann nicht angeklemmt werden."
    return (
        f"Im Status „{UMBAU_STATUS_LABEL[umbau_status]}“ ist für ein Ende im "
        f"Status „{ende_status}“ keine Buchung möglich."
    )


def _aktion_label(aktion: str) -> str:
    if aktion in (ABKLEMMEN, ABKLEMMEN_ZURUECK):
        return "Abklemmen"
    return "Anklemmen"


def _falscher_ende_status(aktion: str, ende_status: str) -> str:
    if aktion == ABKLEMMEN:
        return (
            f"Das Ende ist im Status „{ende_status}“ und kann nicht abgeklemmt werden."
        )
    if aktion == ABKLEMMEN_ZURUECK:
        return (
            f"Das Ende ist im Status „{ende_status}“. Zurücknehmen geht nur für ein "
            "abgeklemmtes Ende."
        )
    if aktion in (ANKLEMMEN, ANKLEMMEN_ABWEICHEND):
        if ende_status in (ANGEKLEMMT, ANGEKLEMMT_ABWEICHEND):
            return (
                "Das Ende ist bereits angeklemmt. Zum Ändern zuerst das Anklemmen "
                "zurücknehmen."
            )
        return (
            f"Das Ende ist im Status „{ende_status}“ und kann nicht angeklemmt werden."
        )
    return (
        f"Das Ende ist im Status „{ende_status}“. Zurücknehmen geht nur für ein "
        "angeklemmtes Ende."
    )


def ist_abweichung(
    soll: Endpunkt, ist_device_id: int | None, ist_port: str | None
) -> bool:
    """Weicht der gemeldete Ist-Port vom Soll ab? Fehlende Angaben gelten als Soll."""
    device_id = ist_device_id if ist_device_id is not None else soll[0]
    port = ist_port if ist_port else soll[1]
    return (device_id, port) != soll


# --- Umbau: Statuswechsel -----------------------------------------------------
# Erlaubte Vorwärtswechsel. → verworfen geht zusätzlich aus jedem Status außer abgeschlossen.
UMBAU_UEBERGAENGE: Mapping[str, str] = {
    ERFASSUNG: RUECKBAU,
    RUECKBAU: UMBAU,
    UMBAU: WIEDERAUFBAU,
    WIEDERAUFBAU: ABGESCHLOSSEN,
}


def umbau_uebergang_sperrgrund(
    status: str,
    ziel: str,
    enden_je_status: Mapping[str, int],
    einfrieren_gesperrt: Sequence[str] = (),
) -> str | None:
    """Warum der Umbau nicht von status nach ziel wechseln kann. None = erlaubt."""
    if ziel == VERWORFEN:
        if status == ABGESCHLOSSEN:
            return "Ein abgeschlossener Umbau kann nicht verworfen werden."
        return None
    if UMBAU_UEBERGAENGE.get(status) != ziel:
        return (
            f"Der Wechsel von „{UMBAU_STATUS_LABEL.get(status, status)}“ nach "
            f"„{UMBAU_STATUS_LABEL.get(ziel, ziel)}“ ist nicht vorgesehen."
        )
    if ziel == RUECKBAU and einfrieren_gesperrt:
        return "Einfrieren gesperrt:\n" + "\n".join(
            f"- {sperre}" for sperre in einfrieren_gesperrt
        )
    if ziel == UMBAU:
        offen = enden_je_status.get(GESTECKT, 0)
        if offen:
            return (
                f"{offen} {_enden(offen)} noch gesteckt. Der Umbau beginnt erst, "
                "wenn alle Enden abgeklemmt sind."
            )
    if ziel == ABGESCHLOSSEN:
        offen = enden_je_status.get(GESTECKT, 0) + enden_je_status.get(ABGEKLEMMT, 0)
        if offen:
            return (
                f"{offen} {_enden(offen)} noch nicht angeklemmt. Abschließen geht "
                "erst, wenn kein Ende mehr gesteckt oder abgeklemmt ist."
            )
    return None


def naechste_ziele(status: str) -> list[str]:
    """Statuswechsel, die die Oberfläche in diesem Status anbietet."""
    ziele: list[str] = []
    if status in UMBAU_UEBERGAENGE:
        ziele.append(UMBAU_UEBERGAENGE[status])
    if status not in (ABGESCHLOSSEN, VERWORFEN):
        ziele.append(VERWORFEN)
    return ziele


def _enden(anzahl: int) -> str:
    return "Ende ist" if anzahl == 1 else "Enden sind"
