// Homescherm — de rustige landingspagina: wat is GrowKit, en een klein
// dashboard met de info die overzichtelijk bij de hand moet zijn.
// Minimalistisch bij de les: één blik, één klik, aan het werk.

import SwiftUI

struct HomeView: View {
    @ObservedObject var runner: Runner
    @ObservedObject var koppelingen: KoppelingenStore
    @Binding var repoPad: String
    @Binding var interpreter: String
    var onNavigeer: (ContentView.Modi) -> Void

    @State private var familie: [[String: Any]] = []
    @State private var leeft: [String: String] = [:]
    @State private var saldoTekst: String = ""
    @State private var saldoLaag: Bool = false
    @State private var gebruikersNaam: String = "Gebruiker"

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                kop
                watIsGrowKit
                dashboard
                graafSectie
                Spacer(minLength: 12)
            }
            .padding(28)
        }
        .background(Thema.kleur(.papier))
        .onAppear { laadDashboard() }
    }

    // MARK: Kop — wie je bent, wat dit huis is

    private var kop: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("THUIS · LANDINGSPAGINA")
                .font(Thema.tekst(10, gewicht: .semibold)).tracking(3)
                .foregroundStyle(Thema.kleur(.zacht))
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text("Goed om je te zien, ").font(Thema.display(30))
                Text(gebruikersNaam + ".").font(Thema.display(30, cursief: true)).foregroundStyle(Thema.kleur(.zacht))
            }
        }
    }

    private var watIsGrowKit: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("GrowKit is jouw huis voor AI-agenten.").font(Thema.display(17))
            Text("Je plant bomen (projecten), de familie-agents voeren taken uit met machine-bewijs, en jij behoudt de laatste stem: elke belangrijke stap wacht op jouw goedkeuringen. Alles loopt via de adapter — de poort, motor en het faalcontract blijven de bewakers. Tests zijn wet; secrets blijven op de doelmachine; de geschiedenis is append-only.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .overlay(Rectangle().fill(Thema.kleur(.lijn)).frame(width: 2), alignment: .leading)
    }

    // MARK: Klein dashboard — de vier dingen die je wilt zien

    private var dashboard: some View {
        HStack(alignment: .top, spacing: 0) {
            dashCel(titel: "FAMILIE", waarde: liveTeller, sub: "van \(familie.count) live")
            verticaleLijn
            dashCel(titel: "SALDO", waarde: saldoTekst.isEmpty ? "—" : saldoTekst,
                    sub: saldoLaag ? "onder €10 — bijvullen" : "OpenRouter",
                    rood: saldoLaag)
            verticaleLijn
            dashCel(titel: "HARNAS", waarde: "wet", sub: "kadertests verankerd")
            verticaleLijn
            dashCel(titel: "GESCHIEDENIS", waarde: "append-only", sub: "niets wordt gewist")
            Spacer()
        }
    }

    private var liveTeller: String {
        let actief = leeft.values.filter { $0 == "active" }.count
        return familie.isEmpty ? "—" : "\(actief)"
    }

    private var verticaleLijn: some View {
        Rectangle().fill(Thema.kleur(.lijn)).frame(width: 1, height: 54)
    }

    private func dashCel(titel: String, waarde: String, sub: String, rood: Bool = false) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(titel).font(Thema.tekst(8, gewicht: .semibold)).tracking(1.5)
                .foregroundStyle(Thema.kleur(.gedempt))
            Text(waarde).font(Thema.display(22))
                .foregroundStyle(rood ? Color.red : Thema.kleur(.inkt))
            Text(sub).font(Thema.tekst(9)).foregroundStyle(Thema.kleur(.gedempt))
        }
        .padding(.horizontal, 18)
    }

    // MARK: Knowledge-graaf op de landing

    private var graafSectie: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("Knowledge Graph").font(Thema.display(20))
                Text("· het hele brein in één kaart — scroll, zoom, klik en lees")
                    .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                Spacer()
                Button("Openen") { onNavigeer(.graaf) }
                    .buttonStyle(.plain)
                    .font(Thema.tekst(11, gewicht: .medium))
                    .foregroundStyle(Thema.kleur(.zacht))
            }
            GraafView(runner: runner, repoPad: $repoPad, interpreter: $interpreter,
                      compactVoorbeeld: true)
                .frame(height: 420)
                .overlay(RoundedRectangle(cornerRadius: 4).stroke(Thema.kleur(.lijn)))
        }
    }

    // MARK: Startpunten (verplaatst naar de graaf en het zijmenu)

    private var startpunten: some View {
        Kaart(kop: "Direct aan de slag") {
            VStack(alignment: .leading, spacing: 0) {
                startpunt("01", "Status", "De staat van je boom — identiteit, register, tellers", .status)
                startpunt("02", "Nieuwe boom planten", "Kies een profiel, bekijk het concept, bevestig", .planten)
                startpunt("03", "Goedkeuringen", "Wachtende mens-momenten in bulk beoordelen", .goedkeuringen)
                startpunt("05", "Agenten", "De familie: taken, controle, observer", .agenten)
            }
        }
    }

    private func startpunt(_ nummer: String, _ titel: String,
                           _ beschrijving: String, _ bestemming: ContentView.Modi) -> some View {
        Button(action: { onNavigeer(bestemming) }) {
            HStack(spacing: 14) {
                Text(nummer).font(Thema.display(16, cursief: true))
                    .foregroundStyle(Thema.kleur(.gedempt))
                    .frame(width: 28, alignment: .leading)
                VStack(alignment: .leading, spacing: 2) {
                    Text(titel).font(Thema.display(17))
                        .foregroundStyle(Thema.kleur(.inkt))
                    Text(beschrijving).font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.zacht))
                }
                Spacer()
                Image(systemName: "arrow.right").font(.system(size: 12))
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
            .padding(.vertical, 13)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
    }

    // MARK: Data

    private func laadDashboard() {
        Task {
            let p = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "profiel", invoer: ["actie": "lees"])
            let f = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "familie", invoer: ["actie": "status"])
            let s = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "agentstatus", invoer: [:])
            let g = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "saldo", invoer: [:])
            await MainActor.run {
                if let p, p.ok, let profiel = p.data["profiel"] as? [String: Any],
                   let naam = profiel["naam"] as? String, !naam.isEmpty {
                    gebruikersNaam = naam
                }
                if let f, f.ok, let fam = f.data["familie"] as? [[String: Any]] {
                    familie = fam
                }
                if let s, let agents = s.data["agents"] as? [[String: Any]] {
                    var kaart: [String: String] = [:]
                    for a in agents {
                        if let naam = a["agent"] as? String, let st = a["status"] as? String {
                            kaart[naam] = st
                        }
                    }
                    leeft = kaart
                }
                if let g, g.ok, let rest = g.data["resterend"] as? Double {
                    saldoTekst = String(format: "€ %.2f", rest)
                    saldoLaag = rest < 10.0
                }
            }
        }
    }
}
