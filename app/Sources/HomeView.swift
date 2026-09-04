// Homescherm — minimalistisch, met directe startpunten en een middelgroot
// chatvenster. De thuisbasis van de tuinier: één blik, één klik, aan het werk.

import SwiftUI

struct HomeView: View {
    @ObservedObject var runner: Runner
    @ObservedObject var koppelingen: KoppelingenStore
    @Binding var repoPad: String
    @Binding var interpreter: String
    var onNavigeer: (ContentView.Modi) -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                kop
                startpunten
                chatVenster
                Spacer(minLength: 12)
            }
            .padding(28)
        }
        .background(Thema.kleur(.papier))
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("THUIS · DE TUINIER AAN HET WERK")
                .font(Thema.tekst(10, gewicht: .semibold)).tracking(3)
                .foregroundStyle(Thema.kleur(.zacht))
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text("Goed om je te zien, ").font(Thema.display(30))
                Text("curator.").font(Thema.display(30, cursief: true)).foregroundStyle(Thema.kleur(.zacht))
            }
            Text("Alles hieronder loopt via de adapter — de poort, motor en het faalcontract blijven de bewakers.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
        }
    }

    private var startpunten: some View {
        Kaart(kop: "Direct aan de slag") {
            VStack(alignment: .leading, spacing: 0) {
                startpunt("01", "Status", "De staat van je boom — identiteit, register, tellers", .status)
                startpunt("02", "Nieuwe boom planten", "Kies een profiel, bekijk het concept, bevestig", .planten)
                startpunt("03", "Ratificatie", "Wachtende mens-momenten in bulk beoordelen", .ratificatie)
                startpunt("05", "Hervatten", "Een onderbroken plant verder uitvoeren", .hervatten)
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

    private var chatVenster: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("Dialoog").font(Thema.display(20))
                Text("· de dialoog loopt nu écht via de adapter; spraakmemo en bijlagen zijn nog schets")
                    .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                Spacer()
                Button("Volledig scherm") { onNavigeer(.dialoog) }
                    .buttonStyle(.plain)
                    .font(Thema.tekst(11, gewicht: .medium))
                    .foregroundStyle(Thema.kleur(.zacht))
            }
            Kaart(kop: "Tuinier · Reviewer · Architect") {
                ChatView(runner: runner, koppelingen: koppelingen,
                         repoPad: $repoPad, interpreter: $interpreter,
                         metScroll: true, compact: true)
                    .frame(height: 320)
            }
        }
    }
}
