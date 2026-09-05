// Hervat-scherm — restdraai vanuit het logboek, met poortjes.
// Eerst tonen wat de reconstructie zegt (herstartpunt, per stap beslissing),
// pas na menselijke bevestiging draait de motor verder. De app interpreteert
// niets: alles via adapter `hervat`.

import SwiftUI

struct HervatView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    var metScroll: Bool = true

    @State private var boomPad = ""
    @State private var geladen = false
    @State private var fout: String?
    @State private var herstartpunt = ""
    @State private var stappen: [[String: Any]] = []
    @State private var restdraai: [String] = []
    @State private var melding: String?
    @State private var draaiLog: [String] = []

    var body: some View {
        groep
            .background(Thema.kleur(.papier))
    }

    @ViewBuilder private var groep: some View {
        if metScroll { ScrollView { inhoudView } } else { inhoudView }
    }

    private var inhoudView: some View {
        VStack(alignment: .leading, spacing: 22) {
            kop
            padVeld
            if let fout { foutKaart(fout) }
            if geladen && fout == nil { overzicht }
            if let melding { meldingKaart(melding) }
            if !draaiLog.isEmpty { draaiKaart }
            Spacer(minLength: 16)
        }
        .padding(28)
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Hervatten").font(Thema.display(30))
            Text("Na een crash of stilgevallen zet dit scherm de draai voort vanuit het logboek. De app stelt voor; jij bevestigt; de motor herhaalt nooit een niet-idempotente stap.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var padVeld: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 4) {
                Text("BOOM-PAD")
                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                    .foregroundStyle(Thema.kleur(.gedempt))
                Veld(placeholder: "~/mijn-brein", tekst: $boomPad)
                    .padding(10)
                    .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                    .background(Thema.kleur(.papierZacht))
            }
            PillKnop(titel: "Laad reconstructie") { laad() }
        }
    }

    private var overzicht: some View {
        Kaart(kop: "Reconstructie uit het logboek",
              rechterKop: restdraai.isEmpty ? "NIETS TE HERVATTEN" : "\(restdraai.count) STAPPEN") {
            VStack(alignment: .leading, spacing: 12) {
                if !herstartpunt.isEmpty {
                    Text("Herstartpunt: \(herstartpunt)").font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.zacht))
                }
                ForEach(Array(stappen.enumerated()), id: \.offset) { _, s in
                    stapRij(s)
                }
                if !restdraai.isEmpty {
                    PillKnop(titel: "Restdraai bevestigen (\(restdraai.count) stappen)", gevuld: true) {
                        hervat()
                    }
                    Text("Pas na jouw bevestiging voert de motor iets uit — faalcontract onaangetast.")
                        .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                }
            }
        }
    }

    private func stapRij(_ s: [String: Any]) -> some View {
        let id = (s["id"] as? String) ?? "?"
        let beslissing = (s["beslissing"] as? String) ?? "?"
        return HStack {
            Text(id).font(Thema.tekst(12, gewicht: .semibold))
            Spacer()
            StatusBadge(tekst: beslissingLabel(beslissing), stijl: badge(beslissing))
        }
    }

    private func beslissingLabel(_ b: String) -> String {
        switch b {
        case "geslaagd": return "GESLAAGD"
        case "heraanbieden", "uitvoeren": return "HERAANBIEDEN"
        case "wacht_goedkeuringen": return "WACHT RATIFICATIE"
        case "overslaan": return "OVERSLAAN"
        default: return b.uppercased()
        }
    }

    private func badge(_ b: String) -> BadgeStijl {
        switch b {
        case "geslaagd": return .bewezen
        case "heraanbieden", "uitvoeren": return .mens
        default: return .neutraal
        }
    }

    private var draaiKaart: some View {
        Kaart(kop: "Motor-uitvoer", rechterKop: "RESTDRAAI") {
            VStack(alignment: .leading, spacing: 6) {
                ForEach(Array(draaiLog.enumerated()), id: \.offset) { _, regel in
                    Text(regel).font(Thema.tekst(11))
                }
            }
        }
    }

    private func foutKaart(_ tekst: String) -> some View {
        Kaart(kop: "Let op", gestippeld: true) {
            Text(tekst).font(Thema.tekst(12))
        }
    }

    private func meldingKaart(_ tekst: String) -> some View {
        Kaart(kop: "Melding") {
            Text(tekst).font(Thema.tekst(12))
        }
    }

    // MARK: Acties — via de adapter, nooit eromheen

    private func vul(_ data: [String: Any]) {
        herstartpunt = data["herstartpunt"] as? String ?? ""
        stappen = data["stappen"] as? [[String: Any]] ?? []
        restdraai = data["restdraai"] as? [String] ?? []
        melding = data["melding"] as? String
    }

    private func laad() {
        let doel = boomPad.trimmingCharacters(in: .whitespaces)
        guard !doel.isEmpty else { fout = "Vul eerst het pad naar de boom."; return }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "hervat",
                                           invoer: ["doel": doel, "bevestig": false])
            await MainActor.run {
                geladen = true
                guard let r, r.ok else {
                    fout = r?.fout ?? "adapter reageerde niet — controleer Instellingen"
                    return
                }
                fout = nil
                vul(r.data)
            }
        }
    }

    private func hervat() {
        let doel = boomPad.trimmingCharacters(in: .whitespaces)
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "hervat",
                                           invoer: ["doel": doel, "bevestig": true])
            await MainActor.run {
                guard let r else { fout = "adapter reageerde niet"; return }
                if let m = r.data["melding"] as? String { melding = m; return }
                if let fouttekst = r.fout { draaiLog.append("✕ " + fouttekst); return }
                if let uitvoer = r.data["stappen"] as? [[String: Any]] {
                    for st in uitvoer {
                        let sid = (st["id"] as? String) ?? "?"
                        let stt = (st["status"] as? String) ?? "?"
                        draaiLog.append((stt == "geslaagd" ? "✓ " : "✕ ") + sid + " — " + stt)
                    }
                }
                laad()
            }
        }
    }
}