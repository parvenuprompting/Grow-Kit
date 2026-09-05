// Taak-scherm — taken uit de groeilaag uitvoeren, met poortjes.
// Eerst de takenlijst met geldigheid (poort-oordeel), pas na bevestiging
// voert de motor uit. Alles via adapter `taak`; de app interpreteert niets.

import SwiftUI

struct TaakView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    var metScroll: Bool = true

    @State private var boomPad = ""
    @State private var agentNaam = ""
    @State private var geladen = false
    @State private var fout: String?
    @State private var taken: [[String: Any]] = []
    @State private var uitslag: String?
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
            padRij
            if let fout { foutKaart(fout) }
            if geladen && fout == nil { takenKaart }
            if let uitslag { uitslagKaart(uitslag) }
            Spacer(minLength: 16)
        }
        .padding(28)
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Taak").font(Thema.display(30))
            Text("Taken bestaan alleen mét machine-bewijs (§7): zonder gecodeerde bewijscheck voert de motor niets uit. De app stelt voor; jij bevestigt per taak.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var padRij: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 4) {
                Text("BOOM-PAD")
                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                    .foregroundStyle(Thema.kleur(.gedempt))
                TextField("~/mijn-brein", text: $boomPad)
                    .textFieldStyle(.plain).font(Thema.tekst(13)).padding(10)
                    .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                    .background(Thema.kleur(.papierZacht))
            }
            VStack(alignment: .leading, spacing: 4) {
                Text("AGENT (GOVERNOR)")
                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                    .foregroundStyle(Thema.kleur(.gedempt))
                TextField("bijv. subagent-1 — leeg = zonder governor", text: $agentNaam)
                    .textFieldStyle(.plain).font(Thema.tekst(13)).padding(10)
                    .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                    .background(Thema.kleur(.papierZacht))
            }
            PillKnop(titel: "Laad taken") { laad() }
        }
    }

    private var takenKaart: some View {
        Kaart(kop: "Takenlijst van de groeilaag", rechterKop: "\(taken.count) TAKEN") {
            VStack(alignment: .leading, spacing: 12) {
                if taken.isEmpty {
                    Text("Geen taken in deze boom (takenlijst.json is leeg of ontbreekt).")
                        .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                }
                ForEach(Array(taken.enumerated()), id: \.offset) { _, t in
                    taakRij(t)
                }
            }
        }
    }

    private func taakRij(_ t: [String: Any]) -> some View {
        let id = (t["id"] as? String) ?? "?"
        let titel = (t["titel"] as? String) ?? ""
        let geldig = (t["geldig"] as? Bool) ?? false
        return HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text(titel.isEmpty ? id : titel).font(Thema.tekst(12, gewicht: .semibold))
                Text(id).font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
            }
            Spacer()
            StatusBadge(tekst: geldig ? "GELDIG" : "ONGELDIG",
                        stijl: geldig ? .bewezen : .herziening)
            if geldig {
                PillKnop(titel: "Voer uit", gevuld: true, compact: true) {
                    voerUit(taak: id)
                }
            }
        }
    }

    private func uitslagKaart(_ tekst: String) -> some View {
        Kaart(kop: "Uitslag", gestippeld: false) {
            Text(tekst).font(Thema.tekst(12))
        }
    }

    private func foutKaart(_ tekst: String) -> some View {
        Kaart(kop: "Let op", gestippeld: true) {
            Text(tekst).font(Thema.tekst(12))
        }
    }

    // MARK: Acties — via de adapter, nooit eromheen

    private func laad() {
        let doel = boomPad.trimmingCharacters(in: .whitespaces)
        guard !doel.isEmpty else { fout = "Vul eerst het pad naar de boom."; return }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "taak",
                                           invoer: ["doel": doel])
            await MainActor.run {
                geladen = true
                guard let r, r.ok else {
                    fout = r?.fout ?? "adapter reageerde niet — controleer Instellingen"
                    return
                }
                fout = nil
                taken = r.data["taken"] as? [[String: Any]] ?? []
            }
        }
    }

    private func voerUit(taak id: String) {
        let doel = boomPad.trimmingCharacters(in: .whitespaces)
        let agent = agentNaam.trimmingCharacters(in: .whitespaces)
        var invoer: [String: Any] = ["doel": doel, "bevestig": true, "taak_id": id]
        if !agent.isEmpty { invoer["agent"] = agent }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "taak",
                                           invoer: invoer,
                                           timeOut: 300)
            await MainActor.run {
                if let fouttekst = r?.fout {
                    uitslag = "✕ " + fouttekst
                    return
                }
                let st = (r?.data["status"] as? String) ?? "?"
                uitslag = ((st == "geslaagd") ? "✓ " : "✕ ") + "taak \(id) — " + st
                    + (agent.isEmpty ? "" : " · governor: wacht op controle (zie Agenten)")
            }
        }
    }
}