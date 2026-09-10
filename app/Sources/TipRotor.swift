// Tip-rotor (ZT-5) — één tip per moment, met de regels uit het plan:
// conditie-tips eerst, geen herhaling vandaag, geen tips na 23:00,
// stilte binnen 60 s na een gebeurtenis-hero, [N] uit tellers,
// max 3 'volgende'-wissels per sessie.
// Spiegel van kern/growkit_tips.py — zelfde regels, client-kant.

import SwiftUI

struct Tip: Codable, Identifiable {
    let id: String
    let tekst: String
    let scherm: String
    let knop: String
    let conditie: [String: Int]?  // {"veld": <teller-index onbenut>, "min": N}
}

enum TipRotor {
    static let volgendeMax = 3
    static let stilteNaGebeurtenis: TimeInterval = 60

    static func laadTips() -> [Tip] {
        guard let url = Bundle.main.url(forResource: "tips", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let tips = try? JSONDecoder().decode([Tip].self, from: data) else { return [] }
        return tips
    }

    static func kiesTip(tips: [Tip], nu: Date = Date(),
                        tellers: [String: Int] = [:],
                        laatstGetoond: [String: Date] = [:],
                        gebeurtenisOp: Date? = nil,
                        wissels: Int = 0) -> Tip? {
        guard nu.hourNietAvond else { return nil }
        if let gebeurtenisOp, nu.timeIntervalSince(gebeurtenisOp) < stilteNaGebeurtenis { return nil }
        let kalender = Calendar.current
        var kandidaten = tips.filter { tip in
            guard let dan = laatstGetoond[tip.id] else { return true }
            return !kalender.isDate(dan, inSameDayAs: nu)
        }
        if kandidaten.isEmpty { return nil }
        let conditie = kandidaten.filter { tip in
            guard let c = tip.conditie else { return false }
            let veld = c.keys.first ?? ""
            return tellers[veld, default: 0] >= (c["min"] ?? 0)
        }
        if !conditie.isEmpty { kandidaten = conditie }
        guard let tip = kandidaten.randomElement() else { return nil }
        var tekst = tip.tekst
        for (veld, waarde) in tellers { tekst = tekst.replacingOccurrences(of: "[\(veld)]", with: String(waarde)) }
        return Tip(id: tip.id, tekst: tekst, scherm: tip.scherm,
                   knop: tip.knop, conditie: tip.conditie)
    }

    static func magWisselen(_ wissels: Int) -> Bool { wissels < volgendeMax }
}

private extension Date {
    var hourNietAvond: Bool { Calendar.current.component(.hour, from: self) < 23 }
}

// SwiftUI-banner voor op het Home-scherm.
struct TipRotorView: View {
    let tellers: [String: Int]
    let onNavigeer: (ContentView.Modi) -> Void

    @State private var tips: [Tip] = []
    @State private var huidige: Tip?
    @State private var wissels = 0

    var body: some View {
        Group {
            if let tip = huidige {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(tip.tekst).font(Thema.tekst(12))
                        Button(tip.knop) {
                            onNavigeer(bestemming(tip.scherm))
                        }
                        .font(Thema.tekst(11, gewicht: .medium))
                        .buttonStyle(.plain)
                    }
                    Spacer()
                    if TipRotor.magWisselen(wissels) {
                        Button("Volgende") {
                            wissels += 1
                            huidige = TipRotor.kiesTip(tips: tips, tellers: tellers, wissels: wissels)
                        }
                        .buttonStyle(.plain)
                        .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.zacht))
                    }
                }
                .padding(14)
                .overlay(RoundedRectangle(cornerRadius: 4).stroke(Thema.kleur(.lijn)))
            }
        }
        .onAppear {
            tips = TipRotor.laadTips()
            huidige = TipRotor.kiesTip(tips: tips, tellers: tellers)
        }
    }

    private func bestemming(_ scherm: String) -> ContentView.Modi {
        switch scherm {
        case "taken": return .taak
        case "automatiek": return .automatiek
        case "agenda": return .agenda
        case "saldo": return .status
        default: return .status
        }
    }
}
