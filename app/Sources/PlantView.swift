// Plant-scherm — formulier → concept → bevestiging → motor met bewijs.

import SwiftUI

struct PlantView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    var metScroll: Bool = true

    @State private var profielen: [[String: Any]] = []
    @State private var breinOpties: [[String: Any]] = []
    @State private var gekozenProfiel: String?
    @State private var doelPad = ""
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
    // dezelfde inhoud zonder scroll-container (metScroll: false).
    @ViewBuilder private var groep: some View {
        if metScroll { ScrollView { inhoudView } } else { inhoudView }
    }

    @ViewBuilder private var inhoudView: some View {
        VStack(alignment: .leading, spacing: 20) {
            kop
            profielKeuze
            doelVeld
            breinKeuzeRij
            acties
            if let concept { conceptKaart(concept) }
            if !stappen.isEmpty { stappenKaart }
            if let fout { foutKaart(fout) }
            Spacer()
        }
        .padding(28)
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("PLANTEN").font(Thema.tekst(10, gewicht: .semibold)).tracking(4).foregroundStyle(Thema.kleur(.zacht))
            Text("Eén zaadje. Eén klik.").font(Thema.display(30))
        }
    }

    private var profielKeuze: some View {
        Kaart(kop: "Kies een boom") {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(profielen.indices, id: \.self) { i in
                    let profiel = profielen[i]
                    profielRij(naam: profiel["naam"] as? String ?? "?",
                               beschrijving: profiel["beschrijving"] as? String ?? "",
                               bron: "bewezen")
                }
                ForEach(breinOpties.indices, id: \.self) { j in
                    let optie = breinOpties[j]
                    profielRij(naam: optie["naam"] as? String ?? "?",
                               beschrijving: "Voorstel uit je eigen brein — advies, geen profiel",
                               bron: "uit je brein")
                }
            }
        }
    }

    private func profielRij(naam: String, beschrijving: String, bron: String) -> some View {
        Button(action: { if bron == "bewezen" { gekozenProfiel = naam } }) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(naam).font(Thema.display(16, cursief: bron == "uit je brein"))
                        .foregroundStyle(Thema.kleur(bron == "bewezen" ? .inkt : .gedempt))
                    Text(beschrijving).font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.zacht))
                }
                Spacer()
                Text(bron).font(Thema.tekst(10, gewicht: .semibold)).tracking(1.5).textCase(.uppercase)
                    .foregroundStyle(Thema.kleur(.gedempt))
                if gekozenProfiel == naam && bron == "bewezen" {
                    Circle().fill(Thema.kleur(.inkt)).frame(width: 8, height: 8)
                }
            }
            .padding(.vertical, 12)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
    }

    private var doelVeld: some View {
        Kaart(kop: "Waar moet het groeien?") {
            TextField("Pad, bijv. ~/mijn-brein", text: $doelPad)
                .textFieldStyle(.plain).font(Thema.tekst(13)).padding(8)
                .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
        }
    }

    private var breinKeuzeRij: some View {
        Kaart(kop: "Oerwoud-registratie") {
            VStack(alignment: .leading, spacing: 10) {
                Picker("", selection: $breinKeuze) {
                    Text("Auto (brein zoals bekend op deze machine)").tag(0)
                    Text("Registreren bij een brein-pad").tag(1)
                    Text("Niet registreren").tag(2)
                }
                .pickerStyle(.radioGroup)
                .font(Thema.tekst(12))
                if breinKeuze == 1 {
                    TextField("Pad naar het brein", text: $breinPadVeld)
                        .textFieldStyle(.plain).font(Thema.tekst(13)).padding(8)
                        .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                }
                Text("Registratie is een machine-feit: het geboortebewijs is al gecontroleerd. De mens curateert het register; niets wordt overschreven.")
                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
            }
        }
    }

    private var acties: some View {
        HStack(spacing: 12) {
            knop("Bekijk concept", gevuld: false) { startPlant(bevestig: false) }
            knop("Plant deze boom", gevuld: true) { startPlant(bevestig: true) }
            if runner.bezig {
                Text("de motor draait…").font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
            }
        }
    }

    private func conceptKaart(_ tekst: String) -> some View {
        Kaart(kop: "Concept-opdracht (poort)") {
            Text(tekst).font(Thema.tekst(13)).textSelection(.enabled)
        }
    }

    private var stappenKaart: some View {
        Kaart(kop: geplant ? "Uitgevoerd met bewijs" : "Motordraai") {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(stappen.indices, id: \.self) { i in
                    let stap = stappen[i]
                    HStack {
                        Text(stap["id"] as? String ?? "?")
                            .font(Thema.display(13)).frame(width: 90, alignment: .leading)
                        Text(stap["bewijs"] as? String ?? "")
                            .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                            .lineLimit(1)
                        Spacer()
                        StatusBadge(tekst: stap["status"] as? String ?? "?",
                                    bewezen: stap["status"] as? String == "geslaagd")
                    }
                    .padding(.vertical, 9)
                    .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
                }
            }
        }
    }

    private func foutKaart(_ tekst: String) -> some View {
        Kaart(kop: "Fout — de mens wordt geroepen") {
            Text(tekst).font(Thema.tekst(13, gewicht: .medium))
        }
    }

    private func knop(_ titel: String, gevuld: Bool, actie: @escaping () -> Void) -> some View {
        Button(action: actie) {
            Text(titel).font(Thema.tekst(12, gewicht: .medium))
                .padding(.horizontal, 18).padding(.vertical, 10)
        }
        .buttonStyle(.plain)
        .background(gevuld ? Thema.kleur(.inkt) : Thema.kleur(.papier))
        .foregroundStyle(gevuld ? Thema.kleur(.papier) : Thema.kleur(.inkt))
        .overlay(Capsule().stroke(Thema.kleur(.inkt)))
        .clipShape(Capsule())
    }

    private func laadProfielen() {
        Task {
            guard let resultaat = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                                         commando: "profielen", invoer: [:]) else { return }
            await MainActor.run {
                profielen = resultaat.data["profielen"] as? [[String: Any]] ?? []
                breinOpties = resultaat.data["brein_opties"] as? [[String: Any]] ?? []
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
