// AgentChatView (ronde 4) — het grote chatvenster: praat met de familie.
//
// Fixes 6 sept:
// - Auto-verversing: elke 15s wordt de draad stilletjes ververst
// - Conversaties blijven staan: store is een singleton per agent
// - Hermes-header weg: antwoorden worden geschoond van CLI-headers
// - Reasoning-toggle: knop om de denkstappen van de agent te tonen/verbergen
// - Antwoord-label toont agentnaam, niet "Hermes"

import SwiftUI
import AppKit

// MARK: - Singleton stores (conversaties overleven tab-wissels)

private var _stores: [String: AgentChatStore] = [:]

final class AgentChatStore: ObservableObject {
    @Published var draad: [AgentChatBericht] = []
    @Published var geladen = false
    @Published var fout: String?
    @Published var bezigVersturen = false

    static func voor(agent: String) -> AgentChatStore {
        let sleutel = agent.lowercased()
        if let bestaand = _stores[sleutel] { return bestaand }
        let nieuw = AgentChatStore()
        _stores[sleutel] = nieuw
        return nieuw
    }

    func laadDraad(agent: String, runner: Runner, repoPad: String, interpreter: String,
                   stil: Bool = false) {
        if !stil { geladen = false }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agentchat",
                                           invoer: ["actie": "draad", "agent": agent])
            await MainActor.run {
                guard let r, r.ok, let lijst = r.data["draad"] as? [[String: Any]] else {
                    if !stil { fout = r?.fout ?? "Draad onbereikbaar." }
                    geladen = true
                    return
                }
                fout = nil
                draad = lijst.map { item in
                    AgentChatBericht(
                        taakId: item["taak_id"] as? String ?? "",
                        bericht: item["bericht"] as? String ?? "",
                        tijd: item["tijd"] as? String ?? "",
                        antwoord: item["antwoord"] as? String)
                }
                geladen = true
            }
        }
    }

    func stuur(agent: String, tekst: String, runner: Runner, repoPad: String,
               interpreter: String, daarna: @escaping () -> Void) {
        guard !tekst.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        bezigVersturen = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agentchat",
                                           invoer: ["actie": "stuur", "agent": agent,
                                                    "bericht": tekst])
            await MainActor.run {
                bezigVersturen = false
                if let r, r.ok {
                    fout = nil
                    daarna()
                } else {
                    fout = r?.fout ?? "Versturen mislukt."
                }
            }
        }
    }
}

struct AgentChatBericht: Identifiable {
    let taakId: String
    let bericht: String
    let tijd: String
    let antwoord: String?
    var id: String { taakId }
}

// MARK: - View

struct AgentChatView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    @State private var gekozenAgent = ""
    @State private var nieuwBericht = ""
    @State private var agentLijst: [(naam: String, live: Bool)] = []
    @State private var agentenGeladen = false
    @State private var toonRedenatie = false
    @State private var autoVerversTimer: Timer?

    private var store: AgentChatStore {
        AgentChatStore.voor(agent: gekozenAgent)
    }

    var body: some View {
        VStack(spacing: 0) {
            kop
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
            HStack(spacing: 0) {
                agentLijstView
                Rectangle().fill(Thema.kleur(.lijn)).frame(width: 1)
                draadPaneel
            }
        }
        .background(Thema.kleur(.papier))
        .onAppear { laadAgenten() }
        .onDisappear { autoVerversTimer?.invalidate(); autoVerversTimer = nil }
    }

    // MARK: - Agenten laden

    private func laadAgenten() {
        Task {
            async let fam = try? runner.roep(repoPad: repoPad, interpreter: interpreter,
                                              commando: "familie", invoer: ["actie": "status"])
            async let stat = try? runner.roep(repoPad: repoPad, interpreter: interpreter,
                                               commando: "agentstatus", invoer: [:])
            let (familieResult, statusResult) = await (fam, stat)
            await MainActor.run {
                var namen: Set<String> = []
                if let fam = familieResult, fam.ok,
                   let leden = fam.data["familie"] as? [[String: Any]] {
                    for lid in leden {
                        if let naam = lid["naam"] as? String, !naam.isEmpty {
                            namen.insert(naam.lowercased())
                        }
                    }
                } else {
                    namen = ["kairos", "riri", "vigil", "libra", "memoria", "codex", "genius"]
                }
                var statusMap: [String: String] = [:]
                if let stat = statusResult,
                   let lijst = stat.data["agents"] as? [[String: Any]] {
                    for a in lijst {
                        if let n = a["agent"] as? String, let s = a["status"] as? String {
                            statusMap[n] = s
                        }
                    }
                }
                agentLijst = namen.sorted().map { naam in
                    (naam: naam, live: statusMap[naam] == "active")
                }
                if agentLijst.isEmpty {
                    store.fout = "Geen agenten gevonden in de familie."
                } else if gekozenAgent.isEmpty, let eerste = agentLijst.first {
                    gekozenAgent = eerste.naam
                    store.laadDraad(agent: eerste.naam, runner: runner,
                                    repoPad: repoPad, interpreter: interpreter)
                }
                agentenGeladen = true
                startAutoVervers()
            }
        }
    }

    private func startAutoVervers() {
        autoVerversTimer?.invalidate()
        autoVerversTimer = Timer.scheduledTimer(withTimeInterval: 15, repeats: true) { _ in
            guard !gekozenAgent.isEmpty else { return }
            store.laadDraad(agent: gekozenAgent, runner: runner,
                            repoPad: repoPad, interpreter: interpreter, stil: true)
        }
    }

    // MARK: Kop

    private var kop: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("01 AGENT CHAT · DE FAMILIE").font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            HStack(alignment: .firstTextBaseline) {
                Text("Praat met ").font(Thema.display(30))
                Text("de familie.").font(Thema.display(30, cursief: true))
                    .foregroundStyle(Thema.kleur(.zacht))
                Spacer()
                // Reasoning toggle
                PillKnop(titel: toonRedenatie ? "Redenatie aan" : "Redenatie uit",
                         gevuld: toonRedenatie, compact: true) {
                    toonRedenatie.toggle()
                }
                PillKnop(titel: "Ververs") {
                    store.laadDraad(agent: gekozenAgent, runner: runner,
                                    repoPad: repoPad, interpreter: interpreter)
                }
            }
            Text("Elk bericht is een taak via de wachtrij — de agent antwoordt met zijn eigen profiel, met de gouverneur en het faalcontract als bewakers.")
                .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
        }
        .padding(.horizontal, 28).padding(.top, 20).padding(.bottom, 10)
    }

    // MARK: Agentlijst (links)

    private var agentLijstView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                if !agentenGeladen {
                    Text("Familie laden…")
                        .font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.gedempt))
                        .padding(16)
                } else if agentLijst.isEmpty {
                    Text("Geen agenten bereikbaar.")
                        .font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.gedempt))
                        .padding(16)
                }
                ForEach(agentLijst, id: \.naam) { agent in
                    Button {
                        gekozenAgent = agent.naam
                        store.laadDraad(agent: agent.naam, runner: runner,
                                        repoPad: repoPad, interpreter: interpreter)
                    } label: {
                        HStack(spacing: 8) {
                            Circle().fill(agent.live ? Color.green : Color.gray)
                                .frame(width: 6, height: 6)
                            Text(agent.naam.capitalized)
                                .font(Thema.tekst(12, gewicht:
                                    gekozenAgent == agent.naam ? .semibold : .regular))
                                .foregroundStyle(Thema.kleur(
                                    gekozenAgent == agent.naam ? .inkt : .zacht))
                            Spacer()
                        }
                        .padding(.horizontal, 16).padding(.vertical, 9)
                        .background(gekozenAgent == agent.naam
                                    ? Thema.kleur(.papierZacht) : Thema.kleur(.papier))
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .frame(width: 150)
    }

    // MARK: Draad (rechts)

    private var draadPaneel: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 14) {
                        if let fout = store.fout {
                            Text(fout).font(Thema.tekst(11)).foregroundStyle(.red)
                        }
                        if store.geladen && store.draad.isEmpty {
                            Text("Nog geen gesprek met \(gekozenAgent.capitalized). Begin hieronder — hij antwoordt binnen enkele minuten.")
                                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                        }
                        ForEach(store.draad) { bericht in
                            chatBlok(bericht)
                                .id(bericht.id)
                        }
                    }
                    .padding(24)
                }
            }
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
            invoerRij
        }
    }

    /// Stript Hermes CLI-headers, resume-commando's en sessie-info uit het
    /// antwoord. Wat overblijft is het pure bericht van de agent.
    private func schoonAntwoord(_ antwoord: String) -> String {
        var uit = antwoord
        // Verwijder Hermes CLI-header (⚕ Hermes lijn + afgeronde boxen)
        if let range = uit.range(of: "─────────────────────────") {
            uit = String(uit[range.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
        }
        // Strip "Resume this session with:" blok
        if let resumeRange = uit.range(of: "Resume this session with:") {
            uit = String(uit[..<resumeRange.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
        }
        // Strip eventuele "hermes --resume" regel
        let regels = uit.components(separatedBy: "\n")
            .filter { !$0.trimmingCharacters(in: .whitespaces).hasPrefix("hermes -") }
        uit = regels.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
        return uit.isEmpty ? antwoord : uit
    }

    /// Splitst het antwoord in "redenatie" (alles vóór het laatste ─ blok
    /// en het pure antwoord erna). Als er geen duidelijke splitsing is,
    /// is alles antwoord.
    private func splitAntwoord(_ antwoord: String) -> (redenatie: String?, antwoord: String) {
        // Hermes CLI-output: de reasoning zit tussen ╭─ en ──────────
        // Het pure antwoord komt na de laatste ────────── scheiding
        let delen = antwoord.components(separatedBy: "─────────────────────────")
        if delen.count >= 2 {
            let redenatie = delen.dropLast().joined(separator: "───").trimmingCharacters(in: .whitespacesAndNewlines)
            let puur = delen.last?.trimmingCharacters(in: .whitespacesAndNewlines) ?? antwoord
            let red = redenatie
                .replacingOccurrences(of: "Resume this session with:", with: "")
                .components(separatedBy: "\n")
                .filter { !$0.trimmingCharacters(in: .whitespaces).hasPrefix("hermes -") }
                .joined(separator: "\n")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            return (red.isEmpty ? nil : red, puur.isEmpty ? antwoord : puur)
        }
        return (nil, antwoord)
    }

    private func chatBlok(_ b: AgentChatBericht) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            // Gebruikersbericht
            Text(b.bericht)
                .font(Thema.tekst(12))
                .padding(10)
                .frame(maxWidth: 420, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 8).fill(Thema.kleur(.papierZacht)))

            if let antwoord = b.antwoord {
                let (redenatie, puurAntwoord) = splitAntwoord(antwoord)

                // Redenatie (in- en uitklapbaar)
                if let red = redenatie, toonRedenatie {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Redenatie").font(Thema.tekst(9, gewicht: .semibold))
                            .tracking(1.5).foregroundStyle(Thema.kleur(.gedempt))
                        Text(red)
                            .font(Thema.tekst(10))
                            .foregroundStyle(Thema.kleur(.zacht))
                            .padding(8)
                            .frame(maxWidth: 420, alignment: .leading)
                            .background(RoundedRectangle(cornerRadius: 6)
                                .stroke(Thema.kleur(.lijn), style: StrokeStyle(dash: [3, 3])))
                    }
                }

                // Het pure antwoord van de agent
                VStack(alignment: .leading, spacing: 4) {
                    Text(gekozenAgent.capitalized)
                        .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                        .foregroundStyle(Thema.kleur(.gedempt))
                    Text(puurAntwoord)
                        .font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.inkt))
                        .textSelection(.enabled)
                }
                .padding(10)
                .frame(maxWidth: 420, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 8)
                    .stroke(Thema.kleur(.lijn)))

            } else {
                HStack(spacing: 6) {
                    Text("wacht op antwoord")
                        .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                    Circle().fill(Thema.kleur(.lijn)).frame(width: 4, height: 4)
                    Circle().fill(Thema.kleur(.lijn)).frame(width: 4, height: 4)
                    Circle().fill(Thema.kleur(.lijn)).frame(width: 4, height: 4)
                }
                .padding(.horizontal, 10)
            }
            Text(b.tijd).font(Thema.tekst(8)).tracking(0.5)
                .foregroundStyle(Thema.kleur(.gedempt))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var invoerRij: some View {
        HStack(spacing: 10) {
            TextField("Bericht aan \(gekozenAgent.capitalized)…",
                      text: $nieuwBericht, axis: .vertical)
                .foregroundStyle(Thema.kleur(.inkt))
                .textFieldStyle(.plain)
                .font(Thema.tekst(13))
                .lineLimit(1...4)
                .padding(10)
                .background(RoundedRectangle(cornerRadius: 8).stroke(Thema.kleur(.lijn)))
                .onSubmit { verstuur() }

            PillKnop(titel: store.bezigVersturen ? "…" : "Verstuur", gevuld: true) {
                verstuur()
            }
        }
        .padding(16)
    }

    private func verstuur() {
        if gekozenAgent.isEmpty, let eerste = agentLijst.first {
            gekozenAgent = eerste.naam
        }
        guard !gekozenAgent.isEmpty else {
            store.fout = "De familie is nog aan het laden — probeer het over enkele seconden opnieuw."
            return
        }
        let tekst = nieuwBericht
        nieuwBericht = ""
        store.stuur(agent: gekozenAgent, tekst: tekst, runner: runner,
                    repoPad: repoPad, interpreter: interpreter) {
            store.laadDraad(agent: gekozenAgent, runner: runner,
                            repoPad: repoPad, interpreter: interpreter)
        }
    }
}