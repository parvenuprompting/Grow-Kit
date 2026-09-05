// FamilieStatusStore (fix-ronde) — de live-status van de familie is één
// gedeelde bron voor de hele app: geladen bij opstart, ververst elke 60s.
// "Onbekend" (service bestaat niet of SSH leeg) tonen we eerlijk als
// "uitgeschakeld" wanneer het profiel dat expliciet is, en als "onbekend"
// alleen bij een echte meetfout.

import SwiftUI

final class FamilieStatusStore: ObservableObject {
    static let gedeeld = FamilieStatusStore()

    @Published var leeft: [String: String] = [:]      // agent -> ruwe status
    @Published var laatsteVerandering: Date = .distantPast
    private var timer: Timer?

    /// Vertaling naar mensentaal:
    /// - active      → "online"
    /// - inactive    → "uitgeschakeld" (service bestaat, draait niet)
    /// - anders      → "onbekend" (meetfout: SSH mislukt of service mist)
    func weergave(_ agent: String) -> (tekst: String, kleur: Color) {
        switch leeft[agent.lowercased()] {
        case "active": return ("online", .green)
        case "inactive": return ("uitgeschakeld", .orange)
        case "failed": return ("fout", .red)
        default: return ("onbekend", .gray)
        }
    }

    func laad(repoPad: String, interpreter: String, runner: Runner) {
        Task {
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
