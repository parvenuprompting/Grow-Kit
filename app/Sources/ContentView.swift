// Hoofdmenu — de vijf modi van het harnas in de editorial-stijl van de mockups.

import SwiftUI

struct ContentView: View {
    @StateObject private var runner = Runner()
    @AppStorage("growkitRepoPad") private var repoPad = Runner.standaardRepoPad
    @AppStorage("growkitInterpreter") private var interpreter = Runner.standaardInterpreter

    enum Modi: Int, CaseIterable, Identifiable {
        case status, planten, ratificatie, hervatten, taak

        var id: Int { rawValue }
        var nummer: String { String(format: "%02d", rawValue + 1) }
        var naam: String {
            switch self {
            case .status: return "Status"
            case .planten: return "Planten"
            case .ratificatie: return "Ratificatie"
            case .hervatten: return "Hervatten"
            case .taak: return "Taak"
            }
        }
        var beschrijving: String {
            switch self {
            case .status: return "Identiteit, register, tellers, logboek"
            case .planten: return "Concept → bevestiging → motor met bewijs"
            case .ratificatie: return "Mens-momenten in bulk goedkeuren of afkeuren"
            case .hervatten: return "Restdraai vanuit het logboek"
            case .taak: return "Taken uit de groeilaag uitvoeren"
            }
        }
        var actiefInV1: Bool { self != .hervatten && self != .taak }
    }

    @State private var geselecteerd: Modi = .status
    @State private var toonInstellingen = false

    var body: some View {
        NavigationSplitView {
            zijbalk
                .navigationSplitViewColumnWidth(min: 240, ideal: 270)
        } detail: {
            detail
        }
        .onAppear { Thema.registreerFonts() }
        .sheet(isPresented: $toonInstellingen) { instellingenSheet }
    }

    // MARK: - Zijbalk

    private var zijbalk: some View {
        VStack(alignment: .leading, spacing: 0) {
            merk
                .padding(.horizontal, 20)
                .padding(.top, 24)
                .padding(.bottom, 18)
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
            ForEach(Modi.allCases) { modus in
                modusRij(modus)
            }
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
            Spacer()
            voet
                .padding(.horizontal, 20)
                .padding(.vertical, 16)
        }
        .background(Thema.kleur(.papier))
    }

    private var merk: some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text("Grow").font(Thema.display(24))
                Text("Kit").font(Thema.display(24, cursief: true)).foregroundStyle(Thema.kleur(.zacht))
            }
            Text("editorial monochrome · het harnas")
                .font(Thema.tekst(9, gewicht: .medium)).tracking(1.5)
                .foregroundStyle(Thema.kleur(.gedempt))
        }
    }

    private func modusRij(_ modus: Modi) -> some View {
        let gekozen = geselecteerd == modus
        return Button(action: { if modus.actiefInV1 { geselecteerd = modus } }) {
            HStack(alignment: .center, spacing: 12) {
                Text(modus.nummer)
                    .font(Thema.display(15, cursief: !modus.actiefInV1))
                    .foregroundStyle(Thema.kleur(gekozen ? .inkt : .gedempt))
                    .frame(width: 26, alignment: .leading)
                VStack(alignment: .leading, spacing: 2) {
                    Text(modus.naam).font(Thema.display(17))
                        .foregroundStyle(Thema.kleur(gekozen ? .inkt : .zacht))
                    Text(modus.beschrijving)
                        .font(Thema.tekst(10))
                        .foregroundStyle(Thema.kleur(.gedempt))
                        .lineLimit(1)
                }
                Spacer()
                if !modus.actiefInV1 {
                    Text("6.1").font(Thema.tekst(9, gewicht: .semibold)).tracking(1)
                        .padding(.horizontal, 7).padding(.vertical, 3)
                        .overlay(Capsule().stroke(Thema.kleur(.lijn)))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 13)
            .contentShape(Rectangle())
            .background(gekozen ? Thema.kleur(.zacht).opacity(0.08) : Thema.kleur(.papier))
            .overlay(alignment: .leading) {
                if gekozen { Rectangle().fill(Thema.kleur(.inkt)).frame(width: 3) }
            }
            .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
        }
        .buttonStyle(.plain)
    }

    private var voet: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Circle().fill(Thema.kleur(.inkt)).frame(width: 7, height: 7)
                Text("adapter gereed").font(Thema.tekst(10, gewicht: .medium)).tracking(1)
                    .textCase(.uppercase).foregroundStyle(Thema.kleur(.zacht))
            }
            Button(action: { toonInstellingen = true }) {
                HStack(spacing: 6) {
                    Image(systemName: "gearshape")
                    Text("Instellingen")
                }
                .font(Thema.tekst(11, gewicht: .medium))
                .foregroundStyle(Thema.kleur(.zacht))
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Detail

    @ViewBuilder
    private var detail: some View {
        VStack(spacing: 0) {
            Group {
                switch geselecteerd {
                case .status:
                    StatusView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .planten:
                    PlantView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .ratificatie:
                    RatificeerView(runner: runner, repoPad: $repoPad, interpreter: $interpreter)
                case .hervatten, .taak:
                    PlaceholderView(titel: geselecteerd.naam,
                                    tekst: "Deze modus volgt in fase 6.1 — gebruik voor nu loop.py in de terminal.")
                }
            }
            .frame(maxHeight: .infinity)
            schermVoet
        }
    }

    private var schermVoet: some View {
        HStack {
            Text("GrowKit 0.6.0")
            Spacer()
            Text("Editorial Monochrome · Fraunces & Inter (SIL OFL)")
        }
        .font(Thema.tekst(9, gewicht: .medium)).tracking(1)
        .foregroundStyle(Thema.kleur(.gedempt))
        .padding(.horizontal, 28).padding(.vertical, 10)
        .background(Thema.kleur(.papier))
        .overlay(alignment: .top) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
    }

    // MARK: - Instellingen

    private var instellingenSheet: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("Instellingen").font(Thema.display(24))
            VStack(alignment: .leading, spacing: 6) {
                Text("GROWKIT-REPO").font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                    .foregroundStyle(Thema.kleur(.gedempt))
                TextField("~/Documents/Code 7/growkit", text: $repoPad)
                    .textFieldStyle(.plain).font(Thema.tekst(13)).padding(10)
                    .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
            }
            VStack(alignment: .leading, spacing: 6) {
                Text("PYTHON-INTERPRETER (3.11+)").font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                    .foregroundStyle(Thema.kleur(.gedempt))
                TextField("/opt/homebrew/bin/python3.13", text: $interpreter)
                    .textFieldStyle(.plain).font(Thema.tekst(13)).padding(10)
                    .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
            }
            Text("De app is een bedienaar: zij roept adapter.py in dit repo aan — de poort, motor en het faalcontract van de kern blijven de bewakers.")
                .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.zacht))
            HStack {
                Spacer()
                knop("Sluit") { toonInstellingen = false }
            }
        }
        .padding(28)
        .frame(width: 460)
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
}
