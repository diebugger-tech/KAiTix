# USV-Stromlaufplan & Topologie (40kW System)

Dieses Dokument beschreibt die elektrotechnisch korrekte, VDE-konforme Hierarchie für die Integration eines 40kW USV-Schranks (z. B. Wöhrle WP2-R oder Eaton 93PM) in die Rechenzentrumsinfrastruktur sowie die Abbildung im KAiTix-Datenmodell via EPLAN-Import.

---

## 1. Korrekter Stromlaufplan (Mermaid)

Im korrekten Stromlaufplan wird die USV von der Haupt-Unterverteilung (`UV-RZ-01`) gespeist und versorgt nachfolgend eine separate, USV-gepufferte Unterverteilung (`UV-USV-01`), von der aus die Racks/PDUs angefahren werden. Ein manueller Bypass-Schalter (MBS) erlaubt das unterbrechungsfreie Umschalten auf Direktnetz für Wartungsarbeiten.

```mermaid
graph TD
    %% Nodes
    Netz["Netz 3~ 400V / 50Hz<br>(TN-S System)"]
    HV["Hauptverteilung (HV)<br>(Sammelschiene)"]
    NH80["NH-Sicherung<br>(80A gG, 3-polig)"]
    UVRZ["Unterverteilung UV-RZ-01<br>(Eingang 63A, ungepuffert)"]
    
    %% USV Path
    LS63_USV["LS-Schalter 3-polig 63A<br>(Abgang USV)"]
    USV["USV-Schrank 40 kW<br>(Wöhrle / Eaton)<br>3x10kW + 1x10kW N+1"]
    
    %% Bypass Path
    LS63_BP["LS-Schalter 3-polig 63A<br>(Abgang Bypass)"]
    
    MBS{"Bypass-Schalter (MBS)<br>(Mechanisch verriegelt)"}
    
    UVUSV["Unterverteilung UV-USV-01<br>(USV-gepuffert)"]
    
    LS32_L1["LS 1-polig 32A L1"]
    LS32_L2["LS 1-polig 32A L2"]
    LS32_L3["LS 1-polig 32A L3"]
    
    PDU_L1["Kentix SmartPDU A-0UL<br>(32A 1-phasig L1)"]
    PDU_L2["Kentix SmartPDU A-0UR<br>(32A 1-phasig L2)"]
    PDU_L3["Kentix SmartPDU B-0UL<br>(32A 1-phasig L3)"]
    
    SRV1["Server Netzteil 1"]
    SRV2["Server Netzteil 2"]

    %% Connections & Cables
    Netz --> HV
    HV -->|NYY-J 5x25 mm²| NH80
    NH80 --> UVRZ
    
    UVRZ -->|NYY-J 5x16 mm²| LS63_USV
    LS63_USV --> USV
    
    UVRZ -->|NYY-J 5x16 mm²| LS63_BP
    LS63_BP -->|Bypass-Leitung| MBS
    
    USV -->|NYY-J 5x16 mm²| MBS
    MBS -->|NYY-J 5x16 mm²| UVUSV
    
    UVUSV --> LS32_L1
    UVUSV --> LS32_L2
    UVUSV --> LS32_L3
    
    LS32_L1 -->|NYY-J 3x10 mm²| PDU_L1
    LS32_L2 -->|NYY-J 3x10 mm²| PDU_L2
    LS32_L3 -->|NYY-J 3x10 mm²| PDU_L3
    
    PDU_L1 -->|C13 / C19 Kabel| SRV1
    PDU_L2 -->|C13 / C19 Kabel| SRV2
    PDU_L3 -->|C13 / C19 Kabel| SRV1
```

---

## 2. Kabeldimensionierung & Sicherungen (VDE-konform)

### Zuleitung Hauptverteilung ──► Unterverteilung `UV-RZ-01`
*   **Max. Last:** 40 kW USV + Hilfseinrichtungen (Lüfter, etc.) ≈ 58 A Nennstrom bei Vollast.
*   **Kabelquerschnitt:** **NYY-J 5×25 mm²**
    *   *Begründung:* Bei Verlegeart B2 (z. B. auf Kabelrinne oder im Installationskanal) beträgt die Strombelastbarkeit für 16 mm² nur ca. 57 A. Dies ist zu knapp. Ein **25 mm²** Kabel hat eine Belastbarkeit von ca. 73 A und bietet ausreichend Reserve.
*   **Absicherung:** **80 A gG (NH-Sicherung oder Leistungsschalter)** in der HV.

### Zuleitungen USV & Bypass-Schalter (MBS)
*   **Max. Strom:** 58 A (begrenzt durch Einspeisung und Überlastreserven).
*   **Kabelquerschnitt:** **NYY-J 5×16 mm²** (für USV-Eingang, USV-Ausgang und Bypass-Zuleitung zum MBS).
*   **Absicherung:** **LS-Schalter 3-polig 63 A (Charakteristik C oder gG-Sicherungen)** in `UV-RZ-01`.

### Zuleitung Unterverteilung `UV-USV-01` ──► SmartPDUs
*   **PDU-Nennstrom:** 32 A (1-phasig).
*   **Kabelquerschnitt:** **NYY-J 3×10 mm²** (oder 5×10 mm² bei 3-phasigen PDUs).
    *   *Begründung:* Gemäß Verlegeart B2 sind 6 mm² (bis 35 A) im Serverraum thermisch oft grenzwertig. Ein **10 mm²** Kabel (belastbar bis 46 A) stellt sicher, dass auch bei Dauerlast (32 A) kein nennenswerter Spannungsabfall entsteht.
*   **Absicherung:** **LS-Schalter 1-polig 32 A (Charakteristik C)** in `UV-USV-01`.

---

## 3. EPLAN-Import Datenstruktur

Über den EPLAN CSV Import (`import_eplan.py`) können diese physischen Power-Verbindungen importiert werden. Dadurch werden die Geräte (HV, UVs, USV, MBS, PDUs) und die entsprechenden Verbindungskabel automatisch im Modell angelegt.

Ein passendes CSV-Template wurde unter `/home/andreas/.gemini/antigravity/brain/1eece267-00ff-4887-982d-21bb8f58c729/scratch/eplan_power_import.csv` generiert.
