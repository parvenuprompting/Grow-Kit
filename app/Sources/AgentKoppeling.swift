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
    /// De ruwe invoer van deze beurt — onthouden voor het vragen-rondje (slice 2).
    let ruweTekst: String
}

final class AgentKoppeling: ObservableObject {
    @Published var bezig = false
    @Published var laatsteFout: String?

    /// Stuur een chat-invoer door de Scope-poort via de adapter.
    /// Antwoorden uit het vragen-rondje gaan onveranderd mee in de invoer-JSON:
    /// de app interpreteert niets, de poort blijft de bewaker.
    func slijp(runner: Runner, repoPad: String, interpreter: String,
               tekst: String, antwoorden: [String: String] = [:],
               agent: String? = nil) async -> SlijpResultaat {
        await MainActor.run { self.bezig = true; self.laatsteFout = nil }
        defer { Task { await MainActor.run { self.bezig = false } } }
        var invoer: [String: Any] = ["tekst": tekst]
        // De gekozen agent reist mee als contextveld — de poort beslist wat
        // hij ermee doet; de app voegt geen interpretatie toe.
        if let agent, !agent.isEmpty, agent != "alle" {
            invoer["agent"] = agent
        }
        for (veld, antwoord) in antwoorden where !antwoord.trimmingCharacters(in: .whitespaces).isEmpty {
            invoer[veld] = antwoord.trimmingCharacters(in: .whitespaces)
        }
        do {
            let r = try await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                          commando: "slijp", invoer: invoer)
            if let fout = r.fout {
                await MainActor.run { self.laatsteFout = fout }
                return SlijpResultaat(geaccepteerd: false, weigering: nil,
                                      conceptJSON: nil, vragen: [], fout: fout,
                                      ruweTekst: tekst)
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
                                  vragen: vragen, fout: nil, ruweTekst: tekst)
        } catch {
            let melding = error.localizedDescription
            await MainActor.run { self.laatsteFout = melding }
            return SlijpResultaat(geaccepteerd: false, weigering: nil,
                                  conceptJSON: nil, vragen: [], fout: melding,
                                  ruweTekst: tekst)
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

    /// Slice 3 — plant-aanroep: eerst voorbeeld (bevestiging_vereist), daarna echt.
    struct PlantResultaat {
        let conceptTekst: String?
        let mijlpaalBlok: String?
        let vragen: [[String: Any]]
        let stappen: [[String: Any]]
        let registratie: String?
        let uitgevoerd: Bool
        let fout: String?
        let faalStappen: [[String: Any]]
    }

    func plant(runner: Runner, repoPad: String, interpreter: String,
               profiel: String, doel: String, brein: String,
               bevestig: Bool, mijlpaalBevestigd: Bool = false) async -> PlantResultaat {
        var invoer: [String: Any] = ["profiel": profiel, "doel": doel]
        if bevestig { invoer["bevestig"] = true }
        if mijlpaalBevestigd { invoer["mijlpaal_bevestigd"] = true }
        if brein == "geen" || brein == "auto" || brein == "pad" { invoer["brein"] = brein }
        do {
            let r = try await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                          commando: "plant", invoer: invoer, timeOut: 300)
            if r.fout != nil, !r.ok {
                return PlantResultaat(conceptTekst: nil, mijlpaalBlok: nil, vragen: [],
                                      stappen: [], registratie: nil, uitgevoerd: false,
                                      fout: r.fout, faalStappen: r.stappen)
            }
            let d = r.data
            var conceptTekst: String?
            if let concept = d["concept"] as? String { conceptTekst = concept }
            if let blok = d["mijlpaal_blok"] as? String { conceptTekst = blok }
            return PlantResultaat(
                conceptTekst: conceptTekst,
                mijlpaalBlok: d["mijlpaal_blok"] as? String,
                vragen: (d["vragen"] as? [[String: Any]]) ?? [],
                stappen: (d["stappen"] as? [[String: Any]]) ?? [],
                registratie: d["registratie"] as? String,
                uitgevoerd: (d["uitgevoerd"] as? Bool) ?? bevestig && (d["mijlpaal_blok"] == nil),
                fout: r.fout, faalStappen: r.stappen)
        } catch {
            return PlantResultaat(conceptTekst: nil, mijlpaalBlok: nil, vragen: [],
                                  stappen: [], registratie: nil, uitgevoerd: false,
                                  fout: error.localizedDescription, faalStappen: [])
        }
    }
}