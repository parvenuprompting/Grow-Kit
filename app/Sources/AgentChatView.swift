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

    private var agenten: [(naam: String, live: Bool)] {
        FamilieStatusStore.gedeeld.leeft
            .sorted { $0.key < $1.key }
            .map { ($0.key, $0.value == "active") }
    }

    /// Kies bij eerste opening de eerste bekende agent uit de familie;
    /// val terug op de eerste uit de live-status als er nog niets gekozen is.
    private func stelEersteAgentIn() {
        guard gekozenAgent.isEmpty else { return }
        if !agenten.isEmpty {
            gekozenAgent = agenten[0].naam
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            kop
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
            HStack(spacing: 0) {
                agentLijst
                Rectangle().fill(Thema.kleur(.lijn)).frame(width: 1)
                draadPaneel
            }
        }
        .background(Thema.kleur(.papier))
        .onAppear {
            stelEersteAgentIn()
            if !gekozenAgent.isEmpty, store.draad.isEmpty {
                store.laadDraad(agent: gekozenAgent, runner: runner,
                                repoPad: repoPad, interpreter: interpreter)
            }
        }
        // De familie-status arriveert asynchroon. Observeer de store direct:
        // alleen dan herlaadt SwiftUI deze view wanneer leeft gevuld wordt.
        .onReceive(FamilieStatusStore.gedeeld.$leeft) { _ in
            stelEersteAgentIn()
            if !gekozenAgent.isEmpty, store.draad.isEmpty {
                store.laadDraad(agent: gekozenAgent, runner: runner,
                                repoPad: repoPad, interpreter: interpreter)
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

    private var agentLijst: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                if agenten.isEmpty {
                    Text(store.geladen ? "Familie nog niet geladen."
                                       : "Familie laden…")
                        .font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.gedempt))
                        .padding(16)
                }
                ForEach(agenten, id: \.naam) { agent in
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
        let tekst = nieuwBericht
        nieuwBericht = ""
        store.stuur(agent: gekozenAgent, tekst: tekst, runner: runner,
                    repoPad: repoPad, interpreter: interpreter) {
            store.laadDraad(agent: gekozenAgent, runner: runner,
                            repoPad: repoPad, interpreter: interpreter)
        }
    }
}
