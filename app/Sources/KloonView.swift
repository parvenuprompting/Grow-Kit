// KloonView — het Digitale Kloon-scherm (inbouw van digitale-kloon-ios).
//
// Volledig lokale persoonlijke kluis: vijf categorieën, geheime velden
// AES-GCM-versleuteld met een master-sleutel in de Sleutelhangar.
// Lijst toont géén geheimen; per item expliciet "Toon" (wordt gelogd).
// Editorial monochrome, lichte modus, Veld-component voor invoer.

import SwiftUI

struct KloonView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    @State private var items: [[String: Any]] = []
    @State private var geladen = false
    @State private var fout: String?

    // Nieuw geheim
    @State private var nieuweTitel = ""
    @State private var nieuweCategorie = "wachtwoord"
    @State private var veldWaarden: [String: String] = [:]
    @State private var melding: String?
    @State private var meldingOk = false
    @State private var bezig = false

    // Geheim tonen
    @State private var zichtbaarItem: [String: Any]? = nil

    private let categorieen: [(code: String, naam: String, velden: [(String, Bool)])] = [
        ("wachtwoord", "Wachtwoord", [("Gebruikersnaam", false), ("Wachtwoord", true)]),
        ("apikey", "API-key", [("Naam", false), ("Key", true)]),
        ("bank", "Bank / IBAN", [("IBAN", true), ("Naam rekeninghouder", false)]),
        ("crypto", "Crypto", [("Wallet", false), ("Private key / seed", true)]),
        ("account", "Account", [("Accountnaam", false), ("Wachtwoord", true)]),
    ]

    var body: some View {
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

    // MARK: - Nieuw geheim

    private var nieuwKaart: some View {
        Kaart(kop: "Nieuw geheim", rechterKop: "AES-GCM · SLEUTELHANGAR") {
            VStack(alignment: .leading, spacing: 12) {
                gelabeld("CATEGORIE") {
                    HStack(spacing: 8) {
                        ForEach(categorieen, id: \.code) { cat in
                            Button {
                                nieuweCategorie = cat.code
                                veldWaarden = [:]
                            } label: {
                                Text(cat.naam)
                                    .font(Thema.tekst(11, gewicht: nieuweCategorie == cat.code ? .semibold : .regular))
                                    .padding(.horizontal, 12).padding(.vertical, 7)
                                    .background(nieuweCategorie == cat.code ? Thema.kleur(.inkt) : Thema.kleur(.papier))
                                    .foregroundStyle(nieuweCategorie == cat.code ? Thema.kleur(.papier) : Thema.kleur(.inkt))
                                    .overlay(Capsule().stroke(Thema.kleur(.inkt), lineWidth: 1))
                                    .clipShape(Capsule())
                            }
                            .buttonStyle(.plain)
                        }
                        Spacer()
                    }
                }
                gelabeld("TITEL") {
                    Veld(placeholder: "bijv. OpenRouter", tekst: $nieuweTitel)
                        .padding(10)
                        .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                        .background(Thema.kleur(.papierZacht))
                }
                gelabeld("VELDEN") {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(actieveVelden, id: \.0) { veld in
                            HStack(spacing: 8) {
                                Text(veld.0.uppercased())
                                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                                    .foregroundStyle(Thema.kleur(.gedempt))
                                    .frame(width: 150, alignment: .leading)
                                Veld(placeholder: veld.1 ? "geheim" : veld.0,
                                     tekst: bindingVoor(veld.0))
                                    .padding(8)
                                    .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                                    .background(Thema.kleur(.papierZacht))
                            }
                        }
                    }
                }
                HStack(spacing: 10) {
                    PillKnop(titel: bezig ? "Bezig…" : "Bewaar in de kluis", gevuld: true) {
                        voegToe()
                    }
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
        Binding(get: { veldWaarden[naam] ?? "" },
                set: { veldWaarden[naam] = $0 })
    }

    // MARK: - Zichtbaar geheim

    private func zichtbaarKaart(_ item: [String: Any]) -> some View {
        Kaart(kop: item["titel"] as? String ?? "?",
              rechterKop: "ONTSLUTELD · WORDT GELOGD") {
            VStack(alignment: .leading, spacing: 8) {
                if let velden = item["velden_ontsleuteld"] as? [String: String] {
                    ForEach(velden.sorted(by: { $0.key < $1.key }), id: \.key) { paar in
                        HStack {
                            Text(paar.key.uppercased())
                                .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                                .foregroundStyle(Thema.kleur(.gedempt))
                                .frame(width: 150, alignment: .leading)
                            Text(paar.value)
                                .font(.system(size: 12, design: .monospaced))
                                .textSelection(.enabled)
                            Spacer()
                            PillKnop(titel: "Kopieer", gevuld: false, compact: true) {
                                NSPasteboard.general.clearContents()
                                NSPasteboard.general.setString(paar.value, forType: .string)
                            }
                        }
                    }
                }
                PillKnop(titel: "Verberg", gevuld: false, compact: true) {
                    zichtbaarItem = nil
                }
            }
        }
    }

    // MARK: - Lijst

    private var lijstKaart: some View {
        Kaart(kop: "Geheimen in de kluis",
              rechterKop: geladen ? "\(items.count) ITEMS" : nil) {
            VStack(alignment: .leading, spacing: 0) {
                if !geladen && fout == nil {
                    Text("Laden…").font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.gedempt))
                } else if items.isEmpty {
                    Text("Nog geen geheimen. Maak hierboven je eerste item.")
                        .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                } else {
                    ForEach(items.indices, id: \.self) { i in
                        itemRij(items[i])
                    }
                }
            }
        }
    }

    private func itemRij(_ item: [String: Any]) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 3) {
                Text(item["titel"] as? String ?? "")
                    .font(Thema.tekst(13, gewicht: .medium))
                Text(categorieNaam(item["categorie"] as? String ?? ""))
                    .font(Thema.tekst(10))
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
            Spacer()
            if let open = item["velden_open"] as? [String: String] {
                ForEach(open.sorted(by: { $0.key < $1.key }), id: \.key) { paar in
                    Text("\(paar.key): \(paar.value)")
                        .font(Thema.tekst(10))
                        .foregroundStyle(Thema.kleur(.gedempt))
                        .lineLimit(1)
                }
            }
            PillKnop(titel: "Toon", gevuld: true, compact: true) {
                toon(item)
            }
            PillKnop(titel: "Weg", gevuld: false, compact: true) {
                verwijder(item)
            }
        }
        .padding(.vertical, 9)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
        }
    }

    private func categorieNaam(_ code: String) -> String {
        categorieen.first(where: { $0.code == code })?.naam ?? code
    }

    // MARK: - Hulpstukken

    private func gelabeld<Inhoud: View>(_ label: String, @ViewBuilder inhoud: () -> Inhoud) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(label)
                .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            inhoud()
        }
    }

    @ViewBuilder
    private func meldingRegel(_ tekst: String, ok: Bool) -> some View {
        HStack(spacing: 8) {
            Image(systemName: ok ? "checkmark.circle" : "exclamationmark.triangle")
                .font(.system(size: 12))
            Text(tekst).font(Thema.tekst(12))
        }
        .foregroundStyle(Thema.kleur(ok ? .inkt : .zacht))
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
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "kloonlijst", invoer: [:])
            await MainActor.run {
                guard let r else { fout = "Adapter niet bereikbaar."; return }
                if r.ok {
                    items = r.data["items"] as? [[String: Any]] ?? []
                    geladen = true
                } else {
                    fout = r.fout ?? "Lijst laden mislukt."
                }
            }
        }
    }

    private func voegToe() {
        melding = nil
        var velden: [String: String] = [:]
        for (naam, _) in actieveVelden {
            velden[naam] = veldWaarden[naam] ?? ""
        }
        bezig = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "kloontoevoegen", invoer: [
                "titel": nieuweTitel,
                "categorie": nieuweCategorie,
                "velden": velden,
            ])
            await MainActor.run {
                bezig = false
                if let r, r.ok {
                    meldingOk = true
                    melding = "Geheim bewaard: \(nieuweTitel)"
                    nieuweTitel = ""
                    veldWaarden = [:]
                    laad()
                } else {
                    meldingOk = false
                    melding = r?.fout ?? "Bewaren mislukt."
                }
            }
        }
    }

    private func toon(_ item: [String: Any]) {
        guard let id = item["id"] as? String else { return }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "kloonlees", invoer: ["id": id])
            await MainActor.run {
                if let r, r.ok {
                    zichtbaarItem = r.data["item"] as? [String: Any]
                } else {
                    fout = r?.fout ?? "Ton mislukt."
                }
            }
        }
    }

    private func verwijder(_ item: [String: Any]) {
        guard let id = item["id"] as? String else { return }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "kloonverwijder", invoer: ["id": id])
            await MainActor.run {
                if let r, r.ok {
                    if (zichtbaarItem?["id"] as? String) == id { zichtbaarItem = nil }
                    laad()
                } else {
                    fout = r?.fout ?? "Verwijderen mislukt."
                }
            }
        }
    }
}
