// Huisstijl — editorial monochrome, rechtstreeks uit de mockups:
// papier #FFFFFF · inkt #000000 · zacht #555555 · gedempt #888888 · lijn 12%.

import AppKit
import CoreText
import SwiftUI

enum ThemaKleur {
    case papier, papierZacht, inkt, zacht, gedempt, lijn
}

enum Thema {
    static func nsKleur(_ k: ThemaKleur) -> NSColor {
        switch k {
        case .papier: return NSColor.white
        case .papierZacht: return NSColor(red: 0xF8 / 255.0, green: 0xF8 / 255.0, blue: 0xF8 / 255.0, alpha: 1)
        case .inkt: return NSColor.black
        case .zacht: return NSColor(red: 0x55 / 255.0, green: 0x55 / 255.0, blue: 0x55 / 255.0, alpha: 1)
        case .gedempt: return NSColor(red: 0x88 / 255.0, green: 0x88 / 255.0, blue: 0x88 / 255.0, alpha: 1)
        case .lijn: return NSColor.black.withAlphaComponent(0.12)
        }
    }

    static func kleur(_ k: ThemaKleur) -> Color { Color(nsColor: nsKleur(k)) }

    /// Registreer de ingebedde fonts éénmalig; al-geregistreerd is geen fout.
    static func registreerFonts() {
        for naam in ["Fraunces.ttf", "Fraunces-Italic.ttf", "Inter.ttf", "Inter-Italic.ttf"] {
            guard let url = Bundle.main.url(forResource: naam, withExtension: nil) else { continue }
            CTFontManagerRegisterFontURLs([url as CFURL] as CFArray, .process, true, nil)
        }
    }

    static func display(_ grootte: CGFloat, cursief: Bool = false) -> Font {
        // Let op: de meegeleverde Fraunces is een variabele font waarvan de
        // PostScript-namen afwijken ("Fraunces-Regular" bestaat; "Fraunces"
        // als opspraak levert een lege render op macOS). Daarom de exacte
        // PS-namen gebruiken — cursief werkt al via "Fraunces-Italic".
        Font.custom(cursief ? "Fraunces-Italic" : "Fraunces-Regular", size: grootte)
    }

    static func tekst(_ grootte: CGFloat, gewicht: Font.Weight = .regular) -> Font {
        // Inter-variabele font: "Inter" als familienaam werkt, maar de
        // gewichts-modifiers (.semibold e.d.) matchen niet betrouwbaar op de
        // benoemde instanties; familienaam + weight is de stabiele route.
        Font.custom("Inter", size: grootte).weight(gewicht)
    }
}
