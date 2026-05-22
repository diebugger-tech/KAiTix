-- ServerFlow DB Schema
-- Stack: MySQL 8+, SQLAlchemy 2.x sync, PyMySQL
-- ============================================================

CREATE DATABASE IF NOT EXISTS serverflow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE serverflow;

-- ============================================================
-- RACKS
-- ============================================================
CREATE TABLE racks (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50)  NOT NULL UNIQUE,   -- z.B. "RACK-01"
    standort    VARCHAR(100) NOT NULL,           -- z.B. "Serverraum EG"
    hoehe_u     TINYINT UNSIGNED NOT NULL DEFAULT 42,
    bemerkung   VARCHAR(255)
);

-- ============================================================
-- USV MODULE
-- ============================================================
CREATE TABLE usv_units (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bezeichnung     VARCHAR(100) NOT NULL,       -- z.B. "Wöhrle 40kW Schrank"
    hersteller      VARCHAR(100) NOT NULL DEFAULT 'Wöhrle SVS',
    rack_id         INT UNSIGNED NOT NULL,
    max_kw          DECIMAL(6,2) NOT NULL,       -- Schrank-Maximum (z.B. 40.00)
    FOREIGN KEY (rack_id) REFERENCES racks(id)
);

CREATE TABLE usv_modules (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    usv_unit_id     INT UNSIGNED NOT NULL,
    slot            TINYINT UNSIGNED NOT NULL,   -- Slot 1,2,3,4
    leistung_kw     DECIMAL(5,2) NOT NULL,       -- z.B. 10.00
    status          ENUM('aktiv','reserve','defekt') NOT NULL DEFAULT 'aktiv',
    seriennummer    VARCHAR(100),
    UNIQUE KEY uq_usv_slot (usv_unit_id, slot),
    FOREIGN KEY (usv_unit_id) REFERENCES usv_units(id)
);

-- ============================================================
-- PHASEN / VERTEILUNG
-- ============================================================
CREATE TABLE distribution_panels (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    bezeichnung VARCHAR(100) NOT NULL,           -- z.B. "UV-RZ-01"
    rack_id     INT UNSIGNED,
    usv_unit_id INT UNSIGNED,
    bemerkung   VARCHAR(255),
    FOREIGN KEY (rack_id) REFERENCES racks(id),
    FOREIGN KEY (usv_unit_id) REFERENCES usv_units(id)
);

CREATE TABLE distribution_circuits (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    panel_id        INT UNSIGNED NOT NULL,
    bezeichnung     VARCHAR(50)  NOT NULL,       -- z.B. "Schiene L1-01"
    phase           ENUM('L1','L2','L3') NOT NULL,
    absicherung_a   DECIMAL(5,1) NOT NULL,       -- z.B. 16.0
    max_watt        DECIMAL(8,2) GENERATED ALWAYS AS (absicherung_a * 230 * 0.8) STORED,
    FOREIGN KEY (panel_id) REFERENCES distribution_panels(id)
);

-- ============================================================
-- GERÄTE (Server, Switch, Kentix, PDU, etc.)
-- ============================================================
CREATE TABLE devices (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    typ             ENUM(
                        'server',
                        'switch',
                        'pdu',
                        'kentix_raconode',
                        'kentix_doormaster',
                        'kentix_multisensor',
                        'sonstige'
                    ) NOT NULL,
    hostname        VARCHAR(100) NOT NULL UNIQUE,
    ip_adresse      VARCHAR(45),                 -- IPv4 oder IPv6
    hersteller      VARCHAR(100),
    modell          VARCHAR(100),
    seriennummer    VARCHAR(100),
    rack_id         INT UNSIGNED,
    u_position      TINYINT UNSIGNED,            -- unterste U-Position im Rack
    u_hoehe         TINYINT UNSIGNED DEFAULT 1,
    circuit_id      INT UNSIGNED,               -- Stromkreis
    phase           ENUM('L1','L2','L3'),
    tdp_watt        DECIMAL(8,2),               -- Nennleistung
    einschaltstrom_faktor DECIMAL(3,1) DEFAULT 2.5, -- Multiplikator für Peak
    api_url         VARCHAR(255),               -- für Kentix / iDRAC / iLO
    api_key         VARCHAR(255),
    bemerkung       VARCHAR(255),
    FOREIGN KEY (rack_id) REFERENCES racks(id),
    FOREIGN KEY (circuit_id) REFERENCES distribution_circuits(id)
);

-- ============================================================
-- SERVER INTERFACES (Netzwerk, FC, etc.)
-- ============================================================
CREATE TABLE server_interfaces (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id       INT UNSIGNED NOT NULL,
    port_name       VARCHAR(50)  NOT NULL,       -- z.B. "eth0", "ens3f0"
    typ             ENUM('1GbE','10GbE','25GbE','40GbE','100GbE','FC','IPMI','sonstige') NOT NULL,
    mac_adresse     VARCHAR(17),
    switch_hostname VARCHAR(100),
    switch_port     VARCHAR(50),
    kabel_id        INT UNSIGNED,               -- FK → cables
    FOREIGN KEY (device_id) REFERENCES devices(id)
);

-- ============================================================
-- KABELLISTE
-- ============================================================
CREATE TABLE cables (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    kabel_nr        VARCHAR(50)  NOT NULL UNIQUE, -- z.B. "KAB-0001"
    typ             ENUM('Cat6','Cat6A','Cat7','DAC','LC-LC','SC-SC','SFP+','Strom-C13','Strom-C19','Strom-Schuko','sonstige') NOT NULL,
    laenge_m        DECIMAL(6,2) NOT NULL,
    farbe           VARCHAR(30),
    von_device      INT UNSIGNED,
    von_port        VARCHAR(50),
    nach_device     INT UNSIGNED,
    nach_port       VARCHAR(50),
    verlegt_am      DATE,
    verlegt_von     VARCHAR(100),
    bemerkung       VARCHAR(255),
    FOREIGN KEY (von_device) REFERENCES devices(id),
    FOREIGN KEY (nach_device) REFERENCES devices(id)
);

-- Rückverknüpfung Interface → Kabel
ALTER TABLE server_interfaces
    ADD CONSTRAINT fk_interface_cable
    FOREIGN KEY (kabel_id) REFERENCES cables(id);

-- ============================================================
-- KENTIX MESSWERTE (Zeitreihe)
-- ============================================================
CREATE TABLE kentix_readings (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device_id       INT UNSIGNED NOT NULL,
    gemessen_am     DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    temperatur_c    DECIMAL(5,2),
    luftfeuchte_pct DECIMAL(5,2),
    alarm_aktiv     TINYINT(1)   NOT NULL DEFAULT 0,
    alarm_typ       VARCHAR(100),               -- z.B. "TEMPERATURE_HIGH"
    raw_json        JSON,                       -- vollständige API-Antwort
    INDEX idx_device_time (device_id, gemessen_am),
    FOREIGN KEY (device_id) REFERENCES devices(id)
);

-- ============================================================
-- USV BERECHNUNGS-SNAPSHOTS
-- ============================================================
CREATE TABLE usv_calculations (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    berechnet_am    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usv_unit_id     INT UNSIGNED NOT NULL,
    last_kw         DECIMAL(8,2) NOT NULL,       -- Σ TDP aller angeschlossenen Geräte
    peak_kw         DECIMAL(8,2) NOT NULL,       -- last_kw × max(einschaltstrom_faktor)
    installiert_kw  DECIMAL(8,2) NOT NULL,       -- Σ aktiver Module
    reserve_kw      DECIMAL(8,2) NOT NULL,       -- installiert - last
    n1_kw           DECIMAL(8,2) NOT NULL,       -- installiert - größtes Modul
    kaltstart_ok    TINYINT(1)   NOT NULL,       -- peak_kw <= n1_kw
    bemerkung       VARCHAR(255),
    FOREIGN KEY (usv_unit_id) REFERENCES usv_units(id)
);
