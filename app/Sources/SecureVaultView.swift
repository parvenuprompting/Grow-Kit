// SecureVaultView — het Secure Vault-scherm (inbouw van SecureVault v2).
//
// Echte macOS-kluizen via de adapter: vaultlijst (Spotlight), vaultmaak
// (hdiutil AES-256/APFS), vaultopen (wachtwoord óf Sleutelhangar) en
// vaultsluit. De app is bedienaar, nooit machthebber: de encryptie doet
// macOS, de audit-spoor leeft in de kern. Editorial monochrome, lichte
// modus, Veld-component voor invoer (placeholder-bug omzeild).

import SwiftUI

struct SecureVaultView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    // Kluisoverzicht
    @State private var kluizen: [String] = []
    @State private var openMounts: [String] = []
    @State private var lijstGeladen = false
    @State private var fout: String?

    // Nieuwe kluis
    @State private var bronPad = ""
    @State private var kluisNaam = ""
    @State private var doelMap = ""
    @State private var wachtwoord = ""
    @State private var gekozenVorm = "UDZO"
    @State private var maakMelding: String?
    @State private var maakOk = false

    // Openen
    @State private var openKluisPad = ""
    @State private var openWachtwoord = ""
    @State private var gebruikKeychain = true
    @State private var openMelding: String?
    @State private var openOk = false

    @State private var bezig = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                kop
                if let fout { foutKaart(fout) }

                openKaart
                maakKaart
                overzichtKaart
                Spacer(minLength: 16)
            }
            .padding(28)
        }
        .background(Thema.kleur(.papier))
        .onAppear { laadLijst() }
    }

    // MARK: - Kop

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Secure Vault")
                .font(Thema.display(30))
            Text("Gevoelige mappen beveiligen in echte macOS-kluizen — AES-256 op APFS via hdiutil. De encryptie doet je Mac zelf; GrowKit is de hand, niet het slot. Wachtwoorden mogen veilig in de Sleutelhangar.")
                .font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: - Overzicht

    private var overzichtKaart: some View {
        Kaart(kop: "Kluizen op deze Mac",
              rechterKop: lijstGeladen ? "\(kluizen.count) GEVONDEN · \(openMounts.count) OPEN" : nil) {
            VStack(alignment: .leading, spacing: 0) {
                if !lijstGeladen && fout == nil {
                    Text("Kluizen zoeken…")
                        .font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.gedempt))
                } else if kluizen.isEmpty {
                    Text("Geen kluizen gevonden. Maak hieronder je eerste kluis — of bewaar bestaande .dmg/.sparsebundle-bestanden op een door Spotlight geïndexeerde plek.")
                        .font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.gedempt))
                } else {
                    ForEach(kluizen, id: \.self) { pad in
                        kluisRij(pad)
                    }
                }
                HStack(spacing: 10) {
                    PillKnop(titel: "Verversen", gevuld: false, compact: true) { laadLijst() }
                    if !openMounts.isEmpty {
                        PillKnop(titel: "Sluit alle open kluizen", gevuld: false, compact: true) {
                            sluitAlles()
                        }
                    }
                    Spacer()
                }
                .padding(.top, 14)
            }
        }
    }

    private func kluisRij(_ pad: String) -> some View {
        let isOpen = openMounts.contains { mount in
            padHasPrefixMount(pad, mount)
        }
        return HStack {
            VStack(alignment: .leading, spacing: 3) {
                Text((pad as NSString).lastPathComponent)
                    .font(Thema.tekst(13, gewicht: .medium))
                    .foregroundStyle(Thema.kleur(.inkt))
                Text(pad)
                    .font(Thema.tekst(10))
                    .foregroundStyle(Thema.kleur(.gedempt))
                    .lineLimit(1)
                    .truncationMode(.head)
            }
            Spacer()
            StatusBadge(tekst: isOpen ? "OPEN" : "VERGRENDELD",
                        stijl: isOpen ? .lopend : .neutraal)
            if isOpen {
                PillKnop(titel: "Sluit", gevuld: false, compact: true) {
                    sluitMount(pad)
                }
            } else {
                PillKnop(titel: "Open", gevuld: true, compact: true) {
                    openKluisPad = pad
                    openWachtwoord = ""
                    gebruikKeychain = true
                }
            }
        }
        .padding(.vertical, 9)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
        }
    }

    /// Heuristiek: hoort dit pad bij dit mountpunt? (naam-match)
    private func padHasPrefixMount(_ pad: String, _ mount: String) -> Bool {
        let naam = ((pad as NSString).lastPathComponent as NSString)
            .deletingPathExtension
        return mount.lowercased().contains(naam.lowercased())
    }

    // MARK: - Openen

    private var openKaart: some View {
        Kaart(kop: "Kluis openen",
              rechterKop: "SLEUTELHANGAR OF WACHTWOORD") {
            VStack(alignment: .leading, spacing: 12) {
                gelabeld("KLUIS-BESTAND (.DMG / .SPARSEBUNDLE)") {
                    Veld(placeholder: "/pad/naar/kluis.dmg", tekst: $openKluisPad)
                        .padding(10)
                        .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                        .background(Thema.kleur(.papierZacht))
                }
                gelabeld("WACHTWOORD (LEEG LATEN BIJ SLEUTELHANGAR)") {
                    Veld(placeholder: "••••••••••••", tekst: $openWachtwoord)
                        .padding(10)
                        .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                        .background(Thema.kleur(.papierZacht))
                }
                HStack(spacing: 10) {
                    PillKnop(titel: "Open via Sleutelhangar", gevuld: true) {
                        gebruikKeychain = true
                        open()
                    }
                    PillKnop(titel: "Open met wachtwoord", gevuld: false) {
                        gebruikKeychain = false
                        open()
                    }
                    Spacer()
                }
                if let openMelding {
                    meldingRegel(openMelding, ok: openOk)
                }
            }
        }
    }

    // MARK: - Nieuwe kluis

    private var maakKaart: some View {
        Kaart(kop: "Nieuwe kluis — map veilig opsluiten",
              rechterKop: "AES-256 · APFS · VIA MACOS") {
            VStack(alignment: .leading, spacing: 12) {
                gelabeld("1 · WELKE MAP GAAT IN DE KLUIS?") {
                    Veld(placeholder: "/pad/naar/geheime-map", tekst: $bronPad)
                        .padding(10)
                        .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                        .background(Thema.kleur(.papierZacht))
                }
                HStack(alignment: .top, spacing: 12) {
                    gelabeld("2 · NAAM VAN DE KLUIS") {
                        Veld(placeholder: "dossier-klant-B", tekst: $kluisNaam)
                            .padding(10)
                            .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                            .background(Thema.kleur(.papierZacht))
                    }
                    gelabeld("3 · WAAR MAG DE KLUIS KOMEN?") {
                        Veld(placeholder: "~/Documenten/Kluizen", tekst: $doelMap)
                            .padding(10)
                            .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                            .background(Thema.kleur(.papierZacht))
                    }
                }
                gelabeld("4 · WACHTWOORD (OF LAAT LEEG VOOR EEN GEGENEREERD STERK WACHTWOORD)") {
                    HStack(spacing: 10) {
                        Veld(placeholder: "••••••••••••••••", tekst: $wachtwoord)
                            .padding(10)
                            .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                            .background(Thema.kleur(.papierZacht))
                        PillKnop(titel: "Genereer sterk wachtwoord", gevuld: false, compact: true) {
                            wachtwoord = genereerLokaal()
                        }
                    }
                }
                gelabeld("5 · SOORT KLUIS") {
                    HStack(spacing: 8) {
                        vormKnop("UDZO", "Archief (alleen-lezen)")
                        vormKnop("UDRW", "Lees & schrijf")
                        vormKnop("UDSB", "Meegroeiend")
                        Spacer()
                    }
                }
                HStack(spacing: 10) {
                    PillKnop(titel: bezig ? "Bezig…" : "Kluis maken", gevuld: true) {
                        maak()
                    }
                    Spacer()
                }
                if let maakMelding {
                    meldingRegel(maakMelding, ok: maakOk)
                }
                Text("Een kluis met dezelfde naam wordt nooit stilletjes overschreven. Elke actie (maken, openen, sluiten) komt in het append-only audit-logboek.")
                    .font(Thema.tekst(10))
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
        }
    }

    private func vormKnop(_ code: String, _ naam: String) -> some View {
        Button {
            gekozenVorm = code
        } label: {
            VStack(spacing: 4) {
                Text(code).font(Thema.tekst(11, gewicht: .semibold)).tracking(1)
                Text(naam).font(Thema.tekst(9)).foregroundStyle(Thema.kleur(.zacht))
            }
            .padding(.horizontal, 12).padding(.vertical, 8)
            .frame(maxWidth: .infinity)
            .background(gekozenVorm == code ? Thema.kleur(.inkt) : Thema.kleur(.papier))
            .foregroundStyle(gekozenVorm == code ? Thema.kleur(.papier) : Thema.kleur(.inkt))
            .overlay(Rectangle().stroke(Thema.kleur(.inkt), lineWidth: 1))
        }
        .buttonStyle(.plain)
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

    /// Lokaal sterk wachtwoord (zelfde regels als de kern, maar zonder de
    /// adapter te belasten). Genereert letters, cijfers en leestekens.
    private func genereerLokaal() -> String {
        let letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        let cijfers = "0123456789"
        let leestekens = "!@#$%^&*()-_=+"
        let alles = letters + cijfers + leestekens
        var sterk = ""
        repeat {
            sterk = String((0..<20).map { _ in
                let groep = [letters, cijfers, leestekens].randomElement()!
                return groep.randomElement()!
            })
            // Mix garanderen: minimaal één van elke soort
            if !sterk.contains(where: { cijfers.contains($0) }) { continue }
            if !sterk.contains(where: { leestekens.contains($0) }) { continue }
            if !sterk.contains(where: { letters.contains($0) }) { continue }
            break
        } while true
        return sterk
    }

    // MARK: - Adapter-aanroepen

    private func laadLijst() {
        fout = nil
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "vaultlijst", invoer: [:])
            await MainActor.run {
                guard let r else { fout = "Adapter niet bereikbaar."; return }
                if r.ok {
                    kluizen = r.data["kluizen"] as? [String] ?? []
                    openMounts = r.data["open"] as? [String] ?? []
                    lijstGeladen = true
                } else {
                    fout = r.fout ?? "Onbekende fout bij het zoeken van kluizen."
                }
            }
        }
    }

    private func maak() {
        maakMelding = nil
        var ww = wachtwoord
        if ww.isEmpty { ww = genereerLokaal() }
        bezig = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "vaultmaak", invoer: [
                "bron": bronPad, "doelmap": doelMap, "naam": kluisNaam,
                "wachtwoord": ww, "vorm": gekozenVorm,
            ])
            await MainActor.run {
                bezig = false
                if let r, r.ok {
                    maakOk = true
                    maakMelding = "Kluis gemaakt: \(r.data["kluis"] as? String ?? "?")"
                    laadLijst()
                } else {
                    maakOk = false
                    maakMelding = r?.fout ?? "Kluis maken mislukt."
                }
            }
        }
    }

    private func open() {
        openMelding = nil
        var invoer: [String: Any] = ["kluis": openKluisPad]
        if gebruikKeychain {
            invoer["keychain"] = true
        } else {
            invoer["wachtwoord"] = openWachtwoord
        }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "vaultopen", invoer: invoer)
            await MainActor.run {
                if let r, r.ok {
                    openOk = true
                    openMelding = "Open: \(r.data["mount"] as? String ?? "?")"
                    laadLijst()
                } else {
                    openOk = false
                    openMelding = r?.fout ?? "Openen mislukt."
                }
            }
        }
    }

    private func sluitMount(_ pad: String) {
        // Bij een open kluis hoort het mountpunt: zoek de match op naam.
        let naam = ((pad as NSString).lastPathComponent as NSString).deletingPathExtension
        guard let mount = openMounts.first(where: { $0.lowercased().contains(naam.lowercased()) }) else { return }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "vaultsluit", invoer: ["mount": mount])
            await MainActor.run { if let r, r.ok { laadLijst() } }
        }
    }

    private func sluitAlles() {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "vaultsluit", invoer: ["alles": true])
            await MainActor.run { if let r, r.ok { laadLijst() } }
        }
    }
}
