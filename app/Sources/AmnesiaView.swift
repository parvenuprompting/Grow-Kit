// AmnesiaView — het Amnesia Protocol-scherm (inbouw van Amnesia Protocol Lite).
//
// Laag 1: tekst plakken → kandidaten via amnesiadetect → per vondst
// accepteren/negeren → amnesiamarker geeft de veilige tekst met markers.
// Laag 2: veilige tekst plakken → amnesiasynth maakt fictieve waarden.
// Alles lokaal via de adapter; de mens keurt per vondst.

import SwiftUI

struct AmnesiaView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    // Laag 1
    @State private var bronTekst = ""
    @State private var vondsten: [[String: Any]] = []
    @State private var besluiten: [String: String] = [:]   // id → besluit
    @State private var aangepast: [String: String] = [:]   // id → nieuwe waarde
    @State private var veiligeTekst = ""
    @State private var laag1Fout: String?
    @State private var bezigDetect = false
    @State private var bezigMarker = false

    // Laag 2
    @State private var synthInvoer = ""
    @State private var synthUitvoer = ""
    @State private var laag2Fout: String?
    @State private var bezigSynth = false
    @State private var sessieZaad = Int(Date().timeIntervalSince1970)

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                kop
                if let laag1Fout { foutKaart(laag1Fout) }

                brontekstKaart
                if !vondsten.isEmpty { kandidatenKaart }
                if !veiligeTekst.isEmpty { veiligeTekstKaart }
                synthKaart
                Spacer(minLength: 16)
            }
            .padding(28)
        }
        .background(Thema.kleur(.papier))
    }

    // MARK: - Kop

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Amnesia Protocol")
                .font(Thema.display(30))
            Text("Gevoelige tekst veilig maken vóórdat die een ander venster of een AI bereikt. Alles gebeurt lokaal op deze Mac — jij keurt per vondst; niets wordt automatisch vervangen. De mapping verdwijnt na de sessie.")
                .font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: - Laag 1: bron

    private var brontekstKaart: some View {
        Kaart(kop: "Laag 1 · Brontekst", rechterKop: "PLAK JE TEKST") {
            VStack(alignment: .leading, spacing: 12) {
                TekstGebied(placeholder: "Plak hier de tekst met gevoelige gegevens…", tekst: $bronTekst)
                HStack(spacing: 10) {
                    PillKnop(titel: bezigDetect ? "Zoeken…" : "Vind kandidaten", gevuld: true) {
                        detecteer()
                    }
                    PillKnop(titel: "Terminal-uitvoer", gevuld: false) {
                        detecteer(terminal: true)
                    }
                    Spacer()
                }
            }
        }
    }

    // MARK: - Kandidaten

    private var kandidatenKaart: some View {
        Kaart(kop: "Gevonden kandidaten",
              rechterKop: "\(vondsten.count) · JIJ BESLIST") {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(vondsten.indices, id: \.self) { i in
                    kandidaatRij(vondsten[i])
                }
                HStack(spacing: 10) {
                    PillKnop(titel: bezigMarker ? "Markeren…" : "Accepteer openstaande",
                             gevuld: true) {
                        for i in vondsten.indices {
                            let id = vondsten[i]["id"] as? String ?? ""
                            if besluiten[id] == nil { besluiten[id] = "geaccepteerd" }
                        }
                        markeer()
                    }
                    Spacer()
                }
                .padding(.top, 12)
            }
        }
    }

    private func kandidaatRij(_ v: [String: Any]) -> some View {
        let id = v["id"] as? String ?? ""
        let besluit = besluiten[id] ?? "open"
        return VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 10) {
                Text(typeLabel(v["type"] as? String ?? "overig"))
                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.2)
                    .textCase(.uppercase)
                    .padding(.horizontal, 8).padding(.vertical, 3)
                    .overlay(Capsule().stroke(Thema.kleur(.lijn), lineWidth: 1))
                    .clipShape(Capsule())
                if let waarde = v["waarde"] as? String {
                    Text(waarde)
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundStyle(Thema.kleur(.inkt))
                        .lineLimit(1)
                        .truncationMode(.middle)
                }
                Spacer()
                if besluit == "open" {
                    PillKnop(titel: "Token", gevuld: true, compact: true) {
                        besluiten[id] = "geaccepteerd"
                    }
                    PillKnop(titel: "Negeren", gevuld: false, compact: true) {
                        besluiten[id] = "genegeerd"
                    }
                    PillKnop(titel: "Aanpassen", gevuld: false, compact: true) {
                        besluiten[id] = "aangepast"
                        aangepast[id] = ""
                    }
                } else {
                    StatusBadge(tekst: besluitTekst(besluit), stijl: .bewezen)
                    PillKnop(titel: "Herstel", gevuld: false, compact: true) {
                        besluiten[id] = nil
                        aangepast[id] = nil
                    }
                }
            }
            if besluit == "aangepast" {
                Veld(placeholder: "Nieuwe waarde…", tekst: bindingVoor(id))
                    .padding(8)
                    .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                    .background(Thema.kleur(.papierZacht))
            }
        }
        .padding(.vertical, 8)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
        }
    }

    private func bindingVoor(_ id: String) -> Binding<String> {
        Binding(get: { aangepast[id] ?? "" },
                set: { aangepast[id] = $0 })
    }

    private func besluitTekst(_ besluit: String) -> String {
        switch besluit {
        case "geaccepteerd": return "TOKEN"
        case "genegeerd": return "GENEGEERD"
        case "aangepast": return "AANGEPAST"
        default: return "OPEN"
        }
    }

    private func typeLabel(_ soort: String) -> String {
        let labels = [
            "email": "E-mail", "telefoon": "Telefoon", "iban": "IBAN",
            "bsn": "BSN", "ip": "IP-adres", "postcode": "Postcode",
            "adres": "Adres", "datum": "Datum", "persoon": "Persoon",
            "klantnummer": "Klantnr.", "transactie": "Transactie",
            "serienummer": "Serie", "referentie": "Referentie",
            "link": "Link", "geheim": "Geheim", "apikey": "API-key",
            "accesstoken": "Token", "jwt": "JWT", "privatekey": "Priv.key",
            "credentialurl": "Cred-URL", "account": "Account",
            "pad": "Pad", "gitremote": "Git", "cloudresource": "Cloud",
        ]
        return labels[soort] ?? soort
    }

    // MARK: - Veilige tekst

    private var veiligeTekstKaart: some View {
        Kaart(kop: "Dezelfde tekst, veilig gemaakt",
              rechterKop: "MARKERS I.P.V. WAARDEN") {
            VStack(alignment: .leading, spacing: 10) {
                Text(veiligeTekst)
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundStyle(Thema.kleur(.inkt))
                    .textSelection(.enabled)
                PillKnop(titel: "Kopieer veilige tekst", gevuld: false) {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(veiligeTekst, forType: .string)
                }
                Text("Plak deze tekst zelf in Laag 2 hieronder — de brontekst verlaat dit scherm niet.")
                    .font(Thema.tekst(10))
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
        }
    }

    // MARK: - Laag 2

    private var synthKaart: some View {
        Kaart(kop: "Laag 2 · Synthetisch", rechterKop: "ALLEEN MARKERS") {
            VStack(alignment: .leading, spacing: 12) {
                TekstGebied(placeholder: "Plak hier zelf de veilige tekst uit Laag 1…", tekst: $synthInvoer)
                if let laag2Fout {
                    Text(laag2Fout).font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.zacht))
                }
                HStack(spacing: 10) {
                    PillKnop(titel: bezigSynth ? "Genereren…" : "Genereer standaardvervangers",
                             gevuld: true) {
                        synthetiseer()
                    }
                    if !synthUitvoer.isEmpty {
                        PillKnop(titel: "Kopieer synthetische tekst", gevuld: false) {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(synthUitvoer, forType: .string)
                        }
                    }
                    Spacer()
                }
                if !synthUitvoer.isEmpty {
                    Text(synthUitvoer)
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundStyle(Thema.kleur(.inkt))
                        .textSelection(.enabled)
                }
            }
        }
    }

    private func foutKaart(_ melding: String) -> some View {
        Kaart(kop: "Let op", rechterKop: "FOUT") {
            Text(melding).font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
        }
    }

    // MARK: - Adapter-aanroepen

    private func detecteer(terminal: Bool = false) {
        laag1Fout = nil
        veiligeTekst = ""
        bezigDetect = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "amnesiadetect",
                                           invoer: ["tekst": bronTekst, "terminal": terminal])
            await MainActor.run {
                bezigDetect = false
                guard let r else { laag1Fout = "Adapter niet bereikbaar."; return }
                if r.ok {
                    vondsten = r.data["vondsten"] as? [[String: Any]] ?? []
                    besluiten = [:]
                    aangepast = [:]
                } else {
                    laag1Fout = r.fout ?? "Detectie mislukt."
                }
            }
        }
    }

    private func markeer() {
        laag1Fout = nil
        bezigMarker = true
        var besluitLijst: [[String: Any]] = []
        for v in vondsten {
            let id = v["id"] as? String ?? ""
            if let b = besluiten[id] {
                var item: [String: Any] = ["id": id, "besluit": b]
                if b == "aangepast", let nieuweWaarde = aangepast[id], !nieuweWaarde.isEmpty {
                    item["waarde"] = nieuweWaarde
                }
                besluitLijst.append(item)
            }
        }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "amnesiamarker", invoer: [
                "tekst": bronTekst, "vondsten": vondsten, "besluiten": besluitLijst,
            ])
            await MainActor.run {
                bezigMarker = false
                guard let r else { laag1Fout = "Adapter niet bereikbaar."; return }
                if r.ok {
                    veiligeTekst = r.data["veilige_tekst"] as? String ?? ""
                } else {
                    laag1Fout = r.fout ?? "Markeren mislukt."
                }
            }
        }
    }

    private func synthetiseer() {
        laag2Fout = nil
        bezigSynth = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "amnesiasynth",
                                           invoer: ["tekst": synthInvoer, "zaad": sessieZaad])
            await MainActor.run {
                bezigSynth = false
                guard let r else { laag2Fout = "Adapter niet bereikbaar."; return }
                if r.ok {
                    synthUitvoer = r.data["synthetische_tekst"] as? String ?? ""
                } else {
                    laag2Fout = r.fout ?? "Synthetiseren mislukt."
                }
            }
        }
    }
}

// Meerregelig invoerveld met de Veld-aanpak (overlay-placeholder, want
// AppKit negeert placeholder-kleuren op macOS).
struct TekstGebied: View {
    let placeholder: String
    @Binding var tekst: String

    var body: some View {
        ZStack(alignment: .topLeading) {
            if tekst.isEmpty {
                Text(placeholder)
                    .font(Thema.tekst(13))
                    .foregroundStyle(Thema.kleur(.gedempt))
                    .allowsHitTesting(false)
                    .padding(12)
            }
            TextEditor(text: $tekst)
                .font(.system(size: 13))
                .foregroundStyle(Thema.kleur(.inkt))
                .scrollContentBackground(.hidden)
                .frame(minHeight: 110)
                .padding(4)
        }
        .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
        .background(Thema.kleur(.papierZacht))
    }
}
