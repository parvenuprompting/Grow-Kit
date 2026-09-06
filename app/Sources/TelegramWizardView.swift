// TelegramWizardView — scherm 21: verbind de hele familie met Telegram.
//
// Familie-modus (bouwplan B3): 7 agents × 6 stappen + 2 groep-stappen.
// Tokens gaan één keer naar de Sleutelhangar (kern bewaart ze, de app
// toont alleen de laatste 4 tekens). Voortgang bewaard in
// ~/.growkit/telegram_wizard.json (nooit tokens daarin).

import SwiftUI

struct TelegramAgentVoortgang: Identifiable {
    let agent: String
    let klaar: [Int]
    var id: String { agent }
}

struct TelegramWizardView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    @State private var voortgang: [String: [Int]] = [:]
    @State private var gekozenAgent = ""
    @State private var stapInvoer: [String: String] = [:]   // per "stap-sleutel" tekst
    @State private var tokenInvoer = ""
    @State private var melding: String?
    @State private var meldingOk = false
    @State private var bezig = false
    @State private var gekozenStap: Int? = nil

    private let familie = ["kairos", "riri", "vigil", "libra",
                           "memoria", "codex", "genius"]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                kop
                if let melding { meldingRegel(melding, ok: meldingOk) }

                if gekozenAgent.isEmpty {
                    familieKaart
                    groepKaart
                } else {
                    agentStroom(gekozenAgent)
                }
                Spacer(minLength: 16)
            }
            .padding(28)
        }
        .background(Thema.kleur(.papier))
        .onAppear { laad() }
    }

    private var zelfStappenGroep: [String] {
        [
            "Telegram-groep \"Parvenu Agent Family\" aanmaken en alle 7 bots toevoegen; groep-ID invullen (komt in elk profiel-config)",
            "Verdeelregel-test: één bericht in de groep → precies één agent antwoordt (volgens de ANTWOORD-VERDEELREGEL in de SOUL's)",
        ]
    }

    private func zelfStappenVoor(_ agent: String) -> [String] {
        let naam = agent.capitalized
        let klein = agent.lowercased()
        return [
            "BotFather: /newbot → naam (bijv. \(naam)) + gebruikersnaam (bijv. \(klein)_family_bot) → token kopiëren",
            "Token plakken in het invoerveld hieronder — hij gaat één keer naar de Sleutelhangar en is daarna niet meer terug te lezen in de app",
            "@userinfobot: stuur hem een bericht → noteer jouw chat-ID",
            "Chat-ID invullen hieronder — de app zet hem in het profiel-config",
            "Gateway-herstart (commando staat bij de knop — uitvoeren blijft bij jou, systeemgrens)",
            "Test: stuur /status naar díe bot — verwacht antwoord van díe agent",
        ]
    }

    // MARK: Kop

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("21 TELEGRAM CONNECT · DE FAMILIE OP JOUW MOBIEL")
                .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            Text("Telegram Connect").font(Thema.display(30))
            Text("Koppel alle 7 agents aan jouw eigen Telegram. Elke bot heeft zijn eigen token (BotFather), één keer invoeren — hij leeft daarna in de Sleutelhangar. De wizard begeleidt; de stappen bij BotFather en de gateway-herstart doe jij.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: Familie-overzicht

    private var familieKaart: some View {
        Kaart(kop: "De familie", rechterKop: "\(voortgangGereed) VAN \(familie.count * 6 + 2) STAPPEN") {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(familie, id: \.self) { agent in
                    agentRij(agent)
                    if agent != familie.last {
                        Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
                    }
                }
                Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
                groepRij
            }
        }
    }

    private var groepKaart: some View {
        Kaart(kop: "Groep: Parvenu Agent Family", rechterKop: nil) {
            VStack(alignment: .leading, spacing: 8) {
                Text("De groep koppelt alle bots aan één kanaal — de antwoord-verdeelregel bepaalt wie reageert.")
                    .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                groepRij
            }
        }
    }

    private var voortgangGereed: Int {
        voortgang.values.reduce(0) { $0 + $1.count }
    }

    private func agentRij(_ agent: String) -> some View {
        let klaar = voortgang[agent]?.count ?? 0
        let kleur: Color = klaar == 6 ? .green : (klaar > 0 ? .orange : .gray)
        return Button {
            gekozenAgent = agent
        } label: {
            HStack {
                Circle().fill(kleur).frame(width: 7, height: 7)
                Text(agent.capitalized)
                    .font(Thema.tekst(13, gewicht: klaar == 6 ? .semibold : .medium))
                Spacer()
                Text("\(klaar)/6")
                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                Image(systemName: "chevron.right")
                    .font(.system(size: 9, weight: .semibold))
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
            .padding(.vertical, 10)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    private var groepRij: some View {
        let klaar = voortgang["__groep__"]?.count ?? 0
        return Button {
            gekozenAgent = "__groep__"
        } label: {
            HStack {
                Circle().fill(klaar == 2 ? .green : .gray).frame(width: 7, height: 7)
                Text("Groep: Parvenu Agent Family")
                    .font(Thema.tekst(13, gewicht: .medium))
                Spacer()
                Text("\(klaar)/2")
                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
            }
            .padding(.vertical, 10)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    // MARK: Agent-stroom

    @ViewBuilder
    private func agentStroom(_ agent: String) -> some View {
        let isGroep = agent == "__groep__"
        let stappen: [String] = isGroep ? zelfStappenGroep : zelfStappenVoor(agent)
        let klaar = voortgang[agent] ?? []
        let naam = isGroep ? "De groep" : agent.capitalized

        Kaart(kop: naam, rechterKop: "\(klaar.count)/\(stappen.count) KLAAR") {
            VStack(alignment: .leading, spacing: 14) {
                ForEach(Array(stappen.enumerated()), id: \.offset) { idx, tekst in
                    let nummer = idx + 1
                    let klaarNu = klaar.contains(nummer)
                    HStack(alignment: .top, spacing: 10) {
                        Button {
                            if klaarNu {
                                ontmarkeer(agent, nummer)
                            } else {
                                gekozenStap = nummer
                            }
                        } label: {
                            Image(systemName: klaarNu
                                  ? "checkmark.circle.fill" : "circle")
                                .font(.system(size: 16))
                                .foregroundStyle(klaarNu ? .green : Thema.kleur(.gedempt))
                        }
                        .buttonStyle(.plain)
                        VStack(alignment: .leading, spacing: 4) {
                            Text(tekst).font(Thema.tekst(12))
                                .fixedSize(horizontal: false, vertical: true)

                            // Token-invoer (stap 2)
                            if nummer == 2 && !isGroep {
                                HStack {
                                    SecureField("token (plak hier — hij verdwijnt in de hangar)",
                                                text: $tokenInvoer)
                                        .textFieldStyle(.plain)
                                        .font(Thema.tekst(11))
                                        .padding(6)
                                        .background(RoundedRectangle(cornerRadius: 6)
                                            .stroke(Thema.kleur(.lijn)))
                                    Text(toon_mask(agent))
                                        .font(Thema.tekst(10))
                                        .foregroundStyle(Thema.kleur(.gedempt))
                                }
                            }
                            // Chat-ID-invoer (stap 4)
                            if nummer == 4 && !isGroep {
                                TextField("jouw chat-ID (cijfers)",
                                          text: bindingVoor("chatid-\(agent)"))
                                    .textFieldStyle(.plain)
                                    .font(Thema.tekst(11))
                                    .padding(6)
                                    .background(RoundedRectangle(cornerRadius: 6)
                                        .stroke(Thema.kleur(.lijn)))
                            }
                        }
                    }
                }

                Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
                HStack {
                    PillKnop(titel: "Markeer gekozen stap klaar",
                             gevuld: true) {
                        if let stap = gekozenStap {
                            markeer(agent, stap: stap)
                        }
                    }
                    Spacer()
                    PillKnop(titel: "Terug naar overzicht", gevuld: false, compact: true) {
                        gekozenAgent = ""
                        gekozenStap = nil
                    }
                }
                if let melding { meldingRegel(melding, ok: meldingOk) }
            }
        }
    }

    private func bindingVoor(_ sleutel: String) -> Binding<String> {
        Binding(get: { stapInvoer[sleutel] ?? "" },
                set: { stapInvoer[sleutel] = $0 })
    }

    private func toon_mask(_ agent: String) -> String {
        // via adapter: toont alleen laatste 4 tekens uit de Sleutelhangar
        maskTekst[agent] ?? "niet ingesteld"
    }

    // MARK: Melding

    @ViewBuilder private func meldingRegel(_ tekst: String, ok: Bool) -> some View {
        HStack(spacing: 8) {
            Image(systemName: ok ? "checkmark.circle" : "exclamationmark.triangle")
                .font(.system(size: 12))
            Text(tekst).font(Thema.tekst(12))
        }
        .foregroundStyle(Thema.kleur(ok ? .inkt : .zacht))
    }

    // MARK: Data

    @State private var maskTekst: [String: String] = [:]

    private func laad() {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "telegramwizard", invoer: [:])
            await MainActor.run {
                if let r, r.ok {
                    let stand = r.data["voortgang"] as? [String: [Int]] ?? [:]
                    voortgang = stand
                    // maskers per agent
                    var nieuwe: [String: String] = [:]
                    for agent in familie {
                        nieuwe[agent] = r.data["mask_\(agent)"] as? String ?? "niet ingesteld"
                    }
                    maskTekst = nieuwe
                }
            }
        }
    }

    private func markeer(_ agent: String, stap: Int) {
        Task {
            var invoer: [String: Any] = ["agent": agent, "stap": stap]
            if stap == 2 && !isGroepAgent(agent) && !tokenInvoer.isEmpty {
                invoer["token"] = tokenInvoer
            }
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "telegramwizard", invoer: invoer)
            await MainActor.run {
                if let r, r.ok {
                    tokenInvoer = ""
                    meldingOk = true
                    melding = "Stap \(stap) gemarkeerd."
                    laad()
                } else {
                    meldingOk = false
                    melding = r?.fout ?? "Markeren mislukt."
                }
            }
        }
    }

    private func ontmarkeer(_ agent: String, _ stap: Int) {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "telegramwizard",
                                           invoer: ["agent": agent, "stap": stap,
                                                    "ontkoppel": true])
            await MainActor.run {
                if let r, r.ok { laad() }
            }
        }
    }

    private func isGroepAgent(_ agent: String) -> Bool { agent == "__groep__" }
}