// AgendaView — scherm 20: alles wat vastligt, in één overzicht.
//
// Bronnen (via adapter `agenda`): cron-jobs (Mac · hermes + VPS),
// ratificaties/goedkeuringen (wacht op jou), uitvoerbare taken.
// Gegroepeerd: WACHT OP JOU · HERHALEND · EENMALIG · ONBEKEND.
// Deterministisch — de adapter levert feiten, het scherm toont ze.

import SwiftUI

struct AgendaItem: Identifiable {
    let bron: String
    let soort: String
    let titel: String
    let schema: String
    let detail: String
    var id: String { bron + "|" + titel + "|" + schema }
}

struct AgendaView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    @State private var items: [AgendaItem] = []
    @State private var geladen = false
    @State private var fout: String?
    @State private var verversTimer: Timer?

    // Groepering
    private var wachtOpJou: [AgendaItem] {
        items.filter { $0.soort == "wacht op jou" }
    }
    private var herhalend: [AgendaItem] {
        items.filter { $0.soort == "herhalend" }
    }
    private var eenmalig: [AgendaItem] {
        items.filter { $0.soort == "eenmalig" }
    }
    private var onbekend: [AgendaItem] {
        items.filter { $0.soort == "onbekend" }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                kop
                if let fout { foutKaart(fout) }
                if geladen && items.isEmpty {
                    Kaart(kop: "Niets gepland", rechterKop: nil) {
                        Text("Er ligt niets vast. Geen cron-jobs, geen wachtende goedkeuringen, geen taken.")
                            .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                    }
                }
                if !wachtOpJou.isEmpty { sectie("NU — WACHT OP JOU", wachtOpJou, accentueer: true) }
                if !herhalend.isEmpty { sectie("HERHALEND (CRON)", herhalend) }
                if !eenmalig.isEmpty { sectie("EENMALIG", eenmalig) }
                if !onbekend.isEmpty { sectie("ONBEKEND", onbekend) }
                Spacer(minLength: 16)
            }
            .padding(28)
        }
        .background(Thema.kleur(.papier))
        .onAppear {
            laad()
            startVervers()
        }
        .onDisappear { verversTimer?.invalidate(); verversTimer = nil }
    }

    // MARK: Kop

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("20 AGENDA · ALLES DAT VASTLIGT")
                .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            HStack(alignment: .firstTextBaseline) {
                Text("Agenda").font(Thema.display(30))
                Spacer()
                PillKnop(titel: "Ververs") { laad() }
            }
            Text("Cron-jobs, wachtende goedkeuringen en uitvoerbare taken — automatisch verzameld uit de bestaande bronnen. Niets nieuws te onderhouden: de agenda leest wat er al staat.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: Secties

    private func sectie(_ titel: String, _ lijst: [AgendaItem], accentueer: Bool = false) -> some View {
        Kaart(kop: titel, rechterKop: "\(lijst.count)") {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(Array(lijst.enumerated()), id: \.element.id) { idx, item in
                    rij(item, accentueer: accentueer && idx == 0)
                    if idx < lijst.count - 1 {
                        Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
                    }
                }
            }
        }
    }

    private func rij(_ item: AgendaItem, accentueer: Bool) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Circle()
                .fill(kleurVoor(item))
                .frame(width: 7, height: 7)
            VStack(alignment: .leading, spacing: 2) {
                Text(item.titel)
                    .font(Thema.tekst(13, gewicht: accentueer ? .semibold : .medium))
                Text(item.bron)
                    .font(Thema.tekst(9)).tracking(0.5)
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
            Spacer()
            Text(item.schema)
                .font(Thema.tekst(11))
                .foregroundStyle(accentueer ? Thema.kleur(.inkt) : Thema.kleur(.zacht))
        }
        .padding(.vertical, 9)
    }

    private func kleurVoor(_ item: AgendaItem) -> Color {
        switch item.soort {
        case "wacht op jou": return .orange
        case "herhalend": return Thema.kleur(.inkt)
        case "eenmalig": return .blue
        default: return .gray
        }
    }

    private func foutKaart(_ melding: String) -> some View {
        Kaart(kop: "Let op", rechterKop: "FOUT") {
            Text(melding).font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
        }
    }

    // MARK: Data

    private func laad() {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agenda", invoer: [:])
            await MainActor.run {
                if let r, r.ok, let lijst = r.data["items"] as? [[String: Any]] {
                    items = lijst.map { i in
                        AgendaItem(bron: i["bron"] as? String ?? "",
                                   soort: i["soort"] as? String ?? "",
                                   titel: i["titel"] as? String ?? "",
                                   schema: i["schema"] as? String ?? "",
                                   detail: i["detail"] as? String ?? "")
                    }
                    fout = nil
                    geladen = true
                } else {
                    fout = r?.fout ?? "Agenda onbereikbaar."
                    geladen = true
                }
            }
        }
    }

    private func startVervers() {
        verversTimer?.invalidate()
        verversTimer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { _ in
            laad()
        }
    }
}