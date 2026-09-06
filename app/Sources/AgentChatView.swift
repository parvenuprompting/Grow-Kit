// AgentChatView (ronde 3) — het grote chatvenster: praat met de familie.
// Elk bericht = taak (bron=agentchat) via de bewezen wachtrij; de poller
// op de VPS voert hem uit met het profiel van de agent; de draad toont
// bericht ↔ antwoord. Gouverneur en faalcontract blijven de bewakers.

import SwiftUI

struct AgentChatBericht: Identifiable {
    let taakId: String
    let bericht: String
    let tijd: String
    let antwoord: String?
    var id: String { taakId }
}

final class AgentChatStore: ObservableObject {
    @Published var draad: [AgentChatBericht] = []
    @Published var geladen = false
    @Published var fout: String?
    @Published var bezigVersturen = false

    func laadDraad(agent: String, runner: Runner, repoPad: String, interpreter: String) {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agentchat",
                                           invoer: ["actie": "draad", "agent": agent])
            await MainActor.run {
                guard let r, r.ok, let lijst = r.data["draad"] as? [[String: Any]] else {
                    fout = r?.fout ?? "Draad onbereikbaar."
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

struct AgentChatView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    @StateObject private var store = AgentChatStore()
    @State private var gekozenAgent = ""
    @State private var nieuwBericht = ""
    @State private var agentLijst: [(naam: String, live: Bool)] = []
    @State private var agentenGeladen = false

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
        .onAppear {
            laadAgenten()
        }
    }

    private func laadAgenten() {
        Task {
            // Tweeledig: laad de namen uit de lokale familie-JSON (geen SSH
            // nodig — dit moet altijd werken) en haal daarna de live-status
            // op voor de groene/grijze stip. Agentnamen komen uit de familie,
            // niet uit de VPS.
            async let fam = try? runner.roep(repoPad: repoPad, interpreter: interpreter,
                                              commando: "familie", invoer: ["actie": "status"])
            async let stat = try? runner.roep(repoPad: repoPad, interpreter: interpreter,
                                               commando: "agentstatus", invoer: [:])
            let (familieResult, statusResult) = await (fam, stat)

            await MainActor.run {
                // Stap 1: namen uit de lokale familie (altijd beschikbaar, geen SSH)
                var namen: Set<String> = []
                if let fam = familieResult, fam.ok,
                   let leden = fam.data["familie"] as? [[String: Any]] {
                    for lid in leden {
                        if let naam = lid["naam"] as? String, !naam.isEmpty {
                            namen.insert(naam.lowercased())
                        }
                    }
                } else {
                    // Fallback: vaste familieleden (voor het geval de adapter
                    // de eerste keer nog niet geladen heeft)
                    namen = ["kairos", "riri", "vigil", "libra", "memoria", "codex", "genius"]
                }

                // Stap 2: live-status voor de groene/grijze stip (optioneel)
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
            }
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
                    }
                }
                .padding(24)
            }
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
            invoerRij
        }
    }

    private func chatBlok(_ b: AgentChatBericht) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(b.bericht)
                .font(Thema.tekst(12))
                .padding(10)
                .frame(maxWidth: 420, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 8).fill(Thema.kleur(.papierZacht)))
            if let antwoord = b.antwoord {
                Text(antwoord)
                    .font(Thema.tekst(12))
                    .foregroundStyle(Thema.kleur(.inkt))
                    .padding(10)
                    .frame(maxWidth: 420, alignment: .leading)
                    .background(RoundedRectangle(cornerRadius: 8)
                        .stroke(Thema.kleur(.lijn)))
                    .textSelection(.enabled)
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
