// ModelDropdown — actuele modellen kiezen uit een dropdown met zoekveld.
//
// De lijst komt via adapter `models` (OpenRouter /models, 15 min gecached,
// fail-open op verlopen cache). De gebruiker kiest; of typt handmatig als
// de provider onbereikbaar is. De app interpreteert niets — hij toont.

import SwiftUI

struct ModelDropdown: View {
    @Binding var model: String
    @ObservedObject var runner: Runner
    let repoPad: String
    let interpreter: String

    @State private var modellen: [[String: Any]] = []
    @State private var bron = "laden…"
    @State private var melding: String?
    @State private var zoek = ""
    @State private var open = false
    @State private var bezig = false

    private var gefilterd: [[String: Any]] {
        let q = zoek.trimmingCharacters(in: .whitespaces).lowercased()
        guard !q.isEmpty else { return modellen }
        return modellen.filter { m in
            ((m["id"] as? String) ?? "").lowercased().contains(q)
                || ((m["naam"] as? String) ?? "").lowercased().contains(q)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text("MODEL (ACTUEEL)")
                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                    .foregroundStyle(Thema.kleur(.gedempt))
                Spacer()
                Text(bronLabel)
                    .font(Thema.tekst(9)).tracking(1)
                    .foregroundStyle(Thema.kleur(.gedempt))
                Button(action: { laad(vernieuw: true) }) {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(Thema.kleur(.zacht))
                }
                .buttonStyle(.plain)
                .help("Ververs de modellenlijst")
            }

            // Het veld: typen kan altijd (handmatige id), klikken opent de lijst.
            HStack(spacing: 8) {
                TextField("kies uit de lijst of typ een model-id",
                          text: $model,
                          onEditingChanged: { edit in if edit { open = true } })
                    .foregroundStyle(Thema.kleur(.inkt))
                    .textFieldStyle(.plain).font(Thema.tekst(13))
                Image(systemName: open ? "chevron.up" : "chevron.down")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
            .padding(10)
            .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
            .background(Thema.kleur(.papierZacht))
            .onTapGesture { open.toggle() }

            if open {
                VStack(alignment: .leading, spacing: 0) {
                    TextField("zoek in \(modellen.count) modellen…", text: $zoek)
                        .foregroundStyle(Thema.kleur(.inkt))
                        .textFieldStyle(.plain).font(Thema.tekst(12))
                        .padding(8)
                        .overlay(alignment: .bottom) {
                            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
                        }
                    if let melding {
                        Text(melding).font(Thema.tekst(11))
                            .foregroundStyle(Thema.kleur(.gedempt))
                            .padding(8)
                    }
                    ScrollView {
                        VStack(alignment: .leading, spacing: 0) {
                            ForEach(Array(gefilterd.prefix(60).enumerated()), id: \.offset) { _, m in
                                modelRij(m)
                            }
                            if gefilterd.count > 60 {
                                Text("… nog \(gefilterd.count - 60) — verfijn met het zoekveld")
                                    .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                                    .padding(8)
                            }
                        }
                    }
                    .frame(maxHeight: 220)
                }
                .background(Thema.kleur(.papier))
                .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
            }
        }
        .onAppear { if modellen.isEmpty { laad(vernieuw: false) } }
    }

    private var bronLabel: String {
        switch bron {
        case "live": return "ACTUEEL"
        case "cache": return "GE cachet"
        default: return bron.uppercased()
        }
    }

    private func modelRij(_ m: [String: Any]) -> some View {
        let id = m["id"] as? String ?? ""
        let naam = m["naam"] as? String ?? ""
        let context = m["context"] as? Int ?? 0
        let prijs = m["prijs_prompt"] as? Double ?? 0
        return VStack(alignment: .leading, spacing: 1) {
            HStack {
                Text(naam).font(Thema.tekst(12, gewicht: .semibold))
                Spacer()
                if id == model { StatusBadge(tekst: "gekozen", bewezen: true) }
            }
            HStack(spacing: 10) {
                Text(id).font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.zacht))
                if context > 0 {
                    Text("\(context / 1000)k context").font(Thema.tekst(10))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
                if prijs > 0 {
                    Text("$\(String(format: "%.2f", prijs))/1M in").font(Thema.tekst(10))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
            }
        }
        .padding(.horizontal, 10).padding(.vertical, 6)
        .contentShape(Rectangle())
        .onTapGesture {
            model = id
            open = false
            zoek = ""
        }
        .overlay(alignment: .bottom) {
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
        }
    }

    private func laad(vernieuw: Bool) {
        bezig = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "models",
                                           invoer: ["doel": "~/growkit-governor",
                                                    "vernieuw": vernieuw])
            await MainActor.run {
                bezig = false
                guard let r, r.ok else {
                    melding = r?.fout ?? "adapter reageerde niet — typ de model-id handmatig"
                    bron = "onbereikbaar"
                    return
                }
                modellen = r.data["modellen"] as? [[String: Any]] ?? []
                bron = r.data["bron"] as? String ?? "?"
                melding = r.data["melding"] as? String
            }
        }
    }
}
