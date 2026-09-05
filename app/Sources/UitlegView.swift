// Uitleg-scherm — de twee brillen uit de mockup (gewoon Nederlands / techneuten),
// rechtstreeks uit docs/mockups/growkit-uitleg-v1.html in de app-gezet.

import SwiftUI

struct UitlegView: View {
    var metScroll: Bool = true
    @State private var bril = 0

    var body: some View {
        groep
            .background(Thema.kleur(.papier))
    }

    @ViewBuilder private var groep: some View {
        if metScroll { ScrollView { inhoudView } } else { inhoudView }
    }

    @ViewBuilder private var inhoudView: some View {
        VStack(alignment: .leading, spacing: 20) {
            VStack(alignment: .leading, spacing: 5) {
                Text("UITLEG · HOE GROWKIT WERKT")
                    .font(Thema.tekst(10, gewicht: .semibold)).tracking(3)
                    .foregroundStyle(Thema.kleur(.zacht))
                Text("Eén methode. Twee brillen.").font(Thema.display(30))
            }
            Picker("", selection: $bril) {
                Text("Gewoon Nederlands").tag(0)
                Text("Voor techneuten").tag(1)
            }
            .pickerStyle(.segmented)
            .font(Thema.tekst(12))

            if bril == 0 { zesRegels } else { engineRoom }
            Spacer(minLength: 12)
        }
        .padding(28)
    }

    // MARK: - Gewoon Nederlands

    private var zesRegels: some View {
        Kaart(kop: "De werking in zes regels", rechterKop: "Voor iedereen") {
            VStack(alignment: .leading, spacing: 14) {
                uitlegItem(1, "De AI is een tuinier, geen alwetend orakel.",
                           "Bij gewone AI-systemen mag de AI zelf bepalen of zijn werk gelukt is — dat leidt tot onterechte succesmeldingen. Binnen GrowKit mag de AI planten en snoeien, maar hij werkt binnen een onwrikbaar hek dat hij zelf niet kan verplaatsen. De controle ligt altijd buiten de AI om.")
                uitlegItem(2, "Alles begint met een zaadje.",
                           "Ieder project start vanuit een vaste, gestandaardiseerde mappenstructuur. Het zaadje is gebouwd met uitsluitend de standaard-onderdelen van Python — geen externe pakketten. Daardoor is het superlicht en raakt het nooit in de war door updates van andere software.")
                uitlegItem(3, "De poortwachter weigert vage opdrachten.",
                           "Zeg je \u{201C}bouw een leuke app\u{201D}, dan weigert het systeem direct de dienst. Je wordt eerst gedwongen tot een heldere opdracht: wat is het exacte einddoel, in welke omgeving moet het draaien, en wanneer is het objectief geslaagd? Pas na jouw goedkeuring gaat de motor draaien.")
                uitlegItem(4, "De stappenmotor met een strak faalcontract.",
                           "De AI voert de opdracht stap voor stap uit en legt elke beslissing vast in een logboek. Gaat iets mis, dan krijgt de AI exact één kans op een alternatieve oplossing. Mislukt die ook, dan stopt het systeem onmiddellijk en wordt de mens erbij geroepen.")
                uitlegItem(5, "Hard machine-bewijs, geen gevoel.",
                           "De AI mag nooit zelf concluderen \u{201C}ik denk dat het werkt\u{201D}. Een onafhankelijk controleprogramma voert harde technische tests uit: bestaat het bestand? Is de inhoud identiek aan het sjabloon (digitale vingerafdruk)? Is de JSON geldig?")
                uitlegItem(6, "De mens heeft de laatste stem.",
                           "De AI bouwt autonoom, maar publiceert nooit zomaar definitief. Alles landt als voorstel in een digitale inbox; jij als menselijke curator geeft de definitieve goedkeuring (goedkeuringen). Een tweede AI-model mag vooraf meekijken — maar bij twijfel wordt altijd jij geroepen.")
            }
        }
    }

    private func uitlegItem(_ nr: Int, _ kop: String, _ tekst: String) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Text(String(nr)).font(Thema.display(16))
                .foregroundStyle(Thema.kleur(.inkt))
                .frame(width: 18, alignment: .leading)
            VStack(alignment: .leading, spacing: 4) {
                Text(kop).font(Thema.tekst(13, gewicht: .semibold))
                Text(tekst).font(Thema.tekst(12.5)).foregroundStyle(Thema.kleur(.zacht))
                    .lineSpacing(3)
            }
        }
        .padding(.vertical, 4)
    }

    // MARK: - Voor techneuten

    private var engineRoom: some View {
        VStack(alignment: .leading, spacing: 18) {
            Kaart(kop: "Het kernprobleem", rechterKop: "Architectuur") {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Twee fatale systeemfouten bij traditionele agents:")
                        .font(Thema.tekst(12.5)).foregroundStyle(Thema.kleur(.zacht))
                    Text("· Self-reported success — de agent leest een traceback als succes en rapporteert triomfantelijk.")
                        .font(Thema.tekst(12.5))
                    Text("· Hallucinatie-lussen — een faalende stap leidt tot ad-hoc bash-hacks en onbeheersbare token-kosten.")
                        .font(Thema.tekst(12.5))
                    Text("GrowKit haalt de interpretatiebevoegdheid over procesuitkomsten volledig weg bij het LLM en onderbrengt die in een deterministische controlelaag.")
                        .font(Thema.tekst(12.5, gewicht: .medium)).padding(.top, 4)
                }
            }
            Kaart(kop: "De stroom", rechterKop: "provider-agnostisch · stdlib-only") {
                Text(uitlegStroom)
                    .font(.system(.caption, design: .monospaced))
                    .foregroundStyle(Thema.kleur(.zacht))
                    .textSelection(.enabled)
            }
            Kaart(kop: "Machine-bewijs — vijf harde checks", rechterKop: "nooit een claim") {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(bewijsChecks, id: \.check) { rij in
                        HStack(alignment: .top) {
                            Text(rij.check).font(Thema.tekst(12, gewicht: .semibold))
                                .frame(width: 100, alignment: .leading)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(rij.mechanisme).font(Thema.tekst(12))
                                Text("vangt af: " + rij.vangtAf).font(Thema.tekst(11))
                                    .foregroundStyle(Thema.kleur(.gedempt))
                            }
                        }
                        .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1).padding(.bottom, -4) }
                    }
                }
            }
            Kaart(kop: "Faalcontract, review en herstel", rechterKop: "de bewakers") {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Bij falen: precies één alternatief_commando, dan stop, exit-code 2, de mens. Geen retries — oneindige herstellussen zijn structureel onmogelijk.")
                        .font(Thema.tekst(12.5))
                    Text("De reviewer is een rol in reviewconfig.json (model/provider-velden zijn een schema-fout); payloads via stdin, shell=False; het oordeel is exact-match — twijfel is altijd de mens. Goedkeuringen in bulk, nooit auto-rollback.")
                        .font(Thema.tekst(12.5))
                    Text("Crash? growkit_hervat.py reconstrueert de staat uit het logboek: niet-idempotent geslaagde stappen worden nooit herdraaid, de laatste bevestigde mijlpaal is het herstartpunt.")
                        .font(Thema.tekst(12.5))
                }
            }
            Kaart(kop: "Voortborduur — fase 5: het oerwoud", rechterKop: "één brein, vele bomen") {
                Text("Meerdere onafhankelijke bomen onder één gedeeld brein op Git. Elke boom plaatst een geboortebewijs en registreert zich in het boom-register. Groei gaat via VOORSTELLEN naar de inbox — de mens curateert. Harde drift-guard: omgevings-specifieke staat (paden, poorten, ssh-doele, sleutels) reist nooit mee.")
                    .font(Thema.tekst(12.5)).foregroundStyle(Thema.kleur(.zacht)).lineSpacing(3)
            }
            Kaart(kop: "Status", rechterKop: "3 september 2026") {
                Text("Fase 1-6 bewezen met machine-bewijs: stappenplan, kieming (7/7 · 5/5), review-laag (5/5), harnas zonder agent (6/6, incl. kill-9-crash en herstart) en het oerwoud (6/6). 206 unit-tests + 7 E2E-scripts groen.")
                    .font(Thema.tekst(12.5)).foregroundStyle(Thema.kleur(.zacht))
            }
        }
    }

    private let uitlegStroom = """
    gebruiker → loop.py / seed.py
      → growkit_poort.py      (weigering · vragenlijst · concept)
      → mens-bevestiging      (hard: niets draait zonder bevestigde scope)
      → growkit_motor.py      (stappen-motor, append-only logboek.json)
      → growkit_bewijs.py     (5 checktypes — de LLM claimt nooit succes)
      → growkit_review.py     (alleen mens_verificatie; stdin, shell=False)
      → goedkeuringen in bulk   (de mens keurt; geen auto-rollback)
      ↳ crash? growkit_hervat.py leest het logboek en bouwt de restdraai
    """

    private struct BewijsRij {
        let check: String
        let mechanisme: String
        let vangtAf: String
    }

    private let bewijsChecks: [BewijsRij] = [
        BewijsRij(check: "shell_check",
                  mechanisme: "check-commando draait; output bevat de verwachte letterlijke tekenreeks",
                  vangtAf: "foutpatronen in terminal-output"),
        BewijsRij(check: "file_exists",
                  mechanisme: "pad bestaat (optioneel met verplichte tekst)",
                  vangtAf: "missende bestanden en mappen"),
        BewijsRij(check: "json_valid",
                  mechanisme: "valide JSON met top_level / exacte_lengte / verplicht_veld",
                  vangtAf: "kapotte of incomplete data"),
        BewijsRij(check: "file_equals",
                  mechanisme: "byte-voor-byte gelijk aan sjabloon (SHA256)",
                  vangtAf: "stiekeme \u{201C}stealth-hallucinaties\u{201D}"),
        BewijsRij(check: "http_check",
                  mechanisme: "URL reageert met de verwachte status",
                  vangtAf: "onbereikbare of foutieve diensten"),
    ]
}
