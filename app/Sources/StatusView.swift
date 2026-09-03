// Status-scherm — identiteit, register, tellers en logboek-momenten.
// Editorial Monochrome · Zero-Trust Harnas

import SwiftUI

struct StatusGegevens {
    let identiteit: [String: Any]?
    let voorFase5: Bool
    let melding: String?
    let registerBreinPad: String?
    let registerStatus: String?
    let registerFout: String?
    let wachtend: Int
    let verzonden: Int
    let laatste: [String: Any]?

    init(_ data: [String: Any]) {
        identiteit = data["identiteit"] as? [String: Any]
        voorFase5 = (data["voor_fase5"] as? Bool) ?? false
        melding = data["melding"] as? String
        if let register = data["register"] as? [String: Any] {
            registerBreinPad = register["brein_pad"] as? String
            registerStatus = register["status"] as? String
            registerFout = register["fout"] as? String
        } else {
            registerBreinPad = nil
            registerStatus = nil
            registerFout = nil
        }
        if let tellers = data["tellers"] as? [String: Any] {
            wachtend = (tellers["wachtend"] as? Int) ?? 0
            verzonden = (tellers["verzonden"] as? Int) ?? 0
        } else {
            wachtend = 0
            verzonden = 0
        }
        laatste = data["laatste_mijlpaal_faal"] as? [String: Any]
    }
}

struct StatusView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    var metScroll: Bool = true

    @State private var boomPad = ""
    @State private var gegevens: StatusGegevens?
    @State private var fout: String?
    @State private var toonVoorbeeldTijdlijn: Bool = true

    var body: some View {
        groep
            .background(Thema.kleur(.papier))
    }

    // ImageRenderer rendert ScrollView leeg; het render-bewijs gebruikt
    // daarom dezelfde inhoud zonder scroll-container (metScroll: false).
    @ViewBuilder private var groep: some View {
        if metScroll { ScrollView { inhoudView } } else { inhoudView }
    }

    @ViewBuilder private var inhoudView: some View {
        VStack(alignment: .leading, spacing: 22) {
            kop
            StappenStreep(stappen: ["Zoekpad", "Identiteit", "Register", "Tellers", "Tijdlijn"],
                          actieveIndex: gegevens != nil ? 4 : 0)
            zoekrij
            if runner.bezig { laadIndicator }
            if let fout { foutKaart(fout) }

            if let gegevens {
                if let melding = gegevens.melding {
                    Kaart(kop: "Melding", rechterKop: "Adapter") {
                        Text(melding).font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
                    }
                }
                if !gegevens.voorFase5, let identiteit = gegevens.identiteit {
                    identiteitsKaart(identiteit)
                }
                if gegevens.voorFase5 {
                    Kaart(kop: "Migratie", rechterKop: "Fase 5") {
                        Text("Geboortebewijs is van vóór fase 5 (bevat placeholders) — migreer via loop.py, modus 5.")
                            .font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
                    }
                }
                HStack(alignment: .top, spacing: 18) {
                    registerKaart(gegevens)
                    tellerKaart(gegevens)
                }
                logboekKaart(gegevens: gegevens)
            } else if fout == nil {
                LegeStaat(kop: "Geen boom geselecteerd",
                          tekst: "Vul hierboven het pad naar een geplante boom in — bijv. ~/mijn-brein — en druk op 'Laad status' om de machine-feiten op te vragen.",
                          regels: ["de identiteit komt rechtstreeks uit het geboortebewijs.json van de boom",
                                   "het register toont of de boom verbonden is met een oerwoud-brein",
                                   "de tellers tonen VOORSTELLEN: wachtend op ratificatie of reeds verzonden",
                                   "de tijdlijn hieronder toont de append-only historie conform het faalcontract"])

                // DEMO: Voorbeeld append-only tijdlijn conform faalcontract
                demoTijdlijnKaart
            }
            Spacer(minLength: 16)
        }
        .padding(28)
    }

    // MARK: - Kop & Zoekveld

    private var kop: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("01 STATUS · IDENTITEIT & REGISTER")
                .font(Thema.tekst(10, gewicht: .semibold))
                .tracking(3)
                .foregroundStyle(Thema.kleur(.gedempt))
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text("De staat van de ").font(Thema.display(30))
                Text("boom.").font(Thema.display(30, cursief: true)).foregroundStyle(Thema.kleur(.zacht))
            }
        }
    }

    private var zoekrij: some View {
        HStack(spacing: 12) {
            HStack {
                Image(systemName: "folder")
                    .font(.system(size: 13))
                    .foregroundStyle(Thema.kleur(.gedempt))
                TextField("Pad naar de boom, bijv. ~/mijn-brein", text: $boomPad,
                          prompt: Text("Pad naar de boom, bijv. ~/mijn-brein")
                              .font(Thema.tekst(13)).foregroundColor(Thema.kleur(.zacht)))
                    .textFieldStyle(.plain)
                    .font(Thema.tekst(13))
                    .foregroundStyle(Thema.kleur(.inkt))
            }
            .padding(10)
            .overlay(Rectangle().stroke(Thema.kleur(.lijn), lineWidth: 1))
            .background(Thema.kleur(.papierZacht))

            PillKnop(titel: "Laad status", gevuld: true) { laad() }
        }
    }

    private var laadIndicator: some View {
        HStack(spacing: 10) {
            ProgressView()
                .controlSize(.small)
            Text("De adapter verifieert de machine-feiten via Process…")
                .font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.gedempt))
        }
        .padding(.vertical, 4)
    }

    // MARK: - Kaarten

    private func identiteitsKaart(_ identiteit: [String: Any]) -> some View {
        Kaart(kop: "Identiteit", rechterKop: "Geboortebewijs") {
            VStack(alignment: .leading, spacing: 10) {
                rij("Boom-id", identiteit["boom_id"] as? String ?? "?", monospaced: true)
                rij("Profiel", identiteit["profiel"] as? String ?? "?")
                rij("Machine", identiteit["machine"] as? String ?? "?")
                rij("Geplant", "\(identiteit["geplant_op"] as? String ?? "?")", monospaced: true)
            }
        }
    }

    private func registerKaart(_ g: StatusGegevens) -> some View {
        Kaart(kop: "Register", rechterKop: "Oerwoud") {
            VStack(alignment: .leading, spacing: 8) {
                if g.registerFout == "brein_onbereikbaar" {
                    Text("Brein onbereikbaar")
                        .font(Thema.tekst(13, gewicht: .medium))
                    Text("Het gekoppelde brein kan niet worden gevonden. Corrigeer via loop.py, modus 5.")
                        .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                } else if let breinPad = g.registerBreinPad {
                    HStack {
                        Text(g.registerStatus ?? "niet geregistreerd")
                            .font(Thema.tekst(13, gewicht: .medium))
                        Spacer()
                        StatusBadge(tekst: "Gekoppeld", stijl: .bewezen)
                    }
                    Text("brein: \(breinPad)")
                        .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                        .monospacedDigit()
                } else {
                    Text("Geen oerwoud-brein gekoppeld")
                        .font(Thema.tekst(13, gewicht: .medium))
                    Text("Deze boom draait standalone op deze machine.")
                        .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                }
            }
        }
    }

    private func tellerKaart(_ g: StatusGegevens) -> some View {
        Kaart(kop: "Voorstellen", rechterKop: "Curatie §9") {
            VStack(alignment: .leading, spacing: 10) {
                HStack(spacing: 12) {
                    StatusBadge(tekst: "\(g.wachtend) Wachtend", stijl: g.wachtend > 0 ? .mens : .neutraal)
                    StatusBadge(tekst: "\(g.verzonden) Verzonden", stijl: g.verzonden > 0 ? .bewezen : .neutraal)
                    Spacer()
                }
                Text("Voorstellen worden pas actief na menselijke ratificatie.")
                    .font(Thema.tekst(11))
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
        }
    }

    private func logboekKaart(gegevens: StatusGegevens) -> some View {
        Kaart(kop: "Logboek (append-only)", rechterKop: "Laatste Mijlpaal") {
            VStack(alignment: .leading, spacing: 12) {
                if let laatste = gegevens.laatste {
                    TijdlijnRij(tijdstip: formatteerTijd(laatste["tijdstip"] as? String),
                                titel: laatste["stap"] as? String ?? "Mijlpaal",
                                detail: "Status: \(laatste["status"] as? String ?? "?") — geregistreerd in logboek.json",
                                statusTekst: laatste["status"] as? String ?? "geslaagd",
                                stijl: (laatste["status"] as? String == "geslaagd") ? .bewezen : .mens,
                                isEerste: true, isLaatste: true)
                } else {
                    Text("Nog geen append-only logboekregels geregistreerd.")
                        .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                }
            }
        }
    }

    // DEMO: Getrouwe tijdlijn conform het faalcontract voor weergave vóór laden
    private var demoTijdlijnKaart: some View {
        Kaart(kop: "Logboek (append-only)", rechterKop: "Voorbeeld · Faalcontract") {
            VStack(alignment: .leading, spacing: 0) {
                Text("VOORBEELD VAN EEN BEWEZEN BOOM-HISTORIE (APPEND-ONLY):")
                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                    .foregroundStyle(Thema.kleur(.gedempt))
                    .padding(.bottom, 14)

                TijdlijnRij(tijdstip: "15:40:12",
                            titel: "stap-001: Mappen aanmaken (kern)",
                            detail: "bewijs: shell_check — 'alle kernmappen bestaan' → OK",
                            statusTekst: "✓ Bewezen",
                            stijl: .bewezen,
                            isEerste: true, isLaatste: false)

                TijdlijnRij(tijdstip: "15:40:14",
                            titel: "stap-002: Sjabloon INDEX.md kopiëren",
                            detail: "bewijs: file_equals — identiek aan sjabloon (SHA256) → OK",
                            statusTekst: "✓ Bewezen",
                            stijl: .bewezen,
                            isEerste: false, isLaatste: false)

                TijdlijnRij(tijdstip: "15:40:17",
                            titel: "stap-005: Logboek initialiseren",
                            detail: "bewijs: json_valid — top-level array gevalideerd → OK",
                            statusTekst: "✓ Bewezen",
                            stijl: .bewezen,
                            isEerste: false, isLaatste: false)

                TijdlijnRij(tijdstip: "15:41:02",
                            titel: "stap-008: Structuur tonen aan de mens",
                            detail: "bewijs: mens_verificatie — wacht op curatie door mens",
                            statusTekst: "Mens-moment",
                            stijl: .mens,
                            isEerste: false, isLaatste: true)
            }
        }
    }

    private func foutKaart(_ tekst: String) -> some View {
        Kaart(kop: "Fout", rechterKop: "Faalcontract §7") {
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "exclamationmark.triangle")
                    .font(.system(size: 14))
                Text(tekst)
                    .font(Thema.tekst(13, gewicht: .medium))
            }
        }
    }

    private func rij(_ label: String, _ waarde: String, monospaced: Bool = false) -> some View {
        HStack(alignment: .top) {
            Text(label)
                .font(Thema.tekst(11, gewicht: .medium))
                .tracking(1)
                .textCase(.uppercase)
                .foregroundStyle(Thema.kleur(.gedempt))
                .frame(width: 90, alignment: .leading)
            Text(waarde)
                .font(Thema.tekst(13, gewicht: .medium))
                .monospacedDigit()
                .textSelection(.enabled)
            Spacer()
        }
    }

    private func formatteerTijd(_ t: String?) -> String {
        guard let t, !t.isEmpty else { return "--:--:--" }
        // Als het een ISO timestamp is, neem het tijd-deel
        if t.contains("T") {
            let delen = t.components(separatedBy: "T")
            if delen.count > 1 {
                return String(delen[1].prefix(8))
            }
        }
        return String(t.suffix(8))
    }

    private func laad() {
        fout = nil
        Task {
            do {
                let resultaat = try await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                                      commando: "status", invoer: ["doel": boomPad])
                await MainActor.run {
                    if resultaat.ok {
                        gegevens = StatusGegevens(resultaat.data)
                    } else {
                        fout = resultaat.fout ?? "onbekende adapter-fout"
                        gegevens = nil
                    }
                }
            } catch {
                await MainActor.run { fout = error.localizedDescription; gegevens = nil }
            }
        }
    }
}
