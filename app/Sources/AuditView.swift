// AuditView — "Wat hebben agenten deze week gedaan?" in simpele taal.
// Leest via adapter `audit` (hergebruikt de goedkeurings-module); kritische
// acties rood gemarkeerd. Dit is het antwoord op: "ik weet niet wat ik
// allemaal goedkeur" — de app legt het uit, jij beslist wat er mee gebeurt.

import SwiftUI

struct AuditView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    @State private var samenvatting = ""
    @State private var totaal = 0
    @State private var kritiek: [[String: Any]] = []
    @State private var geladen = false
    @State private var bezig = false
    @State private var gezien: Set<Int> = []

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                kop
                actiebalk
                if !samenvatting.isEmpty { samenvattingKaart }
                kritiekKaart
            }
            .padding(24)
        }
        .background(Thema.kleur(.papier))
        .onAppear { if !geladen { laad() } }
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Audit").font(Thema.display(30))
            Text("Wat hebben de code-agenten (Codex, Claude) op deze Mac gedaan? Elke actie wordt in simpele taal uitgelegd. Kritische acties — wissen, geheimen, systeem — staan apart, zodat jij kunt nalopen wat je hebt goedgekeurd.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var actiebalk: some View {
        HStack {
            PillKnop(titel: "Opnieuw scannen", gevuld: true) { laad() }
            if bezig { ProgressView().scaleEffect(0.7); Text("analyseren…").font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.zacht)) }
            Spacer()
        }
    }

    private var samenvattingKaart: some View {
        Kaart(kop: "Samenvatting", rechterKop: "\(totaal) ACTIES GEANALYSEERD") {
            Text(samenvatting).font(Thema.tekst(12))
                .lineSpacing(3)
                .textSelection(.enabled)
        }
    }

    private var kritiekKaart: some View {
        Kaart(kop: "Kritische acties — verdienen je aandacht",
              rechterKop: geladen ? "\(kritiek.count - gezien.count) OPEN" : "—") {
            if !geladen {
                Text("Nog niet geanalyseerd.").font(Thema.tekst(12))
                    .foregroundStyle(Thema.kleur(.gedempt))
            } else if kritiek.isEmpty {
                Text("Geen kritische acties gevonden — alles was lezen, bouwen of bestanden schrijven binnen je projecten.")
                    .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
            } else {
                VStack(alignment: .leading, spacing: 0) {
                    ForEach(Array(kritiek.enumerated()), id: \.offset) { index, a in
                        kritiekRij(index, a)
                    }
                }
            }
        }
    }

    private func kritiekRij(_ index: Int, _ a: [String: Any]) -> some View {
        let isGezien = gezien.contains(index)
        return VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 10) {
                Text((a["tijdstip"] as? String ?? "").replacingOccurrences(of: "T", with: " "))
                    .font(Thema.tekst(10)).tracking(0.5)
                    .foregroundStyle(Thema.kleur(.gedempt))
                StatusBadge(tekst: a["soort"] as? String ?? "?", stijl: .herziening)
                Text(a["bron"] as? String ?? "").font(Thema.tekst(10))
                    .foregroundStyle(Thema.kleur(.gedempt))
                Spacer()
                if isGezien { StatusBadge(tekst: "gezien", bewezen: true) }
            }
            Text(a["actie"] as? String ?? "")
                .font(Thema.tekst(11))
                .foregroundStyle(Thema.kleur(.inkt))
                .lineLimit(2)
            Text(a["uitleg"] as? String ?? "")
                .font(Thema.tekst(11))
                .foregroundStyle(Thema.kleur(.zacht))
            if !isGezien {
                PillKnop(titel: "Markeer als gezien") {
                    _ = gezien.insert(index)
                }
            }
        }
        .padding(.vertical, 8)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
        }
    }

    private func laad() {
        bezig = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "audit",
                                           invoer: ["doel": "~/growkit-governor", "max": 8000],
                                           timeOut: 300)
            await MainActor.run {
                bezig = false; geladen = true
                samenvatting = r?.data["samenvatting"] as? String ?? ""
                totaal = r?.data["totaal"] as? Int ?? 0
                kritiek = r?.data["kritiek"] as? [[String: Any]] ?? []
            }
        }
    }
}