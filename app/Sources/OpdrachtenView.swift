import SwiftUI

/// Eén dossier: de adapter bewaart het plan, voortgang, bewijs en oordeel.
/// In de stand "Vandaag" staat er bovendien het dagoverzicht dat eerder op
/// het thuisscherm stond: begroeting met de ZT-3-variant, vier cijfers in
/// één oogopslag en de knowledge graph.
struct OpdrachtenView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    var vandaag = false
    var onNavigeer: (ContentView.Modi) -> Void = { _ in }
    @State private var opdrachten: [[String: Any]] = []
    @State private var profielen: [[String: Any]] = []
    @State private var dossier: [String: Any]?
    @State private var titel = ""
    @State private var criterium = ""
    @State private var profiel = ""
    @State private var toelichting = ""
    @State private var fout: String?
    @State private var bezig = false
    @State private var nieuw = false
    @State private var voorbeelden: [[String: Any]] = []
    // Dagoverzicht (verhuisd uit HomeView): alleen gevuld in de stand "Vandaag".
    @State private var gebruikersNaam = "Gebruiker"
    @State private var heroTekst = ""
    @State private var familie: [[String: Any]] = []
    @State private var leeft: [String: String] = [:]
    @State private var saldoTekst = ""
    @State private var saldoLaag = false
    @State private var wachtendeGoedkeuringen = 0

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if vandaag { vandaagKop.padding(.horizontal, 28).padding(.top, 24) }
            HStack(alignment: .top, spacing: 0) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        if vandaag {
                            Text("OPDRACHTEN").font(Thema.tekst(10, gewicht: .semibold)).tracking(3)
                                .foregroundStyle(Thema.kleur(.zacht))
                        } else {
                            Text("Opdrachten").font(Thema.display(28))
                            Text("Wat heeft jouw aandacht nodig?").foregroundStyle(.secondary)
                        }
                        Button("Nieuwe opdracht") { nieuw = true; dossier = nil }
                        Button("Verversen") { Task { await laad() } }
                        if opdrachten.isEmpty {
                            Text("Begin met één opdracht. Je bekijkt eerst het plan en beslist daarna of het mag draaien.")
                                .font(.callout).foregroundStyle(.secondary)
                        }
                        ForEach(opdrachten.indices, id: \.self) { i in
                            let item = opdrachten[i]
                            Button {
                                Task { await actie("lees", extra: ["id": item["id"] ?? ""]) }
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(item["titel"] as? String ?? "Opdracht").fontWeight(.medium)
                                    Text(label(item["status"] as? String ?? "")).font(.caption).foregroundStyle(.secondary)
                                }.frame(maxWidth: .infinity, alignment: .leading).padding(10)
                            }.buttonStyle(.bordered)
                        }
                        if !opdrachten.isEmpty {
                            Text("\(opdrachten.filter { ($0["status"] as? String) == "goedgekeurd" }.count) van \(opdrachten.count) opdrachten door jou goedgekeurd")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                        voorbeeldLijst
                    }.padding(22)
                }.frame(width: 280)
                Divider()
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        if let dossier { detail(dossier) }
                        else {
                            formulier
                            if vandaag { graafBlok }
                        }
                        if let fout { Text(fout).foregroundStyle(.red).textSelection(.enabled) }
                        if bezig { ProgressView("Bezig — voortgang wordt bewaard") }
                    }.padding(28).frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        .background(Thema.kleur(.papier))
        .task { await laad() }
    }

    // MARK: - Dagoverzicht ("Vandaag")

    private var vandaagKop: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 5) {
                Text("VANDAAG").font(Thema.tekst(10, gewicht: .semibold)).tracking(3)
                    .foregroundStyle(Thema.kleur(.zacht))
                HStack(alignment: .firstTextBaseline, spacing: 0) {
                    // ZT-3: gebeurtenis-variant (goedkeuringen, saldo, nachtronde)
                    // wint van de kale dagdeel-begroeting.
                    Text((heroTekst.isEmpty ? begroeting : heroTekst) + " ")
                        .font(Thema.display(30))
                    if heroTekst.isEmpty {
                        Text(gebruikersNaam + ".").font(Thema.display(30, cursief: true))
                            .foregroundStyle(Thema.kleur(.zacht))
                    }
                }
            }
            dagrapport
            if wachtendeGoedkeuringen > 0 {
                Button("Bekijk de wachtende goedkeuringen") { onNavigeer(.goedkeuringen) }
                    .buttonStyle(.plain).font(Thema.tekst(11, gewicht: .medium))
                    .foregroundStyle(Thema.kleur(.zacht))
            }
            TipRotorView(tellers: [
                "planten": familie.count,
                "taken": 0,
                "saldo": saldoTekst.isEmpty ? 0 : 1,
            ], onNavigeer: onNavigeer)
        }
    }

    private var begroeting: String {
        let uur = Calendar.current.component(.hour, from: Date())
        switch uur {
        case 0...11: return "Goedemorgen,"
        case 12...17: return "Goedemiddag,"
        default: return "Goedenavond,"
        }
    }

    private var dagrapport: some View {
        HStack(alignment: .top, spacing: 0) {
            dashCel(titel: "FAMILIE", waarde: liveTeller, sub: "van \(familie.count) live")
            verticaleLijn
            dashCel(titel: "SALDO", waarde: saldoTekst.isEmpty ? "—" : saldoTekst,
                    sub: saldoLaag ? "onder €10 — bijvullen" : "OpenRouter", rood: saldoLaag)
            verticaleLijn
            dashCel(titel: "WACHT OP JOU", waarde: wachtendeGoedkeuringen == 0 ? "—" : "\(wachtendeGoedkeuringen)",
                    sub: "goedkeuringen", rood: wachtendeGoedkeuringen > 0)
            verticaleLijn
            dashCel(titel: "GESCHIEDENIS", waarde: "append-only", sub: "niets wordt gewist")
            Spacer()
        }
    }

    private var liveTeller: String {
        let actief = leeft.values.filter { $0 == "active" }.count
        return familie.isEmpty ? "—" : "\(actief)"
    }

    private var verticaleLijn: some View {
        Rectangle().fill(Thema.kleur(.lijn)).frame(width: 1, height: 54)
    }

    private func dashCel(titel: String, waarde: String, sub: String, rood: Bool = false) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(titel).font(Thema.tekst(8, gewicht: .semibold)).tracking(1.5)
                .foregroundStyle(Thema.kleur(.gedempt))
            Text(waarde).font(Thema.display(22))
                .foregroundStyle(rood ? Color.red : Thema.kleur(.inkt))
            Text(sub).font(Thema.tekst(9)).foregroundStyle(Thema.kleur(.gedempt))
        }
        .padding(.horizontal, 18)
    }

    private var graafBlok: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("Knowledge Graph").font(Thema.display(20))
                Text("· het hele brein in één kaart — scroll, zoom, klik en lees")
                    .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                Spacer()
                Button("Openen") { onNavigeer(.graaf) }
                    .buttonStyle(.plain)
                    .font(Thema.tekst(11, gewicht: .medium))
                    .foregroundStyle(Thema.kleur(.zacht))
            }
            GraafView(runner: runner, repoPad: $repoPad, interpreter: $interpreter,
                      compactVoorbeeld: true)
                .frame(height: 420)
                .overlay(RoundedRectangle(cornerRadius: 4).stroke(Thema.kleur(.lijn)))
        }
    }

    // MARK: - Voorbeeldopdrachten (drie lokale demo's, advies 5)

    /// Drie kant-en-klare opdrachten uit de repo. Ze komen uit de adapter, niet uit
    /// een tweede lijst in Swift — anders kan de demo losraken van het echte plan.
    private var voorbeeldLijst: some View {
        VStack(alignment: .leading, spacing: 8) {
            if !voorbeelden.isEmpty {
                Text("VOORBEELDEN").font(Thema.tekst(10, gewicht: .semibold)).tracking(3)
                    .foregroundStyle(Thema.kleur(.zacht)).padding(.top, 10)
                Text("Kies er één. Je ziet eerst het plan, daarna beslis jij of het mag draaien.")
                    .font(.caption).foregroundStyle(.secondary)
                ForEach(voorbeelden.indices, id: \.self) { i in
                    let v = voorbeelden[i]
                    Button {
                        Task { await startVoorbeeld(v) }
                    } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(v["titel"] as? String ?? "Voorbeeld").fontWeight(.medium)
                            Text(v["uitleg"] as? String ?? "").font(.caption)
                                .foregroundStyle(.secondary).lineLimit(3)
                            Text("\(v["stappen"] as? Int ?? 0) stappen · \(v["mens_stappen"] as? Int ?? 0) keer jouw besluit")
                                .font(.caption2).foregroundStyle(Thema.kleur(.gedempt))
                        }.frame(maxWidth: .infinity, alignment: .leading).padding(8)
                    }.buttonStyle(.plain)
                    .disabled(bezig)
                    .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
                }
            }
        }
    }

    @MainActor private func startVoorbeeld(_ v: [String: Any]) async {
        await actie("nieuw", extra: ["titel": v["titel"] ?? "",
                                     "profiel": v["profiel"] ?? "",
                                     "criteria": v["criteria"] ?? []])
    }

    private var formulier: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Wat wil je bereiken?").font(Thema.display(26))
            TextField("Naam van je opdracht", text: $titel)
            Picker("Stappenplan", selection: $profiel) {
                Text("Kies een profiel").tag("")
                ForEach(profielen.indices, id: \.self) { i in
                    let naam = profielen[i]["naam"] as? String ?? ""
                    Text(naam).tag(naam)
                }
            }
            Text("Geslaagd wanneer…").fontWeight(.semibold)
            TextEditor(text: $criterium).frame(minHeight: 90).border(Color.secondary.opacity(0.3))
            Text("Eén acceptatiecriterium per regel. Grow Kit toont straks welke controles dit technisch bewijzen en wat jij nog moet beoordelen.")
                .font(.callout).foregroundStyle(.secondary)
            Button("Maak plan — nog niets uitvoeren") {
                Task { await actie("nieuw", extra: ["titel": titel, "profiel": profiel,
                    "criteria": criterium.split(separator: "\n").map(String.init)]) }
            }.disabled(bezig || titel.isEmpty || profiel.isEmpty || criterium.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }.textFieldStyle(.roundedBorder)
    }

    @ViewBuilder private func detail(_ d: [String: Any]) -> some View {
        let status = d["status"] as? String ?? "concept"
        let plan = d["profiel"] as? [String: Any] ?? [:]
        let rapport = d["rapport"] as? [String: Any] ?? [:]
        let stappen = rapport["stappen"] as? [[String: Any]] ?? []
        let panic = (d["panic"] as? [String: Any])?["actief"] as? Bool ?? false
        Text(d["titel"] as? String ?? "Opdracht").font(Thema.display(28))
        Text(label(status)).font(.headline)
        Text("Opdracht → Plan → Goedkeuring → Uitvoering → Bewijs → Resultaat")
            .font(.callout).foregroundStyle(.secondary)
        GroupBox("Afgesproken resultaat") {
            VStack(alignment: .leading, spacing: 6) {
                ForEach(plan["acceptatiecriteria"] as? [String] ?? [], id: \.self) { Text("• " + $0) }
                Text("Uitvoer: \(d["doel"] as? String ?? "")").textSelection(.enabled)
                Text("Gegevensroute: \(plan["gegevensroute"] as? String ?? "Profielafhankelijk — controleer de commando’s vóór uitvoering")")
                Text("Kosten: \(kosten(d)) · Looptijd: \(Int(d["seconden"] as? Double ?? 0)) s · Beslissingen: \(d["ingrepen"] as? Int ?? 0)")
            }.frame(maxWidth: .infinity, alignment: .leading).padding(6)
        }
        DisclosureGroup("Bekijk het volledige uitvoeringsplan") {
            Text(json(plan)).font(.system(.caption, design: .monospaced)).textSelection(.enabled)
        }
        if panic {
            Text("PANIC actief: er starten geen nieuwe commando’s. Een lopend commando wordt niet afgebroken.").foregroundStyle(.red)
            Button("PANIC handmatig herstellen") { Task { await actie("herstel") } }
        } else {
            HStack {
                if ["concept", "gepauzeerd", "bezig", "afgekeurd"].contains(status) {
                    Button(status == "concept" ? "Plan en grenzen goedkeuren · uitvoeren" : "Hervatten bevestigen") {
                        Task { await actie("uitvoeren", extra: ["bevestig": true, "plan_hash": d["plan_hash"] ?? ""]) }
                    }.disabled(bezig)
                }
                Button("Pauzeer nieuwe stappen", role: .destructive) { Task { await pauzeer() } }
            }
        }
        if status == "bezig" && !bezig {
            Text("Deze run is actief of onderbroken. Ververs eerst. Bij hervatten: controleer of een onvoltooide stap al effect had; geslaagde stappen worden overgeslagen.").font(.callout)
        }
        if status == "wacht_op_mens" || status == "resultaat" {
            GroupBox(status == "wacht_op_mens" ? "Jouw besluit is nodig" : "Beoordeel het resultaat") {
                VStack(alignment: .leading, spacing: 12) {
                    Button("Open resultaatmap") {
                        if let pad = d["doel"] as? String { NSWorkspace.shared.open(URL(fileURLWithPath: pad)) }
                    }
                    TextField("Wat heb je inhoudelijk gecontroleerd?", text: $toelichting).textFieldStyle(.roundedBorder)
                    HStack {
                        Button("Goedkeuren") { Task { await oordeel(true) } }
                        Button("Afkeuren") { Task { await oordeel(false) } }
                    }.disabled(bezig || toelichting.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }.padding(6)
            }
        }
        if status == "goedgekeurd" { Text("Door jou goedgekeurd: \(d["toelichting"] as? String ?? "")") }
        ForEach(stappen.indices, id: \.self) { i in
            let stap = stappen[i]
            GroupBox(stap["id"] as? String ?? "Stap") {
                VStack(alignment: .leading, spacing: 6) {
                    Text(stap["criterium"] as? String ?? "")
                    Text("Technisch: \(label(stap["technisch"] as? String ?? ""))")
                    Text("Inhoudelijk: \(label(stap["inhoudelijk"] as? String ?? ""))")
                    Text("Menselijke stapgoedkeuring: \(label(stap["mens"] as? String ?? ""))")
                    Text(stap["bewijs"] as? String ?? "").font(.caption).textSelection(.enabled)
                }.frame(maxWidth: .infinity, alignment: .leading).padding(6)
            }
        }
        Text(rapport["uitleg"] as? String ?? "").font(.caption).foregroundStyle(.secondary)
        DisclosureGroup("Geschiedenis en bewijsdetails") {
            Text(json(["opdracht": d["geschiedenis"] ?? [], "stappen": d["geschiedenis_stappen"] ?? []]))
                .font(.system(.caption, design: .monospaced)).textSelection(.enabled)
        }
    }

    private func label(_ value: String) -> String { value.replacingOccurrences(of: "_", with: " ").capitalized }
    private func kosten(_ d: [String: Any]) -> String {
        guard let bedrag = d["kosten_eur"] as? Double else { return "niet gemeten" }
        return String(format: "€ %.2f", bedrag)
    }
    private func json(_ value: Any) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys]) else { return "" }
        return String(data: data, encoding: .utf8) ?? ""
    }
    @MainActor private func laad() async {
        do {
            let lijst = try await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "opdrachten", invoer: [:])
            if !lijst.ok { throw AdapterFout.proces(lijst.fout ?? "Laden mislukt") }
            opdrachten = lijst.data["opdrachten"] as? [[String: Any]] ?? []
            let fouten = lijst.data["fouten"] as? [String] ?? []
            if !fouten.isEmpty { fout = fouten.joined(separator: "\n") }
            let p = try await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "profielen", invoer: [:])
            profielen = p.data["profielen"] as? [[String: Any]] ?? []
            if let v = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                              commando: "opdrachten", invoer: ["actie": "voorbeelden"]) {
                voorbeelden = v.data["voorbeelden"] as? [[String: Any]] ?? []
            }
        } catch { fout = error.localizedDescription }
        if vandaag { await laadVandaag() }
    }
    /// Het dagoverzicht: naam, familie, saldo, wachtende goedkeuringen en de
    /// ZT-3-herovariant. Elke bron apart, zodat één onbereikbare bron het hele
    /// overzicht niet leegmaakt.
    @MainActor private func laadVandaag() async {
        let profielR = try? await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "profiel", invoer: ["actie": "lees"])
        let familieR = try? await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "familie", invoer: ["actie": "status"])
        let agentR = try? await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "agentstatus", invoer: [:])
        let saldoR = try? await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "saldo", invoer: [:])
        let keurR = try? await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "goedkeuringen", invoer: ["actie": "lijst"])
        if let profielR, profielR.ok, let profiel = profielR.data["profiel"] as? [String: Any],
           let naam = profiel["naam"] as? String, !naam.isEmpty {
            gebruikersNaam = naam
        }
        if let familieR, familieR.ok, let fam = familieR.data["familie"] as? [[String: Any]] {
            familie = fam
        }
        if let agentR, let agents = agentR.data["agents"] as? [[String: Any]] {
            var kaart: [String: String] = [:]
            for a in agents {
                if let naam = a["agent"] as? String, let st = a["status"] as? String { kaart[naam] = st }
            }
            leeft = kaart
        }
        if let saldoR, saldoR.ok, let rest = saldoR.data["resterend"] as? Double {
            saldoTekst = String(format: "€ %.2f", rest)
            saldoLaag = rest < 10.0
        }
        if let keurR, keurR.ok, let items = keurR.data["items"] as? [[String: Any]] {
            wachtendeGoedkeuringen = items.count
        }
        let nachtrondeNieuws = false // nachtelijke bouwronde-koppeling volgt in een latere slice
        let uur = Calendar.current.component(.hour, from: Date())
        if let v = ZTHero.variant(uur: uur, goedkeuringen: wachtendeGoedkeuringen,
                                  saldo: saldoLaag ? 0 : 100, saldoDrempel: 10,
                                  nachtronde: nachtrondeNieuws) {
            heroTekst = ZTHero.tekstVoor(variant: v, goedkeuringen: wachtendeGoedkeuringen)
        } else {
            heroTekst = ""
        }
    }
    @MainActor private func actie(_ actie: String, extra: [String: Any] = [:]) async {
        bezig = true; fout = nil
        defer { bezig = false }
        var invoer: [String: Any] = ["actie": actie]
        if let id = dossier?["id"] { invoer["id"] = id }
        invoer.merge(extra) { _, new in new }
        do {
            let r = try await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "opdrachten", invoer: invoer, timeOut: 3600)
            if !r.ok { throw AdapterFout.proces(r.fout ?? "Opdracht mislukt") }
            dossier = r.data; nieuw = false; toelichting = ""
            await laad()
        } catch { fout = error.localizedDescription }
    }
    @MainActor private func pauzeer() async {
        guard let id = dossier?["id"] else { return }
        do {
            let r = try await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "opdrachten", invoer: ["actie": "panic", "id": id])
            if r.ok { dossier = r.data } else { fout = r.fout }
        } catch { fout = error.localizedDescription }
    }
    @MainActor private func oordeel(_ goed: Bool) async {
        await actie("beoordeel", extra: ["goedgekeurd": goed, "toelichting": toelichting])
    }
}
