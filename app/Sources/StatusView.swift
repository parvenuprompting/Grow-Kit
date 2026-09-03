// Status-scherm — identiteit, register, tellers en logboek-momenten.

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
        VStack(alignment: .leading, spacing: 20) {
            kop
            StappenStreep(stappen: ["Pad", "Identiteit", "Register", "Tellers"])
            zoekrij
            if let fout { foutKaart(fout) }
            if gegevens == nil && fout == nil {
                LegeStaat(kop: "Nog geen boom geladen",
                          tekst: "Vul hierboven het pad naar een geplante boom in — bijv. ~/mijn-brein — en druk op 'Laad status'.",
                          regels: ["de identiteit komt uit het geboortebewijs van de boom",
                                   "het register vertelt bij welk brein de boom hoort",
                                   "de tellers tonen VOORSTELLEN wachtend en verzonden"])
            }
            if runner.bezig {
                Text("De adapter denkt na…").font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
            }
            if let gegevens {
                if let melding = gegevens.melding {
                    Kaart(kop: "Melding") {
                        Text(melding).font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
                    }
                }
                if !gegevens.voorFase5, let identiteit = gegevens.identiteit {
                    identiteitsKaart(identiteit)
                }
                if gegevens.voorFase5 {
                    Kaart(kop: "Migratie") {
                        Text("Geboortebewijs is van vóór fase 5 (placeholders) — migreer via loop.py, modus 5.")
                            .font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
                    }
                }
                registerKaart(gegevens)
                tellerKaart(gegevens)
                if let laatste = gegevens.laatste {
                    Kaart(kop: "Laatste mijlpaal / faal") {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("\(laatste["stap"] as? String ?? "?") — \(laatste["status"] as? String ?? "?")")
                                .font(Thema.tekst(13, gewicht: .medium))
                            Text(laatste["tijdstip"] as? String ?? "")
                                .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                        }
                    }
                }
            }
            Spacer()
        }
        .padding(28)
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("STATUS").font(Thema.tekst(10, gewicht: .semibold)).tracking(4).foregroundStyle(Thema.kleur(.zacht))
            Text("De staat van de boom").font(Thema.display(30))
        }
    }

    private var zoekrij: some View {
        HStack(spacing: 10) {
            TextField("Pad naar de boom, bijv. ~/mijn-brein", text: $boomPad)
                .textFieldStyle(.plain)
                .font(Thema.tekst(13))
                .padding(10)
                .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
            knop("Laad status") { laad() }
        }
    }

    private func identiteitsKaart(_ identiteit: [String: Any]) -> some View {
        Kaart(kop: "Identiteit") {
            VStack(alignment: .leading, spacing: 8) {
                rij("Boom-id", identiteit["boom_id"] as? String ?? "?")
                rij("Profiel", identiteit["profiel"] as? String ?? "?")
                rij("Machine", identiteit["machine"] as? String ?? "?")
                rij("Geplant", "\(identiteit["geplant_op"] as? String ?? "?")")
            }
        }
    }

    private func registerKaart(_ g: StatusGegevens) -> some View {
        Kaart(kop: "Register") {
            VStack(alignment: .leading, spacing: 6) {
                if g.registerFout == "brein_onbereikbaar" {
                    Text("Het brein is niet bereikbaar (verplaatst of weg?) — corrigeer via loop.py, modus 5.")
                        .font(Thema.tekst(13, gewicht: .medium))
                } else if let breinPad = g.registerBreinPad {
                    Text(g.registerStatus ?? "niet geregistreerd")
                        .font(Thema.tekst(13, gewicht: .medium))
                    Text("brein: \(breinPad)")
                        .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                } else {
                    Text("geen oerwoud-brein bekend op deze machine")
                        .font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
                }
            }
        }
    }

    private func tellerKaart(_ g: StatusGegevens) -> some View {
        Kaart(kop: "VOORSTEL") {
            HStack(spacing: 14) {
                StatusBadge(tekst: "\(g.wachtend) wachtend", bewezen: g.wachtend > 0)
                StatusBadge(tekst: "\(g.verzonden) verzonden", bewezen: g.verzonden > 0)
                Spacer()
            }
        }
    }

    private func foutKaart(_ tekst: String) -> some View {
        Kaart(kop: "Fout") {
            Text(tekst).font(Thema.tekst(13, gewicht: .medium))
        }
    }

    private func rij(_ label: String, _ waarde: String) -> some View {
        HStack(alignment: .top) {
            Text(label).font(Thema.tekst(12)).tracking(1).textCase(.uppercase)
                .foregroundStyle(Thema.kleur(.gedempt)).frame(width: 90, alignment: .leading)
            Text(waarde).font(Thema.tekst(13, gewicht: .medium))
                .textSelection(.enabled)
            Spacer()
        }
    }

    private func knop(_ titel: String, actie: @escaping () -> Void) -> some View {
        Button(action: actie) {
            Text(titel).font(Thema.tekst(12, gewicht: .medium))
                .padding(.horizontal, 18).padding(.vertical, 10)
        }
        .buttonStyle(.plain)
        .background(Thema.kleur(.inkt))
        .foregroundStyle(Thema.kleur(.papier))
        .clipShape(Capsule())
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
