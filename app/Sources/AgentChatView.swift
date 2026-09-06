// AgentChatView (ronde 5) — het grote chatvenster: praat met de familie.
//
// Ronde 5 (6 sept, UX):
// - Bericht verschijnt DIRECT na versturen (optimistisch), geen flash/weg-dan-terug
// - Typing-indicator: animatie van 3 stippen terwijl het antwoord onderweg is
// - Antwoorden in markdown (kopjes, lijsten, code) i.p.v. lap tekst
// - Auto-verversing 15s (stil); scroll naar beneden bij nieuw bericht
// - Conversaties per agent bewaard (singleton stores)
// - "van"-veld: de agent weet wie er praat (profiel-naam, werkt voor elke gebruiker)
// - Reasoning-toggle; antwoordlabel = agentnaam; Hermes-CLI-meuk weg

import SwiftUI

// MARK: - Singleton stores (conversaties overleven tab-wissels)

private var _stores: [String: AgentChatStore] = [:]

final class AgentChatStore: ObservableObject {
    @Published var draad: [AgentChatBericht] = []
    @Published var geschiedenis: [AgentChatBericht] = []
    @Published var geladen = false
    @Published var fout: String?
    @Published var bezigVersturen = false
    @Published var wachtOpAntwoord = false

    static func voor(agent: String) -> AgentChatStore {
        let sleutel = agent.lowercased()
        if let bestaand = _stores[sleutel] { return bestaand }
        let nieuw = AgentChatStore()
        _stores[sleutel] = nieuw
        return nieuw
    }

    /// Voeg het eigen bericht direct toe (optimistisch) — het komt pas
    /// van de VPS terug bij de volgende verversing, maar de gebruiker
    /// ziet het nú.
    func voegLokaalToe(tekst: String) {
        let tijd = ISO8601DateFormatter().string(from: Date())
        draad.append(AgentChatBericht(taakId: "lokaal-" + tijd, bericht: tekst,
                                      tijd: tijd, antwoord: nil, redenatie: nil))
        wachtOpAntwoord = true
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
                        antwoord: item["antwoord"] as? String ?? nil,
                        redenatie: item["redenatie"] as? String ?? nil)
                }
                // Wacht-indicator uit als het laatste bericht een antwoord heeft
                if let laatste = draad.last {
                    wachtOpAntwoord = (laatste.antwoord == nil)
                } else {
                    wachtOpAntwoord = false
                }
                geladen = true
            }
        }
    }

    /// Wis de zichtbare chat (berichten gaan naar archief op de VPS).
    func wisDraad(agent: String, runner: Runner, repoPad: String, interpreter: String) {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agentchat",
                                           invoer: ["actie": "wis", "agent": agent])
            await MainActor.run {
                if let r, r.ok {
                    draad = []
                    wachtOpAntwoord = false
                    fout = nil
                    geladen = true
                } else {
                    fout = r?.fout ?? "Wissen mislukt."
                }
            }
        }
    }

    /// De gearchiveerde sessie (alleen-lezen).
    func laadGeschiedenis(agent: String, runner: Runner, repoPad: String,
                          interpreter: String) {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agentchat",
                                           invoer: ["actie": "geschiedenis", "agent": agent])
            await MainActor.run {
                if let r, r.ok, let lijst = r.data["geschiedenis"] as? [[String: Any]] {
                    geschiedenis = lijst.map { item in
                        AgentChatBericht(
                            taakId: item["taak_id"] as? String ?? "",
                            bericht: item["bericht"] as? String ?? "",
                            tijd: item["tijd"] as? String ?? "",
                            antwoord: item["antwoord"] as? String ?? nil,
                            redenatie: item["redenatie"] as? String ?? nil)
                    }
                }
            }
        }
    }

    /// DEFINITIEF de gearchiveerde sessie wissen (vereist bevestiging in de UI).
    func wisGeschiedenis(agent: String, runner: Runner, repoPad: String,
                         interpreter: String) {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agentchat",
                                           invoer: ["actie": "wisgeschiedenis",
                                                    "agent": agent, "bevestig": true])
            await MainActor.run {
                if let r, r.ok {
                    geschiedenis = []
                }
            }
        }
    }

    func stuur(agent: String, tekst: String, van: String, runner: Runner,
               repoPad: String, interpreter: String, daarna: @escaping () -> Void) {
        guard !tekst.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        bezigVersturen = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agentchat",
                                           invoer: ["actie": "stuur", "agent": agent,
                                                    "bericht": tekst, "van": van])
            await MainActor.run {
                bezigVersturen = false
                if let r, r.ok {
                    fout = nil
                    daarna()
                } else {
                    fout = r?.fout ?? "Versturen mislukt."
                    wachtOpAntwoord = false
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
    let redenatie: String?
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
    @State private var toonGeschiedenis = false
    @State private var wisBevestiging = false
    @State private var wisGeschiedenisBevestiging = false
    @State private var autoVerversTimer: Timer?
    @State private var gebruikersNaam: String = ""

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
                if toonGeschiedenis {
                    geschiedenisPaneel
                } else {
                    draadPaneel
                }
            }
        }
        .background(Thema.kleur(.papier))
        .onAppear {
            laadAgenten()
            laadGebruiker()
        }
        .onDisappear { autoVerversTimer?.invalidate(); autoVerversTimer = nil }
        // Wis-chat: berichten gaan naar archief op de VPS (omkeerbaar)
        .alert("Gesprek wissen?", isPresented: $wisBevestiging) {
            Button("Annuleer", role: .cancel) {}
            Button("Wis (naar archief)", role: .destructive) {
                store.wisDraad(agent: gekozenAgent, runner: runner,
                               repoPad: repoPad, interpreter: interpreter)
            }
        } message: {
            Text("De chat wordt leeg. Berichten blijven bewaard in de geschiedenis.")
        }
        // Wis-geschiedenis: DEFINITIEF, vraagt om aparte bevestiging
        .alert("Geschiedenis definitief wissen?", isPresented: $wisGeschiedenisBevestiging) {
            Button("Annuleer", role: .cancel) {}
            Button("Definitief wissen", role: .destructive) {
                store.wisGeschiedenis(agent: gekozenAgent, runner: runner,
                                      repoPad: repoPad, interpreter: interpreter)
            }
        } message: {
            Text("De gearchiveerde sessie van \(gekozenAgent.capitalized) wordt permanent verwijderd. Dit kan niet ongedaan worden.")
        }
    }

    /// De bewaarde sessie — alleen-lezen, met eigen wis-knop.
    private var geschiedenisPaneel: some View {
        VStack(spacing: 0) {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 14) {
                    HStack {
                        Text("GESCHIEDENIS · \(gekozenAgent.capitalized)")
                            .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                            .foregroundStyle(Thema.kleur(.gedempt))
                        Spacer()
                        PillKnop(titel: "Definitief wissen", gevuld: false, compact: true) {
                            wisGeschiedenisBevestiging = true
                        }
                        PillKnop(titel: "Terug naar chat", gevuld: true, compact: true) {
                            toonGeschiedenis = false
                        }
                    }
                    if store.geschiedenis.isEmpty {
                        Text("Geen gearchiveerde sessies voor \(gekozenAgent.capitalized).")
                            .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                    }
                    ForEach(store.geschiedenis) { bericht in
                        chatBlok(bericht).id(bericht.id)
                    }
                }
                .padding(24)
            }
        }
    }

    private func laadGebruiker() {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "profiel", invoer: ["actie": "lees"])
            await MainActor.run {
                if let r, r.ok,
                   let profiel = r.data["profiel"] as? [String: Any],
                   let naam = profiel["naam"] as? String, !naam.isEmpty {
                    gebruikersNaam = naam
                }
            }
        }
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
                PillKnop(titel: "Geschiedenis", gevuld: false, compact: true) {
                    toonGeschiedenis.toggle()
                    if toonGeschiedenis {
                        store.laadGeschiedenis(agent: gekozenAgent, runner: runner,
                                               repoPad: repoPad, interpreter: interpreter)
                    }
                }
                PillKnop(titel: "Wis", gevuld: false, compact: true) {
                    wisBevestiging = true
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
                        if store.wachtOpAntwoord {
                            typingIndicator
                                .id("typing")
                        }
                    }
                    .padding(24)
                }
                .onChange(of: store.draad.count) { _ in
                    withAnimation(.easeOut(duration: 0.2)) {
                        proxy.scrollTo(store.wachtOpAntwoord ? "typing" : store.draad.last?.id,
                                       anchor: .bottom)
                    }
                }
            }
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
            invoerRij
        }
    }

    /// Typing-indicator: drie pulserende stippen — de agent "typt".
    private var typingIndicator: some View {
        HStack(spacing: 5) {
            ForEach(0..<3, id: \.self) { i in
                TypingStip(vertraging: Double(i) * 0.2)
            }
        }
        .padding(.horizontal, 12).padding(.vertical, 10)
    }

    private func splitAntwoord(_ antwoord: String) -> (redenatie: String?, antwoord: String) {
        let delen = antwoord.components(separatedBy: "─────────────────────────")
        if delen.count >= 2 {
            let redenatie = delen.dropLast().joined(separator: "───").trimmingCharacters(in: .whitespacesAndNewlines)
            let puur = delen.last?.trimmingCharacters(in: .whitespacesAndNewlines) ?? antwoord
            let red = redenatie
                .components(separatedBy: "\n")
                .filter { !$0.trimmingCharacters(in: .whitespaces).hasPrefix("hermes -") }
                .joined(separator: "\n")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            return (red.isEmpty ? nil : red, puur.isEmpty ? antwoord : puur)
        }
        return (nil, antwoord)
    }

    @ViewBuilder
    private func chatBlok(_ b: AgentChatBericht) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            // Gebruikersbericht
            HStack(alignment: .bottom, spacing: 8) {
                Text(gebruikersNaam.isEmpty ? "Jij" : gebruikersNaam)
                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                    .foregroundStyle(Thema.kleur(.gedempt))
                Text(formatteerTijd(b.tijd))
                    .font(Thema.tekst(8)).foregroundStyle(Thema.kleur(.gedempt))
            }
            Text(b.bericht)
                .font(Thema.tekst(12))
                .padding(10)
                .frame(maxWidth: 420, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 8).fill(Thema.kleur(.papierZacht)))

            if let antwoord = b.antwoord {
                // Redenatie: uit data (nieuw) of uit ruwe antwoordtekst (oud)
                let gesplitst = splitAntwoord(antwoord)
                let red = b.redenatie ?? gesplitst.redenatie
                let puurAntwoord = b.redenatie != nil ? antwoord : gesplitst.antwoord

                // Thought \u{25BE} — inklapbaar denkproces per bericht (net als Hermes)
                if let red, !red.isEmpty {
                    DenkBlok(redenatie: red)
                }

                // Antwoord van de agent — met naam-label en markdown-opmaak
                VStack(alignment: .leading, spacing: 4) {
                    HStack(alignment: .bottom, spacing: 8) {
                        Text(gekozenAgent.capitalized)
                            .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                            .foregroundStyle(Thema.kleur(.gedempt))
                    }
                    // Simpele markdown: kopjes, bullets, code worden netjes getoond
                    MarkdownTekst(tekst: puurAntwoord)
                        .font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.inkt))
                        .textSelection(.enabled)
                }
                .padding(10)
                .frame(maxWidth: 480, alignment: .leading)
                .background(RoundedRectangle(cornerRadius: 8)
                    .stroke(Thema.kleur(.lijn)))
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func formatteerTijd(_ iso: String) -> String {
        // ISO → HH:MM
        if let datum = ISO8601DateFormatter().date(from: iso) {
            let f = DateFormatter()
            f.dateFormat = "HH:mm"
            return f.string(from: datum)
        }
        return iso
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
        // Optimistisch: direct tonen
        store.voegLokaalToe(tekst: tekst)
        store.stuur(agent: gekozenAgent, tekst: tekst, van: gebruikersNaam,
                    runner: runner, repoPad: repoPad, interpreter: interpreter) {
            store.laadDraad(agent: gekozenAgent, runner: runner,
                            repoPad: repoPad, interpreter: interpreter)
        }
    }
}

// MARK: - DenkBlok — inklapbaar "Thought \u{25BE}" per bericht (net als Hermes)

struct DenkBlok: View {
    let redenatie: String
    @State private var open = false   // standaard DICHT (keuze Tiëndo 6 sept)

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Button {
                withAnimation(.easeInOut(duration: 0.2)) { open.toggle() }
            } label: {
                HStack(spacing: 4) {
                    Text("Thought")
                        .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.2)
                        .foregroundStyle(Thema.kleur(.gedempt))
                    Image(systemName: open ? "chevron.down" : "chevron.right")
                        .font(.system(size: 8, weight: .semibold))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
            }
            .buttonStyle(.plain)

            if open {
                Text(redenatie)
                    .font(Thema.tekst(10))
                    .foregroundStyle(Thema.kleur(.zacht))
                    .padding(8)
                    .frame(maxWidth: 420, alignment: .leading)
                    .background(RoundedRectangle(cornerRadius: 6)
                        .stroke(Thema.kleur(.lijn), style: StrokeStyle(dash: [3, 3])))
                    .textSelection(.enabled)
            }
        }
    }
}

// MARK: - Typing-stip (geanimeerd)

struct TypingStip: View {
    let vertraging: Double
    @State private var pulseren = false

    var body: some View {
        Circle()
            .fill(Thema.kleur(.gedempt))
            .frame(width: 5, height: 5)
            .opacity(pulseren ? 1.0 : 0.3)
            .animation(.easeInOut(duration: 0.6).repeatForever().delay(vertraging),
                       value: pulseren)
            .onAppear { pulseren = true }
    }
}

// MARK: - Simpele markdown-rendering voor antwoorden

struct MarkdownTekst: View {
    let tekst: String

    private var regels: [String] {
        tekst.components(separatedBy: "\n")
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(Array(regels.enumerated()), id: \.offset) { _, regel in
                if regel.hasPrefix("### ") {
                    Text(String(regel.dropFirst(4)))
                        .font(Thema.tekst(12, gewicht: .semibold))
                } else if regel.hasPrefix("## ") {
                    Text(String(regel.dropFirst(3)))
                        .font(Thema.tekst(13, gewicht: .semibold))
                } else if regel.hasPrefix("# ") {
                    Text(String(regel.dropFirst(2)))
                        .font(Thema.tekst(14, gewicht: .bold))
                } else if regel.hasPrefix("- ") || regel.hasPrefix("• ") {
                    HStack(alignment: .top, spacing: 6) {
                        Text("•").font(Thema.tekst(12))
                        Text(String(regel.dropFirst(2)))
                            .font(Thema.tekst(12))
                    }
                } else if regel.hasPrefix("```") {
                    Text(regel)
                        .font(.system(size: 11, design: .monospaced))
                        .padding(6)
                        .background(RoundedRectangle(cornerRadius: 4).fill(Thema.kleur(.papierZacht)))
                } else if !regel.isEmpty {
                    Text(regel).font(Thema.tekst(12))
                }
            }
        }
    }
}

