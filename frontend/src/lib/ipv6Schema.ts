/**
 * NUR-DOKU-VERMERK:
 * Diese Datei ist ausschließlich ein Benennungs-/Merkschema für Menschen, die die Dokumentation in KAiTix lesen.
 * Es findet KEIN Routing statt, es wird keine IP-Adresse validiert, aufgelöst oder erreicht.
 * KAiTix führt keine externen Netzwerk-Calls oder Ping-Überprüfungen durch.
 * Dieses Schema dient nur zur konsequenten Benennung von Geräten im RZ-Betrieb.
 */

export interface Ipv6Category {
  typ: string;
  name: string;
  prefix: string; // The specific prefix segment for the category (e.g. "1")
  description: string;
}

export const ipv6Categories: Ipv6Category[] = [
  { typ: 'server', name: 'Server & Compute', prefix: '1', description: 'Hypervisor, Bare Metal Server, Storage' },
  { typ: 'switch', name: 'Netzwerk & Switch', prefix: '2', description: 'Switches, Router, Firewalls' },
  { typ: 'pdu', name: 'Power & PDU', prefix: '3', description: 'Rack PDUs, USV-Management-Cards' },
  { typ: 'kentix_raconode', name: 'Sensorik & IoT', prefix: '4', description: 'Kentix Sensoren, Doormaster, Kameras' },
  { typ: 'sonstige', name: 'Sonstige', prefix: '9', description: 'Drucker, Terminals, Sonstige' },
];

export const ipv6VlanExample = '2001:db8:0:10::'; // Example for VLAN 10
export const ipv6UlaExample = 'fd00:0:0:10::'; // Example for ULA VLAN 10
