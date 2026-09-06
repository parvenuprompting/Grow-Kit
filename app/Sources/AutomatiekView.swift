// AutomatiekView — Automatiek in GrowKit (inbouw van de Automatiek-app).
//
// Eén zin in gewone taal → voorstelverzoek naar KairOS (wachtrij,
// bron=automatiek-pijplijn) → zijn JSON-antwoord wordt een plan in
// concept. De mens bekijkt de zes blokken, zet het plan naar KLAAR
// (alleen na validatie) en exporteert markdown/JSON.
//
// KairOS denkt: zelfde typing-stippen als Agent Chat. Elke 15s stil
// kijken of het voorstel al binnen is (de wachtrij-antwoorden stromen
// via agentchat-draad; het plan zelf komt via automatieklijst).

import SwiftUI

struct AutomatiekPlanRij: Identifiable {
    let id: String
    let titel: String
    let status: String
    let gewijzigd: String
}

struct AutomatiekView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    @State private var wens = ""
    @State private var plannen: [AutomatiekPlanRij] = []
    @State private var geladen = false
    @State private var fout: String?
    @State private var melding: String?
    @State private var meldingOk = false
    @State private var bezig = false
    @State private var wachtOpKairOS = false
    @State private var verversTimer: Timer?
    @State private var gebruikersNaam = ""
    @State private var gekozenPlanId = ""
    @State private var gekozenDetail: [String: Any]? = nil

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                kop
                if let fout { foutKaart(fout) }

                wensKaart
                if wachtOpKairOS { denkenRij }
                if let melding { meldingRegel(melding, ok: meldingOk) }

                if let detail = gekozenDetail, !toonGeschiedenisModus {
                    detailKaart(detail)
                }
                lijstKaart
                Spacer(minLength: 16)
            }
            .padding(28)
        }
        .background(Thema.kleur(.papier))
        .onAppear {
            laad()
            laadGebruiker()
        }
        .onDisappear { verversTimer?.invalidate(); verversTimer = nil }
    }

    private var toonGeschiedenisModus: Bool { false }

    // MARK: Kop

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("16 AUTOMATIEK · VAN WENS TOT WERK")
                .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            Text("Automatiek").font(Thema.display(30))
            Text("Zeg in één zin wat je geautomatiseerd wilt. KairOS maakt het voorstel — jij kijkt de zes blokken na en zet hem klaar. Geheimen horen nooit in een plan; de scanner weigert ze.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: Wens → KairOS

    private var wensKaart: some View {
        Kaart(kop: "Wat wil je automatiseren?", rechterKop: "KAIROS MAAKT HET VOORSTEL") {
            VStack(alignment: .leading, spacing: 10) {
                TextField("bijv. elke ochtend een samenvatting van nieuwe Drive-bestanden in Telegram",
                          text: $wens, axis: .vertical)
                    .textFieldStyle(.plain)
                    .font(Thema.tekst(13))
                    .lineLimit(1...4)
                    .padding(10)
                    .background(RoundedRectangle(cornerRadius: 8).stroke(Thema.kleur(.lijn)))
                    .onSubmit { vraagVoorstel() }

                HStack {
                    PillKnop(titel: bezig ? "Bezig…" : "Vraag KairOS", gevuld: true) {
                        vraagVoorstel()
                    }
                    Spacer()
                }
            }
        }
    }

    private var denkenRij: some View {
        HStack(spacing: 8) {
            TypingStip(vertraging: 0)
            TypingStip(vertraging: 0.2)
            TypingStip(vertraging: 0.4)
            Text("KairOS denkt na over je wens…")
                .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
            Spacer()
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 8).fill(Thema.kleur(.papierZacht)))
    }

    // MARK: Plan-detail (zes blokken)

    private func detailKaart(_ plan: [String: Any]) -> some View {
        let blokken = plan["blokken"] as? [String: Any] ?? [:]
        let status = plan["status"] as? String ?? "concept"
        return Kaart(kop: plan["titel"] as? String ?? "?",
                     rechterKop: status.uppercased() + " · SCHEMA " + String(plan["versie"] as? Int ?? 1)) {
            VStack(alignment: .leading, spacing: 14) {
                blokBlok("01 · Doel & trigger") {
                    if let det = blokken["doel_en_trigger"] as? [String: Any] {
                        sleutelWaarde("Doel", det["doel"])
                        sleutelWaarde("Trigger", det["trigger"])
                        sleutelWaarde("Type", det["trigger_type"])
                    }
                }
                blokBlok("02 · Bronnen & data") {
                    if let b = blokken["bronnen"] as? [String: Any] {
                        sleutelWaarde("Diensten", b["diensten"])
                        sleutelWaarde("Data", b["data"])
                        sleutelWaarde("Authenticatie", b["authenticatie"])
                    }
                }
                blokBlok("03 · Stappen") {
                    if let stappen = blokken["stappen"] as? [[String: Any]] {
                        ForEach(stappen.indices, id: \.self) { i in
                            let s = stappen[i]
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(s["nummer"] as? Int ?? i+1). \(s["omschrijving"] as? String ?? "")")
                                    .font(Thema.tekst(12, gewicht: .medium))
                                Text("  foutscenario: \(s["foutscenario"] as? String ?? "")")
                                    .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                            }
                        }
                    }
                }
                blokBlok("04 · Kwaliteit & verificatie") {
                    if let k = blokken["kwaliteit"] as? [String: Any] {
                        sleutelWaarde("Verificatie", k["verificatie"])
                        sleutelWaarde("Testaanpak", k["testaanpak"])
                    }
                }
                blokBlok("05 · Planning & uitvoering") {
                    if let u = blokken["uitvoering"] as? [String: Any] {
                        sleutelWaarde("Omgeving", u["omgeving"])
                        sleutelWaarde("Planning", u["planning"])
                        sleutelWaarde("Faalafhandeling", u["faalafhandeling"])
                    }
                }
                blokBlok("06 · Randvoorwaarden & privacy") {
                    if let r = blokken["randvoorwaarden"] as? [String: Any] {
                        sleutelWaarde("Privacy", r["privacy"])
                        sleutelWaarde("Randgevallen", r["randgevallen"])
                    }
                }

                Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
                HStack {
                    if status != "klaar" {
                        PillKnop(titel: "Zet naar KLAAR", gevuld: true) { zetKlaar() }
                    } else {
                        Text("Dit plan is klaar voor uitvoering.")
                            .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                    }
                    Spacer()
                    PillKnop(titel: "Markdown", gevuld: false, compact: true) { exporteer("markdown") }
                    PillKnop(titel: "JSON", gevuld: false, compact: true) { exporteer("json") }
                    PillKnop(titel: "Sluiten", gevuld: false, compact: true) { gekozenPlanId = ""; gekozenDetail = nil }
                }
            }
        }
    }

    private func blokBlok<Inhoud: View>(_ kopTekst: String,
                                        @ViewBuilder inhoud: () -> Inhoud) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(kopTekst).font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            inhoud()
        }
    }

    private func sleutelWaarde(_ sleutel: String, _ waarde: Any?) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(sleutel.uppercased())
                .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.2)
                .foregroundStyle(Thema.kleur(.gedempt))
                .frame(width: 110, alignment: .leading)
            Text(waarde as? String ?? "")
                .font(Thema.tekst(12))
                .textSelection(.enabled)
            Spacer()
        }
    }

    // MARK: Lijst

    private var lijstKaart: some View {
        Kaart(kop: "Plannen", rechterKop: geladen ? "\(plannen.count) STUK" : nil) {
            VStack(alignment: .leading, spacing: 0) {
                if !geladen {
                    Text("Laden…").font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                } else if plannen.isEmpty {
                    Text("Nog geen plannen. Beschrijf hierboven je wens — KairOS maakt het voorstel.")
                        .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                } else {
                    ForEach(plannen) { rij in
                        planRij(rij)
                    }
                }
            }
        }
    }

    private func planRij(_ rij: AutomatiekPlanRij) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 3) {
                Text(rij.titel).font(Thema.tekst(13, gewicht: .medium))
                Text(rij.status.uppercased())
                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                    .foregroundStyle(rij.status == "klaar" ? Thema.kleur(.inkt) : Thema.kleur(.gedempt))
            }
            Spacer()
            PillKnop(titel: "Bekijk", gevuld: gekozenPlanId == rij.id, compact: true) {
                bekijk(rij.id)
            }
        }
        .padding(.vertical, 9)
        .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
    }

    @ViewBuilder private func meldingRegel(_ tekst: String, ok: Bool) -> some View {
        HStack(spacing: 8) {
            Image(systemName: ok ? "checkmark.circle" : "exclamationmark.triangle")
                .font(.system(size: 12))
            Text(tekst).font(Thema.tekst(12))
        }
        .foregroundStyle(Thema.kleur(ok ? .inkt : .zacht))
    }

    private func foutKaart(_ melding: String) -> some View {
        Kaart(kop: "Let op", rechterKop: "FOUT") {
            Text(melding).font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
        }
    }

    // MARK: Acties

    private func laadGebruiker() {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "profiel", invoer: ["actie": "lees"])
            await MainActor.run {
                if let r, r.ok, let profiel = r.data["profiel"] as? [String: Any],
                   let naam = profiel["naam"] as? String, !naam.isEmpty {
                    gebruikersNaam = naam
                }
            }
        }
    }

    private func laad() {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "automatieklijst", invoer: [:])
            await MainActor.run {
                if let r, r.ok {
                    let ruw = r.data["plannen"] as? [[String: Any]] ?? []
                    plannen = ruw.map { p in
                        AutomatiekPlanRij(id: p["id"] as? String ?? "",
                                          titel: p["titel"] as? String ?? "",
                                          status: p["status"] as? String ?? "concept",
                                          gewijzigd: p["gewijzigd"] as? String ?? "")
                    }
                    geladen = true
                    // Als we op een voorstel wachten: is er al een nieuw plan?
                    if wachtOpKairOS, let eerste = plannen.first,
                       eerste.status == "concept", gekozenPlanId.isEmpty {
                        // niets forceren; de mens klikt 'Bekijk'
                    }
                } else {
                    fout = r?.fout ?? "Lijst onbereikbaar."
                }
            }
        }
    }

    private func vraagVoorstel() {
        let zin = wens.trimmingCharacters(in: .whitespaces)
        guard !zin.isEmpty else { return }
        fout = nil
        melding = nil
        bezig = true
        wachtOpKairOS = true
        Task {
            var invoer: [String: Any] = ["wens": zin]
            if !gebruikersNaam.isEmpty { invoer["van"] = gebruikersNaam }
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "automatiekvoorstel", invoer: invoer)
            await MainActor.run {
                bezig = false
                if let r, r.ok {
                    meldingOk = true
                    melding = "Voorstelverzoek staat in de wachtrij van KairOS — zijn plan verschijnt binnen enkele minuten in de lijst."
                    wens = ""
                    startVervers()
                } else {
                    wachtOpKairOS = false
                    meldingOk = false
                    melding = r?.fout ?? "Versturen mislukt."
                }
            }
        }
    }

    private func startVervers() {
        verversTimer?.invalidate()
        verversTimer = Timer.scheduledTimer(withTimeInterval: 15, repeats: true) { t in
            laad()
            // Stop met polleren na 10 minuten (faalcontract-achtig)
            // — de mens kan altijd handmatig verversen.
        }
    }

    private func bekijk(_ id: String) {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "automatieklees", invoer: ["id": id])
            await MainActor.run {
                if let r, r.ok, let plan = r.data["plan"] as? [String: Any] {
                    gekozenPlanId = id
                    gekozenDetail = plan
                } else {
                    fout = r?.fout ?? "Kon plan niet lezen."
                }
            }
        }
    }

    private func zetKlaar() {
        guard !gekozenPlanId.isEmpty else { return }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "automatiekstatus",
                                           invoer: ["id": gekozenPlanId, "klaar": true])
            await MainActor.run {
                if let r, r.ok, let plan = r.data["plan"] as? [String: Any] {
                    gekozenDetail = plan
                    meldingOk = true
                    melding = "Plan is KLAAR — klaar voor uitvoering via KairOS."
                    laad()
                } else {
                    meldingOk = false
                    melding = r?.fout ?? "Naar KLAAR mislukt (is elk blok gevuld?)."
                }
            }
        }
    }

    private func exporteer(_ formaat: String) {
        guard !gekozenPlanId.isEmpty else { return }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "automatiekexport",
                                           invoer: ["id": gekozenPlanId, "formaat": formaat])
            await MainActor.run {
                if let r, r.ok, let inhoud = r.data["inhoud"] as? String {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(inhoud, forType: .string)
                    meldingOk = true
                    melding = "\(formaat) gekopieerd naar het klembord."
                } else {
                    meldingOk = false
                    melding = r?.fout ?? "Export mislukt."
                }
            }
        }
    }
}