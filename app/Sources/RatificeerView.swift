// Ratificatie-scherm — wachtende stappen in bulk goedkeuren of afkeuren mét reden.

import SwiftUI

struct RatificeerView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    @State private var boomPad = ""
    @State private var wachtend: [String] = []
    @State private var afgekeurd: Set<String> = []
    @State private var reden = ""
    @State private var verwerkt: [[String: Any]] = []
    @State private var fout: String?
    @State private var melding: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                kop
                zoekrij
                if let melding { tekstKaart("Melding", melding) }
                if !wachtend.isEmpty { wachtendeKaart }
                if !verwerkt.isEmpty { verwerktKaart }
                if let fout { foutKaart(fout) }
                Spacer()
            }
            .padding(28)
        }
        .background(Thema.kleur(.papier))
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("RATIFICATIE").font(Thema.tekst(10, gewicht: .semibold)).tracking(4).foregroundStyle(Thema.kleur(.zacht))
            Text("De mens heeft de laatste stem").font(Thema.display(30))
        }
    }

    private var zoekrij: some View {
        HStack(spacing: 10) {
            TextField("Pad naar de boom", text: $boomPad)
                .textFieldStyle(.plain).font(Thema.tekst(13)).padding(10)
                .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
            knop("Laad wachtende stappen") { laad() }
        }
    }

    private var wachtendeKaart: some View {
        Kaart(kop: "Wacht op ratificatie (§9)") {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(wachtend, id: \.self) { stap in
                    HStack {
                        Text(stap).font(Thema.display(14))
                        Spacer()
                        Toggle("afkeuren", isOn: Binding(
                            get: { afgekeurd.contains(stap) },
                            set: { if $0 { afgekeurd.insert(stap) } else { afgekeurd.remove(stap) } }))
                            .font(Thema.tekst(11)).toggleStyle(.checkbox)
                    }
                    .padding(.vertical, 9)
                    .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
                }
                TextField("Reden bij afkeuring (verplicht als je iets afkeurt)", text: $reden)
                    .textFieldStyle(.plain).font(Thema.tekst(13)).padding(8)
                    .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                    .padding(.top, 12)
                HStack {
                    knop("Ratificeer") { verwerk() }
                    Text("niet-afgekeurde stappen worden geratificeerd")
                        .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                }.padding(.top, 14)
            }
        }
    }

    private var verwerktKaart: some View {
        Kaart(kop: "Verwerkt (append-only)") {
            VStack(alignment: .leading, spacing: 6) {
                ForEach(verwerkt.indices, id: \.self) { i in
                    let entry = verwerkt[i]
                    HStack {
                        Text(entry["stap"] as? String ?? "?").font(Thema.display(14))
                        Spacer()
                        StatusBadge(tekst: entry["status"] as? String ?? "?",
                                    bewezen: entry["status"] as? String == "geratificeerd")
                    }
                }
            }
        }
    }

    private func tekstKaart(_ kopTekst: String, _ inhoud: String) -> some View {
        Kaart(kop: kopTekst) {
            Text(inhoud).font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
        }
    }

    private func foutKaart(_ tekst: String) -> some View {
        Kaart(kop: "Fout") { Text(tekst).font(Thema.tekst(13, gewicht: .medium)) }
    }

    private func knop(_ titel: String, actie: @escaping () -> Void) -> some View {
        Button(action: actie) {
            Text(titel).font(Thema.tekst(12, gewicht: .medium))
                .padding(.horizontal, 18).padding(.vertical, 10)
        }
        .buttonStyle(.plain)
        .background(Thema.kleur(.inkt))
        .foregroundStyle(Thema.kleur(.papier))
        .clipShape(Capsule())
    }

    private func laad() {
        fout = nil
        melding = nil
        verwerkt = []
        Task {
            let resultaat = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                                   commando: "ratificeer", invoer: ["doel": boomPad])
            await MainActor.run {
                wachtend = resultaat?.data["stappen"] as? [String] ?? []
                if wachtend.isEmpty { melding = "Geen ratificatie-moment — geen stappen wachten op de mens." }
            }
        }
    }

    private func verwerk() {
        fout = nil
        let afkeurEntries: [[String: String]] = wachtend
            .filter { afgekeurd.contains($0) }
            .map { ["stap_id": $0, "reden": reden.trimmingCharacters(in: .whitespaces)] }
        if !afkeurEntries.isEmpty && reden.trimmingCharacters(in: .whitespaces).isEmpty {
            fout = "Afkeuren vereist een reden — zonder reden bestaat de afkeur niet."
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
