// Chat-scherm — dialoog met 1 of meerdere geïnstalleerde AI-agenten in Editorial Monochrome stijl.
// Filosofie: de agent is de tuinier en adviseur; de mens blijft de enige curator.

import SwiftUI
import UniformTypeIdentifiers

struct ChatBericht: Identifiable {
    let id = UUID()
    let afzender: String       // "Tuinier", "Reviewer", "Architect", "Mens"
    let rol: Rol
    let tijdstip: String
    let tekst: String
    let bewijsRef: String?
    let isVoorstel: Bool

    enum Rol {
        case mens, tuinier, reviewer, architect

        var label: String {
            switch self {
            case .mens: return "MENS (CURATOR)"
            case .tuinier: return "TUINIER (AGENT)"
            case .reviewer: return "REVIEWER (CONTROLEUR)"
            case .architect: return "ARCHITECT (PROFIELEN)"
            }
        }

        var badgeStijl: BadgeStijl {
            switch self {
            case .mens: return .bewezen
            case .tuinier: return .lopend
            case .reviewer: return .mens
            case .architect: return .neutraal
            }
        }
    }
}

struct AIAgentInfo: Identifiable {
    let id: String
    let naam: String
    let rolTitel: String
    let beschrijving: String
    let status: String
}

struct ChatView: View {
    @ObservedObject var runner: Runner
    @ObservedObject var koppelingen: KoppelingenStore
    @Binding var repoPad: String
    @Binding var interpreter: String
    var metScroll: Bool = true
    var compact: Bool = false

    // Geïnstalleerde agents conform de GrowKit-architectuur
    private let geinstalleerdeAgents: [AIAgentInfo] = [
        AIAgentInfo(id: "alle", naam: "Ronde Tafel", rolTitel: "Multi-Agent Dialoog",
                    beschrijving: "Tuinier & Reviewer luisteren beiden mee", status: "Actief"),
        AIAgentInfo(id: "tuinier", naam: "Tuinier", rolTitel: "Lokale Uitvoerder",
                    beschrijving: "Stelt mappen, sjablonen en stappen voor", status: "Gereed"),
        AIAgentInfo(id: "reviewer", naam: "Reviewer", rolTitel: "Zero-Trust Bewaker",
                    beschrijving: "Toetst faalcontracten en bewijs-checks", status: "Verbonden"),
        AIAgentInfo(id: "architect", naam: "Architect", rolTitel: "Profiel-Adviseur",
                    beschrijving: "Beheert boom-sjablonen en register", status: "Stand-by")
    ]

    @State private var geselecteerdeAgentId: String = "alle"
    @State private var bijlagen: [URL] = []
    @State private var toonBestandskiezer = false
    @State private var invoerTekst: String = ""
    @StateObject private var agentKoppeling = AgentKoppeling()
    // Slice 1: het welkom is de enige vaste tekst — het verdere gesprek is echt
    // en loopt via de adapter (commando `slijp`) door de Scope-poort.
    @State private var berichten: [ChatBericht] = [
        ChatBericht(afzender: "Tuinier", rol: .tuinier, tijdstip: "—",
                    tekst: "Welkom in het GrowKit-dialoogvenster. Typ een opdracht en ik slijp hem door de Scope-poort: doel, plek en slaag-criterium komen als keurbaar concept terug. Ik beslis nooit zelf — elke mutatie vereist jouw bekrachtiging.",
                    bewijsRef: "SEED.md §1", isVoorstel: false)
    ]
    @State private var agentDenktNa: Bool = false
    // Slice 2 — vragen-rondje: de poort stelde vragen; antwoorden gaan onveranderd mee.
    @State private var openVragen: [[String: Any]] = []
    @State private var vraagAntwoorden: [String: String] = [:]
    @State private var vraagTekst: String = ""   // de ruwe invoer van de geweigerde beurt
    // Slice 3 — planten vanuit de dialoog: concept-akkoord → voorbeeld → echte plant.
    @State private var plantProfiel: String = "tweede-brein"
    @State private var plantDoel: String = ""
    @State private var plantBezig: Bool = false
    @State private var wachtMijlpaal: Bool = false
    @StateObject private var spraak = SpraakMemo()

    var body: some View {
        groep
            .background(Thema.kleur(.papier))
    }

    @ViewBuilder private var groep: some View {
        if metScroll { ScrollView { inhoudView } } else { inhoudView }
    }

    @ViewBuilder private var inhoudView: some View {
        VStack(alignment: .leading, spacing: 20) {
            if !compact {
                kop
                demoBanner
            }
            StappenStreep(stappen: ["Agentkeuze", "Prompt-slijper", "Voorstel", "Curatie"], actieveIndex: 1)
            agentKiezer
            gespreksPaneel
            if !openVragen.isEmpty { vragenKaart }
            if heeftVoorstel { plantKaart }
            snelleVragen
            invoerBalk
            Spacer(minLength: 16)
        }
        .padding(28)
    }

    // MARK: - Demo-banner

    private var demoBanner: some View {
        HStack(spacing: 10) {
            Text("DEMO-RONDE").font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .padding(.horizontal, 8).padding(.vertical, 4)
                .overlay(Capsule().stroke(Thema.kleur(.zacht), style: StrokeStyle(lineWidth: 1, dash: [3])))
                .foregroundStyle(Thema.kleur(.zacht))
            Text("Dit dialoog loopt écht via adapter.py: elke opdracht gaat door de Scope-poort — nooit om de poort heen. Spraakmemo en bijlagen zijn nog schets.")
                .font(Thema.tekst(11))
                .foregroundStyle(Thema.kleur(.zacht))
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Thema.kleur(.papierZacht))
        .overlay(alignment: .leading) { Rectangle().fill(Thema.kleur(.zacht)).frame(width: 2) }
    }

    // MARK: - Kop

    private var kop: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("05 DIALOOG · GEÏNSTALLEERDE AGENTEN")
                .font(Thema.tekst(10, gewicht: .semibold))
                .tracking(3)
                .foregroundStyle(Thema.kleur(.gedempt))
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text("Gesprek met de ").font(Thema.display(30))
                Text("tuinier & curator.").font(Thema.display(30, cursief: true)).foregroundStyle(Thema.kleur(.zacht))
            }
            Text("Overleg over scope, inspecteer machine-bewijs of vraag om een nieuw stap-voorstel.")
                .font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.zacht))
        }
    }

    // MARK: - Agent Selector

    private var agentKiezer: some View {
        Kaart(kop: "Geïnstalleerde AI-Agenten", rechterKop: "Zero-Trust Context") {
            HStack(spacing: 12) {
                ForEach(geinstalleerdeAgents) { agent in
                    let isGekozen = geselecteerdeAgentId == agent.id
                    Button(action: { geselecteerdeAgentId = agent.id }) {
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(agent.naam)
                                    .font(Thema.tekst(12, gewicht: .semibold))
                                    .foregroundStyle(Thema.kleur(isGekozen ? .inkt : .zacht))
                                Spacer()
                                StatusBadge(tekst: agent.status, stijl: isGekozen ? .bewezen : .neutraal)
                            }
                            Text(agent.rolTitel)
                                .font(Thema.display(13, cursief: true))
                                .foregroundStyle(Thema.kleur(isGekozen ? .inkt : .gedempt))
                            Text(agent.beschrijving)
                                .font(Thema.tekst(10))
                                .foregroundStyle(Thema.kleur(.gedempt))
                                .lineLimit(1)
                        }
                        .padding(12)
                        .background(isGekozen ? Thema.kleur(.papierZacht) : Thema.kleur(.papier))
                        .overlay(Rectangle().stroke(Thema.kleur(isGekozen ? .inkt : .lijn), lineWidth: 1))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    // MARK: - Berichtenstroom

    private var gespreksPaneel: some View {
        Kaart(kop: "Berichtenstroom (Append-Only)", rechterKop: "\(berichten.count) berichten") {
            VStack(alignment: .leading, spacing: 16) {
                ForEach(berichten) { bericht in
                    berichtRij(bericht)
                }

                if agentDenktNa {
                    HStack(spacing: 8) {
                        ProgressView().controlSize(.small)
                        Text("De geselecteerde agent formuleert een deterministisch voorstel…")
                            .font(Thema.tekst(11))
                            .foregroundStyle(Thema.kleur(.gedempt))
                    }
                    .padding(.vertical, 6)
                }
            }
        }
    }

    private func berichtRij(_ b: ChatBericht) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .center, spacing: 8) {
                Text(b.afzender)
                    .font(Thema.display(14))
                StatusBadge(tekst: b.rol.label, stijl: b.rol.badgeStijl)
                if let ref = b.bewijsRef {
                    Text("ref: \(ref)")
                        .font(Thema.tekst(10))
                        .foregroundStyle(Thema.kleur(.gedempt))
                        .monospacedDigit()
                }
                Spacer()
                Text(b.tijdstip)
                    .font(Thema.tekst(11))
                    .foregroundStyle(Thema.kleur(.gedempt))
                    .monospacedDigit()
            }

            VStack(alignment: .leading, spacing: 8) {
                Text(b.tekst)
                    .font(Thema.tekst(13))
                    .lineSpacing(3.5)
                    .foregroundStyle(Thema.kleur(.inkt))

                if b.isVoorstel {
                    HStack {
                        StatusBadge(tekst: "Voorstel — Wacht op bekrachtiging", stijl: .mens)
                        Spacer()
                        Text("Curatie door mens vereist")
                            .font(Thema.tekst(10))
                            .foregroundStyle(Thema.kleur(.gedempt))
                    }
                    .padding(.top, 4)
                }
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(b.rol == .mens ? Thema.kleur(.papierZacht) : (b.isVoorstel ? Thema.kleur(.papierZacht) : Thema.kleur(.papier)))
            .overlay(
                Rectangle()
                    .stroke(Thema.kleur(b.isVoorstel ? .inkt : .lijn), lineWidth: 1)
            )
        }
        .padding(.bottom, 6)
    }

    // MARK: - Snelle Vragen

    private var snelleVragen: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("SNELLE OPGAVEN — GAAN ECHT DOOR DE POORT")
                .font(Thema.tekst(9, gewicht: .semibold))
                .tracking(1.5)
                .foregroundStyle(Thema.kleur(.gedempt))

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    snelleKnop("Slijp mijn prompt voor een dev-omgeving") {
                        stuurVraag("ik wil een schone python repo met tests")
                    }
                    snelleKnop("Tweede brein op deze machine") {
                        stuurVraag("een tweede brein voor mijn notities, lokaal op deze machine")
                    }
                }
            }
        }
    }

    private func snelleKnop(_ titel: String, actie: @escaping () -> Void) -> some View {
        Button(action: actie) {
            Text(titel)
                .font(Thema.tekst(11))
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(Thema.kleur(.papierZacht))
                .overlay(Capsule().stroke(Thema.kleur(.lijn), lineWidth: 1))
                .clipShape(Capsule())
                .foregroundStyle(Thema.kleur(.inkt))
        }
        .buttonStyle(.plain)
    }

    // MARK: - Planten vanuit de dialoog (slice 3)

    /// Er ligt een geaccepteerd concept: de curator mag planten.
    private var heeftVoorstel: Bool {
        berichten.last?.isVoorstel == true
    }

    private var plantKaart: some View {
        Kaart(kop: "Dit concept planten", rechterKop: "jouw bekrachtiging, stap voor stap") {
            VStack(alignment: .leading, spacing: 10) {
                labeledPoortVeld("PROFIEL (kiem)", text: $plantProfiel,
                                 placeholder: "tweede-brein · autonome-fabriek · dev-werkplaats")
                labeledPoortVeld("DOEL (waar de boom groeit)", text: $plantDoel,
                                 placeholder: "~/Projects/mijn-nieuwe-brein")
                HStack {
                    if wachtMijlpaal {
                        PillKnop(titel: "Mijlpaal bekrachtigd — plant nu", gevuld: true) {
                            plantNu(mijlpaalBevestigd: true)
                        }
                    } else {
                        PillKnop(titel: "1 · Bekijk concept", gevuld: false) { plantVoorbeeld() }
                        PillKnop(titel: "2 · Plant deze boom", gevuld: true) { plantNu(mijlpaalBevestigd: false) }
                    }
                    Spacer()
                    if plantBezig { ProgressView().controlSize(.small) }
                }
                Text("De app plaatst niets zelf: stap 1 vraagt een voorbeeld aan de adapter, stap 2 stuurt jouw bevestiging door. Een faal na alternatief stopt de plant — dan roep jij, de mens.")
                    .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.zacht)).lineSpacing(2)
            }
        }
    }

    private func labeledPoortVeld(_ label: String, text: Binding<String>, placeholder: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            Veld(placeholder: placeholder, tekst: text, lettergrootte: 12)
                .padding(8)
                .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                .background(Thema.kleur(.papierZacht))
        }
    }

    private func plantVoorbeeld() {
        let doel = plantDoel.trimmingCharacters(in: .whitespaces)
        guard !doel.isEmpty else {
            berichten.append(ChatBericht(afzender: "Tuinier", rol: .tuinier, tijdstip: actueleTijd(),
                tekst: "Vul eerst de doelmap in — waar moet de boom groeien?",
                bewijsRef: nil, isVoorstel: false))
            return
        }
        startPlant(bevestig: false, mijlpaalBevestigd: false)
    }

    private func plantNu(mijlpaalBevestigd: Bool) {
        startPlant(bevestig: true, mijlpaalBevestigd: mijlpaalBevestigd)
    }

    private func startPlant(bevestig: Bool, mijlpaalBevestigd: Bool) {
        let doel = plantDoel.trimmingCharacters(in: .whitespaces)
        let profiel = plantProfiel.trimmingCharacters(in: .whitespaces)
        guard !doel.isEmpty, !profiel.isEmpty else { return }
        plantBezig = true
        let tijd = actueleTijd()
        berichten.append(ChatBericht(
            afzender: "Mens", rol: .mens, tijdstip: tijd,
            tekst: bevestig
                ? "Ik bekrachtig: plant profiel '\(profiel)' in \(doel)\(mijlpaalBevestigd ? " (mijlpaal bevestigd)" : "")."
                : "Bekijk eerst het voorbeeld voor '\(profiel)' in \(doel).",
            bewijsRef: nil, isVoorstel: false))
        let repoPad = repoPad
        let interpreter = interpreter
        Task {
            let resultaat = await agentKoppeling.plant(runner: runner, repoPad: repoPad,
                                                       interpreter: interpreter,
                                                       profiel: profiel, doel: doel,
                                                       brein: "geen",
                                                       bevestig: bevestig,
                                                       mijlpaalBevestigd: mijlpaalBevestigd)
            await MainActor.run {
                plantBezig = false
                verwerkPlant(resultaat, bevestig: bevestig)
            }
        }
    }

    private func verwerkPlant(_ r: AgentKoppeling.PlantResultaat, bevestig: Bool) {
        let tijd = actueleTijd()
        if let fout = r.fout {
            berichten.append(ChatBericht(
                afzender: "Tuinier", rol: .tuinier, tijdstip: tijd,
                tekst: "Planten kon niet: \(fout)",
                bewijsRef: "adapter.py", isVoorstel: false))
            plantBezig = false
            wachtMijlpaal = false
            return
        }
        if let blok = r.mijlpaalBlok, !bevestig || bevestig && r.vragen.isEmpty {
            wachtMijlpaal = true
            berichten.append(ChatBericht(
                afzender: "Tuinier", rol: .tuinier, tijdstip: tijd,
                tekst: "Grote plant — dit raakt de mijlpaal-drempel. Niks is uitgevoerd. Lees dit blok en bevestig hieronder:\n\n\(blok)",
                bewijsRef: "§11.4 mijlpaal", isVoorstel: true))
            plantBezig = false
            return
        }
        if let concept = r.conceptTekst, !r.uitgevoerd {
            berichten.append(ChatBericht(
                afzender: "Tuinier", rol: .tuinier, tijdstip: tijd,
                tekst: "Voorbeeld van de plant (niets uitgevoerd):\n\n\(concept)\n\nKlik '2 · Plant nu' om te bekrachtigen.",
                bewijsRef: "adapter.py plant", isVoorstel: true))
            plantBezig = false
            return
        }
        if !r.stappen.isEmpty {
            let bewijsRegels = r.stappen.map { s -> String in
                let id = (s["id"] as? String) ?? "?"
                let status = (s["status"] as? String) ?? "?"
                let bewijs = (s["bewijs"] as? String) ?? ""
                return "• \(status == "geslaagd" ? "[OK]" : (status == "wacht_op_mens" ? "[MENS]" : "[✗]")) \(id) — \(bewijs)"
            }.joined(separator: "\n")
            berichten.append(ChatBericht(
                afzender: "Tuinier", rol: .tuinier, tijdstip: tijd,
                tekst: "De boom is geplant. Bewijs per stap:\n\n\(bewijsRegels)\n\nRegistratie: \(r.registratie ?? "—")",
                bewijsRef: "logboek.json (append-only)", isVoorstel: false))
            // Slice 6 — de reviewer in beeld: stappen mét review-oordeel als eigen berichten.
            let tijd = tijd
            for s in r.stappen where (s["review_rol"] as? String) != nil {
                let oordeel = (s["review_oordeel"] as? String) ?? "onduidelijk"
                berichten.append(ChatBericht(
                    afzender: "Reviewer", rol: .reviewer, tijdstip: tijd,
                    tekst: "Stap \(s["id"] as? String ?? "?"): rol '\(s["review_rol"] as? String ?? "reviewer")' oordeelde '\(oordeel)'. \(oordeel == "geslaagd" ? "De motor ging door; goedkeuringen door jou volgt nog." : "De motor is gestopt — jij beslist.")",
                    bewijsRef: "reviewconfig-rol", isVoorstel: false))
            }
            wachtMijlpaal = false
            plantBezig = false
            return
        }
        plantBezig = false
    }

    // MARK: - Vragen-rondje (slice 2)

    private var vragenKaart: some View {
        Kaart(kop: "De poort stelde vragen", rechterKop: "antwoorden gaan onveranderd door") {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(Array(openVragen.enumerated()), id: \.offset) { index, vraag in
                    let vraagTekstje = (vraag["vraag"] as? String) ?? "?"
                    VStack(alignment: .leading, spacing: 6) {
                        Text(vraagTekstje).font(Thema.tekst(12, gewicht: .semibold))
                            .foregroundStyle(Thema.kleur(.inkt))
                        if let opties = vraag["opties"] as? [String], !opties.isEmpty {
                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: 6) {
                                    ForEach(opties, id: \.self) { optie in
                                        Button(optie) {
                                            vraagAntwoorden[vraagTekstje] = optie
                                        }
                                        .buttonStyle(.plain)
                                        .font(Thema.tekst(11))
                                        .padding(.horizontal, 10).padding(.vertical, 5)
                                        .background(Thema.kleur(vraagAntwoorden[vraagTekstje] == optie ? .inkt : .papierZacht))
                                        .foregroundStyle(Thema.kleur(vraagAntwoorden[vraagTekstje] == optie ? .papier : .inkt))
                                        .overlay(Capsule().stroke(Thema.kleur(.lijn)))
                                        .clipShape(Capsule())
                                    }
                                }
                            }
                        }
                        TextField("of typ je eigen antwoord…", text: Binding(
                            get: { vraagAntwoorden[vraagTekstje] ?? "" },
                            set: { vraagAntwoorden[vraagTekstje] = $0 }))
                            .textFieldStyle(.plain).font(Thema.tekst(12)).padding(8)
                            .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                            .background(Thema.kleur(.papierZacht))
                            .foregroundStyle(Thema.kleur(.inkt))
                    }
                    .id(index)
                }
                HStack {
                    PillKnop(titel: "Verstuur antwoorden", gevuld: true) { verstuurAntwoorden() }
                    PillKnop(titel: "Laat staan", gevuld: false) { openVragen = []; vraagAntwoorden = [:] }
                }
            }
        }
    }

    private func verstuurAntwoorden() {
        let vragen = openVragen
        let tekst = vraagTekst
        openVragen = []
        let antwoorden = vraagAntwoorden
        vraagAntwoorden = [:]
        // Vaste mapping vraag-tekst → poort-veld (geen interpretatie van inhoud).
        let mapping: [String: String] = [
            "Wat is het einddoel?": "einddoel",
            "Waar moet het groeien (omgeving)?": "omgeving",
            "Wanneer is het geslaagd (slaag-criterium)?": "slaag_criterium",
        ]
        var velden: [String: String] = [:]
        for (vraag, antwoord) in antwoorden {
            if let veld = mapping[vraag] { velden[veld] = antwoord }
        }
        let tijd = actueleTijd()
        berichten.append(ChatBericht(
            afzender: "Mens", rol: .mens, tijdstip: tijd,
            tekst: vragen.compactMap { $0["vraag"] as? String }
                .map { "\($0) → \(antwoorden[$0] ?? "(niet beantwoord)")" }
                .joined(separator: "\n"),
            bewijsRef: nil, isVoorstel: false))
        agentDenktNa = true
        let repoPad = repoPad
        let interpreter = interpreter
        Task {
            let resultaat = await agentKoppeling.slijp(runner: runner, repoPad: repoPad,
                                                       interpreter: interpreter,
                                                       tekst: tekst, antwoorden: velden)
            await MainActor.run {
                agentDenktNa = false
                verwerk(resultaat, vraag: tekst)
            }
        }
    }

    // MARK: - Invoerbalk

    private var invoerBalk: some View {
        VStack(alignment: .leading, spacing: 10) {
            if !bijlagen.isEmpty { bijlagenRij }
            if spraak.fout != nil || spraak.neemtOp { opnameRij }
            HStack(spacing: 10) {
                providerMenu
                HStack {
                    Image(systemName: "bubble.left.and.bubble.right")
                        .font(.system(size: 13))
                        .foregroundStyle(Thema.kleur(.gedempt))
                    Veld(placeholder: "Stel een vraag of geef een opdracht aan de geselecteerde agent…", tekst: $invoerTekst)
                        .onSubmit { verzendBericht() }
                }
                .padding(10)
                .overlay(Rectangle().stroke(Thema.kleur(.lijn), lineWidth: 1))
                .background(Thema.kleur(.papierZacht))

                balkKnop("paperclip", toegankelijk: "Bijlage toevoegen") { toonBestandskiezer = true }
                balkKnop(spraak.neemtOp ? "stop.circle" : "mic",
                         toegankelijk: spraak.neemtOp ? "Opname stoppen en transcript plaatsen" : "Spraakmemo opnemen") {
                    wisselOpname()
                }
                PillKnop(titel: "Verstuur", gevuld: true) { verzendBericht() }
            }
        }
        .fileImporter(isPresented: $toonBestandskiezer,
                      allowedContentTypes: [.item], allowsMultipleSelection: true) { resultaat in
            if case .success(let urls) = resultaat {
                bijlagen.append(contentsOf: urls.filter { !bijlagen.contains($0) })
            }
        }
    }

    private var providerMenu: some View {
        Menu {
            ForEach(koppelingen.providerKeuzes, id: \.self) { keuze in
                Button(keuze) { koppelingen.actieveProvider = keuze }
            }
        } label: {
            HStack(spacing: 6) {
                Image(systemName: "cpu").font(.system(size: 12))
                Text(koppelingen.actieveProvider)
                    .lineLimit(1)
                Image(systemName: "chevron.up.chevron.down").font(.system(size: 9))
            }
            .font(Thema.tekst(11, gewicht: .medium))
            .padding(.horizontal, 12).padding(.vertical, 9)
            .overlay(Capsule().stroke(Thema.kleur(.lijn)))
            .background(Thema.kleur(.papierZacht))
            .foregroundStyle(Thema.kleur(.zacht))
        }
        .menuStyle(.borderlessButton)
        .menuIndicator(.hidden)
        .fixedSize()
    }

    private var bijlagenRij: some View {
        HStack(spacing: 8) {
            ForEach(bijlagen, id: \.self) { url in
                HStack(spacing: 6) {
                    Image(systemName: "doc").font(.system(size: 10))
                    Text(url.lastPathComponent).lineLimit(1)
                    Button(action: { bijlagen.removeAll { $0 == url } }) {
                        Image(systemName: "xmark").font(.system(size: 8))
                    }.buttonStyle(.plain)
                }
                .font(Thema.tekst(11))
                .padding(.horizontal, 10).padding(.vertical, 6)
                .overlay(Capsule().stroke(Thema.kleur(.lijn)))
                .background(Thema.kleur(.papierZacht))
            }
            Spacer()
        }
    }

    private var opnameRij: some View {
        HStack(spacing: 8) {
            Circle().fill(Thema.kleur(spraak.fout != nil ? .zacht : .inkt)).frame(width: 8, height: 8)
            Text(spraak.fout ?? (spraak.transcript.isEmpty
                 ? "Spraakmemo — luisteren… spreek je opdracht uit"
                 : spraak.transcript))
                .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(spraak.fout != nil ? .zacht : .zacht))
                .lineLimit(3)
            Spacer()
            if spraak.fout == nil {
                Text("lokaal · audio verlaat de machine niet")
                    .font(Thema.tekst(9)).foregroundStyle(Thema.kleur(.gedempt))
            }
        }
        .padding(10)
        .background(Thema.kleur(.papierZacht))
        .overlay(alignment: .leading) { Rectangle().fill(Thema.kleur(spraak.fout != nil ? .zacht : .inkt)).frame(width: 2) }
    }

    private func balkKnop(_ symbool: String, toegankelijk: String,
                          actie: @escaping () -> Void) -> some View {
        Button(action: actie) {
            Image(systemName: symbool).font(.system(size: 13))
                .frame(width: 38, height: 38)
                .overlay(Capsule().stroke(Thema.kleur(.lijn)))
                .background(Thema.kleur(.papierZacht))
                .foregroundStyle(Thema.kleur(.zacht))
        }
        .buttonStyle(.plain)
        .accessibilityLabel(toegankelijk)
    }

    private func wisselOpname() {
        if spraak.neemtOp {
            let tekst = spraak.stop()
            if !tekst.isEmpty { invoerTekst = tekst }
        } else {
            spraak.wisselOpname()
        }
    }

    private func verzendBericht() {
        let tekst = invoerTekst.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !tekst.isEmpty else { return }
        invoerTekst = ""
        stuurVraag(tekst)
    }

    private func stuurVraag(_ vraag: String) {
        let tijd = actueleTijd()
        let gebruikersBericht = ChatBericht(afzender: "Mens", rol: .mens, tijdstip: tijd,
                                            tekst: vraag, bewijsRef: nil, isVoorstel: false)
        berichten.append(gebruikersBericht)

        agentDenktNa = true
        let repoPad = repoPad
        let interpreter = interpreter
        Task {
            let resultaat = await agentKoppeling.slijp(runner: runner,
                                                       repoPad: repoPad,
                                                       interpreter: interpreter,
                                                       tekst: vraag,
                                                       agent: geselecteerdeAgentId)
            await MainActor.run {
                agentDenktNa = false
                verwerk(resultaat, vraag: vraag)
            }
        }
    }

    private func verwerk(_ r: SlijpResultaat, vraag: String) {
        let tijd = actueleTijd()
        if let fout = r.fout {
            berichten.append(ChatBericht(
                afzender: "Tuinier", rol: .tuinier, tijdstip: tijd,
                tekst: "De koppeling met de kern lukte niet: \(fout)\n\nControleer het repo-pad en de python-interpreter in Instellingen — het gesprek loopt via adapter.py en kan nooit om de poort heen.",
                bewijsRef: "adapter.py", isVoorstel: false))
            return
        }
        if !r.geaccepteerd, let weigering = r.weigering {
            var tekst = weigering
            if !r.vragen.isEmpty {
                let lijst = r.vragen.compactMap { $0["vraag"] as? String }
                    .map { "• \($0)" }.joined(separator: "\n")
                tekst += "\n\nAanvullende vragen van de poort:\n\(lijst)"
                openVragen = r.vragen
                vraagAntwoorden = [:]
                vraagTekst = r.ruweTekst
            }
            berichten.append(ChatBericht(
                afzender: "Tuinier", rol: .tuinier, tijdstip: tijd,
                tekst: tekst, bewijsRef: "growkit_poort.py", isVoorstel: false))
            return
        }
        if r.geaccepteerd, let concept = r.conceptJSON {
            berichten.append(ChatBericht(
                afzender: "Tuinier", rol: .tuinier, tijdstip: tijd,
                tekst: "Hier is het geschuurde concept uit de Scope-poort:\n\n\(concept)",
                bewijsRef: "poort.concept §11.1", isVoorstel: true))
            return
        }
        berichten.append(ChatBericht(
            afzender: "Tuinier", rol: .tuinier, tijdstip: tijd,
            tekst: "Ik heb je bericht ontvangen maar kon er geen poort-uitspraak uit lezen. Roep de mens — dit hoort niet te gebeuren.",
            bewijsRef: "adapter.py", isVoorstel: false))
    }

    private func actueleTijd() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter.string(from: Date())
    }
}
