// Hoofdmenu — de modi van het harnas in Editorial Monochrome stijl.
// Papier #FFFFFF · Inkt #000000 · Zacht #555555 · Gedempt #888888 · Lijn 12%.

import SwiftUI

struct ContentView: View {
    @StateObject private var runner = Runner()
    @StateObject private var koppelingen = KoppelingenStore()
    @Binding var geselecteerd: ContentView.Modi
    @Binding var toonInstellingen: Bool
    @Binding var toonOver: Bool
    @AppStorage("growkitRepoPad") private var repoPad = Runner.standaardRepoPad
    @AppStorage("growkitInterpreter") private var interpreter = Runner.standaardInterpreter

    enum Modi: Int, CaseIterable, Identifiable {
        case home = -1, status, planten, goedkeuringen, dialoog, agenten, vangnet, audit, hervatten, taak, rondleiding, uitleg
        // Fase A-mocks: de toekomstige functies, al zichtbaar (grijs, niet aanklikbaar)
        case agentchat = 100, skills, browser, ide, connectors
        case graaf = 110

        var id: Int { rawValue }
        var nummer: String {
            switch self {
            case .home: return "00"
            case .rondleiding: return "07"
            case .uitleg: return "08"
            case .agentchat: return "B1"
            case .skills: return "B2"
            case .browser: return "B5"
            case .ide: return "B6"
            case .connectors: return "B4"
            case .graaf: return "KG"
            default: return String(format: "%02d", rawValue + 1)
            }
        }
        var naam: String {
            switch self {
            case .home: return "Thuis"
            case .rondleiding: return "Rondleiding"
            case .uitleg: return "Uitleg"
            case .status: return "Status"
            case .planten: return "Planten"
            case .goedkeuringen: return "Goedkeuringen"
            case .dialoog: return "Dialoog"
            case .agenten: return "Agenten"
            case .vangnet: return "Vangnet"
            case .audit: return "Audit"
            case .hervatten: return "Hervatten"
            case .taak: return "Taak"
            case .agentchat: return "Agent Chat"
            case .skills: return "Skills"
            case .browser: return "Browser"
            case .ide: return "IDE"
            case .connectors: return "Connectors"
            case .graaf: return "Knowledge Graph"
            }
        }
        var beschrijving: String {
            switch self {
            case .home: return "Startpunten en de dialoog binnen handbereik"
            case .rondleiding: return "De vijf schermen van het ontwerp"
            case .uitleg: return "Zes regels · de engine room"
            case .status: return "Identiteit, register, tellers, logboek"
            case .planten: return "Concept → bevestiging → motor met bewijs"
            case .goedkeuringen: return "Mens-momenten in bulk goedkeuren of afkeuren"
            case .dialoog: return "Gesprek met geïnstalleerde AI-agenten"
            case .agenten: return "Governor: taken, controle, observer"
            case .vangnet: return "Opvanglaag: wat is er vanzelf opgevangen"
            case .audit: return "Wat hebben agenten gedaan, in simpele taal"
            case .hervatten: return "Restdraai vanuit het logboek"
            case .taak: return "Taken uit de groeilaag uitvoeren"
            case .agentchat: return "Agents ondernemen direct actie — groot venster"
            case .skills: return "Welke skills draaien er op jouw GrowKit?"
            case .browser: return "Ingebouwde browser voor het web"
            case .ide: return "Mini-IDE voor de projectmappen"
            case .connectors: return "Google Drive en andere bronnen koppelen"
            case .graaf: return "Het hele brein in één soepele kaart"
            }
        }
        var isMock: Bool {
            switch self {
            case .agentchat, .skills, .browser, .ide, .connectors: return true
            case .graaf: return false   // live functie
            default: return false
            }
        }
        var actiefInV1: Bool { !isMock }
    }

    @State private var toonInstellingenTab = 0
    @State private var hoverModus: Modi? = nil
    @State private var saldoTekst = ""
    @StateObject private var statusbalkStore = StatusBalkStore()

    var body: some View {
        NavigationSplitView {
            zijbalk
                .navigationSplitViewColumnWidth(min: 250, ideal: 280)
                .navigationTitle("Grow Kit")
        } detail: {
            detail
        }
        .onAppear { Thema.registreerFonts(); laadSaldo(); startSaldoTimer(); statusbalkStore.start() }
        .sheet(isPresented: $toonInstellingen) { instellingenSheet }
        .background(SneltoetsBeheerder()) // ⌘\ = zijbalk in/uitklappen
    }

    // Saldo (Fase 2): één mini-regel boven Instellingen. Stille stippel:
    // leeg = geen sleutel gevonden, dan toont de regel gewoon niet.
    // Verversen: elke 60 seconden (timer) + bij opstart.
    private var saldoRegel: String { saldoTekst }
    @State private var saldoURL: String = ""
    @State private var saldoLaag: Bool = false

    private func laadSaldo() {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "saldo", invoer: [:])
            await MainActor.run {
                if let r, r.ok,
                   let rest = r.data["resterend"] as? Double {
                    saldoTekst = String(format: "€ %.2f", rest)
                    saldoLaag = rest < 10.0
                    saldoURL = r.data["credits_url"] as? String ?? ""
                }
            }
        }
    }

    private func startSaldoTimer() {
        Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { _ in
            laadSaldo()
        }
    }

    // MARK: - Zijbalk

    private var zijbalk: some View {
        VStack(alignment: .leading, spacing: 0) {
            merk
                .padding(.horizontal, 20)
                .padding(.top, 24)
                .padding(.bottom, 18)

            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)

            // Menu in een scrollbare kolom — Instellingen blijft altijd bereikbaar,
            // ook op een klein venster.
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    // THUIS — de landingspagina, altijd bereikbaar
                    ForEach([Modi.home]) { modus in
                        modusRij(modus)
                    }

                    Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)

                    // WERK — de dagelijkse modi
                    zijbalkSectie("WERK")
                    ForEach([Modi.status, .planten, .goedkeuringen, .dialoog, .agenten, .graaf, .vangnet, .audit]) { modus in
                        modusRij(modus)
                    }

                    Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)

                    // SYSTEEM — herstel en taken
                    zijbalkSectie("SYSTEEM")
                    ForEach([Modi.hervatten, .taak]) { modus in
                        modusRij(modus)
                    }

                    Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)

                    // LEREN — rondleiding en uitleg
                    zijbalkSectie("LEREN")
                    ForEach([Modi.rondleiding, .uitleg]) { modus in
                        modusRij(modus)
                    }
                }
            }
            .scrollIndicators(.hidden)

            Spacer(minLength: 0)

            // Tijd, datum en weer — thuishoren in het zijmenu, het scherm blijft leeg.
            HStack(spacing: 6) {
                Image(systemName: "clock").font(.system(size: 9))
                    .foregroundStyle(Thema.kleur(.gedempt))
                Text("\(statusbalkStore.datum) · \(statusbalkStore.tijd)")
                    .font(Thema.tekst(9)).tracking(0.3)
                    .foregroundStyle(Thema.kleur(.gedempt))
                    .lineLimit(1)
            }
            .padding(.horizontal, 20)
            .padding(.bottom, 4)

            if let weer = statusbalkStore.weer {
                HStack(spacing: 6) {
                    Image(systemName: weer.icoon).font(.system(size: 9))
                        .foregroundStyle(Thema.kleur(.gedempt))
                    Text("\(String(format: "%.0f", weer.temperatuur))° — \(weer.omschrijving)")
                        .font(Thema.tekst(9)).tracking(0.3)
                        .foregroundStyle(Thema.kleur(.gedempt))
                    Spacer()
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 8)
            }

            if !saldoRegel.isEmpty {
                Button(action: {
                    if let url = URL(string: saldoURL) { NSWorkspace.shared.open(url) }
                }) {
                    HStack(spacing: 6) {
                        Circle().fill(saldoLaag ? Color.red : Thema.kleur(.inkt)).frame(width: 5, height: 5)
                        Text("SALDO").font(Thema.tekst(8, gewicht: .semibold)).tracking(1.4)
                            .foregroundStyle(Thema.kleur(.gedempt))
                        Spacer()
                        Text(saldoRegel).font(Thema.tekst(10, gewicht: .medium))
                            .foregroundStyle(saldoLaag ? Color.red : Thema.kleur(.zacht))
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .help("Open credits-pagina bij \(saldoURL.isEmpty ? "de provider" : "OpenRouter")")
                .padding(.horizontal, 20)
                .padding(.bottom, 8)
            }

            voet
                .padding(.horizontal, 20)
                .padding(.vertical, 16)
        }
        .background(Thema.kleur(.papier))
    }

    private func zijbalkSectie(_ titel: String) -> some View {
        Text(titel)
            .font(Thema.tekst(8, gewicht: .semibold)).tracking(1.8)
            .foregroundStyle(Thema.kleur(.gedempt))
            .padding(.horizontal, 20)
            .padding(.top, 12)
            .padding(.bottom, 4)
    }

    private var merk: some View {
        HStack(alignment: .center, spacing: 10) {
            BoomIcoon(formaat: 24)

            // App-font (Inter), met spatie: "Grow Kit"
            Text("Grow Kit").font(Thema.tekst(17, gewicht: .semibold))
                .tracking(0.3)
                .foregroundStyle(Thema.kleur(.inkt))
        }
    }

    private func modusRij(_ modus: Modi) -> some View {
        let gekozen = geselecteerd == modus
        let isHovered = hoverModus == modus
        return Button(action: { if modus.actiefInV1 { geselecteerd = modus } }) {
            HStack(alignment: .center, spacing: 10) {
                Text(modus.nummer)
                    .font(Thema.tekst(10, gewicht: .semibold)).tracking(0.5)
                    .foregroundStyle(Thema.kleur(gekozen ? .inkt : .gedempt))
                    .frame(width: 22, alignment: .leading)

                Text(modus.naam).font(Thema.tekst(12, gewicht: .medium))
                    .foregroundStyle(Thema.kleur(gekozen ? .inkt : .zacht))
                    .lineLimit(1)

                Spacer()

                if !modus.actiefInV1 {
                    Text("6.1")
                        .font(Thema.tekst(8, gewicht: .semibold))
                        .tracking(1)
                        .padding(.horizontal, 5).padding(.vertical, 2)
                        .overlay(Capsule().stroke(Thema.kleur(.lijn)))
                        .foregroundStyle(Thema.kleur(.gedempt))
                } else if modus == .dialoog {
                    Text("AI")
                        .font(Thema.tekst(8, gewicht: .semibold))
                        .tracking(1)
                        .padding(.horizontal, 5).padding(.vertical, 2)
                        .overlay(Capsule().stroke(Thema.kleur(gekozen ? .inkt : .lijn)))
                        .foregroundStyle(Thema.kleur(gekozen ? .inkt : .gedempt))
                }
            }
            .padding(.horizontal, 20)
            .frame(height: 30)  // vaste hoogte: selectie kan niets laten schuiven
            .contentShape(Rectangle())
            .background(gekozen ? Thema.kleur(.papierZacht) : (isHovered ? Thema.kleur(.papierZacht).opacity(0.5) : Thema.kleur(.papier)))
            .overlay(alignment: .leading) {
                if gekozen { Rectangle().fill(Thema.kleur(.inkt)).frame(width: 2) }
            }
            .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 0.5) }
        }
        .buttonStyle(.plain)
        .onHover { hover in
            if hover { hoverModus = modus } else if hoverModus == modus { hoverModus = nil }
        }
    }

    private var voet: some View {
        VStack(alignment: .leading, spacing: 10) {
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
                case .goedkeuringen:
                    GoedkeuringsView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .dialoog:
                    ChatView(runner: runner, koppelingen: koppelingen,
                             repoPad: $repoPad, interpreter: $interpreter)
                case .agenten:
                    AgentsView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .graaf:
                    GraafView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .vangnet:
                    VangnetView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .audit:
                    AuditView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .home:
                    HomeView(runner: runner, koppelingen: koppelingen,
                             repoPad: $repoPad, interpreter: $interpreter) { modus in
                        geselecteerd = modus
                    }
                case .rondleiding:
                    RondleidingView()
                case .uitleg:
                    UitlegView()
                case .hervatten:
                    HervatView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .taak:
                    TaakView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .agentchat:
                    MockScherm(icoon: "bubble.left.and.text.bubble.right",
                               titel: "Agent Chat",
                               belofte: "Eén groot venster waarin de familie-agents direct actie ondernemen — zoals Hermes, maar dan in jouw huis. Elke agent blijft binnen zijn rol en het gouverneur-plafond.",
                               komendeStappen: [
                                "Groot chatvenster met agent-keuze (de zeven familieleden)",
                                "Agents voeren acties uit via de adapter — poort en faalcontract blijven bewaken",
                                "Ronde Tafel-modus: Tuinier, Reviewer en Architect luisteren mee",
                                "Context-cap en ref-lookups zodat lange sessies betaalbaar blijven",
                                "Elke agent beheert zijn eigen domein in de app"])
                case .skills:
                    MockScherm(icoon: "square.stack.3d.up",
                               titel: "Skills",
                               belofte: "Zie in één oogopslag welke skills er op jouw GrowKit draaien — met per skill de machine-controles (evals) die bewijzen dat ze doen wat ze beloven.",
                               komendeStappen: [
                                "Lokale skills-browser: alle geïnstalleerde skills, leesbaar in gewone taal",
                                "Skills-triade: instructie + referenties + evals als data bij de stap",
                                "Machine-controles per stap, niet als vrije tekst ernaast",
                                "Skills aan- of uitzetten zonder de kern te raken"])
                case .browser:
                    MockScherm(icoon: "globe",
                               titel: "Browser",
                               belofte: "Een ingebouwde browser voor het web — documentatie bekijken, live previews van je boom en provider-dashboards, zonder GrowKit te verlaten.",
                               komendeStappen: [
                                "Ingebouwde webweergave met adresbalk",
                                "Bladwijzers voor de plekken die de familie vaak gebruikt",
                                "Agent mag lezen wat jij laat lezen — zero-trust blijft gelden"])
                case .ide:
                    MockScherm(icoon: "chevron.left.forwardslash.chevron.right",
                               titel: "IDE",
                               belofte: "Een mini-ontwikkelomgeving voor de projectmappen: bestanden bekijken, kleine aanpassingen, met de browser ernaast. Voor de momenten dat je zelf even tussen de code wilt staan.",
                               komendeStappen: [
                                "Bestandsverkenner voor de projectmappen",
                                "Leesbare weergave van bronbestanden met zoekfunctie",
                                "Kleine bewerkingen via de adapter — elke wijziging een gebeurtenis in het register",
                                "Browser-paneel ernaast voor live previews"])
                case .connectors:
                    MockScherm(icoon: "link",
                               titel: "Connectors",
                               belofte: "Koppel de bronnen die de familie nodig heeft — Google Drive eerst — met duidelijke, in te trekken bevoegdheden per connector.",
                               komendeStappen: [
                                "Google Drive: documenten lezen voor de brein-sync",
                                "Per connector een vaste, tonbare bevoegdhedenlijst",
                                "Verbreek de koppeling met één klik — niets blijft achter",
                                "Meer connectors volgen hetzelfde patroon"])
                }
            }
            .frame(maxHeight: .infinity)
            schermVoet
        }
    }

    private var schermVoet: some View {
        HStack {
            HStack(spacing: 6) {
                Text("© Parvenu GrowKit 1.3.0 · Zero-Trust Harnas — ontwikkeld door Tiëndo Welles")
            }
            Spacer()
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
            Picker("", selection: $toonInstellingenTab) {
                Text("Algemeen").tag(0)
                Text("AI-providers").tag(1)
                Text("Breinen").tag(2)
            }
            .pickerStyle(.segmented)
            .font(Thema.tekst(12))

            Group {
                if toonInstellingenTab == 0 { algemeenPaneel }
                if toonInstellingenTab == 1 { providersPaneel }
                if toonInstellingenTab == 2 { breinenPaneel }
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
                            ModelDropdown(model: $provider.model,
                                          runner: runner,
                                          repoPad: repoPad,
                                          interpreter: interpreter)
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
