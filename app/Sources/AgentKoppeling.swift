// AgentKoppeling — de echte dialoog met de kern via adapter.py.
// De chat stuurt elke opdracht door de Scope-poort (adapter `slijp`);
// de app interpreteert niets, de poort blijft de bewaker.

import Foundation

struct SlijpResultaat {
    let geaccepteerd: Bool
    let weigering: String?
    let conceptJSON: String?      // nette weergave van het concept
    let vragen: [[String: Any]]
    let fout: String?
}

final class AgentKoppeling: ObservableObject {
    @Published var bezig = false
    @Published var laatsteFout: String?

    /// Stuur een chat-invoer door de Scope-poort via de adapter.
    func slijp(runner: Runner, repoPad: String, interpreter: String,
               tekst: String) async -> SlijpResultaat {
        await MainActor.run { self.bezig = true; self.laatsteFout = nil }
        defer { Task { await MainActor.run { self.bezig = false } } }
        do {
            let r = try await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                          commando: "slijp",
                                          invoer: ["tekst": tekst])
            if let fout = r.fout {
                await MainActor.run { self.laatsteFout = fout }
                return SlijpResultaat(geaccepteerd: false, weigering: nil,
                                      conceptJSON: nil, vragen: [], fout: fout)
            }
            var weigering: String?
            var conceptJSON: String?
            let vragen = (r.data["vragen"] as? [[String: Any]]) ?? []
            if r.data["geaccepteerd"] as? Bool == true {
                if let concept = r.data["concept"] as? [String: Any] {
                    conceptJSON = Self.netteConceptWeergave(concept)
                }
            } else {
                weigering = r.data["weigering"] as? String
            }
            return SlijpResultaat(geaccepteerd: r.data["geaccepteerd"] as? Bool == true,
                                  weigering: weigering, conceptJSON: conceptJSON,
                                  vragen: vragen, fout: nil)
        } catch {
            let melding = error.localizedDescription
            await MainActor.run { self.laatsteFout = melding }
            return SlijpResultaat(geaccepteerd: false, `weigering`: nil,
                                  conceptJSON: nil, vragen: [], fout: melding)
        }
    }

    /// Concept-dict → leesbare tekst voor in het gesprek (alleen weergave).
    static func netteConceptWeergave(_ concept: [String: Any]) -> String {
        var regels: [String] = []
        if let doel = concept["einddoel"] as? String { regels.append("• Doel: \(doel)") }
        if let omgeving = concept["omgeving"] as? [String: Any] {
            let waarde = (omgeving["waarde"] as? String) ?? "?"
            let gelabeld = (omgeving["standaardwaarde"] as? Bool) == true
            regels.append("• Plek: \(waarde)\(gelabeld ? " (gelabelde standaardwaarde — bevestig of pas aan)" : "")")
        }
        if let slaag = concept["slaag_criterium"] as? String {
            regels.append("• Slaag wanneer: \(slaag)")
        }
        if let bron = concept["bron"] as? [String: Any],
           let ruw = bron["ruwe_invoer"] as? String, !ruw.isEmpty {
            regels.append("• Bron: jouw woorden, ongewijzigd doorgelaten")
        }
        regels.append("• Status: wacht op jouw bekrachtiging (de app voert nooit zelf uit)")
        return regels.joined(separator: "\n")
    }
}
