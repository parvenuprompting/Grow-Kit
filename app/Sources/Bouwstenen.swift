// Gedeelde bouwstenen voor de modus-schermen in Editorial Monochrome stijl.
// Papier #FFFFFF · Inkt #000000 · Zacht #555555 · Gedempt #888888 · Lijn 12%.

import SwiftUI

// MARK: - Boom Icoon (Vector conform de SVG-mockup)

struct BoomIcoon: View {
    var formaat: CGFloat = 26

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: formaat * (14.0 / 64.0))
                .fill(Thema.kleur(.inkt))
                .frame(width: formaat, height: formaat)

            Canvas { context, size in
                let w = size.width
                let s = w / 64.0

                // Stam
                var stam = Path()
                stam.move(to: CGPoint(x: 32 * s, y: 50 * s))
                stam.addCurve(to: CGPoint(x: 32 * s, y: 30 * s),
                              control1: CGPoint(x: 32 * s, y: 42 * s),
                              control2: CGPoint(x: 32 * s, y: 38 * s))
                context.stroke(stam, with: .color(Thema.kleur(.papier)),
                               style: StrokeStyle(lineWidth: 4 * s, lineCap: .round))

                // Linkerblad
                var bladLinks = Path()
                bladLinks.move(to: CGPoint(x: 32 * s, y: 32 * s))
                bladLinks.addCurve(to: CGPoint(x: 12 * s, y: 16 * s),
                                   control1: CGPoint(x: 32 * s, y: 20 * s),
                                   control2: CGPoint(x: 23 * s, y: 16 * s))
                bladLinks.addCurve(to: CGPoint(x: 32 * s, y: 32 * s),
                                   control1: CGPoint(x: 12 * s, y: 28 * s),
                                   control2: CGPoint(x: 21 * s, y: 32 * s))
                bladLinks.closeSubpath()
                context.fill(bladLinks, with: .color(Thema.kleur(.papier)))

                // Rechterblad (met 55% dekking)
                var bladRechts = Path()
                bladRechts.move(to: CGPoint(x: 32 * s, y: 32 * s))
                bladRechts.addCurve(to: CGPoint(x: 49 * s, y: 18 * s),
                                    control1: CGPoint(x: 32 * s, y: 22 * s),
                                    control2: CGPoint(x: 39 * s, y: 18 * s))
                bladRechts.addCurve(to: CGPoint(x: 32 * s, y: 32 * s),
                                    control1: CGPoint(x: 49 * s, y: 28 * s),
                                    control2: CGPoint(x: 42 * s, y: 32 * s))
                bladRechts.closeSubpath()
                context.fill(bladRechts, with: .color(Thema.kleur(.papier).opacity(0.55)))
            }
            .frame(width: formaat, height: formaat)
        }
    }
}

// MARK: - Kaart (Paneel)

struct Kaart<Inhoud: View>: View {
    let kop: String
    var rechterKop: String? = nil
    var gestippeld: Bool = false
    @ViewBuilder let inhoud: Inhoud

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text(kop)
                    .font(Thema.tekst(10, gewicht: .semibold))
                    .tracking(2)
                    .textCase(.uppercase)
                    .foregroundStyle(Thema.kleur(.gedempt))

                Spacer()

                if let rechterKop {
                    Text(rechterKop)
                        .font(Thema.tekst(10, gewicht: .semibold))
                        .tracking(1.5)
                        .textCase(.uppercase)
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Thema.kleur(.papier))
            .overlay(alignment: .bottom) {
                Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
            }

            inhoud
                .padding(20)
        }
        .background(Thema.kleur(.papier))
        .overlay {
            if gestippeld {
                Rectangle().stroke(Thema.kleur(.lijn), style: StrokeStyle(lineWidth: 1, dash: [4, 4]))
            } else {
                Rectangle().stroke(Thema.kleur(.lijn), lineWidth: 1)
            }
        }
    }
}

// MARK: - Status Badge

enum BadgeStijl {
    case bewezen, lopend, mens, neutraal, herziening
}

struct StatusBadge: View {
    let tekst: String
    var stijl: BadgeStijl = .neutraal

    init(tekst: String, bewezen: Bool) {
        self.tekst = tekst
        self.stijl = bewezen ? .bewezen : .neutraal
    }

    init(tekst: String, stijl: BadgeStijl = .neutraal) {
        self.tekst = tekst
        self.stijl = stijl
    }

    var body: some View {
        Text(tekst)
            .font(Thema.tekst(10, gewicht: .semibold))
            .tracking(1.4)
            .textCase(.uppercase)
            .padding(.horizontal, 10)
            .padding(.vertical, 3.5)
            .background(achtergrond)
            .overlay(rand)
            .foregroundStyle(voorgrondKleur)
            .clipShape(Capsule())
    }

    @ViewBuilder
    private var achtergrond: some View {
        switch stijl {
        case .herziening:
            Thema.kleur(.inkt)
        default:
            Color.clear
        }
    }

    @ViewBuilder
    private var rand: some View {
        switch stijl {
        case .bewezen:
            Capsule().stroke(Thema.kleur(.inkt), lineWidth: 1)
        case .lopend:
            Capsule().stroke(Thema.kleur(.zacht), lineWidth: 1)
        case .mens:
            Capsule().stroke(Thema.kleur(.gedempt), style: StrokeStyle(lineWidth: 1, dash: [3, 3]))
        case .herziening:
            Capsule().stroke(Thema.kleur(.inkt), lineWidth: 1)
        case .neutraal:
            Capsule().stroke(Thema.kleur(.lijn), lineWidth: 1)
        }
    }

    private var voorgrondKleur: Color {
        switch stijl {
        case .bewezen: return Thema.kleur(.inkt)
        case .lopend: return Thema.kleur(.inkt)
        case .mens: return Thema.kleur(.gedempt)
        case .herziening: return Thema.kleur(.papier)
        case .neutraal: return Thema.kleur(.zacht)
        }
    }
}

// MARK: - Lege Staat

struct LegeStaat: View {
    let kop: String
    let tekst: String
    var regels: [String] = []

    var body: some View {
        Kaart(kop: "Begin hier", rechterKop: "Gids") {
            VStack(alignment: .leading, spacing: 14) {
                Text(kop).font(Thema.display(20))
                Text(tekst).font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
                    .lineSpacing(4)
                if !regels.isEmpty {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(regels.indices, id: \.self) { i in
                            HStack(alignment: .top, spacing: 12) {
                                Text(String(format: "%02d", i + 1))
                                    .font(Thema.display(13, cursief: true))
                                    .foregroundStyle(Thema.kleur(.gedempt))
                                    .frame(width: 20, alignment: .leading)
                                Text(regels[i])
                                    .font(Thema.tekst(12))
                                    .foregroundStyle(Thema.kleur(.zacht))
                            }
                        }
                    }
                    .padding(.top, 4)
                }
            }
        }
    }
}

// MARK: - Stappen Streep (Flow Indicator)

struct StappenStreep: View {
    let stappen: [String]
    var actieveIndex: Int = 0

    var body: some View {
        HStack(spacing: 0) {
            ForEach(stappen.indices, id: \.self) { i in
                if i > 0 {
                    Text("→")
                        .font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.gedempt))
                        .padding(.horizontal, 10)
                }
                HStack(spacing: 5) {
                    Text(String(format: "%02d", i + 1))
                        .font(Thema.display(11, cursief: true))
                        .foregroundStyle(Thema.kleur(i <= actieveIndex ? .inkt : .gedempt))
                    Text(stappen[i])
                        .font(Thema.tekst(10, gewicht: .semibold))
                        .tracking(1.5)
                        .textCase(.uppercase)
                        .foregroundStyle(Thema.kleur(i <= actieveIndex ? .inkt : .gedempt))
                }
            }
            Spacer()
        }
    }
}

// MARK: - Knoppen

struct PillKnop: View {
    let titel: String
    var gevuld: Bool = true
    var compact: Bool = false
    let actie: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: actie) {
            Text(titel)
                .font(Thema.tekst(compact ? 11 : 12, gewicht: .medium))
                .padding(.horizontal, compact ? 14 : 20)
                .padding(.vertical, compact ? 6 : 9)
                .background(gevuld ? Thema.kleur(.inkt) : Thema.kleur(.papier))
                .foregroundStyle(gevuld ? Thema.kleur(.papier) : Thema.kleur(.inkt))
                .overlay(Capsule().stroke(Thema.kleur(.inkt), lineWidth: 1))
                .clipShape(Capsule())
                .opacity(isHovered ? 0.85 : 1.0)
        }
        .buttonStyle(.plain)
        .onHover { isHovered = $0 }
    }
}

// MARK: - Append-Only Tijdlijn Rij

struct TijdlijnRij: View {
    let tijdstip: String
    let titel: String
    let detail: String
    let statusTekst: String
    let stijl: BadgeStijl
    var isEerste: Bool = false
    var isLaatste: Bool = false

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            // Tijdstip kolom (tabular)
            Text(tijdstip)
                .font(Thema.tekst(11))
                .foregroundStyle(Thema.kleur(.gedempt))
                .monospacedDigit()
                .frame(width: 55, alignment: .leading)

            // Verticale hairline verbinding met knoop
            VStack(spacing: 0) {
                Rectangle()
                    .fill(isEerste ? Color.clear : Thema.kleur(.lijn))
                    .frame(width: 1, height: 6)

                Circle()
                    .fill(Thema.kleur(stijl == .bewezen ? .inkt : .gedempt))
                    .frame(width: 7, height: 7)

                Rectangle()
                    .fill(isLaatste ? Color.clear : Thema.kleur(.lijn))
                    .frame(width: 1)
            }
            .frame(width: 9)

            // Inhoud
            VStack(alignment: .leading, spacing: 3) {
                HStack {
                    Text(titel)
                        .font(Thema.tekst(13, gewicht: .medium))
                    Spacer()
                    StatusBadge(tekst: statusTekst, stijl: stijl)
                }
                Text(detail)
                    .font(Thema.tekst(11))
                    .foregroundStyle(Thema.kleur(.zacht))
            }
            .padding(.bottom, isLaatste ? 0 : 12)
        }
    }
}

// MARK: - Placeholder View

struct PlaceholderView: View {
    let titel: String
    let tekst: String

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(titel).font(Thema.display(28))
            Text(tekst).font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
            Spacer()
        }
        .padding(28)
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct Pulserend: ViewModifier {
    @State private var zichtbaar = false

    func body(content: Content) -> some View {
        content
            .opacity(zichtbaar ? 0.25 : 1)
            .animation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true), value: zichtbaar)
            .onAppear { zichtbaar = true }
    }
}
