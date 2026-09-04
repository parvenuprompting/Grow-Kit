// Hoofdmenu — de modi van het harnas in Editorial Monochrome stijl.
// Papier #FFFFFF · Inkt #000000 · Zacht #555555 · Gedempt #888888 · Lijn 12%.

import SwiftUI

struct ContentView: View {
    @StateObject private var runner = Runner()
    @StateObject private var koppelingen = KoppelingenStore()
    @AppStorage("growkitRepoPad") private var repoPad = Runner.standaardRepoPad
    @AppStorage("growkitInterpreter") private var interpreter = Runner.standaardInterpreter

    enum Modi: Int, CaseIterable, Identifiable {
        case status, planten, ratificatie, dialoog, hervatten, taak

        var id: Int { rawValue }
        var nummer: String { String(format: "%02d", rawValue + 1) }
        var naam: String {
            switch self {
            case .status: return "Status"
            case .planten: return "Planten"
            case .ratificatie: return "Ratificatie"
            case .dialoog: return "Dialoog"
            case .hervatten: return "Hervatten"
            case .taak: return "Taak"
            }
        }
        var beschrijving: String {
            switch self {
            case .status: return "Identiteit, register, tellers, logboek"
            case .planten: return "Concept → bevestiging → motor met bewijs"
            case .ratificatie: return "Mens-momenten in bulk goedkeuren of afkeuren"
            case .dialoog: return "Gesprek met geïnstalleerde AI-agenten"
            case .hervatten: return "Restdraai vanuit het logboek"
            case .taak: return "Taken uit de groeilaag uitvoeren"
            }
        }
        var actiefInV1: Bool { self != .hervatten && self != .taak }
        var demo: Bool { self == .dialoog }
    }

    @State private var geselecteerd: Modi = .status
    @State private var toonInstellingen = false
    @State private var instellingenTab = 0
    @State private var hoverModus: Modi? = nil

    var body: some View {
        NavigationSplitView {
            zijbalk
                .navigationSplitViewColumnWidth(min: 250, ideal: 280)
        } detail: {
            detail
        }
        .onAppear { Thema.registreerFonts() }
        .sheet(isPresented: $toonInstellingen) { instellingenSheet }
    }

    // MARK: - Zijbalk

    private var zijbalk: some View {
        VStack(alignment: .leading, spacing: 0) {
            merk
                .padding(.horizontal, 20)
                .padding(.top, 24)
                .padding(.bottom, 18)

            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)

            ForEach(Modi.allCases) { modus in
                modusRij(modus)
            }

            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)

            Spacer()

            voet
                .padding(.horizontal, 20)
                .padding(.vertical, 16)
        }
        .background(Thema.kleur(.papier))
    }

    private var merk: some View {
        HStack(alignment: .center, spacing: 12) {
            BoomIcoon(formaat: 30)

            VStack(alignment: .leading, spacing: 2) {
                HStack(alignment: .firstTextBaseline, spacing: 0) {
                    Text("Grow").font(Thema.display(24))
                    Text("Kit").font(Thema.display(24, cursief: true)).foregroundStyle(Thema.kleur(.zacht))
                }
                Text("EDITORIAL MONOCHROME · ZERO-TRUST")
                    .font(Thema.tekst(8, gewicht: .semibold)).tracking(1.8)
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
        }
    }

    private func modusRij(_ modus: Modi) -> some View {
        let gekozen = geselecteerd == modus
        let isHovered = hoverModus == modus
        return Button(action: { if modus.actiefInV1 { geselecteerd = modus } }) {
            HStack(alignment: .center, spacing: 12) {
                Text(modus.nummer)
                    .font(Thema.display(15, cursief: !modus.actiefInV1))
                    .foregroundStyle(Thema.kleur(gekozen ? .inkt : .gedempt))
                    .frame(width: 26, alignment: .leading)

                VStack(alignment: .leading, spacing: 2) {
                    Text(modus.naam).font(Thema.display(17))
                        .foregroundStyle(Thema.kleur(gekozen ? .inkt : .zacht))
                    Text(modus.beschrijving)
                        .font(Thema.tekst(10))
                        .foregroundStyle(Thema.kleur(.gedempt))
                        .lineLimit(1)
                }

                Spacer()

                if modus.demo {
                    Text("DEMO").font(Thema.tekst(9, gewicht: .semibold)).tracking(1)
                        .padding(.horizontal, 7).padding(.vertical, 3)
                        .overlay(Capsule().stroke(Thema.kleur(.zacht), style: StrokeStyle(lineWidth: 1, dash: [3])))
                        .foregroundStyle(Thema.kleur(.zacht))
                }
                if !modus.actiefInV1 {
                    Text("6.1")
                        .font(Thema.tekst(9, gewicht: .semibold))
                        .tracking(1)
                        .padding(.horizontal, 7).padding(.vertical, 3)
                        .overlay(Capsule().stroke(Thema.kleur(.lijn)))
                        .foregroundStyle(Thema.kleur(.gedempt))
                } else if modus == .dialoog {
                    Text("AI")
                        .font(Thema.tekst(9, gewicht: .semibold))
                        .tracking(1)
                        .padding(.horizontal, 6).padding(.vertical, 2)
                        .overlay(Capsule().stroke(Thema.kleur(gekozen ? .inkt : .lijn)))
                        .foregroundStyle(Thema.kleur(gekozen ? .inkt : .gedempt))
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 13)
            .contentShape(Rectangle())
            .background(gekozen ? Thema.kleur(.papierZacht) : (isHovered ? Thema.kleur(.papierZacht).opacity(0.5) : Thema.kleur(.papier)))
            .overlay(alignment: .leading) {
                if gekozen { Rectangle().fill(Thema.kleur(.inkt)).frame(width: 3) }
            }
            .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
        }
        .buttonStyle(.plain)
        .onHover { hover in
            if hover { hoverModus = modus } else if hoverModus == modus { hoverModus = nil }
        }
    }

    private var voet: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Circle().fill(Thema.kleur(.inkt)).frame(width: 7, height: 7)
                Text("ADAPTER GEREED")
                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                    .foregroundStyle(Thema.kleur(.zacht))
                Spacer()
                Text("PROCESS")
                    .font(Thema.tekst(8, gewicht: .medium)).tracking(1)
                    .foregroundStyle(Thema.kleur(.gedempt))
            }

            Button(action: { toonInstellingen = true }) {
                HStack(spacing: 6) {
                    Image(systemName: "gearshape")
                        .font(.system(size: 12))
                    Text("Instellingen")
                }
                .font(Thema.tekst(11, gewicht: .medium))
                .foregroundStyle(Thema.kleur(.zacht))
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Detail

    @ViewBuilder
    private var detail: some View {
        VStack(spacing: 0) {
            Group {
                switch geselecteerd {
                case .status:
                    StatusView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .planten:
                    PlantView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .ratificatie:
                    RatificeerView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .dialoog:
                    ChatView(runner: runner, koppelingen: koppelingen,
                             repoPad: $repoPad, interpreter: $interpreter)
                case .hervatten, .taak:
                    PlaceholderView(titel: geselecteerd.naam,
                                    tekst: "Deze modus volgt in fase 6.1 — gebruik voor nu loop.py in de terminal.")
                }
            }
            .frame(maxHeight: .infinity)
            schermVoet
        }
    }

    private var schermVoet: some View {
        HStack {
            HStack(spacing: 6) {
                Text("© Parvenu GrowKit 0.6.0")
                Text("·").foregroundStyle(Thema.kleur(.lijn))
                Text("Zero-Trust Harnas")
            }
            Spacer()
            Text("Editorial Monochrome · Fraunces & Inter (SIL OFL)")
        }
        .font(Thema.tekst(9, gewicht: .medium)).tracking(1)
        .foregroundStyle(Thema.kleur(.gedempt))
        .padding(.horizontal, 28).padding(.vertical, 10)
        .background(Thema.kleur(.papier))
        .overlay(alignment: .top) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
    }

    // MARK: - Instellingen

    private var instellingenSheet: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Text("Instellingen").font(Thema.display(24))
                Spacer()
                PillKnop(titel: "Sluit", gevuld: true, compact: true) { toonInstellingen = false }
            }
            Picker("", selection: $instellingenTab) {
                Text("Algemeen").tag(0)
                Text("AI-providers").tag(1)
                Text("Breinen").tag(2)
            }
            .pickerStyle(.segmented)
            .font(Thema.tekst(12))

            Group {
                if instellingenTab == 0 { algemeenPaneel }
                if instellingenTab == 1 { providersPaneel }
                if instellingenTab == 2 { breinenPaneel }
            }
            Spacer()
        }
        .padding(28)
        .frame(width: 600, height: 620)
    }

    private var algemeenPaneel: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Kaart(kop: "Configuratie", rechterKop: "Omgeving") {
                    VStack(alignment: .leading, spacing: 14) {
                        labeledVeld("GROWKIT-REPO", text: $repoPad,
                                    placeholder: "~/Documents/Code 7/growkit")
                        labeledVeld("PYTHON-INTERPRETER (3.11+)", text: $interpreter,
                                    placeholder: "/opt/homebrew/bin/python3.13")
                    }
                }
                Text("De app is een bedienaar: zij roept adapter.py aan via Process — de Scope-poort, motor en het faalcontract in de Python-kern bewaken de integriteit.")
                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.zacht)).lineSpacing(3)
            }
        }
    }

    private var providersPaneel: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                if let fout = koppelingen.laadFout {
                    Text(fout).font(Thema.tekst(12, gewicht: .medium))
                }
                Kaart(kop: "Actieve provider in de chatbalk") {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(koppelingen.providerKeuzes, id: \.self) { keuze in
                            HStack {
                                Text(keuze).font(Thema.tekst(13, gewicht:
                                    koppelingen.actieveProvider == keuze ? .semibold : .regular))
                                Spacer()
                                if koppelingen.actieveProvider == keuze {
                                    StatusBadge(tekst: "actief", bewezen: true)
                                }
                            }
                            .contentShape(Rectangle())
                            .onTapGesture { koppelingen.actieveProvider = keuze }
                        }
                    }
                }
                ForEach($koppelingen.providers) { $provider in
                    Kaart(kop: "Provider · \(provider.naam)", rechterKop: provider.type) {
                        VStack(alignment: .leading, spacing: 10) {
                            labeledVeld("NAAM", text: $provider.naam)
                            labeledVeld("ENDPOINT", text: $provider.endpoint,
                                        placeholder: "https://…/v1/chat")
                            labeledVeld("MODEL", text: $provider.model,
                                        placeholder: "bijv. een rolnaam — géén leveranciers-binding in de kern")
                            VStack(alignment: .leading, spacing: 4) {
                                Text("API-SLEUTEL (uitsluitend op deze machine)")
                                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                                    .foregroundStyle(Thema.kleur(.gedempt))
                                SecureField("plak of typ de sleutel — verlaat ~/.growkit nooit",
                                            text: $provider.apiSleutel)
                                    .textFieldStyle(.plain).font(Thema.tekst(13)).padding(10)
                                    .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                                    .background(Thema.kleur(.papierZacht))
                            }
                        }
                    }
                }
                HStack {
                    PillKnop(titel: "Voeg provider toe", gevuld: false) {
                        koppelingen.providers.append(
                            ProviderKoppeling(naam: "provider-\(koppelingen.providers.count + 1)",
                                              type: "http", endpoint: "", model: "", apiSleutel: ""))
                    }
                    Spacer()
                }
                Text("Sleutels worden uitsluitend opgeslagen in ~/.growkit/koppelingen.json — buiten de repo, per machine. De reviewer-rol (reviewconfig) wijst je in een volgende fase naar deze providers.")
                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.zacht)).lineSpacing(3)
            }
        }
    }

    private var breinenPaneel: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Kaart(kop: "Actief brein (het hart van het oerwoud)") {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(koppelingen.breinen) { brein in
                            HStack {
                                Text(brein.naam)
                                    .font(Thema.display(15, cursief: brein.naam == "Agent-Brain"))
                                Spacer()
                                if koppelingen.actiefBrein == brein.naam {
                                    StatusBadge(tekst: "actief", bewezen: true)
                                }
                            }
                            .contentShape(Rectangle())
                            .onTapGesture { koppelingen.actiefBrein = brein.naam }
                        }
                    }
                }
                ForEach($koppelingen.breinen) { $brein in
                    Kaart(kop: "Brein · \(brein.naam)", rechterKop: "git") {
                        VStack(alignment: .leading, spacing: 10) {
                            labeledVeld("NAAM", text: $brein.naam)
                            labeledVeld("PAD (LOKAAL)", text: $brein.pad,
                                        placeholder: "~/Projects/…")
                            labeledVeld("GIT-REMOTE (SYNC, FASE 5.1)", text: $brein.remote,
                                        placeholder: "github.com/…")
                        }
                    }
                }
                HStack {
                    PillKnop(titel: "Voeg brein toe", gevuld: false) {
                        koppelingen.breinen.append(
                            BreinKoppeling(naam: "brein-\(koppelingen.breinen.count + 1)",
                                           pad: "", remote: ""))
                    }
                    Spacer()
                }
                Text("Ons eigen Agent-Brain is de standaard-brein-provider: het hart van het oerwoud waar bomen hun voorstellen heen sturen (§13). De koppeling naar de oerwoud-staat (~/.growkit/oerwoud.json) gaat mee met de eerstvolgende functionele fase.")
                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.zacht)).lineSpacing(3)
            }
        }
    }

    private func labeledVeld(_ label: String, text: Binding<String>, placeholder: String = "") -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            TextField(placeholder.isEmpty ? label : placeholder, text: text,
                      prompt: Text(placeholder.isEmpty ? label : placeholder)
                          .font(Thema.tekst(13)).foregroundColor(Thema.kleur(.zacht)))
                .foregroundStyle(Thema.kleur(.inkt))
                .textFieldStyle(.plain).font(Thema.tekst(13)).padding(10)
                .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                .background(Thema.kleur(.papierZacht))
        }
    }
}
