// ZT-5 tip-rotor (Swift-zijde) — spiegelt kern/growkit_tips.py.
// Regels: conditie-tips vóór generiek, kans 0 bij laatst-getoond vandaag,
// geen tips na 23:00 en in de nacht (0-4), geen tip binnen 60 s na een
// gebeurtenis-hero, [N]-placeholders tellen niet mee, max 3 "volgende"-
// wissels per sessie. Tips komen uit app/Resources/tips.json.

import Foundation

struct Tip: Codable, Identifiable {
    let id: String
    let tekst: String
    let scherm: String
    let knop: String
    let conditie: String?
}

enum TipsRotor {
    static let avondklokUur = 23
    static let heroRust: TimeInterval = 60
    static let maxWissels = 3

    static func laadTips() -> [Tip] {
        guard let url = Bundle.main.url(forResource: "tips", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let tips = try? JSONDecoder().decode([Tip].self, from: data)
        else { return [] }
        return tips
    }

    // [N]-placeholders uit de lengte-teller.
    static func tellerTekst(_ tekst: String) -> String {
        var resultaat = ""
        var inPlaceholder = false
        for teken in tekst {
            if teken == "[" { inPlaceholder = true; continue }
            if teken == "]" { inPlaceholder = false; continue }
            if !inPlaceholder { resultaat.append(teken) }
        }
        return resultaat
    }

    /// Kies de eerste geldige tip volgens de ZT-5-regels, of nil.
    /// - Parameters:
    ///   - getoondVandaag: id's die vandaag al getoond zijn (kans 0).
    ///   - condities: set van momenteel ware condities (bv. "saldo_laag").
    ///   - heroMoment: tijdstip van de laatste gebeurtenis-hero (nil = geen).
    static func kies(tips: [Tip], uur: Int, getoondVandaag: Set<String>,
                     condities: Set<String>, heroMoment: Date?) -> Tip? {
        guard uur < avondklokUur, uur > 4 else { return nil }
        if let heroMoment, Date().timeIntervalSince(heroMoment) < heroRust {
            return nil
        }
        let beschikbaar = tips.filter { !getoondVandaag.contains($0.id) }
        // Conditie-tips (waar) vóór generieke.
        let conditieTips = beschikbaar.filter {
            $0.conditie.map { condities.contains($0) } ?? false
        }
        let generiek = beschikbaar.filter { $0.conditie == nil || $0.conditie!.isEmpty }
        return (conditieTips + generiek).first
    }

    /// Max 3 "volgende"-wissels per sessie.
    static func magVolgende(wissels: Int) -> Bool { wissels < maxWissels }
}
