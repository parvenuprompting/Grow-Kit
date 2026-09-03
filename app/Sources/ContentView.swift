// Hoofdmenu — de vijf modi van het harnas; v1: status, planten, ratificatie.

import SwiftUI

struct ContentView: View {
    @StateObject private var runner = Runner()
    @AppStorage("growkitRepoPad") private var repoPad = Runner.standaardRepoPad
    @AppStorage("growkitInterpreter") private var interpreter = Runner.standaardInterpreter

    enum Modi: String, CaseIterable, Identifiable {
        case status = "Status"
        case planten = "Planten"
        case ratificatie = "Ratificatie"
        case hervatten = "Hervatten"
        case taak = "Taak"

        var id: String { rawValue }
        var beschrijving: String {
            switch self {
            case .status: return "Identiteit, register, tellers, logboek"
            case .planten: return "Concept → bevestiging → motor met bewijs"
            case .ratificatie: return "Mens-momenten in bulk goedkeuren of afkeuren"
            case .hervatten: return "Restdraai vanuit het logboek (fase 6.1)"
            case .taak: return "Taken uit de groeilaag uitvoeren (fase 6.1)"
            }
        }
        var actiefInV1: Bool { self != .hervatten && self != .taak }
    }

    @State private var geselecteerd: Modi = .status

    var body: some View {
        NavigationSplitView {
            List(Modi.allCases, selection: $geselecteerd) { modus in
                rij(modus)
            }
            .listStyle(.sidebar)
            .navigationTitle("GrowKit")
        } detail: {
            detail
        }
        .onAppear { Thema.registreerFonts() }
    }

    private func rij(_ modus: Modi) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(modus.rawValue).font(Thema.display(17))
                Text(modus.beschrijving)
                    .font(Thema.tekst(11))
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
            Spacer()
            if !modus.actiefInV1 {
                Text("6.1").font(Thema.tekst(10, gewicht: .semibold))
                    .padding(.horizontal, 8).padding(.vertical, 3)
                    .overlay(Capsule().stroke(Thema.kleur(.lijn)))
            }
        }
        .contentShape(Rectangle())
        .opacity(modus.actiefInV1 ? 1 : 0.45)
        .onTapGesture { if modus.actiefInV1 { geselecteerd = modus } }
    }

    @ViewBuilder
    private var detail: some View {
        switch geselecteerd {
        case .status:
            StatusView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
        case .planten:
            PlantView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
        case .ratificatie:
            RatificeerView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
        case .hervatten, .taak:
            tekstPane("Deze modus volgt in fase 6.1 — gebruik voor nu loop.py in de terminal.")
        }
    }

    private func tekstPane(_ tekst: String) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Nog niet gebouwd").font(Thema.display(28))
            Text(tekst).font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
            Spacer()
        }
        .padding(28)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
