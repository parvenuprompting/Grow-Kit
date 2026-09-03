// Chat-scherm — dialoog met 1 of meerdere geïnstalleerde AI-agenten in Editorial Monochrome stijl.
// Filosofie: de agent is de tuinier en adviseur; de mens blijft de enige curator.

import SwiftUI

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
    @Binding var repoPad: String
    @Binding var interpreter: String
    var metScroll: Bool = true

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
    @State private var invoerTekst: String = ""
    // DEMO: deze berichten zijn een ontwerpschets — de echte agent-koppeling
    // komt in een volgende fase en loopt via adapter.py, nooit om de poort heen.
    @State private var berichten: [ChatBericht] = [
        ChatBericht(afzender: "Tuinier", rol: .tuinier, tijdstip: "15:40:02",
                    tekst: "Welkom in het GrowKit-dialoogvenster. Ik ben je tuinier. Ik kan stappen voorstellen, prompts slijpen en het logboek inspecteren. Ik beslis nooit zelf: elke mutatie vereist jouw bekrachtiging.",
                    bewijsRef: "SEED.md §1", isVoorstel: false),
        ChatBericht(afzender: "Reviewer", rol: .reviewer, tijdstip: "15:40:08",
                    tekst: "Reviewer online. Ik bewaak reviewconfig.json en toets alle machine-controles (shell_check, file_equals, json_valid). Wat niet bewezen is, telt niet als waarheid.",
                    bewijsRef: "faalcontract §7", isVoorstel: false)
    ]
    @State private var agentDenktNa: Bool = false

    var body: some View {
        groep
            .background(Thema.kleur(.papier))
    }

    @ViewBuilder private var groep: some View {
        if metScroll { ScrollView { inhoudView } } else { inhoudView }
    }

    @ViewBuilder private var inhoudView: some View {
        VStack(alignment: .leading, spacing: 20) {
            kop
            demoBanner
            StappenStreep(stappen: ["Agentkeuze", "Prompt-slijper", "Voorstel", "Curatie"], actieveIndex: 1)
            agentKiezer
            gespreksPaneel
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
            Text("Dit dialoog is een ontwerpschets: de berichten zijn voorbeelden. De echte agent-koppeling komt in een volgende fase en loopt via adapter.py — nooit om de poort heen.")
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
            Text("06 DIALOOG · GEÏNSTALLEERDE AGENTEN")
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
            Text("VEELGESTELDE VRAGEN & ACTIES")
                .font(Thema.tekst(9, gewicht: .semibold))
                .tracking(1.5)
                .foregroundStyle(Thema.kleur(.gedempt))

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    snelleKnop("Slijp mijn prompt voor een dev-omgeving") {
                        stuurVraag("Kun je mijn prompt 'ik wil een schone python repo met tests' slijpen volgens de scope-poort?")
                    }
                    snelleKnop("Waarom faalde de laatste bewijs-check?") {
                        stuurVraag("Leg uit waarom de bewijs-check van de laatste stap oordeelt zoals hij deed.")
                    }
                    snelleKnop("Stel curatie-regels voor inbox/REGELS.md voor") {
                        stuurVraag("Stel drie concrete curatie-regels voor die de agent als alleen-lezen begrenzen.")
                    }
                    snelleKnop("Controleer register-integriteit") {
                        stuurVraag("Controleer of het oerwoud-brein register synchroon loopt met het geboortebewijs.")
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

    // MARK: - Invoerbalk

    private var invoerBalk: some View {
        HStack(spacing: 12) {
            HStack {
                Image(systemName: "bubble.left.and.bubble.right")
                    .font(.system(size: 13))
                    .foregroundStyle(Thema.kleur(.gedempt))
                TextField("Stel een vraag of geef een opdracht aan de geselecteerde agent…", text: $invoerTekst,
                          prompt: Text("Stel een vraag of geef een opdracht aan de geselecteerde agent…")
                              .font(Thema.tekst(13)).foregroundColor(Thema.kleur(.zacht)))
                    .textFieldStyle(.plain)
                    .font(Thema.tekst(13))
                    .foregroundStyle(Thema.kleur(.inkt))
                    .onSubmit { verzendBericht() }
            }
            .padding(10)
            .overlay(Rectangle().stroke(Thema.kleur(.lijn), lineWidth: 1))
            .background(Thema.kleur(.papierZacht))

            PillKnop(titel: "Verstuur", gevuld: true) { verzendBericht() }
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
        Task {
            try? await Task.sleep(nanoseconds: 600_000_000) // 0.6s voor rustige overgang
            await MainActor.run {
                agentDenktNa = false
                beantwoord(vraag: vraag)
            }
        }
    }

    private func beantwoord(vraag: String) {
        let tijd = actueleTijd()
        let q = vraag.lowercased()

        if q.contains("slijp") || q.contains("prompt") {
            berichten.append(ChatBericht(
                afzender: "Tuinier", rol: .tuinier, tijdstip: tijd,
                tekst: "Hier is het geschuurde voorstel conform de Scope-poort:\n\n• Doel: Gecontroleerde ontwikkelomgeving met geautomatiseerde teststraat.\n• Plek: ~/Documents/Code/nieuw-project (lokaal).\n• Slaag wanneer: pytest draait zonder fouten, ruff linting slaagt, geboortebewijs is gevalideerd.\n• Open vraag: Moet er een virtuele omgeving (.venv) automatisch worden aangemaakt?",
                bewijsRef: "poort.concept §2", isVoorstel: true))
        } else if q.contains("waarom") || q.contains("faal") || q.contains("check") {
            berichten.append(ChatBericht(
                afzender: "Reviewer", rol: .reviewer, tijdstip: tijd,
                tekst: "De bewijscontrole 'file_equals' berekent de SHA256-hash van het doelbestand en vergelijkt die met het sjabloon. Als er ook maar één whitespace verschilt, oordeelt de motor 'gefaald'. De motor probeert precies één alternatief commando. Faalt dat ook, dan stopt de motor en wordt de mens geroepen. Geen oneindige loops.",
                bewijsRef: "growkit_bewijs.py §4", isVoorstel: false))
        } else if q.contains("curatie") || q.contains("regel") || q.contains("inbox") {
            berichten.append(ChatBericht(
                afzender: "Tuinier", rol: .tuinier, tijdstip: tijd,
                tekst: "Voorstel voor inbox/REGELS.md:\n\n1. De agent plaatst nieuwe documenten uitsluitend als concept in inbox/ met de tag 'VOORSTEL'.\n2. Alleen de mens verplaatst documenten van inbox/ naar kennis/ of projecten/.\n3. Het logboek registreert elke curatiestap append-only.",
                bewijsRef: "inbox/REGELS.md", isVoorstel: true))
        } else {
            berichten.append(ChatBericht(
                afzender: geselecteerdeAgentId == "reviewer" ? "Reviewer" : "Tuinier",
                rol: geselecteerdeAgentId == "reviewer" ? .reviewer : .tuinier,
                tijdstip: tijd,
                tekst: "Ik heb je bericht ontvangen. Volgens de zero-trust filosofie kan ik opdrachten voorbereiden en analyseren, maar zal ik nooit acties uitvoeren zonder expliciete bevestiging via de Scope-poort en ratificatie via de adapter.",
                bewijsRef: "growkit_poort.py", isVoorstel: false))
        }
    }

    private func actueleTijd() -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter.string(from: Date())
    }
}
