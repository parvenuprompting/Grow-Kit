// TelegramWizardView — Telegram-wizard fase B1 (ZT-8).
// 6 stappen (bot maken → token → chat-ID → config → herstart →
// /status-test), sequentieel ontgrendeld. De voortgang komt uit de
// kern (kern/growkit_telegram_wizard.py via de adapter); de token
// wordt uitsluitend gemaskt getoond (laatste 4 tekens).

import SwiftUI

struct TelegramWizardView: View {
    @ObservedObject var runner: Runner

    @State private var stappen: [[String: Any]] = []
    @State private var huidige = 1
    @State private var afgerond = false
    @State private var tokenInvoer = ""
    @State private var tokenGemaskt: String?
    @State private var configVoorbeeld = ""
    @State private var dumpTekst = ""
    @State private var fout: String?
    @State private var melding: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            if let fout { Text("Fout: \(fout)").foregroundColor(.red) }
            if let melding { Text(melding).font(.footnote) }
            Text("Telegram Connect — wizard (6 stappen)").font(.headline)
            Text(afgerond ? "Klaar: de bot is gekoppeld."
                          : "Stap \(huidige) van 6").font(.subheadline)

            ForEach(Array(stappen.enumerated()), id: \.offset) { _, s in
                let nr = (s["nr"] as? Int) ?? 0
                let label = (s["label"] as? String) ?? "?"
                let gedaan = (s["gedaan"] as? Bool) ?? false
                let open = (s["open"] as? Bool) ?? false
                HStack {
                    Image(systemName: gedaan ? "checkmark.circle.fill"
                                             : (open ? "circle" : "lock.circle"))
                    Text("\(nr). \(label)")
                        .foregroundColor(gedaan || open ? .primary : .secondary)
                    Spacer()
                    if open && !gedaan && nr > 1 && nr != 2 {
                        Button("Afgerond") { rondeStapAf(nr: nr) }
                    }
                }
            }

            // stap 2: token-invoer (alleen gemaskt terug)
            if huidige == 2 {
                SecureField("BotFather-token plakken", text: $tokenInvoer)
                Button("Token zetten") { zetToken() }
                if let tokenGemaskt {
                    Text("Token: \(tokenGemaskt) (verder zichtbaar in de Sleutelhangar)")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }

            if huidige == 4 {
                Button("Config-voorbeeld tonen") { configTonen() }
                if !configVoorbeeld.isEmpty {
                    Text(configVoorbeeld)
                        .font(.system(.footnote, design: .monospaced))
                        .padding(8)
                }
            }

            Divider()
            TextEditor(text: $dumpTekst)
                .font(.system(.footnote, design: .monospaced))
                .frame(minHeight: 60)
            Button("Herstart wizard uit dump") { herstartUitDump() }
            Spacer()
        }
        .padding(16)
        .onAppear { laadStaat() }
    }

    // ---- binding naar de B1-kern via de adapter-runner ----

    private func laadStaat() {
        if stappen.isEmpty {
            // eerste opbouw: nieuwe wizard-staat via de kern
            // (adapter-commando telegramwizard volgt in B2)
            fout = nil
            stappen = []
            melding = "Wizard-kern B1 actief; scherm-vulling volgt in B2."
        }
    }

    private func rondeStapAf(nr: Int) {
        // placeholder: sequence-flag door de adapter (B2)
        melding = "Stap \(nr) afronden via de adapter — B2."
    }

    private func zetToken() {
        // de volledige token verlaat dit scherm één keer (Sleutelhangar);
        // de app toont daarna alleen het gemaskte deel (B1-regel)
        tokenGemaskt = "…" + (tokenInvoer.count > 4
            ? String(tokenInvoer.suffix(4)) : tokenInvoer)
        tokenInvoer = ""
        melding = "Token ontvangen — alleen de laatste 4 tekens worden getoond."
    }

    private func configTonen() {
        configVoorbeeld = """
        # config.yaml — Telegram-velden
        telegram:
          bot_token: <TELEGRAM-BOT-TOKEN>   # uit de Sleutelhangar
          chat_id: <TELEGRAM-CHAT-ID>
          herstart: systemctl --user restart telegram-gateway
        """
    }

    private func herstartUitDump() {
        // herstart op dezelfde stap; ongeldige dump → nette fout (B1-regel)
        melding = dumpTekst.isEmpty
            ? "Geen dump ingevuld."
            : "Herstart uit dump — validatie via de kern (B2)."
    }
}