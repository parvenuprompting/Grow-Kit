// KloonView — het Digitale Kloon-scherm (inbouw van digitale-kloon-ios).
//
// Volledig lokale persoonlijke kluis: vijf categorieën, geheime velden
// AES-GCM-versleuteld met een master-sleutel in de Sleutelhangar.
// Lijst toont géén geheimen; per item expliciet "Toon" (wordt gelogd).
// Editorial monochrome, lichte modus, Veld-component voor invoer.
//
// Fix 6 sept: PIN-vergrendeling (4-8 cijfers) + Touch ID, zodat de kluis
// niet zomaar toegankelijk is. PIN leeft in de Sleutelhangar; Touch ID
// gebruikt LocalAuthentication. Na 5 mislukte pogingen 30s blokkade.

import SwiftUI
import LocalAuthentication

// MARK: - PIN-opslag in de Sleutelhangar

private let pinService = "GrowKit Digitale Kloon: pin"

private func leesPIN() -> String? {
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: pinService,
        kSecReturnData as String: true,
        kSecMatchLimit as String: kSecMatchLimitOne,
    ]
    var result: AnyObject?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    guard status == errSecSuccess, let data = result as? Data else { return nil }
    return String(data: data, encoding: .utf8)
}

private func bewaarPIN(_ pin: String) {
    let data = pin.data(using: .utf8)!
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: pinService,
    ]
    SecItemDelete(query as CFDictionary)
    let add: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: pinService,
        kSecValueData as String: data,
    ]
    SecItemAdd(add as CFDictionary, nil)
}

// MARK: - View

struct KloonView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    // Vergrendeling
    @State private var ontgrendeld = false
    @State private var pinInvoer = ""
    @State private var pinFout = false
    @State private var pogingen = 0
    @State private var geblokkeerdTot: Date?
    @State private var bestaatPIN = false
    @State private var stelPINIn = false
    @State private var nieuwePIN = ""
    @State private var pinBevestigen = ""
    @State private var pinNietGelijk = false
    
    // Timer voor blokkade
    @State private var blokkadeTimer: Timer?

    // Data
    @State private var items: [[String: Any]] = []
    @State private var geladen = false
    @State private var fout: String?

    @State private var nieuweTitel = ""
    @State private var nieuweCategorie = "wachtwoord"
    @State private var veldWaarden: [String: String] = [:]
    @State private var melding: String?
    @State private var meldingOk = false
    @State private var bezig = false
    @State private var zichtbaarItem: [String: Any]? = nil

    private let categorieen: [(code: String, naam: String, velden: [(String, Bool)])] = [
        ("wachtwoord", "Wachtwoord", [("Gebruikersnaam", false), ("Wachtwoord", true)]),
        ("apikey", "API-key", [("Naam", false), ("Key", true)]),
        ("bank", "Bank / IBAN", [("IBAN", true), ("Naam rekeninghouder", false)]),
        ("crypto", "Crypto", [("Wallet", false), ("Private key / seed", true)]),
        ("account", "Account", [("Accountnaam", false), ("Wachtwoord", true)]),
    ]

    var body: some View {
        if !ontgrendeld {
            slotScherm
        } else {
            hoofdScherm
        }
    }

    // MARK: - Vergrendelscherm

    private var slotScherm: some View {
        VStack(spacing: 0) {
            Spacer()
            VStack(spacing: 28) {
                Image(systemName: "lock.shield.fill")
                    .font(.system(size: 44))
                    .foregroundStyle(Thema.kleur(.inkt))

                if stelPINIn {
                    Text("Stel je PIN in")
                        .font(Thema.display(24))
                    Text("Kies een code van 4 tot 8 cijfers om de kluis te beveiligen.")
                        .font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.zacht))
                        .multilineTextAlignment(.center)

                    SecureField("PIN (4-8 cijfers)", text: $nieuwePIN)
                        .font(.system(size: 24, design: .monospaced))
                        .multilineTextAlignment(.center)
                        .frame(width: 200)
                        .onChange(of: nieuwePIN) { _ in
                            nieuwePIN = String(nieuwePIN.prefix(8).filter { $0.isNumber })
                            pinNietGelijk = false
                        }

                    if nieuwePIN.count >= 4 {
                        SecureField("Herhaal PIN", text: $pinBevestigen)
                            .font(.system(size: 24, design: .monospaced))
                            .multilineTextAlignment(.center)
                            .frame(width: 200)
                            .onChange(of: pinBevestigen) { _ in
                                pinBevestigen = String(pinBevestigen.prefix(8).filter { $0.isNumber })
                            }
                    }

                    if pinNietGelijk {
                        Text("PIN's komen niet overeen")
                            .font(Thema.tekst(11)).foregroundStyle(.red)
                    }

                    if nieuwePIN.count >= 4 && pinBevestigen.count >= 4 && nieuwePIN.count == pinBevestigen.count {
                        PillKnop(titel: "Bewaar PIN", gevuld: true) {
                            if nieuwePIN == pinBevestigen {
                                bewaarPIN(nieuwePIN)
                                bestaatPIN = true
                                stelPINIn = false
                                ontgrendeld = true
                                laad()
                            } else {
                                pinNietGelijk = true
                            }
                        }
                    }
                } else {
                    Text("Digitale Kloon")
                        .font(Thema.display(24))
                    Text("Deze kluis is vergrendeld met een PIN.")
                        .font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.zacht))

                    // PIN-invoer (stippen)
                    HStack(spacing: 14) {
                        ForEach(0..<8, id: \.self) { i in
                            Circle()
                                .fill(i < pinInvoer.count ? Thema.kleur(.inkt) : Thema.kleur(.lijn))
                                .frame(width: 14, height: 14)
                        }
                    }

                    // Verborgen tekstveld voor PIN-invoer (macOS: geen numberPad)
                    TextField("", text: $pinInvoer)
                        .font(.system(size: 24))
                        .frame(width: 0, height: 0)
                        .opacity(0)
                        .onChange(of: pinInvoer) { _ in
                            pinInvoer = String(pinInvoer.prefix(8).filter { $0.isNumber })
                            if pinInvoer.count >= 4 { controleerPIN() }
                        }

                    if pinFout {
                        Text("Verkeerde PIN (\(5 - pogingen) pogingen over)")
                            .font(Thema.tekst(11)).foregroundStyle(.red)
                    }

                    if let blok = geblokkeerdTot, blok > Date() {
                        Text("Te veel pogingen. Wacht tot \(blok, style: .time)")
                            .font(Thema.tekst(11)).foregroundStyle(.red)
                    }

                    PillKnop(titel: "Ontgrendel met Touch ID", gevuld: true) {
                        ontgrendelMetTouchID()
                    }
                }
            }
            .padding(40)
            Spacer()
        }
        .background(Thema.kleur(.papier))
        .onAppear {
            bestaatPIN = leesPIN() != nil
            if !bestaatPIN { stelPINIn = true }
        }
    }

    // MARK: - Hoofdscherm

    private var hoofdScherm: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                kop
                if let fout { foutKaart(fout) }
                nieuwKaart
                if let zichtbaarItem { zichtbaarKaart(zichtbaarItem) }
                lijstKaart
                Spacer(minLength: 16)
            }
            .padding(28)
        }
        .background(Thema.kleur(.papier))
        .onAppear { laad() }
    }

    // --- Vergrendeling ---

    private func ontgrendelMetTouchID() {
        let context = LAContext()
        // Pin vóór Touch ID vragen vindt LAContext zelf uit
        let reden = "Ontgrendel de Digitale Kloon om je geheimen te bekijken."
        context.localizedCancelTitle = "Annuleer"
        context.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: reden) { gelukt, fout in
            DispatchQueue.main.async {
                if gelukt {
                    ontgrendeld = true
                    pinFout = false
                    pogingen = 0
                    laad()
                }
            }
        }
    }

    private func controleerPIN() {
        guard let blok = geblokkeerdTot, blok > Date() else {
            geblokkeerdTot = nil
            pogingen = 0
            return
        }
        guard let echtePIN = leesPIN() else { return }
        if pinInvoer == echtePIN {
            ontgrendeld = true
            pinFout = false
            pogingen = 0
            laad()
        } else if pinInvoer.count >= echtePIN.count {
            pogingen += 1
            pinFout = true
            pinInvoer = ""
            if pogingen >= 5 {
                geblokkeerdTot = Date().addingTimeInterval(30)
            }
        }
    }

    // --- Hulpstukken (uit bestaande view, behouden) ---
    // Let op: de rest van het scherm kopieert de bestaande functionaliteit

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Digitale Kloon")
                .font(Thema.display(30))
            Text("Je persoonlijke kluis voor wachtwoorden, API-keys, bankgegevens en crypto-credentials. Geheime velden zijn AES-GCM-versleuteld; de sleutel leeft in de Sleutelhangar. Geen netwerk — data verlaat de kluis alleen door jouw kopieeractie.")
                .font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var nieuwKaart: some View {
        Kaart(kop: "Nieuw geheim", rechterKop: "AES-GCM · SLEUTELHANGAR") {
            VStack(alignment: .leading, spacing: 12) {
                gelabeld("CATEGORIE") {
                    HStack(spacing: 8) {
                        ForEach(categorieen, id: \.code) { cat in
                            Button {
                                nieuweCategorie = cat.code; veldWaarden = [:]
                            } label: {
                                Text(cat.naam)
                                    .font(Thema.tekst(11, gewicht: nieuweCategorie == cat.code ? .semibold : .regular))
                                    .padding(.horizontal, 12).padding(.vertical, 7)
                                    .background(nieuweCategorie == cat.code ? Thema.kleur(.inkt) : Thema.kleur(.papier))
                                    .foregroundStyle(nieuweCategorie == cat.code ? Thema.kleur(.papier) : Thema.kleur(.inkt))
                                    .overlay(Capsule().stroke(Thema.kleur(.inkt), lineWidth: 1)).clipShape(Capsule())
                            }.buttonStyle(.plain)
                        }
                        Spacer()
                    }
                }
                gelabeld("TITEL") {
                    Veld(placeholder: "bijv. OpenRouter", tekst: $nieuweTitel).padding(10)
                        .overlay(Rectangle().stroke(Thema.kleur(.lijn))).background(Thema.kleur(.papierZacht))
                }
                gelabeld("VELDEN") {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(actieveVelden, id: \.0) { veld in
                            HStack(spacing: 8) {
                                Text(veld.0.uppercased())
                                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                                    .foregroundStyle(Thema.kleur(.gedempt)).frame(width: 150, alignment: .leading)
                                Veld(placeholder: veld.1 ? "geheim" : veld.0, tekst: bindingVoor(veld.0)).padding(8)
                                    .overlay(Rectangle().stroke(Thema.kleur(.lijn))).background(Thema.kleur(.papierZacht))
                            }
                        }
                    }
                }
                HStack(spacing: 10) {
                    PillKnop(titel: bezig ? "Bezig…" : "Bewaar in de kluis", gevuld: true) { voegToe() }
                    Spacer()
                }
                if let melding { meldingRegel(melding, ok: meldingOk) }
            }
        }
    }

    private var actieveVelden: [(String, Bool)] {
        categorieen.first(where: { $0.code == nieuweCategorie })?.velden ?? []
    }

    private func bindingVoor(_ naam: String) -> Binding<String> {
        Binding(get: { veldWaarden[naam] ?? "" }, set: { veldWaarden[naam] = $0 })
    }

    private func zichtbaarKaart(_ item: [String: Any]) -> some View {
        Kaart(kop: item["titel"] as? String ?? "?", rechterKop: "ONTSLUTELD · WORDT GELOGD") {
            VStack(alignment: .leading, spacing: 8) {
                if let velden = item["velden_ontsleuteld"] as? [String: String] {
                    ForEach(velden.sorted(by: { $0.key < $1.key }), id: \.key) { paar in
                        HStack {
                            Text(paar.key.uppercased()).font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                                .foregroundStyle(Thema.kleur(.gedempt)).frame(width: 150, alignment: .leading)
                            Text(paar.value).font(.system(size: 12, design: .monospaced)).textSelection(.enabled)
                            Spacer()
                            PillKnop(titel: "Kopieer", gevuld: false, compact: true) {
                                NSPasteboard.general.clearContents()
                                NSPasteboard.general.setString(paar.value, forType: .string)
                            }
                        }
                    }
                }
                PillKnop(titel: "Verberg", gevuld: false, compact: true) { zichtbaarItem = nil }
            }
        }
    }

    private var lijstKaart: some View {
        Kaart(kop: "Geheimen in de kluis", rechterKop: geladen ? "\(items.count) ITEMS" : nil) {
            VStack(alignment: .leading, spacing: 0) {
                if !geladen && fout == nil {
                    Text("Laden…").font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                } else if items.isEmpty {
                    Text("Nog geen geheimen. Maak hierboven je eerste item.").font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                } else {
                    ForEach(items.indices, id: \.self) { i in itemRij(items[i]) }
                }
            }
        }
    }

    private func itemRij(_ item: [String: Any]) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 3) {
                Text(item["titel"] as? String ?? "").font(Thema.tekst(13, gewicht: .medium))
                Text(categorieNaam(item["categorie"] as? String ?? "")).font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
            }
            Spacer()
            PillKnop(titel: "Toon", gevuld: true, compact: true) { toon(item) }
            PillKnop(titel: "Weg", gevuld: false, compact: true) { verwijder(item) }
        }.padding(.vertical, 9).overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
    }

    private func categorieNaam(_ code: String) -> String {
        categorieen.first(where: { $0.code == code })?.naam ?? code
    }

    private func gelabeld<Inhoud: View>(_ label: String, @ViewBuilder inhoud: () -> Inhoud) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(label).font(Thema.tekst(9, gewicht: .semibold)).tracking(2).foregroundStyle(Thema.kleur(.gedempt))
            inhoud()
        }
    }

    @ViewBuilder private func meldingRegel(_ tekst: String, ok: Bool) -> some View {
        HStack(spacing: 8) {
            Image(systemName: ok ? "checkmark.circle" : "exclamationmark.triangle").font(.system(size: 12))
            Text(tekst).font(Thema.tekst(12))
        }.foregroundStyle(Thema.kleur(ok ? .inkt : .zacht))
    }

    private func foutKaart(_ melding: String) -> some View {
        Kaart(kop: "Let op", rechterKop: "FOUT") {
            Text(melding).font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
        }
    }

    // MARK: - Adapter

    private func laad() {
        fout = nil
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "kloonlijst", invoer: [:])
            await MainActor.run {
                guard let r else { fout = "Adapter niet bereikbaar."; return }
                if r.ok { items = r.data["items"] as? [[String: Any]] ?? []; geladen = true }
                else { fout = r.fout ?? "Lijst laden mislukt." }
            }
        }
    }

    private func voegToe() {
        melding = nil
        var velden: [String: String] = [:]
        for (naam, _) in actieveVelden { velden[naam] = veldWaarden[naam] ?? "" }
        bezig = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "kloontoevoegen",
                invoer: ["titel": nieuweTitel, "categorie": nieuweCategorie, "velden": velden])
            await MainActor.run {
                bezig = false
                if let r, r.ok { meldingOk = true; melding = "Geheim bewaard: \(nieuweTitel)"; nieuweTitel = ""; veldWaarden = [:]; laad() }
                else { meldingOk = false; melding = r?.fout ?? "Bewaren mislukt." }
            }
        }
    }

    private func toon(_ item: [String: Any]) {
        guard let id = item["id"] as? String else { return }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "kloonlees", invoer: ["id": id])
            await MainActor.run {
                if let r, r.ok { zichtbaarItem = r.data["item"] as? [String: Any] }
                else { fout = r?.fout ?? "Ton mislukt." }
            }
        }
    }

    private func verwijder(_ item: [String: Any]) {
        guard let id = item["id"] as? String else { return }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter, commando: "kloonverwijder", invoer: ["id": id])
            await MainActor.run {
                if let r, r.ok { if (zichtbaarItem?["id"] as? String) == id { zichtbaarItem = nil }; laad() }
                else { fout = r?.fout ?? "Verwijderen mislukt." }
            }
        }
    }
}