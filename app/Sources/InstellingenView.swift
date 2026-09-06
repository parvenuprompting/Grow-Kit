// InstellingenView — het volwaardige bedieningspaneel (6 tabbladen).
//
// Alle instellingen leven in InstellingenStore (één bron van waarheid,
// ~/.growkit/instellingen.json). Wijzigingen worden direct bewaard.

import SwiftUI

struct InstellingenView: View {
    @ObservedObject var store = InstellingenStore.gedeeld
    @State private var tab = 0
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Text("Instellingen").font(Thema.display(24))
                Spacer()
                PillKnop(titel: "Sluit", gevuld: true, compact: true) { dismiss() }
            }
            Picker("", selection: $tab) {
                Text("Algemeen").tag(0)
                Text("Uiterlijk").tag(1)
                Text("AI-providers").tag(2)
                Text("Agenten").tag(3)
                Text("CyberSeed").tag(4)
                Text("Breinen").tag(5)
            }
            .pickerStyle(.segmented)
            .font(Thema.tekst(11))

            ScrollView {
                Group {
                    if tab == 0 { algemeen }
                    if tab == 1 { uiterlijk }
                    if tab == 2 { providers }
                    if tab == 3 { agenten }
                    if tab == 4 { cyberseed }
                    if tab == 5 { breinen }
                }
            }
        }
        .padding(28)
        .frame(width: 640, height: 640)
    }

    // MARK: 0 · Algemeen

    private var algemeen: some View {
        VStack(alignment: .leading, spacing: 14) {
            Kaart(kop: "Configuratie", rechterKop: "Omgeving") {
                VStack(alignment: .leading, spacing: 14) {
                    LabeledVeld(label: "GROWKIT-REPO", tekst: $store.instellingen.repoPad,
                            placeholder: "~/Documents/Code 7/growkit")
                    LabeledVeld(label: "PYTHON-INTERPRETER (3.11+)", tekst: $store.instellingen.interpreter,
                            placeholder: "/opt/homebrew/bin/python3.13")
                }
            }
            Kaart(kop: "Wie ben je", rechterKop: "VAN-VELD") {
                VStack(alignment: .leading, spacing: 10) {
                    LabeledVeld(label: "JOUW NAAM", tekst: $store.instellingen.gebruikersnaam,
                            placeholder: "Tiëndo")
                    Text("Agents spreken je aan met deze naam in Agent Chat en Automatiek. Repo-cloners vullen hier hun eigen naam in.")
                        .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                }
            }
            Kaart(kop: "Opstart", rechterKop: nil) {
                schakelRij("Herstel het laatste scherm bij start",
                           $store.instellingen.herstelLaatsteScherm)
            }
        }
    }

    // MARK: 1 · Uiterlijk

    private var uiterlijk: some View {
        VStack(alignment: .leading, spacing: 14) {
            Kaart(kop: "Thema", rechterKop: nil) {
                VStack(alignment: .leading, spacing: 10) {
                    Picker("", selection: $store.instellingen.themaModus) {
                        ForEach(Instellingen.ThemaModus.allCases, id: \.self) { m in
                            Text(m.rawValue).tag(m)
                        }
                    }
                    .pickerStyle(.segmented)
                    .font(Thema.tekst(11))
                    Text("Donker volgt de inkt-kleuren in een donkere grijstint. \"Volg systeem\" wisselt mee met macOS.")
                        .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                }
            }
            Kaart(kop: "Zijmenu-extra's", rechterKop: nil) {
                VStack(alignment: .leading, spacing: 12) {
                    schakelRij("Weer (datum · tijd · temperatuur)",
                               $store.instellingen.weerInZijmenu)
                    schakelRij("Saldo-regel tonen",
                               $store.instellingen.saldoInZijmenu)
                    HStack {
                        Text("Saldo-rood onder (€)").font(Thema.tekst(11))
                        Spacer()
                        TextField("", value: $store.instellingen.saldoDrempel, format: .number)
                            .textFieldStyle(.plain)
                            .font(Thema.tekst(11))
                            .frame(width: 70)
                            .padding(6)
                            .background(RoundedRectangle(cornerRadius: 6)
                                .stroke(Thema.kleur(.lijn)))
                    }
                }
            }
        }
    }

    // MARK: 2 · Providers (behouden; koppelingen leven in Koppelingen.swift)

    private var providers: some View {
        VStack(alignment: .leading, spacing: 14) {
            Kaart(kop: "AI-providers", rechterKop: "BESTAAND") {
                Text("De provider-koppelingen (OpenRouter e.a.) en de actieve chat-provider beheer je via \"Koppelingen\" in de zijbalk. Hier komt later per-provider sleutelbeheer uit de Sleutelhangar.")
                    .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
            }
            Kaart(kop: "Saldo", rechterKop: nil) {
                Text("De saldo-drempel (wanneer de regel rood wordt) stel je in bij Uiterlijk — hij hoort bij de zijmenu-regel.")
                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
            }
        }
    }

    // MARK: 3 · Agenten

    private var agenten: some View {
        VStack(alignment: .leading, spacing: 14) {
            Kaart(kop: "Agent Chat", rechterKop: nil) {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("Auto-verversing").font(Thema.tekst(11))
                        Spacer()
                        Picker("", selection: $store.instellingen.autoVerversing) {
                            Text("uit").tag(0)
                            Text("15s").tag(15)
                            Text("30s").tag(30)
                            Text("60s").tag(60)
                        }
                        .pickerStyle(.segmented)
                        .frame(width: 220)
                        .font(Thema.tekst(10))
                    }
                    schakelRij("Typing-indicator (drie stippen bij wachten)",
                               $store.instellingen.typingIndicator)
                    schakelRij("Thought-blokken standaard open",
                               $store.instellingen.thoughtStandaardOpen)
                }
            }
            Kaart(kop: "Standaardagent", rechterKop: nil) {
                HStack {
                    Text("Chat opent met").font(Thema.tekst(11))
                    Spacer()
                    Picker("", selection: $store.instellingen.standaardAgent) {
                        ForEach(["kairos", "riri", "vigil", "libra",
                                 "memoria", "codex", "genius"], id: \.self) { a in
                            Text(a.capitalized).tag(a)
                        }
                    }
                    .labelsHidden()
                    .font(Thema.tekst(11))
                }
            }
        }
    }

    // MARK: 4 · CyberSeed

    private var cyberseed: some View {
        VStack(alignment: .leading, spacing: 14) {
            Kaart(kop: "CyberSeed Sprout v0.5", rechterKop: "LOKAAL") {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("Basis-model").font(Thema.tekst(11))
                        Spacer()
                        TextField("qwen3:8b", text: $store.instellingen.cyberseedBasisModel)
                            .textFieldStyle(.plain)
                            .font(Thema.tekst(11))
                            .frame(width: 160)
                            .padding(6)
                            .background(RoundedRectangle(cornerRadius: 6)
                                .stroke(Thema.kleur(.lijn)))
                    }
                    HStack {
                        Text("SOUL-verfrissing").font(Thema.tekst(11))
                        Spacer()
                        Picker("", selection: $store.instellingen.cyberseedVerfrisUren) {
                            Text("uit").tag(0)
                            Text("12u").tag(12)
                            Text("24u").tag(24)
                            Text("48u").tag(48)
                        }
                        .pickerStyle(.segmented)
                        .frame(width: 220)
                        .font(Thema.tekst(10))
                    }
                    Text("Draait volledig op deze Mac. Niets verlaat het huis. Open scherm 19 (CyberSeed) voor het gesprek en de status.")
                        .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                }
            }
        }
    }

    // MARK: 5 · Breinen (behouden — koppelingen staan in Koppelingen.swift)

    private var breinen: some View {
        VStack(alignment: .leading, spacing: 14) {
            Kaart(kop: "Breinen", rechterKop: "BESTAAND") {
                Text("De breinen (Agent-Brain e.a.), hun lokale paden en git-remotes beheer je in het Breinen-paneel van de oude instellingen — die migreren in de volgende ronde naar hier, met een \"Brain-sync nu\"-knop.")
                    .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
            }
        }
    }

    // MARK: Bouwstenen

    private func schakelRij(_ titel: String, _ binding: Binding<Bool>) -> some View {
        Toggle(isOn: binding) {
            Text(titel).font(Thema.tekst(11))
        }
        .toggleStyle(.switch)
        .font(Thema.tekst(11))
    }
}