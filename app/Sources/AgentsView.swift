// AgentsView — het governor-scherm: wie draagt welke taken, wie wacht op
// controle, wie is vrijgelaten, en wat de observer meldt.
//
// Bedienaar-principe: de app interpreteert niets. Alle regels (2 taken per
// agent, subagent bij limiet, controle vóór vrijlating, observer zonder
// uitvoer, max 8 agents) zitten in kern/growkit_agents.py; dit scherm leest
// de status via adapter `governor` en stuurt jouw besluiten door.

import SwiftUI

// MARK: - Data (slecht-streng: wat de adapter zegt, zegt het scherm)

final class GovernorStatus: ObservableObject {
    @Published var geladen = false
    @Published var fout: String?
    @Published var limieten: [String: Any] = [:]
    @Published var agents: [[String: Any]] = []
    @Published var taken: [String: Any] = [:]
    @Published var meldingen: [[String: Any]] = []
    @Published var familie: [[String: Any]] = []
    @Published var leeft: [String: String] = [:]
    @Published var controleWachtrij: [[String: Any]] = []
    @Published var voorstellen: [[String: Any]] = []
    @Published var harnasStatus: String? = nil
    @Published var laatsteActie: String?

    var takenPerAgent: Int { limieten["taken_per_agent"] as? Int ?? 2 }
    var maxAgents: Int { limieten["max_agents"] as? Int ?? 8 }
    var maxTaken: Int { limieten["max_taken_totaal"] as? Int ?? 16 }

    static func leeg() -> GovernorStatus { GovernorStatus() }
}

// MARK: - View

struct AgentsView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    @StateObject private var status = GovernorStatus.leeg()
    @State private var nieuwAgent = ""
    @State private var nieuwTaak = ""
    @State private var nieuwTitel = ""
    @State private var bezig = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                kop
                familieKaart
                observatieKaart
                controleKaart
                limietenKaart
                if let fout = status.fout {
                    foutKaart(fout)
                }
                agentsKaart
                takenKaart
                observerKaart
            }
            .padding(24)
        }
        .background(Thema.kleur(.papier))
        .onAppear { laadStatus() }
    }

    // MARK: Kop

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Governor").font(Thema.display(30))
            Text("Elke agent draagt maximaal \(status.takenPerAgent) taken. Bij meer vormt hij een tijdelijke subagent. Een taak is pas af na controle. De observer ziet alles en voert niets uit.")
                .font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: Familie (slice A — de vaste cast)

    private var familieKaart: some View {
        Kaart(kop: "Familie", rechterKop: "\(status.familie.count) VAN 7 · TELEGRAM") {
            VStack(alignment: .leading, spacing: 0) {
                if status.familie.isEmpty {
                    Text("Familie nog niet geladen.").font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
                ForEach(Array(status.familie.enumerated()), id: \.offset) { i, agent in
                    familieRij(agent)
                    if i < status.familie.count - 1 {
                        Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
                    }
                }
            }
        }
    }

    private func familieRij(_ agent: [String: Any]) -> some View {
        let naam = agent["naam"] as? String ?? "?"
        let rol = agent["rol"] as? String ?? ""
        let beschrijving = agent["beschrijving"] as? String ?? ""
        let isObserver = rol == "observer"
        let leeftStatus = status.leeft[naam.lowercased()] ?? "onbekend"
        let leeftKleur: Color = leeftStatus == "active" ? .green
            : (leeftStatus == "onbekend" ? .gray : .red)

        return HStack(alignment: .firstTextBaseline, spacing: 14) {
            Text(naam).font(Thema.display(16))
                .frame(width: 110, alignment: .leading)
            Text(rol.uppercased())
                .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.2)
                .foregroundStyle(Thema.kleur(isObserver ? .inkt : .gedempt))
                .frame(width: 90, alignment: .leading)
            Text(beschrijving)
                .font(Thema.tekst(11))
                .foregroundStyle(Thema.kleur(.zacht))
            Spacer()
            HStack(spacing: 5) {
                Circle().fill(leeftKleur).frame(width: 7, height: 7)
                Text(leeftStatus == "active" ? "LIVE" : leeftStatus.uppercased())
                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(1)
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
            .frame(width: 70, alignment: .trailing)
        }
        .padding(.vertical, 10)
    }

    // MARK: Observaties (slice E — Genius' voorstellen)

    private var observatieKaart: some View {
        Kaart(kop: "Observaties", rechterKop: "GENIUS · ALLEEN-LEZEN") {
            VStack(alignment: .leading, spacing: 10) {
                if status.voorstellen.isEmpty {
                    Text("Geen open voorstellen in de brein-inbox — het stille genie heeft niets aan te merken.")
                        .font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
                ForEach(Array(status.voorstellen.prefix(5).enumerated()), id: \.offset) { _, v in
                    VStack(alignment: .leading, spacing: 3) {
                        HStack {
                            Text(v["titel"] as? String ?? "")
                                .font(Thema.tekst(12, gewicht: .medium))
                            Spacer()
                            Text((v["afzender"] as? String ?? "").uppercased())
                                .font(Thema.tekst(8, gewicht: .semibold)).tracking(1)
                                .foregroundStyle(Thema.kleur(.gedempt))
                        }
                        Text(v["inhoud"] as? String ?? "")
                            .font(Thema.tekst(10))
                            .foregroundStyle(Thema.kleur(.zacht))
                            .lineLimit(2)
                    }
                    .padding(.vertical, 3)
                }
                if status.voorstellen.count > 5 {
                    Text("+ \(status.voorstellen.count - 5) meer in de inbox")
                        .font(Thema.tekst(10))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
            }
        }
    }

    // MARK: Controle (slice D — de rondte)

    private var controleKaart: some View {
        Kaart(kop: "Controle", rechterKop: "DE MENS HEEFT DE LAATSTE STEM") {
            VStack(alignment: .leading, spacing: 10) {
                if status.controleWachtrij.isEmpty {
                    Text("Niets wacht op jouw oordeel. Haal afgeronde taken op zodra agents ze neerleggen.")
                        .font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
                ForEach(Array(status.controleWachtrij.enumerated()), id: \.offset) { _, item in
                    controleRij(item)
                }
                HStack {
                    PillKnop(titel: "Haal afgeronde taken op") { haalOp() }
                    if let laatste = status.laatsteActie {
                        Text(laatste)
                            .font(Thema.tekst(11))
                            .foregroundStyle(Thema.kleur(.zacht))
                    }
                }
                if let harnas = status.harnasStatus {
                    Text("🛡 " + harnas)
                        .font(Thema.tekst(11, gewicht: .semibold))
                        .foregroundStyle(.red)
                        .padding(8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Thema.kleur(.papierZacht))
                }
            }
        }
    }

    private func controleRij(_ item: [String: Any]) -> some View {
        let agent = item["agent"] as? String ?? "?"
        let taakId = item["taak_id"] as? String ?? "?"
        let titel = item["titel"] as? String ?? ""
        let bewijs = item["bewijs"] as? String ?? ""

        return HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(agent.capitalized).font(Thema.display(14))
                .frame(width: 90, alignment: .leading)
            VStack(alignment: .leading, spacing: 2) {
                Text(titel.isEmpty ? taakId : titel).font(Thema.tekst(12))
                if !bewijs.isEmpty {
                    Text("bewijs: " + bewijs)
                        .font(Thema.tekst(10))
                        .foregroundStyle(Thema.kleur(.gedempt))
                        .lineLimit(1)
                }
            }
            Spacer()
            PillKnop(titel: "Goedkeuren") { doeBesluit(agent: agent, taakId: taakId, goed: true) }
            PillKnop(titel: "Afkeuren") { doeBesluit(agent: agent, taakId: taakId, goed: false) }
        }
        .padding(.vertical, 4)
    }

    private func haalOp() {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agentcontrole",
                                           invoer: ["actie": "ophalen"])
            await MainActor.run {
                if let r, let lijst = r.data["afgerond"] as? [[String: Any]] {
                    status.controleWachtrij = lijst
                    status.laatsteActie = lijst.isEmpty
                        ? "Niets nieuw opgehaald."
                        : "\(lijst.count) taak/taken opgehaald voor controle."
                }
            }
        }
    }

    private func doeBesluit(agent: String, taakId: String, goed: Bool) {
        // Eérst het harnas: tests zijn wet. Gewijzigde kadertests blokkeren
        // goedkeuring — ongeacht hoe groen het bewijs eruitziet.
        Task {
            let h = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "harnas",
                                           invoer: ["actie": "check"])
            await MainActor.run {
                if let h, let data = h.data as? [String: Any],
                   let ok = data["ok"] as? Bool, !ok {
                    status.harnasStatus = "GEBOLOKKEERD: " +
                        ((data["fouten"] as? [String])?.joined(separator: " · ") ?? "tests gewijzigd")
                    return
                }
                status.harnasStatus = nil
                Task {
                    let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                                   commando: "agentcontrole",
                                                   invoer: ["actie": "besluit", "agent": agent,
                                                            "taak_id": taakId, "goed": goed])
                    await MainActor.run {
                        if let r, r.ok {
                            status.controleWachtrij.removeAll {
                                ($0["taak_id"] as? String) == taakId
                            }
                            status.laatsteActie = (goed ? "✓ Goedgekeurd: " : "✕ Afgekeurd: ") + taakId
                        } else {
                            status.laatsteActie = "✕ " + (r?.fout ?? "controle onbereikbaar")
                        }
                    }
                }
            }
        }
    }

    // MARK: Limieten

    private var limietenKaart: some View {
        Kaart(kop: "Grenzen", rechterKop: "VAST — geen gretigheid") {
            HStack(spacing: 24) {
                limietCell(titel: "TAKEN PER AGENT", waarde: "\(status.takenPerAgent)")
                limietCell(titel: "MAX AGENTS", waarde: "\(status.maxAgents)")
                limietCell(titel: "MAX TAKEN", waarde: "\(status.maxTaken)")
                Spacer()
            }
        }
    }

    private func limietCell(titel: String, waarde: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(waarde).font(Thema.display(34))
            Text(titel).font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                .foregroundStyle(Thema.kleur(.gedempt))
        }
    }

    private func foutKaart(_ tekst: String) -> some View {
        Kaart(kop: "Let op", gestippeld: true) {
            Text(tekst).font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.inkt))
        }
    }

    // MARK: Agents

    private var agentsKaart: some View {
        Kaart(kop: "Agenten", rechterKop: "OBSERVER MAG NIETS") {
            VStack(alignment: .leading, spacing: 14) {
                if status.agents.isEmpty {
                    Text("Nog geen agenten geregistreerd.").font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
                ForEach(Array(status.agents.enumerated()), id: \.offset) { _, agent in
                    agentRij(agent)
                }
                if let laatste = status.laatsteActie {
                    Text(laatste)
                        .font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.zacht))
                }
                nieuweTaakRij
            }
        }
    }

    private func agentRij(_ agent: [String: Any]) -> some View {
        let naam = agent["agent"] as? String ?? "?"
        let rol = agent["rol"] as? String ?? "hoofd"
        let open = agent["open"] as? [String] ?? []
        let afrondend = agent["afrondend"] as? [String] ?? []
        let vrijgelaten = agent["vrijgelaten"] as? Bool ?? false

        return HStack(alignment: .top, spacing: 14) {
            VStack(alignment: .leading, spacing: 3) {
                Text(naam).font(Thema.display(16))
                Text(rolOpmerking(rol, vrijgelaten))
                    .font(Thema.tekst(10)).tracking(0.5)
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
            .frame(width: 170, alignment: .leading)

            VStack(alignment: .leading, spacing: 6) {
                if rol == "observer" {
                    Text("ziet alles · voert niets uit · krijgt nooit taken")
                        .font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.gedempt))
                } else if open.isEmpty && afrondend.isEmpty {
                    Text("geen taken — \(vrijgelaten ? "vrijgelaten" : "beschikbaar")")
                        .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                }
                ForEach(open, id: \.self) { taak in
                    taakChip(taak, stijl: .neutraal)
                }
                ForEach(afrondend, id: \.self) { taak in
                    taakChip(taak, stijl: .mens)
                }
            }

            Spacer()

            if rol != "observer", open.count >= status.takenPerAgent {
                PillKnop(titel: "Subagent vormen") { subagentVormen(ouder: naam) }
            }
        }
        .padding(.vertical, 6)
    }

    private func rolOpmerking(_ rol: String, _ vrijgelaten: Bool) -> String {
        let basis: String
        switch rol {
        case "observer": basis = "OBSERVER"
        case "subagent": basis = "SUBAGENT (TIJDELIJK)"
        default: basis = "HOOFD-AGENT"
        }
        return vrijgelaten ? basis + " · VRIJGELATEN" : basis
    }

    private func taakChip(_ id: String, stijl: BadgeStijl) -> some View {
        HStack(spacing: 8) {
            StatusBadge(tekst: stijl == .mens ? "WACHT OP CONTROLE" : "OPEN", stijl: stijl)
            Text(id).font(Thema.tekst(12))
            if stijl == .mens {
                PillKnop(titel: "Goedkeuren") { controleer(taak: id, goed: true) }
                PillKnop(titel: "Afkeuren") { controleer(taak: id, goed: false) }
            }
        }
    }

    private var nieuweTaakRij: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 10) {
                Picker("", selection: $nieuwAgent) {
                    Text("Agent…").tag("")
                    ForEach(familieNamen, id: \.self) { naam in
                        Text(naam).tag(naam.lowercased())
                    }
                }
                .font(Thema.tekst(12))
                .frame(width: 130)

                Text("Taak-id (bijv. taak-001)")
                    .font(Thema.tekst(11))
                    .foregroundStyle(Thema.kleur(.gedempt))
                    .frame(width: 150, alignment: .leading)
                TextField("", text: $nieuwTaak)
                    .textFieldStyle(.plain)
                    .font(Thema.tekst(12))
                    .frame(width: 110)
                TextField("Wat moet er gedaan worden?", text: $nieuwTitel)
                    .textFieldStyle(.plain)
                    .font(Thema.tekst(12))
                PillKnop(titel: "Taak koppelen", gevuld: true) {
                    koppelTaak()
                }
            }
            if !nieuwAgent.isEmpty, let gekozen = geladenAgent {
                HStack(spacing: 6) {
                    Circle().fill(Thema.kleur(.inkt)).frame(width: 6, height: 6)
                    Text("Geladen: \(gekozen["naam"] as? String ?? nieuwAgent) — \(gekozen["beschrijving"] as? String ?? "")")
                        .font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.zacht))
                    Spacer()
                }
                .transition(.opacity)
            }
        }
        .padding(.top, 6)
    }

    private var geladenAgent: [String: Any]? {
        status.familie.first { ($0["naam"] as? String ?? "").lowercased() == nieuwAgent }
    }

    private var familieNamen: [String] {
        status.familie.compactMap { $0["naam"] as? String }
    }

    private func koppelTaak() {
        let a = nieuwAgent.trimmingCharacters(in: .whitespaces)
        let t = nieuwTaak.trimmingCharacters(in: .whitespaces)
        let titel = nieuwTitel.trimmingCharacters(in: .whitespaces)
        guard !a.isEmpty, !t.isEmpty, !titel.isEmpty else {
            status.laatsteActie = "Vul agent, taak-id en titel in."; return
        }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agenttaak",
                                           invoer: ["agent": a, "taak_id": t,
                                                    "titel": titel])
            await MainActor.run {
                if let res = r?.data["resultaat"] as? [String: Any] {
                    status.laatsteActie = (res["ok"] as? Bool == true ? "✓ " : "✕ ")
                        + (res["reden"] as? String ?? "")
                } else if let fout = r?.fout {
                    status.laatsteActie = "✕ " + fout
                }
            }
        }
        nieuwTaak = ""
        nieuwTitel = ""
    }

    // MARK: Taken

    private var takenKaart: some View {
        Kaart(kop: "Tellen", rechterKop: "\(status.taken.count) VAN \(status.maxTaken)") {
            if status.taken.isEmpty {
                Text("Nog geen taken aangemeld.").font(Thema.tekst(12))
                    .foregroundStyle(Thema.kleur(.gedempt))
            } else {
                Text("\(status.taken.count) taak/taken in het register — max \(status.maxTaken). Meer willen is gewoon gretig.")
                    .font(Thema.tekst(12))
            }
        }
    }

    // MARK: Observer

    private var observerKaart: some View {
        Kaart(kop: "Observer-meldingen", rechterKop: "ALLEEN LEZEN") {
            if status.meldingen.isEmpty {
                Text("De observer heeft nog niets gemeld — dat is goed nieuws.")
                    .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
            } else {
                VStack(alignment: .leading, spacing: 10) {
                    ForEach(Array(status.meldingen.enumerated().reversed()), id: \.offset) { _, m in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(m["tekst"] as? String ?? "")
                                .font(Thema.tekst(12))
                            Text(m["tijdstip"] as? String ?? "")
                                .font(Thema.tekst(9)).tracking(1)
                                .foregroundStyle(Thema.kleur(.gedempt))
                        }
                    }
                }
            }
        }
    }

    // MARK: Acties (alles via de adapter — de app beslist niets)

    private func laadStatus() {
        bezig = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "governor",
                                           invoer: ["doel": "~/growkit-governor"])
            let f = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "familie",
                                           invoer: ["actie": "status"])
            let s = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agentstatus",
                                           invoer: [:])
            let o = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "observaties",
                                           invoer: [:])
            await MainActor.run {
                bezig = false
                if let o, let lijst = o.data["voorstellen"] as? [[String: Any]] {
                    status.voorstellen = lijst
                }
                if let f, f.ok, let fam = f.data["familie"] as? [[String: Any]] {
                    status.familie = fam
                }
                if let s, let agents = s.data["agents"] as? [[String: Any]] {
                    var kaart: [String: String] = [:]
                    for a in agents {
                        if let naam = a["agent"] as? String,
                           let st = a["status"] as? String {
                            kaart[naam] = st
                        }
                    }
                    status.leeft = kaart
                }
                vulStatus(r)
            }
        }
    }

    private func vulStatus(_ r: AdapterResultaat?) {
        guard let r, r.ok else {
            status.fout = r?.fout ?? "De adapter reageerde niet. Controleer repo-pad en interpreter in Instellingen."
            status.geladen = true
            return
        }
        status.fout = nil
        status.limieten = r.data["limieten"] as? [String: Any] ?? [:]
        status.agents = r.data["agents"] as? [[String: Any]] ?? []
        status.taken = r.data["taken"] as? [String: Any] ?? [:]
        status.meldingen = r.data["observer_meldingen"] as? [[String: Any]] ?? []
        status.geladen = true
    }

    private func actie(_ invoer: [String: Any]) {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "governor", invoer: invoer)
            await MainActor.run {
                if let res = r?.data["resultaat"] as? [String: Any] {
                    let ok = res["ok"] as? Bool ?? false
                    let reden = res["reden"] as? String ?? ""
                    status.laatsteActie = (ok ? "✓ " : "✕ ") + reden
                }
                vulStatus(r)
            }
        }
    }

    private func controleer(taak: String, goed: Bool) {
        actie(["doel": "~/growkit-governor", "actie": "controle",
               "taak_id": taak, "goed": goed,
               "reden": goed ? "" : "afgekeurd in de app"])
    }

    private func subagentVormen(ouder: String) {
        actie(["doel": "~/growkit-governor", "actie": "subagent", "agent": ouder])
    }
}

// Kleine hulp: Optional-UIT-check zonder de standaardwaarde te verbergen.
extension Optional {
    var isNil: Bool { self == nil }
}
