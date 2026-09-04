// Rondleiding — de vijf schermen van het ontwerp (docs/mockups/growkit-ui-v1.html)
// als statische showcase: van vage prompt tot geplante boom.

import SwiftUI

struct RondleidingView: View {
    var metScroll: Bool = true

    var body: some View {
        groep
            .background(Thema.kleur(.papier))
    }

    @ViewBuilder private var groep: some View {
        if metScroll { ScrollView { inhoudView } } else { inhoudView }
    }

    @ViewBuilder private var inhoudView: some View {
        VStack(alignment: .leading, spacing: 22) {
            VStack(alignment: .leading, spacing: 5) {
                Text("RONDLEIDING · GROEIKETEN")
                    .font(Thema.tekst(10, gewicht: .semibold)).tracking(3)
                    .foregroundStyle(Thema.kleur(.zacht))
                Text("Eén zaadje. Eén klik. Eén boom.").font(Thema.display(30))
                Text("Vijf schermen van vage prompt tot geplante boom — elke beslissing bevestigd, elk bewijs machine-gecontroleerd.")
                    .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
            }
            scherm01
            scherm02
            scherm03
            scherm04
            scherm05
            Spacer(minLength: 12)
        }
        .padding(28)
    }

    private func schermNummer(_ nr: String, _ eyebrow: String, _ titel: String,
                              _ tekst: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(eyebrow).font(Thema.tekst(10, gewicht: .semibold)).tracking(3)
                .foregroundStyle(Thema.kleur(.zacht))
            Text(titel).font(Thema.display(24))
            Text(tekst).font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht)).lineSpacing(3)
        }
        .overlay(alignment: .topLeading) {
            Text(nr).font(Thema.display(44, cursief: true))
                .foregroundStyle(Thema.kleur(.lijn))
                .offset(x: -2, y: -34)
        }
        .padding(.top, 18)
    }

    private var scherm01: some View {
        VStack(alignment: .leading, spacing: 10) {
            schermNummer("01", "Scope-poort · Vragenformulier", "Kiemkeuze",
                         "Geen vrije tekst, maar opties — aangevuld met wat het eigen brein al weet. Aanwijzen in plaats van formuleren.")
            Kaart(kop: "Wat wil je laten groeien?", rechterKop: "Vraag 1 / 2") {
                VStack(alignment: .leading, spacing: 0) {
                    rijOptie("📻  Tweede brein — gecontroleerd geheugen", "standaard")
                    rijOptie("⚙️  Autonome fabriek — VPS-dienst", "standaard")
                    rijOptie("🛠  Dev-werkplaats — codeeromgeving", "standaard")
                    rijOptie("📁  Mijn Logboeken-project apart bijhouden", "uit je brein")
                    Text("Iets anders — beschrijf het…")
                        .font(Thema.tekst(13, gewicht: .medium)).italic()
                        .foregroundStyle(Thema.kleur(.zacht))
                        .padding(.vertical, 10)
                }
            }
        }
    }

    private func rijOptie(_ naam: String, _ bron: String) -> some View {
        HStack {
            Text(naam).font(Thema.tekst(13, gewicht: bron == "standaard" ? .regular : .medium))
                .foregroundStyle(Thema.kleur(bron == "standaard" ? .zacht : .inkt))
            Spacer()
            Text(bron).font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5).textCase(.uppercase)
                .foregroundStyle(Thema.kleur(.gedempt))
        }
        .padding(.vertical, 10)
        .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
    }

    private var scherm02: some View {
        VStack(alignment: .leading, spacing: 10) {
            schermNummer("02", "Prompt-slijper", "Schuring",
                         "De vage prompt links, de geschuurde opdracht rechts. De slijper vult nooit in wat er niet staat — wat ontbreekt, wordt een open vraag.")
            Kaart(kop: "Ruwe invoer → Geslepen concept", rechterKop: "Voorstel") {
                VStack(alignment: .leading, spacing: 12) {
                    Text("\u{201C}maak me iets om m'n notities te ordenen of zo\u{201D}")
                        .font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
                        .padding(14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Thema.kleur(.papierZacht))
                        .overlay(alignment: .leading) { Rectangle().fill(Thema.kleur(.gedempt)).frame(width: 2) }
                    VStack(alignment: .leading, spacing: 8) {
                        slepenVeld("Doel", "een tweede brein: notities opslaan en ordenen per project, met de agent als alleen-lezen adviseur")
                        slepenVeld("Plek", "lokaal, in ~/my-brain/ (standaard, pas aan indien anders)")
                        slepenVeld("Slaag wanneer", "mappen bestaan, logboek is valide JSON, eerste notitie geplaatst")
                        Text("Open vraag — niet afgeleid: moeten oude notities meteen geïmporteerd worden?")
                            .font(Thema.tekst(12.5)).italic().foregroundStyle(Thema.kleur(.gedempt))
                    }
                    HStack {
                        pill("Klopt — plant het", gevuld: true)
                        pill("Eerst corrigeren", gevuld: false)
                    }
                }
            }
        }
    }

    private func slepenVeld(_ label: String, _ tekst: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(Thema.tekst(11, gewicht: .semibold)).tracking(1).textCase(.uppercase)
                .foregroundStyle(Thema.kleur(.inkt))
            Text(tekst).font(Thema.tekst(12.5)).foregroundStyle(Thema.kleur(.zacht))
        }
        .padding(.top, 6)
        .overlay(alignment: .top) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
    }

    private var scherm03: some View {
        VStack(alignment: .leading, spacing: 10) {
            schermNummer("03", "Uitvoering · Machine-bewijs", "Het stappenplan",
                         "De agent voert uit, maar seed.py oordeelt. Een stap is pas geslaagd als de check dat zegt.")
            Kaart(kop: "Tweede brein — aan het planten", rechterKop: "Stap 3 / 8") {
                VStack(alignment: .leading, spacing: 0) {
                    stapRij("stap-01", "Mappen aanmaken (identiteit, kennis, projecten, inbox, logboek)",
                            "shell_check — alle vijf mappen bestaan", "✓ bewezen", bewezen: true)
                    stapRij("stap-02", "Sjabloon INDEX.md naar de root kopiëren",
                            "file_equals — identiek aan sjabloon", "✓ bewezen", bewezen: true)
                    stapRij("stap-03", "Logboek initialiseren als lege JSON-array",
                            "json_valid — top-level array", "✓ bewezen", bewezen: true)
                    stapRij("stap-04", "Curatie-regels naar inbox/ schrijven",
                            "file_equals — bevat VOORSTEL", "⏳ lopend", bewezen: false)
                    stapRij("stap-08", "Structuur tonen aan de mens",
                            "mens_verificatie — reviewer kijkt mee", "mens-moment", bewezen: false)
                }
            }
        }
    }

    private func stapRij(_ id: String, _ cmd: String, _ bewijs: String,
                         _ status: String, bewezen: Bool) -> some View {
        HStack(alignment: .top, spacing: 14) {
            Text(id).font(Thema.display(13)).foregroundStyle(Thema.kleur(.gedempt))
                .frame(width: 68, alignment: .leading)
            VStack(alignment: .leading, spacing: 4) {
                Text(cmd).font(Thema.tekst(13, gewicht: .medium))
                Text("bewijs: " + bewijs).font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.zacht))
                StatusBadge(tekst: status, bewezen: bewezen)
            }
            Spacer()
        }
        .padding(.vertical, 10)
        .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
    }

    private var scherm04: some View {
        VStack(alignment: .leading, spacing: 10) {
            schermNummer("04", "Mijlpaal-bevestiging", "Vóór definitief",
                         "Bij grote scope vat de agent op wat hij begrepen heeft, wat er is afgesproken en wat bewezen is. Pas na bevestiging is de mijlpaal definitief.")
            Kaart(kop: "Mijlpaal 2 — Skelet staat", rechterKop: "Ter bevestiging") {
                VStack(alignment: .leading, spacing: 10) {
                    mijlpaalRij("Wat ik begrepen heb", "je wilt een generiek tweede brein, alleen-lezen voor de agent, curatie door jou", boven: true)
                    mijlpaalRij("Wat we afgesproken hebben", "vijf kernmappen, geen sync-mechanisme in fase 1 (logboek, 15:42)", boven: false)
                    mijlpaalRij("Bewijs tot nu toe", "6 van 8 stappen machine-gecontroleerd geslaagd", boven: false)
                    mijlpaalRij("Wat hierna komt", "laatste twee stappen, dan de boom zelf laten zien", boven: false)
                    HStack {
                        pill("Bevestigen — definitief maken", gevuld: true)
                        pill("Nog niet — pas aan", gevuld: false)
                    }
                }
            }
        }
    }

    private func mijlpaalRij(_ label: String, _ tekst: String, boven: Bool) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Text(label).font(Thema.tekst(12.5, gewicht: .semibold))
                .foregroundStyle(Thema.kleur(.inkt))
            Text("— " + tekst).font(Thema.tekst(12.5)).foregroundStyle(Thema.kleur(.zacht))
                .lineSpacing(2)
        }
        .padding(.vertical, 6)
        .overlay(alignment: .top) {
            if boven { Rectangle().fill(Thema.kleur(.inkt)).frame(height: 1) }
        }
    }

    private var scherm05: some View {
        VStack(alignment: .leading, spacing: 10) {
            schermNummer("05", "De groeilaag", "De boom",
                         "Vijf kernmappen, strak omlijnd — de rest optioneel en duidelijk gestippeld. Hoe voller het brein, hoe persoonlijker de opties in scherm 01: het vliegwiel.")
            HStack(alignment: .top, spacing: 12) {
                Kaart(kop: "Kern — elke tweede brein") {
                    VStack(alignment: .leading, spacing: 0) {
                        mapRij("identiteit/", "wie dit brein is, en de rol van de agent")
                        mapRij("kennis/", "geverifieerde kennis, alleen mens promoveert")
                        mapRij("projecten/", "actieve en afgeronde projecten")
                        mapRij("inbox/", "agent-voorstellen, status VOORSTEL")
                        mapRij("logboek/", "append-only: alles wat er gebeurd is")
                    }
                }
                Kaart(kop: "Optioneel — naar eigen smaak") {
                    VStack(alignment: .leading, spacing: 0) {
                        mapRij("stem/", "toon- en stijlrichtlijnen", gedempt: true)
                        mapRij("ideeën/", "los archief, nog niet uitgewerkt", gedempt: true)
                        mapRij("prompts/", "herbruikbare prompt-templates", gedempt: true)
                    }
                }
            }
        }
    }

    private func mapRij(_ naam: String, _ doel: String, gedempt: Bool = false) -> some View {
        HStack {
            Text(naam).font(Thema.display(14))
                .foregroundStyle(Thema.kleur(gedempt ? .gedempt : .inkt))
            Spacer()
            Text(doel).font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
        }
        .padding(.vertical, 8)
        .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1) }
    }

    private func pill(_ titel: String, gevuld: Bool) -> some View {
        Text(titel).font(Thema.tekst(11, gewicht: .medium))
            .padding(.horizontal, 16).padding(.vertical, 8)
            .background(gevuld ? Thema.kleur(.inkt) : Thema.kleur(.papier))
            .foregroundStyle(gevuld ? Thema.kleur(.papier) : Thema.kleur(.inkt))
            .overlay(Capsule().stroke(Thema.kleur(.inkt)))
            .clipShape(Capsule())
    }
}
