// CyberSeedView — scherm 19: het lokale model met zijn eigen SOUL.
//
// CyberSeed Sprout v0.5: Ollama-lokaal, SOUL-snapshot uit GrowKit-data,
// chat in Agent Chat-stijl. Alles via adapter (cyberseed_*-commando's).

import SwiftUI

struct CyberSeedBericht: Identifiable {
    let rol: String      // gebruiker | assistent
    let tekst: String
    var id: String { rol + "|" + tekst.prefix(120) }
}

struct CyberSeedView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    @State private var status: [String: Any]?
    @State private var soul: String?
    @State private var toonSoul = false
    @State private var berichten: [CyberSeedBericht] = []
    @State private var invoer = ""
    @State private var bezig = false
    @State private var melding: String?
    @State private var meldingOk = false
    @State private var bevestigWis = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                kop
                statusKaart
                if let melding { meldingRegel(melding, ok: meldingOk) }
                chatKaart
                soulKaart
                Spacer(minLength: 16)
            }
            .padding(28)
        }
        .background(Thema.kleur(.papier))
        .onAppear { laadAlles() }
        .alert("Chatlog definitief wissen?", isPresented: $bevestigWis) {
            Button("Wis", role: .destructive) { wisLog() }
            Button("Annuleer", role: .cancel) {}
        } message: {
            Text("De lokale chatgeschiedenis van CyberSeed wordt verwijderd. Dit kan niet ongedaan worden.")
        }
    }

    // MARK: Kop

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("19 CYBERSEED · LOKAAL MODEL MET EIGEN SOUL")
                .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            HStack(alignment: .firstTextBaseline) {
                Text("CyberSeed").font(Thema.display(30))
                Text("Sprout v0.5").font(Thema.display(17, cursief: true))
                    .foregroundStyle(Thema.kleur(.zacht))
                Spacer()
                PillKnop(titel: "Ververs", gevuld: false, compact: true) { laadAlles() }
            }
            Text("CyberSeed is het lokale model van het huis. Hij leest bij elk gesprek zijn SOUL — een automatisch bijgewerkte samenvatting van wie jij bent, wat er wacht en waar je aan werkt. Draait volledig op deze Mac; niets verlaat het huis.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: Status

    private var statusKaart: some View {
        Kaart(kop: "Status", rechterKop: "CYBERSEED SPROUT V0.5") {
            if let s = status {
                VStack(alignment: .leading, spacing: 10) {
                    statusRij("Ollama", draait: s["draait"] as? Bool ?? false,
                              goed: "draait", slecht: "niet bereikbaar")
                    statusRij("Basis-model (\(s["basis_model"] as? String ?? "?"))",
                              draait: s["sprout_basis_aanwezig"] as? Bool ?? false,
                              goed: "aanwezig",
                              slecht: "ontbreekt — pull met: ollama pull \(s["basis_model"] as? String ?? "qwen3:8b")")
                    HStack {
                        Text("SOUL-leeftijd").font(Thema.tekst(11))
                        Spacer()
                        if let uren = s["soul_leeftijd_uren"] as? Double {
                            Text(leeftijdTekst(uren))
                                .font(Thema.tekst(11, gewicht: .semibold))
                        } else {
                            Text("nog geen SOUL").font(Thema.tekst(11))
                                .foregroundStyle(Thema.kleur(.gedempt))
                        }
                    }
                    HStack {
                        PillKnop(titel: "Genereer SOUL nu", gevuld: true) { genereerSoul() }
                        Spacer()
                        PillKnop(titel: "Wis chatlog", gevuld: false, compact: true) {
                            bevestigWis = true
                        }
                    }
                }
            } else {
                Text("Status laden…").font(Thema.tekst(11))
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
        }
    }

    private func statusRij(_ titel: String, draait: Bool, goed: String, slecht: String) -> some View {
        HStack {
            Circle().fill(draait ? .green : .red).frame(width: 7, height: 7)
            Text(titel).font(Thema.tekst(11))
            Spacer()
            Text(draait ? goed : slecht)
                .font(Thema.tekst(11, gewicht: draait ? .medium : .semibold))
                .foregroundStyle(draait ? Thema.kleur(.zacht) : .red)
                .lineLimit(2)
                .multilineTextAlignment(.trailing)
        }
    }

    private func leeftijdTekst(_ uren: Double) -> String {
        if uren < 1 { return "net vers (\(Int(uren * 60)) min)" }
        if uren < 48 { return "\(Int(uren)) uur" }
        return "\(Int(uren / 24)) dagen — overweeg te verversen"
    }

    // MARK: Chat

    private var chatKaart: some View {
        Kaart(kop: "Gesprek", rechterKop: "LOKAAL · NIETS VERLAAT HET HUIS") {
            VStack(alignment: .leading, spacing: 10) {
                if berichten.isEmpty {
                    Text("Zeg hallo — CyberSeed leest zijn SOUL en weet wie je bent, wat er wacht en waar je aan werkt.")
                        .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                }
                ForEach(berichten) { b in
                    VStack(alignment: .leading, spacing: 3) {
                        Text(b.rol == "gebruiker" ? "Jij" : "CyberSeed")
                            .font(Thema.tekst(8, gewicht: .semibold)).tracking(1.5)
                            .foregroundStyle(Thema.kleur(.gedempt))
                        Text(b.tekst).font(Thema.tekst(12))
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(.vertical, 3)
                }
                if bezig {
                    TypingStip(vertraging: 0.4)
                }
                Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
                HStack {
                    TextField("Praat met CyberSeed…", text: $invoer)
                        .textFieldStyle(.plain)
                        .font(Thema.tekst(12))
                        .onSubmit { stuur() }
                    PillKnop(titel: "Stuur", gevuld: true, compact: true) { stuur() }
                        .disabled(invoer.trimmingCharacters(in: .whitespaces).isEmpty || bezig)
                }
            }
        }
    }

    // MARK: SOUL

    private var soulKaart: some View {
        Kaart(kop: "Zijn SOUL (wat hij bij elk gesprek leest)", rechterKop: nil) {
            VStack(alignment: .leading, spacing: 8) {
                if let soul {
                    if toonSoul {
                        Text(soul).font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(Thema.kleur(.zacht))
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    PillKnop(titel: toonSoul ? "Verberg SOUL" : "Bekijk SOUL",
                             gevuld: false, compact: true) { toonSoul.toggle() }
                } else {
                    Text("Nog geen SOUL — genereer er één hierboven.")
                        .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                }
            }
        }
    }

    @ViewBuilder private func meldingRegel(_ tekst: String, ok: Bool) -> some View {
        HStack(spacing: 8) {
            Image(systemName: ok ? "checkmark.circle" : "exclamationmark.triangle")
                .font(.system(size: 12))
            Text(tekst).font(Thema.tekst(12))
        }
        .foregroundStyle(Thema.kleur(ok ? .inkt : .zacht))
    }

    // MARK: Data

    private func roep(_ commando: String, _ invoerDict: [String: Any] = [:]) async -> AdapterResultaat? {
        try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                               commando: commando, invoer: invoerDict)
    }

    private func laadAlles() {
        Task {
            let s = await roep("cyberseedstatus")
            let soulR = await roep("cyberseedsoul", ["actie": "lees"])
            let log = await roep("cyberseedlog", ["aantal": 30])
            await MainActor.run {
                if let s, s.ok { status = s.data }
                if let soulR, soulR.ok { soul = soulR.data["soul"] as? String }
                if let log, log.ok, let regels = log.data["regels"] as? [[String: Any]] {
                    berichten = regels.map { r in
                        CyberSeedBericht(rol: r["rol"] as? String ?? "gebruiker",
                                         tekst: r["tekst"] as? String ?? "")
                    }
                }
            }
        }
    }

    private func genereerSoul() {
        Task {
            let r = await roep("cyberseedsoul", ["actie": "genereer"])
            await MainActor.run {
                if let r, r.ok {
                    soul = r.data["soul"] as? String
                    meldingOk = true
                    melding = "SOUL vers gegenereerd."
                    laadAlles()
                } else {
                    meldingOk = false
                    melding = r?.fout ?? "Genereren mislukt."
                }
            }
        }
    }

    private func stuur() {
        let tekst = invoer.trimmingCharacters(in: .whitespaces)
        guard !tekst.isEmpty, !bezig else { return }
        let van = InstellingenStore.gedeeld.instellingen.gebruikersnaam
        berichten.append(CyberSeedBericht(rol: "gebruiker", tekst: tekst))
        invoer = ""
        bezig = true
        Task {
            let r = await roep("cyberseedchat", ["bericht": tekst, "van": van])
            await MainActor.run {
                bezig = false
                if let r, r.ok {
                    berichten.append(CyberSeedBericht(
                        rol: "assistent",
                        tekst: r.data["antwoord"] as? String ?? ""))
                } else {
                    meldingOk = false
                    melding = r?.fout ?? "CyberSeed reageerde niet — draait Ollama?"
                }
            }
        }
    }

    private func wisLog() {
        Task {
            let r = await roep("cyberseedwis", ["bevestig": true])
            await MainActor.run {
                if let r, r.ok {
                    berichten = []
                    meldingOk = true
                    melding = "Chatlog gewist."
                }
            }
        }
    }
}