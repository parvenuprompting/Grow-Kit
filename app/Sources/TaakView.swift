// TaakView — taken uit de groeilaag uitvoeren: lijst met validatie-status,
// twee-staps bevestiging (lijst → keuze → bevestigde uitvoering met bewijs).
// Poort-regel: taken bestaan alleen mét bewijs — zonder geldig bewijs bestaat
// de taak niet (kern weigert, de app toont het alleen).

import SwiftUI

struct TaakView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    @AppStorage("growkitBoomPad") private var boomPad = ""

    @State private var taken: [[String: Any]] = []
    @State private var geladen = false
    @State private var geselecteerd: String?
    @State private var bezig = false
    @State private var resultaatTekst = ""

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                kop
                boomPadVeld
                takenKaart
                if let gekozen = geselecteerd { bevestigingKaart(gekozen) }
                if !resultaatTekst.isEmpty { resultaatKaart }
            }
            .padding(24)
        }
        .background(Thema.kleur(.papier))
        .onAppear { if !boomPad.isEmpty { laad() } }
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Taak").font(Thema.display(30))
            Text("Taken uit de groeilaag: taken bestaan alleen mét machine-bewijs. De poort weigert een taak zonder geldige bewijs-check — wat hij niet vrijgeeft, voert niemand uit.")
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
                PillKnop(titel: "Laad taken") { laad() }
            }
        }
    }

    private var takenKaart: some View {
        Kaart(kop: "Takenlijst", rechterKop: geladen ? "\(taken.count) GEVONDEN" : "—") {
            if !geladen {
                Text("Kies een boom en laad de takenlijst.").font(Thema.tekst(12))
                    .foregroundStyle(Thema.kleur(.gedempt))
            } else if taken.isEmpty {
                Text("Geen taken in de takenlijst van deze boom.").font(Thema.tekst(12))
                    .foregroundStyle(Thema.kleur(.gedempt))
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(Array(taken.enumerated()), id: \.offset) { _, taak in
                        taakRij(taak)
                    }
                }
            }
        }
    }

    private func taakRij(_ taak: [String: Any]) -> some View {
        let id = taak["id"] as? String ?? "?"
        let titel = taak["titel"] as? String ?? ""
        let geldig = taak["geldig"] as? Bool ?? false
        return HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(id).font(Thema.display(15))
                if !titel.isEmpty {
                    Text(titel).font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.zacht))
                }
            }
            Spacer()
            StatusBadge(tekst: geldig ? "geldig" : "zonder bewijs — geweigerd",
                        stijl: geldig ? .bewezen : .herziening)
            if geldig {
                PillKnop(titel: geselecteerd == id ? "gekozen" : "Kies",
                         gevuld: geselecteerd == id) { geselecteerd = id }
            }
        }
        .padding(.vertical, 4)
    }

    private func bevestigingKaart(_ id: String) -> some View {
        Kaart(kop: "Bevestiging", rechterKop: "TWEE STAPS") {
            VStack(alignment: .leading, spacing: 8) {
                Text("Taak '\(id)' echt uitvoeren in \(boomPad)?")
                    .font(Thema.tekst(13, gewicht: .semibold))
                Text("De motor volgt het faalcontract: één commando, bij falen één alternatief, dan de mens. Alles wordt append-only gelogd met bewijs.")
                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                HStack {
                    PillKnop(titel: "Voer uit", gevuld: true) { voerUit(id) }
                    if bezig { ProgressView().scaleEffect(0.7) }
                }
            }
        }
    }

    private var resultaatKaart: some View {
        Kaart(kop: "Resultaat", rechterKop: "APPEND-ONLY GELOGD") {
            Text(resultaatTekst).font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.zacht))
        }
    }

    // MARK: acties

    private func laad() {
        let doel = boomPad.trimmingCharacters(in: .whitespaces)
        guard !doel.isEmpty else { return }
        bezig = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "taak", invoer: ["doel": doel])
            await MainActor.run {
                bezig = false; geladen = true; geselecteerd = nil
                taken = r?.data["taken"] as? [[String: Any]] ?? []
            }
        }
    }

    private func voerUit(_ id: String) {
        bezig = true; resultaatTekst = ""
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "taak",
                                           invoer: ["doel": boomPad, "bevestig": true,
                                                    "taak_id": id],
                                           timeOut: 600)
            await MainActor.run {
                bezig = false
                if let status = r?.data["status"] as? String {
                    resultaatTekst = status == "geslaagd"
                        ? "Geslaagd — bewijs in het logboek."
                        : "Status: \(status)"
                } else {
                    resultaatTekst = r?.fout ?? "klaar"
                }
                laad()
            }
        }
    }
}
