// Plant-scherm — formulier → concept → bevestiging → motor met bewijs.
// Editorial Monochrome · Zero-Trust Harnas

import SwiftUI

struct PlantView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    var metScroll: Bool = true

    @State private var profielen: [[String: Any]] = []
    @State private var breinOpties: [[String: Any]] = []
    @State private var gekozenProfiel: String? = "tweede-brein"
    @State private var doelPad = "~/mijn-brein"
    @State private var breinKeuze = 0                      // 0 auto · 1 pad · 2 geen
    @State private var breinPadVeld = ""
    @State private var concept: String?
    @State private var stappen: [[String: Any]] = []
    @State private var geplant = false
    @State private var fout: String?

    var body: some View {
        groep
            .background(Thema.kleur(.papier))
            .onAppear { laadProfielen() }
    }

    // ImageRenderer rendert ScrollView leeg; het render-bewijs gebruikt
    // daarom dezelfde inhoud zonder scroll-container (metScroll: false).
    @ViewBuilder private var groep: some View {
        if metScroll { ScrollView { inhoudView } } else { inhoudView }
    }

    @ViewBuilder private var inhoudView: some View {
        VStack(alignment: .leading, spacing: 22) {
            kop
            StappenStreep(stappen: ["Kiemkeuze", "Concept", "Bevestiging", "Machine-bewijs"],
                          actieveIndex: stappenIndex)
            profielKeuze
            doelVeld
            breinKeuzeRij
            acties
            if let concept { conceptKaart(concept) }
            if !stappen.isEmpty { stappenKaart }
            if let fout { foutKaart(fout) }
            Spacer(minLength: 16)
        }
        .padding(28)
    }

    private var stappenIndex: Int {
        if geplant || !stappen.isEmpty { return 3 }
        if concept != nil { return 1 }
        if gekozenProfiel != nil { return 0 }
        return 0
    }

    // MARK: - Kop & Flow

    private var kop: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("02 PLANTEN · SCOPE-POORT")
                .font(Thema.tekst(10, gewicht: .semibold))
                .tracking(3)
                .foregroundStyle(Thema.kleur(.gedempt))
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text("Eén zaadje. Eén ").font(Thema.display(30))
                Text("klik.").font(Thema.display(30, cursief: true)).foregroundStyle(Thema.kleur(.zacht))
            }
            Text("Elke beslissing wordt bevestigd, elk resultaat machine-gecontroleerd.")
                .font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.zacht))
        }
    }

    // MARK: - Kiemkeuze

    private var profielKeuze: some View {
        Kaart(kop: "Wat wil je laten groeien?", rechterKop: "Vraag 1 / 3") {
            VStack(alignment: .leading, spacing: 0) {
                if profielen.isEmpty {
                    HStack(spacing: 8) {
                        ProgressView().controlSize(.small)
                        Text("Profielen worden geladen uit de kiemkeuze-catalogus…")
                            .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                    }
                    .padding(.vertical, 10)
                }
                ForEach(profielen.indices, id: \.self) { i in
                    let profiel = profielen[i]
                    profielRij(naam: profiel["naam"] as? String ?? "?",
                               beschrijving: profiel["beschrijving"] as? String ?? "",
                               bron: "standaard",
                               isGekozen: gekozenProfiel == (profiel["naam"] as? String))
                }
                ForEach(breinOpties.indices, id: \.self) { j in
                    let optie = breinOpties[j]
                    profielRij(naam: optie["naam"] as? String ?? "?",
                               beschrijving: "Voorstel uit je eigen brein — advies, geen profiel",
                               bron: "uit je brein",
                               isGekozen: false)
                }
            }
        }
    }

    private func profielRij(naam: String, beschrijving: String, bron: String, isGekozen: Bool) -> some View {
        Button(action: {
            if bron != "uit je brein" {
                gekozenProfiel = naam
            }
        }) {
            HStack(alignment: .center, spacing: 14) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(naam)
                        .font(Thema.display(16, cursief: bron == "uit je brein"))
                        .foregroundStyle(Thema.kleur(bron == "uit je brein" ? .gedempt : .inkt))
                    Text(beschrijving)
                        .font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.zacht))
                }
                Spacer()
                Text(bron)
                    .font(Thema.tekst(9, gewicht: .semibold))
                    .tracking(1.5)
                    .textCase(.uppercase)
                    .foregroundStyle(Thema.kleur(.gedempt))

                ZStack {
                    Circle()
                        .stroke(Thema.kleur(.lijn), lineWidth: 1)
                        .frame(width: 14, height: 14)
                    if isGekozen {
                        Circle()
                            .fill(Thema.kleur(.inkt))
                            .frame(width: 8, height: 8)
                    }
                }
            }
            .padding(.vertical, 12)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
    }

    // MARK: - Doel & Registratie

    private var doelVeld: some View {
        Kaart(kop: "Waar moet het groeien?", rechterKop: "Vraag 2 / 3") {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "folder")
                        .font(.system(size: 13))
                        .foregroundStyle(Thema.kleur(.gedempt))
                    TextField("Pad, bijv. ~/mijn-brein", text: $doelPad)
                        .textFieldStyle(.plain)
                        .font(Thema.tekst(13))
                }
                .padding(10)
                .overlay(Rectangle().stroke(Thema.kleur(.lijn), lineWidth: 1))
                .background(Thema.kleur(.papierZacht))

                Text("Lokaal pad op deze machine. Wordt gecontroleerd door de scope-poort vóór uitvoering.")
                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
            }
        }
    }

    private var breinKeuzeRij: some View {
        Kaart(kop: "Oerwoud-registratie", rechterKop: "Vraag 3 / 3") {
            VStack(alignment: .leading, spacing: 12) {
                Picker("", selection: $breinKeuze) {
                    Text("Automatisch (koppelen met oerwoud-brein op deze machine)").tag(0)
                    Text("Registreren bij een specifiek brein-pad").tag(1)
                    Text("Niet registreren (standalone boom)").tag(2)
                }
                .pickerStyle(.radioGroup)
                .font(Thema.tekst(12))

                if breinKeuze == 1 {
                    HStack {
                        Image(systemName: "link")
                            .font(.system(size: 12))
                            .foregroundStyle(Thema.kleur(.gedempt))
                        TextField("Pad naar het brein", text: $breinPadVeld)
                            .textFieldStyle(.plain)
                            .font(Thema.tekst(13))
                    }
                    .padding(8)
                    .overlay(Rectangle().stroke(Thema.kleur(.lijn), lineWidth: 1))
                    .background(Thema.kleur(.papierZacht))
                }
                Text("Registratie is een machine-feit: het geboortebewijs is al gecontroleerd. De mens curateert het register; niets wordt overschreven.")
                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
            }
        }
    }

    // MARK: - Actieknoppen

    private var acties: some View {
        HStack(spacing: 12) {
            PillKnop(titel: "Bekijk concept", gevuld: false) { startPlant(bevestig: false) }
            PillKnop(titel: "Plant deze boom", gevuld: true) { startPlant(bevestig: true) }

            if runner.bezig {
                HStack(spacing: 8) {
                    ProgressView().controlSize(.small)
                    Text("de motor draait…")
                        .font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
                .padding(.leading, 8)
            }
        }
    }

    // MARK: - Concept & Slijper

    private func conceptKaart(_ tekst: String) -> some View {
        Kaart(kop: "Ruwe Invoer → Geslepen Concept", rechterKop: "Scope-poort") {
            VStack(alignment: .leading, spacing: 14) {
                // Geslepen blok conform mockup scherm 02
                VStack(alignment: .leading, spacing: 8) {
                    Text("CONCEPT-OPDRACHT")
                        .font(Thema.tekst(9, gewicht: .semibold))
                        .tracking(2)
                        .foregroundStyle(Thema.kleur(.gedempt))
                    Text(tekst)
                        .font(Thema.tekst(13))
                        .lineSpacing(4)
                        .textSelection(.enabled)
                }
                .padding(14)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Thema.kleur(.papierZacht))
                .overlay(Rectangle().stroke(Thema.kleur(.inkt), lineWidth: 1))

                HStack(spacing: 8) {
                    StatusBadge(tekst: "Scope getoetst", stijl: .bewezen)
                    Text("Bevestig met 'Plant deze boom' om de motor te starten.")
                        .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                }
            }
        }
    }

    // MARK: - Stappenplan

    private var stappenKaart: some View {
        Kaart(kop: geplant ? "Uitgevoerd met bewijs" : "Motordraai", rechterKop: "\(stappen.count) stappen") {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(stappen.indices, id: \.self) { i in
                    let stap = stappen[i]
                    let status = stap["status"] as? String ?? "?"
                    HStack(alignment: .top, spacing: 14) {
                        Text(stap["id"] as? String ?? "?")
                            .font(Thema.tekst(12, gewicht: .medium))
                            .monospacedDigit()
                            .foregroundStyle(Thema.kleur(.gedempt))
                            .frame(width: 75, alignment: .leading)

                        VStack(alignment: .leading, spacing: 3) {
                            Text(stap["doel"] as? String ?? (stap["id"] as? String ?? "Stap"))
                                .font(Thema.tekst(13, gewicht: .medium))
                            Text(stap["bewijs"] as? String ?? "")
                                .font(Thema.tekst(11))
                                .foregroundStyle(Thema.kleur(.zacht))
                        }

                        Spacer()

                        StatusBadge(tekst: statusLabel(status), stijl: badgeStijlVoor(status))
                    }
                    .padding(.vertical, 10)
                    .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
                }
            }
        }
    }

    private func statusLabel(_ status: String) -> String {
        switch status {
        case "geslaagd": return "✓ Bewezen"
        case "wacht_op_mens": return "Mens-moment"
        case "review_ok_wacht_ratificatie": return "Review OK"
        case "lopend": return "⏳ Lopend"
        case "gefaald": return "Gefaald"
        default: return status
        }
    }

    private func badgeStijlVoor(_ status: String) -> BadgeStijl {
        switch status {
        case "geslaagd": return .bewezen
        case "wacht_op_mens", "review_ok_wacht_ratificatie": return .mens
        case "lopend": return .lopend
        case "gefaald": return .herziening
        default: return .neutraal
        }
    }

    private func foutKaart(_ tekst: String) -> some View {
        Kaart(kop: "Fout — de mens wordt geroepen", rechterKop: "Faalcontract §7") {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "exclamationmark.triangle")
                    .font(.system(size: 14))
                Text(tekst)
                    .font(Thema.tekst(13, gewicht: .medium))
            }
        }
    }

    // MARK: - Adapter Aanroepen

    private func laadProfielen() {
        Task {
            guard let resultaat = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                                         commando: "profielen", invoer: [:]) else { return }
            await MainActor.run {
                profielen = resultaat.data["profielen"] as? [[String: Any]] ?? []
                breinOpties = resultaat.data["brein_opties"] as? [[String: Any]] ?? []
                if gekozenProfiel == nil, let eerste = profielen.first?["naam"] as? String {
                    gekozenProfiel = eerste
                }
            }
        }
    }

    private func startPlant(bevestig: Bool) {
        fout = nil
        if !bevestig { concept = nil; stappen = []; geplant = false }
        var invoer: [String: Any] = ["profiel": gekozenProfiel ?? "", "doel": doelPad,
                                     "bevestig": bevestig]
        switch breinKeuze {
        case 1:
            invoer["brein"] = "pad"
            invoer["brein_pad"] = breinPadVeld
        case 2:
            invoer["brein"] = "geen"
        default:
            invoer["brein"] = "auto"
        }
        Task {
            do {
                let resultaat = try await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                                      commando: "plant", invoer: invoer, timeOut: 300)
                await MainActor.run {
                    if !resultaat.vragen.isEmpty {
                        fout = "Het brein is nog niet bekend op deze machine — kies hierboven 'Registreren bij een brein-pad' of 'Niet registreren'."
                        return
                    }
                    if resultaat.ok {
                        if let conceptTekst = resultaat.data["concept"] as? String {
                            concept = conceptTekst
                        }
                        stappen = resultaat.data["stappen"] as? [[String: Any]] ?? []
                        geplant = resultaat.data["bevestiging_vereist"] as? Bool != true
                    } else {
                        fout = resultaat.fout ?? "onbekende adapter-fout"
                    }
                }
            } catch {
                await MainActor.run { fout = error.localizedDescription }
            }
        }
    }
}
