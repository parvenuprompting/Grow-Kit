// Gedeelde bouwstenen voor de modus-schermen.

import SwiftUI

struct PlaceholderView: View {
    let titel: String
    let tekst: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(titel).font(Thema.display(28))
            Text(tekst).font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
            Spacer()
        }
        .padding(28)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct Kaart<Inhoud: View>: View {
    let kop: String
    @ViewBuilder let inhoud: Inhoud

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(kop)
                .font(Thema.tekst(10, gewicht: .semibold))
                .tracking(2)
                .textCase(.uppercase)
                .foregroundStyle(Thema.kleur(.gedempt))
                .padding(.horizontal, 20)
                .padding(.vertical, 12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Thema.kleur(.papier))
                .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
            inhoud.padding(20)
        }
        .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
        .background(Thema.kleur(.papier))
    }
}

struct StatusBadge: View {
    let tekst: String
    let bewezen: Bool

    var body: some View {
        Text(tekst)
            .font(Thema.tekst(10, gewicht: .semibold))
            .tracking(1.5)
            .textCase(.uppercase)
            .padding(.horizontal, 10).padding(.vertical, 3)
            .overlay(Capsule().stroke(Thema.kleur(bewezen ? .inkt : .lijn)))
            .foregroundStyle(Thema.kleur(bewezen ? .inkt : .zacht))
    }
}

struct LegeStaat: View {
    let kop: String
    let tekst: String
    var regels: [String] = []

    var body: some View {
        Kaart(kop: "Begin hier") {
            VStack(alignment: .leading, spacing: 14) {
                Text(kop).font(Thema.display(20))
                Text(tekst).font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
                ForEach(regels.indices, id: \.self) { i in
                    HStack(alignment: .top, spacing: 10) {
                        Text(String(format: "%02d", i + 1))
                            .font(Thema.display(12, cursief: true))
                            .foregroundStyle(Thema.kleur(.gedempt))
                        Text(regels[i]).font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                    }
                }
            }
        }
    }
}

struct StappenStreep: View {
    let stappen: [String]

    var body: some View {
        HStack(spacing: 0) {
            ForEach(stappen.indices, id: \.self) { i in
                if i > 0 {
                    Text("→").font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.gedempt)).padding(.horizontal, 10)
                }
                Text(stappen[i])
                    .font(Thema.tekst(10, gewicht: .semibold)).tracking(1.5).textCase(.uppercase)
                    .foregroundStyle(Thema.kleur(.zacht))
            }
            Spacer()
        }
    }
}
