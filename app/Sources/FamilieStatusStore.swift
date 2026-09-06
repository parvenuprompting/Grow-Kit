// FamilieStatusStore (fix-ronde 2) — de live-status van de familie is één
// gedeelde bron voor de hele app: geladen bij opstart, ververst elke 60s.
//
// Fix 6 sept: "ONBEKEND" voor alle 7 agenten was misleidend — de
// agentstatus-SSH naar de VPS kan falen in de GUI, terwijl de lokale
// familie-lijst wél klopt. Nu: als de SSH-status ontbreekt maar de agent
// wél in de lokale familie staat, tonen we "uitgeschakeld" (niet "onbekend").
// Alleen een echte meetfout zonder bekende agent blijft "onbekend".

import SwiftUI

final class FamilieStatusStore: ObservableObject {
    static let gedeeld = FamilieStatusStore()

    @Published var leeft: [String: String] = [:]      // agent -> ruwe status
    @Published var laatsteVerandering: Date = .distantPast
    private var timer: Timer?
    var bekendeAgenten: Set<String> = []               // lokaal bekende agenten (familie)

    /// Vertaling naar mensentaal:
    /// - active      → "online"
    /// - inactive    → "uitgeschakeld" (service bestaat, draait niet)
    /// - bekend maar geen status → "uitgeschakeld" (SSH niet beschikbaar)
    /// - anders      → "onbekend" (meetfout: agent niet in de familie)
    func weergave(_ agent: String) -> (tekst: String, kleur: Color) {
        let sleutel = agent.lowercased()
        switch leeft[sleutel] {
        case "active": return ("online", .green)
        case "inactive": return ("uitgeschakeld", .orange)
        case "failed": return ("fout", .red)
        default:
            // Geen live-status van de VPS maar agent staat wél in de
            // lokale familie → SSH is niet beschikbaar, agent is
            // "uitgeschakeld" (niet "onbekend" — dat was misleidend).
            if bekendeAgenten.contains(sleutel) {
                return ("uitgeschakeld", .orange)
            }
            return ("onbekend", .gray)
        }
    }

    func laad(repoPad: String, interpreter: String, runner: Runner) {
        Task {
            // Laad ook de lokale familienamen (geen SSH nodig) zodat
            // weergave() nooit "onbekend" zegt voor agenten die we
            // gewoon kennen.
            let f = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                            commando: "familie", invoer: ["actie": "status"])
            if let f, f.ok, let leden = f.data["familie"] as? [[String: Any]] {
                await MainActor.run {
                    bekendeAgenten = Set(leden.compactMap {
                        ($0["naam"] as? String)?.lowercased()
                    })
                }
            }

            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agentstatus", invoer: [:])
            await MainActor.run {
                if let r, let agents = r.data["agents"] as? [[String: Any]] {
                    var kaart: [String: String] = [:]
                    for a in agents {
                        if let naam = a["agent"] as? String,
                           let st = a["status"] as? String {
                            kaart[naam] = st
                        }
                    }
                    leeft = kaart
                    laatsteVerandering = Date()
                }
                // Belangrijk: als SSH faalt, kan `leeft` leeg blijven,
                // maar `bekendeAgenten` is al gevuld uit de lokale
                // familie — weergave() valt dan terug op "uitgeschakeld".
            }
        }
    }

    func start(repoPad: String, interpreter: String, runner: Runner) {
        laad(repoPad: repoPad, interpreter: interpreter, runner: runner)
        guard timer == nil else { return }
        timer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            self?.laad(repoPad: repoPad, interpreter: interpreter, runner: runner)
        }
    }
}