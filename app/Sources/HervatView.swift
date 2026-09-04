// HervatView — crash-herstel in beeld: reconstructie uit het logboek,
// restdraai tonen, met jouw bevestiging pas hervatten.
// Bedienaar-principe: de app beslist niets — adapter `hervat` + de kern
// (growkit_hervat + motor) bepalen wat er mag.

import SwiftUI

struct HervatView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    @AppStorage("growkitBoomPad") private var boomPad = ""

    @State private var scan: ScanResultaat?
    @State private var bezig = false
    @State private var draait = false
    @State private var uitvoerTekst = ""

    struct ScanResultaat {
        var herstartpunt: String
        var restdraai: [String]
        var stappen: [String: Any]
        var melding: String?
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                kop
                boomPadVeld
                if bezig { Text("Bezig…").font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht)) }
                if let scan { scanKaart(scan) }
                if draait { uitvoerKaart }
            }
            .padding(24)
        }
        .background(Thema.kleur(.papier))
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Hervatten").font(Thema.display(30))
            Text("Na een crash of stop bouwt het harnas de toestand opnieuw op uit het append-only logboek. Niet-idempotente stappen worden nooit opnieuw gedraaid — wat al bewezen is, blijft bewezen.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var boomPadVeld: some View {
        Kaart(kop: "Boom", rechterKop: "DOEL-MAP") {
            TextField("bijv. ~/mijn-brein", text: $boomPad)
                .textFieldStyle(.plain).font(Thema.tekst(13)).padding(10)
                .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                .background(Thema.kleur(.papierZacht))
            HStack {
                PillKnop(titel: "1 · Analyseer", gevuld: false) { analyseer() }
                PillKnop(titel: "2 · Hervat restdraai", gevuld: scan != nil) { hervat() }
                if bezig { ProgressView().scaleEffect(0.7) }
            }
            .padding(.top, 8)
        }
    }

    private func scanKaart(_ s: ScanResultaat) -> some View {
        Kaart(kop: "Reconstructie", rechterKop: "UIT HET LOGBOEK") {
            VStack(alignment: .leading, spacing: 10) {
                if let melding = s.melding {
                    Text(melding).font(Thema.tekst(13, gewicht: .semibold))
                } else {
                    HStack {
                        Text("Herstartpunt").font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                        Spacer()
                        StatusBadge(tekst: s.herstartpunt, stijl: .bewezen)
                    }
                    if s.restdraai.isEmpty {
                        Text("Niets te hervatten — alle stappen zijn geslaagd of wachten op ratificatie.")
                            .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                    } else {
                        Text("Restdraai (\(s.restdraai.count) stappen):").font(Thema.tekst(12, gewicht: .semibold))
                        ForEach(s.restdraai, id: \.self) { id in
                            HStack(spacing: 8) {
                                StatusBadge(tekst: "HERAANBIEDEN", stijl: .herziening)
                                Text(id).font(Thema.tekst(12))
                            }
                        }
                        Text("Stap 2 hervat alleen deze stappen — met jouw bevestiging hierboven.")
                            .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                    }
                }
            }
        }
    }

    private var uitvoerKaart: some View {
        Kaart(kop: "Uitvoering", rechterKop: "LIVE") {
            Text(uitvoerTekst.isEmpty ? "gestart…" : uitvoerTekst)
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
        }
    }

    // MARK: acties

    private func analyseer() {
        let doel = boomPad.trimmingCharacters(in: .whitespaces)
        guard !doel.isEmpty else { return }
        bezig = true; scan = nil
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "hervat", invoer: ["doel": doel])
            await MainActor.run {
                bezig = false
                guard let r, r.ok else {
                    scan = ScanResultaat(herstartpunt: "fout", restdraai: [], stappen: [:],
                                         melding: r?.fout ?? "adapter reageerde niet")
                    return
                }
                if let m = r.data["melding"] as? String {
                    scan = ScanResultaat(herstartpunt: "compleet", restdraai: [], stappen: [:], melding: m)
                    return
                }
                scan = ScanResultaat(
                    herstartpunt: r.data["herstartpunt"] as? String ?? "?",
                    restdraai: r.data["restdraai"] as? [String] ?? [],
                    stappen: r.data["stappen"] as? [String: Any] ?? [:],
                    melding: nil)
            }
        }
    }

    private func hervat() {
        let doel = boomPad.trimmingCharacters(in: .whitespaces)
        guard !doel.isEmpty, scan != nil, !(scan?.restdraai.isEmpty ?? true) else { return }
        bezig = true; draait = true; uitvoerTekst = ""
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "hervat",
                                           invoer: ["doel": doel, "bevestig": true],
                                           timeOut: 600)
            await MainActor.run {
                bezig = false
                if let data = r?.data["melding"] as? String {
                    uitvoerTekst = data
                } else if let stappen = r?.stappen, !stappen.isEmpty {
                    uitvoerTekst = stappen.map { s in
                        "[\(s["status"] as? String ?? "?")] \(s["stap"] as? String ?? "?") — \(s["bewijs"] as? String ?? "")"
                    }.joined(separator: "\n")
                } else {
                    uitvoerTekst = r?.fout ?? "klaar"
                }
                // na een hervat-draai opnieuw analyseren voor de actuele stand
                analyseer()
            }
        }
    }
}
