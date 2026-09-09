// ZT-3 — hero-variantkeuze, spiegel van kern/growkit_home.py.
// De Python-kern is de bron van waarheid (getest via test_home_hero.py);
// deze Swift-spiegel houdt de app zelfstandig zonder adapter-roep voor
// pure tekstopmaak.
import Foundation

enum ZTHero {
    // Max 1 variant op vaste prioriteit: goedkeuringen > saldo > nachtronde.
    static func variant(uur: Int, goedkeuringen: Int, saldo: Double,
                        saldoDrempel: Double, nachtronde: Bool) -> String? {
        if goedkeuringen > 0 { return "goedkeuringen" }
        if saldo < saldoDrempel { return "saldo" }
        if nachtronde { return "nachtronde" }
        return nil
    }

    static func tekstVoor(variant: String, goedkeuringen: Int) -> String {
        switch variant {
        case "goedkeuringen":
            return goedkeuringen == 1
                ? "Er ligt 1 goedkeuring te wachten."
                : "Er liggen \(goedkeuringen) goedkeuringen te wachten."
        case "saldo": return "Je saldo zit onder de drempel."
        case "nachtronde": return "De nachtelijke bouwronde heeft nieuws."
        default: return ""
        }
    }
}
