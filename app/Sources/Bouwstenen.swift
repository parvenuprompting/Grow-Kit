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
