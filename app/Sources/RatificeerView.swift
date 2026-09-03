// Ratificatie-scherm — wachtende stappen in bulk goedkeuren of afkeuren mét reden.
// Editorial Monochrome · Zero-Trust Harnas

import SwiftUI

struct RatificeerView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    var metScroll: Bool = true

    @State private var boomPad = ""
    @State private var wachtend: [String] = []
    @State private var afgekeurd: Set<String> = []
    @State private var reden = ""
    @State private var verwerkt: [[String: Any]] = []
    @State private var fout: String?
    @State private var melding: String?
    @State private var heeftGeladen = false

    var body: some View {
        groep
            .background(Thema.kleur(.papier))
    }

    // ImageRenderer rendert ScrollView leeg; het render-bewijs gebruikt
    // daarom dezelfde inhoud zonder scroll-container (metScroll: false).
    @ViewBuilder private var groep: some View {
        if metScroll { ScrollView { inhoudView } } else { inhoudView }
    }

    @ViewBuilder private var inhoudView: some View {
        VStack(alignment: .leading, spacing: 22) {
            kop
            StappenStreep(stappen: ["Zoekpad", "Wachtende stappen", "Curatie", "Append-only"],
                          actieveIndex: stappenIndex)
            zoekrij
            if runner.bezig { laadIndicator }
            if let fout { foutKaart(fout) }

            if !heeftGeladen && wachtend.isEmpty && verwerkt.isEmpty {
                LegeStaat(kop: "Curatie & Ratificatie (§9)",
                          tekst: "De AI kan voorstellen doen of stappen uitvoeren, maar beslist nooit zelf over de definitieve afronding. Vul een boompad in om openstaande mens-momenten op te vragen.",
                          regels: ["stappen met status 'review_ok_wacht_ratificatie' wachten op bekrachtiging",
                                   "niet-afgekeurde stappen worden in één klik geratificeerd",
                                   "afkeuring vereist altijd een inhoudelijke reden conform het faalcontract",
                                   "afkeuring leidt tot 'herziening_nodig' in het append-only logboek, nooit rollback"])
            }

            if let melding { tekstKaart("Curatie-status", melding) }
            if !wachtend.isEmpty { wachtendeKaart }
            if !verwerkt.isEmpty { verwerktKaart }

            Spacer(minLength: 16)
        }
        .padding(28)
    }

    private var stappenIndex: Int {
        if !verwerkt.isEmpty { return 3 }
        if !afgekeurd.isEmpty { return 2 }
        if !wachtend.isEmpty { return 1 }
        return 0
    }

    // MARK: - Kop & Zoekrij

    private var kop: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("03 RATIFICATIE · CURATIE §9")
                .font(Thema.tekst(10, gewicht: .semibold))
                .tracking(3)
                .foregroundStyle(Thema.kleur(.gedempt))
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text("De mens heeft de ").font(Thema.display(30))
                Text("laatste stem.").font(Thema.display(30, cursief: true)).foregroundStyle(Thema.kleur(.zacht))
            }
            Text("De machine stelt voor of toetst; alleen de mens ratificeert of wijst af mét reden.")
                .font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.zacht))
        }
    }

    private var zoekrij: some View {
        HStack(spacing: 12) {
            HStack {
                Image(systemName: "folder")
                    .font(.system(size: 13))
                    .foregroundStyle(Thema.kleur(.gedempt))
                TextField("Pad naar de boom, bijv. ~/mijn-brein", text: $boomPad,
                          prompt: Text("Pad naar de boom, bijv. ~/mijn-brein")
                              .font(Thema.tekst(13)).foregroundColor(Thema.kleur(.zacht)))
                    .textFieldStyle(.plain)
                    .font(Thema.tekst(13))
                    .foregroundStyle(Thema.kleur(.inkt))
            }
            .padding(10)
            .overlay(Rectangle().stroke(Thema.kleur(.lijn), lineWidth: 1))
            .background(Thema.kleur(.papierZacht))

            PillKnop(titel: "Laad wachtende stappen", gevuld: true) { laad() }
        }
    }

    private var laadIndicator: some View {
        HStack(spacing: 8) {
            ProgressView().controlSize(.small)
            Text("De adapter controleert wachtende stappen in het logboek…")
                .font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.gedempt))
        }
        .padding(.vertical, 4)
    }

    // MARK: - Wachtende Stappen

    private var wachtendeKaart: some View {
        Kaart(kop: "Wacht op ratificatie (§9)", rechterKop: "\(wachtend.count) wachtend") {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(wachtend, id: \.self) { stap in
                    let isAfgekeurd = afgekeurd.contains(stap)
                    HStack(alignment: .center) {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(stap)
                                .font(Thema.tekst(13, gewicht: .medium))
                                .monospacedDigit()
                            Text("Machine-status: review_ok — wacht op menselijke bekrachtiging")
                                .font(Thema.tekst(11))
                                .foregroundStyle(Thema.kleur(.zacht))
                        }
                        Spacer()
                        Toggle("Afkeuren", isOn: Binding(
                            get: { isAfgekeurd },
                            set: { if $0 { afgekeurd.insert(stap) } else { afgekeurd.remove(stap) } }))
                            .font(Thema.tekst(11, gewicht: .medium))
                            .toggleStyle(.checkbox)
                    }
                    .padding(.vertical, 11)
                    .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
                }

                if !afgekeurd.isEmpty {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text("REDEN VOOR AFKEURING")
                                .font(Thema.tekst(9, gewicht: .semibold))
                                .tracking(1.5)
                                .foregroundStyle(Thema.kleur(.inkt))
                            Text("(verplicht bij afkeur)")
                                .font(Thema.tekst(9))
                                .foregroundStyle(Thema.kleur(.gedempt))
                        }
                        TextField("Beschrijf waarom deze stap niet akkoord is…", text: $reden,
                                  prompt: Text("Beschrijf waarom deze stap niet akkoord is…")
                                      .font(Thema.tekst(13)).foregroundColor(Thema.kleur(.zacht)))
                            .textFieldStyle(.plain)
                            .font(Thema.tekst(13))
                            .foregroundStyle(Thema.kleur(.inkt))
                            .padding(10)
                            .overlay(Rectangle().stroke(Thema.kleur(.inkt), lineWidth: 1))
                            .background(Thema.kleur(.papierZacht))
                    }
                    .padding(.top, 16)
                }

                HStack(spacing: 14) {
                    PillKnop(titel: afgekeurd.isEmpty ? "Ratificeer alle stappen" : "Verwerk curatie",
                             gevuld: true) { verwerk() }

                    Text(afgekeurd.isEmpty ? "alle stappen worden gemarkeerd als 'geratificeerd'" : "geselecteerde stappen krijgen 'herziening_nodig'")
                        .font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
                .padding(.top, 16)
            }
        }
    }

    // MARK: - Verwerkte Stappen

    private var verwerktKaart: some View {
        Kaart(kop: "Verwerkt in Logboek", rechterKop: "Append-only") {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(verwerkt.indices, id: \.self) { i in
                    let entry = verwerkt[i]
                    let status = entry["status"] as? String ?? "?"
                    let stap = entry["stap"] as? String ?? "?"
                    HStack {
                        Text(stap)
                            .font(Thema.tekst(13, gewicht: .medium))
                            .monospacedDigit()
                        Spacer()
                        StatusBadge(tekst: status == "geratificeerd" ? "✓ Geratificeerd" : "Herziening nodig",
                                    stijl: status == "geratificeerd" ? .bewezen : .herziening)
                    }
                    .padding(.vertical, 10)
                    .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
                }
                Text("De beslissing is onomkeerbaar toegevoegd aan logboek.json — geen rollback.")
                    .font(Thema.tekst(11))
                    .foregroundStyle(Thema.kleur(.gedempt))
                    .padding(.top, 12)
            }
        }
    }

    private func tekstKaart(_ kopTekst: String, _ inhoud: String) -> some View {
        Kaart(kop: kopTekst, rechterKop: "Rust") {
            HStack(spacing: 12) {
                Image(systemName: "checkmark.circle")
                    .font(.system(size: 15))
                Text(inhoud)
                    .font(Thema.tekst(13))
                    .foregroundStyle(Thema.kleur(.zacht))
            }
        }
    }

    private func foutKaart(_ tekst: String) -> some View {
        Kaart(kop: "Fout", rechterKop: "Faalcontract §7") {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "exclamationmark.triangle")
                    .font(.system(size: 14))
                Text(tekst)
                    .font(Thema.tekst(13, gewicht: .medium))
            }
        }
    }

    // MARK: - Adapter Aanroepen

    private func laad() {
        fout = nil
        melding = nil
        verwerkt = []
        heeftGeladen = true
        Task {
            let resultaat = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                                   commando: "ratificeer", invoer: ["doel": boomPad])
            await MainActor.run {
                wachtend = resultaat?.data["stappen"] as? [String] ?? []
                if wachtend.isEmpty {
                    melding = "Geen ratificatie-moment — er wachten momenteel geen stappen op de mens."
                }
            }
        }
    }

    private func verwerk() {
        fout = nil
        let afkeurEntries: [[String: String]] = wachtend
            .filter { afgekeurd.contains($0) }
            .map { ["stap_id": $0, "reden": reden.trimmingCharacters(in: .whitespaces)] }
        if !afkeurEntries.isEmpty && reden.trimmingCharacters(in: .whitespaces).isEmpty {
            fout = "Afkeuren vereist een reden — zonder inhoudelijke reden bestaat de afkeur niet."
            return
        }
        Task {
            let resultaat = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                                   commando: "ratificeer",
                                                   invoer: ["doel": boomPad, "bevestig": true,
                                                            "afkeur": afkeurEntries])
            await MainActor.run {
                verwerkt = resultaat?.data["verwerkt"] as? [[String: Any]] ?? []
                wachtend = []
                afgekeurd = []
                reden = ""
            }
        }
    }
}
