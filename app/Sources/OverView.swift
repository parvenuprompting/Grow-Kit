// OverView — het Over-scherm (⌘I): versie, bouw, grenzen, en de zes regels.
// Enterprise-detail: een app die zichzelf uitlegt.

import SwiftUI

struct OverView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .center, spacing: 14) {
                BoomIcoon(formaat: 44)
                VStack(alignment: .leading, spacing: 2) {
                    HStack(alignment: .firstTextBaseline, spacing: 0) {
                        Text("Grow").font(Thema.display(28))
                        Text("Kit").font(Thema.display(28, cursief: true))
                            .foregroundStyle(Thema.kleur(.zacht))
                    }
                    Text("VERSIE 1.4.0 · BOUW 11 · EDITORIAL MONOCHROME")
                        .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.6)
                        .foregroundStyle(Thema.kleur(.gedempt))
                    Text("GROW — Governed Reproducible Operational Workflow")
                        .font(Thema.tekst(8)).tracking(1.2)
                        .foregroundStyle(Thema.kleur(.zacht))
                }
                Spacer()
            }

            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)

            Text("Een zero-trust harnas: de app bedient, de kern beslist. Alles loopt via adapter.py — de poort, motor en faalcontract staan buiten de app en kunnen er nooit omheen.")
                .font(Thema.tekst(12))
                .fixedSize(horizontal: false, vertical: true)

            HStack(spacing: 12) {
                Link(destination: URL(string: "https://x.com/GrowKitHarnas")!) {
                    HStack(spacing: 6) {
                        Image(systemName: "bird")   // X heeft geen SF-symbool; vogel als knipoog
                        Text("@GrowKitHarnas op X")
                    }
                    .font(Thema.tekst(11))
                }
                Link(destination: URL(string: "https://github.com/parvenuprompting/Grow-Kit")!) {
                    HStack(spacing: 6) {
                        Image(systemName: "chevron.left.forwardslash.chevron.right")
                        Text("GitHub")
                    }
                    .font(Thema.tekst(11))
                }
                Spacer()
            }
            .foregroundStyle(Thema.kleur(.gedempt))

            VStack(alignment: .leading, spacing: 8) {
                grensRij(getal: "2", tekst: "taken per agent — meer is een subagent")
                grensRij(getal: "8", tekst: "agents gelijktijdig — 16 taken totaal")
                grensRij(getal: "1", tekst: "observer: ziet alles, voert niets uit")
                grensRij(getal: "5", tekst: "bewijstypes — succes is bewijs, nooit een claim")
            }

            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)

            HStack {
                Text("© Parvenu · Zero-Trust Harnas")
                Spacer()
                PillKnop(titel: "Sluit", gevuld: true, compact: true) { dismiss() }
            }
        }
        .padding(26)
        .frame(width: 480)
        .background(Thema.kleur(.papier))
    }

    private func grensRij(getal: String, tekst: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(getal).font(Thema.display(20)).frame(width: 30, alignment: .trailing)
            Text(tekst).font(Thema.tekst(12))
        }
    }
}
