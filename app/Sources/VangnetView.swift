// VangnetView — de opvanglaag in beeld: wat is er vanzelf opgevangen?
// Alleen lezen. Het vangnet vangt zonder dat iemand iets doet; dit scherm
// maakt dat geloofwaardig en controleerbaar (Vangnet-ontwerp, fase 1).

import SwiftUI

struct VangnetView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    @AppStorage("growkitBoomPad") private var boomPad = ""

    @State private var bestaat = false
    @State private var totaal = 0
    @State private var perBron: [[String: Any]] = []
    @State private var recente: [[String: Any]] = []
    @State private var geladen = false
    @State private var bezig = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                kop
                boomPadVeld
                if geladen { tellingen }
                if geladen { recenteKaart }
                uitleg
            }
            .padding(24)
        }
        .background(Thema.kleur(.papier))
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Vangnet").font(Thema.display(30))
            Text("Elke modelaanroep en elke stap-uitkomst in deze boom wordt vanzelf vastgelegd — zonder dat iemand iets bijhoudt. Fail-open: faalt het vangnet, dan merkt de loop er niets van. Secrets worden gehasht vóór opslag.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var boomPadVeld: some View {
        Kaart(kop: "Boom", rechterKop: "DOEL-MAP") {
            HStack {
                TextField("bijv. ~/mijn-brein", text: $boomPad)
                    .textFieldStyle(.plain).font(Thema.tekst(13)).padding(10)
                    .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                    .background(Thema.kleur(.papierZacht))
                PillKnop(titel: "Laad") { laad() }
                if bezig { ProgressView().scaleEffect(0.7) }
            }
        }
    }

    private var tellingen: some View {
        Kaart(kop: "Opgevangen", rechterKop: bestaat ? "\(totaal) VANGSTEN" : "NOG GEEN") {
            if !bestaat {
                Text("Nog geen vangnet in deze boom — het ontstaat vanzelf zodra de motor stappen of reviews uitvoert.")
                    .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
            } else {
                HStack(spacing: 28) {
                    ForEach(Array(perBron.enumerated()), id: \.offset) { _, rij in
                        VStack(alignment: .leading, spacing: 3) {
                            Text("\(rij["aantal"] as? Int ?? 0)").font(Thema.display(30))
                            Text((rij["bron"] as? String ?? "").uppercased())
                                .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                                .foregroundStyle(Thema.kleur(.gedempt))
                        }
                    }
                    Spacer()
                }
            }
        }
    }

    private var recenteKaart: some View {
        Kaart(kop: "Recente vangsten", rechterKop: "LAATSTE 20") {
            if recente.isEmpty {
                Text("Nog niets opgevangen.").font(Thema.tekst(12))
                    .foregroundStyle(Thema.kleur(.gedempt))
            } else {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(recente.enumerated()), id: \.offset) { _, r in
                        vangstRij(r)
                    }
                }
            }
        }
    }

    private func vangstRij(_ r: [String: Any]) -> some View {
        let ts = (r["ts"] as? String ?? "").replacingOccurrences(of: "T", with: " ")
        let bron = r["bron"] as? String ?? "?"
        let taak = r["taak"] as? String ?? "—"
        let oordeel = r["oordeel"] as? String ?? "—"
        return HStack(spacing: 12) {
            Text(String(ts.suffix(8)))
                .font(Thema.tekst(10)).tracking(0.5)
                .foregroundStyle(Thema.kleur(.gedempt))
                .frame(width: 62, alignment: .leading)
            StatusBadge(tekst: bron, stijl: bron == "review" ? .mens : .neutraal)
            Text(taak).font(Thema.tekst(12))
            Spacer()
            Text(oordeel).font(Thema.tekst(11))
                .foregroundStyle(oordeel.contains("gefaald") ? Thema.kleur(.inkt) : Thema.kleur(.zacht))
        }
        .padding(.vertical, 5)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
        }
    }

    private var uitleg: some View {
        Kaart(kop: "Waar het heen gaat", gestippeld: true) {
            Text("Fase 2 van het Vangnet-ontwerp leidt hier labels uit af (signaalbronnen: goedgekeurde voorstellen, git-correcties, test-uitkomsten). Dan wordt dit logboek een trainingsset — met je minuut per dag alleen waar de automaat twijfelt.")
                .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func laad() {
        let doel = boomPad.trimmingCharacters(in: .whitespaces)
        guard !doel.isEmpty else { return }
        bezig = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "vangnet", invoer: ["doel": doel])
            await MainActor.run {
                bezig = false; geladen = true
                bestaat = r?.data["bestaat"] as? Bool ?? false
                totaal = r?.data["totaal"] as? Int ?? 0
                perBron = r?.data["per_bron"] as? [[String: Any]] ?? []
                recente = r?.data["recente"] as? [[String: Any]] ?? []
            }
        }
    }
}
