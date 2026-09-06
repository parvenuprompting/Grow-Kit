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
    @State private var launchAgentAan = false
    @State private var gekozenNaam = "sprout"
    @State private var gekozenModus = "lokaal"
    @State private var gekozenCloudModel: [String: String] = [:]
    @State private var eigenInvoer: [String: String] = [:]
    @State private var tabData: [String: Any]? = nil

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                kop
                statusKaart
                if let melding { meldingRegel(melding, ok: meldingOk) }
                naamKeuzeKaart
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
                        PillKnop(titel: launchAgentAan ? "Auto-verfrissen uit" : "Auto-verfrissen aan (48u)",
                                 gevuld: false, compact: true) { wisselLaunchAgent() }
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

    // MARK: Naam-keuze (6 tiers · cloud/lokaal · RAM-vergrendeling)

    private var naamKeuzeKaart: some View {
        Kaart(kop: "Welke CyberSeed antwoordt?", rechterKop: ramLabel) {
            VStack(alignment: .leading, spacing: 12) {
                if let d = tabData, let namen = d["namen"] as? [String: [String: Any]] {
                    let titels = d["titels"] as? [String: String] ?? [:]
                    ForEach(namen.keys.sorted(), id: \.self) { sleutel in
                        naamRij(sleutel,
                                titels[sleutel] ?? sleutel,
                                namen[sleutel] ?? [:])
                    }
                } else {
                    Text("Instellingen laden…").font(Thema.tekst(11))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
                Text("Lokaal is de eindbestemming — cloud is de brug. Sprout is de slimme default; zwaardere namen kies je expliciet.")
                    .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
            }
        }
    }

    private var ramLabel: String {
        if let d = tabData,
           let klasse = d["ram_klasse"] as? String,
           let gb = d["ram_gb"] as? Int {
            return "RAM \(gb) GB · klasse \(klasse)"
        }
        return "RAM detecteren…"
    }

    private func naamRij(_ sleutel: String, _ titel: String,
                         _ info: [String: Any]) -> some View {
        let status = info["status"] as? String ?? "?"
        let model = info["model"] as? String ?? "—"
        let vergrendeld = info["vergrendeld"] as? Bool ?? false
        let grootte = info["download_grootte"] as? String ?? ""
        let minRam = info["min_ram_gb"] as? Int ?? 0
        let gekozen = gekozenNaam == sleutel && gekozenModus != ""

        return VStack(alignment: .leading, spacing: 5) {
            HStack {
                Circle()
                    .fill(kleurVoor(status))
                    .frame(width: 7, height: 7)
                Text(titel).font(Thema.tekst(12, gewicht: gekozen ? .semibold : .medium))
                Spacer()
                if gekozen {
                    Text("actief").font(Thema.tekst(9, gewicht: .semibold)).tracking(1)
                }
            }
            if vergrendeld {
                Text("Vergrendeld — vereist minimaal \(minRam) GB RAM")
                    .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
            } else {
                HStack {
                    Text(model).font(Thema.tekst(10)).monospaced()
                        .foregroundStyle(Thema.kleur(.zacht))
                    if !grootte.isEmpty && status == "niet geinstalleerd" {
                        Text("· \(grootte) download").font(Thema.tekst(10))
                            .foregroundStyle(.orange)
                    }
                    Spacer()
                }
                HStack(spacing: 8) {
                    PillKnop(titel: "Lokaal", gevuld: gekozenModus == "lokaal" && gekozenNaam == sleutel, compact: true) {
                        gekozenNaam = sleutel; gekozenModus = "lokaal"
                    }
                    .disabled(status != "geinstalleerd")
                    PillKnop(titel: "Cloud", gevuld: gekozenModus == "cloud" && gekozenNaam == sleutel, compact: true) {
                        gekozenNaam = sleutel
                        gekozenModus = "cloud"
                        if gekozenCloudModel[sleutel] == nil {
                            gekozenCloudModel[sleutel] = cloudDefaultVoor(sleutel)
                        }
                    }
                    if status == "niet geinstalleerd",
                       let cmd = info["pull_commando"] as? String {
                        Text(cmd).font(.system(size: 9)).monospaced()
                            .foregroundStyle(Thema.kleur(.gedempt))
                    }
                }
            }

            if !vergrendeld {
                cloudOptieRij(sleutel)
            }
        }
        .padding(.vertical, 4)
    }

    private func cloudOptieRij(_ sleutel: String) -> some View {
        var opties = cloudOptiesVoor(sleutel)
        let eigen = eigenCloudModel(sleutel)
        if !eigen.isEmpty && !opties.contains(eigen) { opties.append(eigen) }
        return VStack(alignment: .leading, spacing: 5) {
            HStack {
                Text("cloud-model:").font(Thema.tekst(10))
                    .foregroundStyle(Thema.kleur(.gedempt))
                Picker("", selection: bindingCloud(sleutel, opties)) {
                    ForEach(opties, id: \.self) { o in
                        Text(o).tag(o)
                    }
                }
                .labelsHidden()
                .font(Thema.tekst(10))
                Spacer()
            }
            HStack {
                TextField("eigen OpenRouter-model-id (bijv. vendor/model)",
                          text: bindingEigen(sleutel))
                    .textFieldStyle(.plain)
                    .font(Thema.tekst(10)).monospaced()
                    .padding(6)
                    .background(RoundedRectangle(cornerRadius: 6)
                        .stroke(Thema.kleur(.lijn)))
                PillKnop(titel: "Bewaar", gevuld: false, compact: true) {
                    bewaarEigen(sleutel)
                }
            }
            Text("De eigen id overschrijft de dropdown voor deze naam. Systeemprompt hoort bij de naam, niet bij het model.")
                .font(Thema.tekst(9)).foregroundStyle(Thema.kleur(.gedempt))
        }
        .padding(.leading, 17)
        .padding(.bottom, 6)
    }

    private func eigenCloudModel(_ sleutel: String) -> String {
        if let d = tabData,
           let eigen = d["eigen_cloud"] as? [String: String] {
            return eigen[sleutel] ?? ""
        }
        return ""
    }

    private func bindingEigen(_ sleutel: String) -> Binding<String> {
        Binding(
            get: { eigenInvoer[sleutel] ?? eigenCloudModel(sleutel) },
            set: { eigenInvoer[sleutel] = $0 })
    }

    private func bewaarEigen(_ sleutel: String) {
        let waarde = (eigenInvoer[sleutel] ?? "").trimmingCharacters(in: .whitespaces)
        Task {
            let r = await roep("cyberseedinstellingen",
                               ["zet_eigen_cloud": sleutel, "model": waarde])
            await MainActor.run {
                if let r, r.ok {
                    meldingOk = true
                    melding = waarde.isEmpty
                        ? "Eigen cloud-model gewist voor \(sleutel)."
                        : "Eigen cloud-model bewaard voor \(sleutel)."
                    laadAlles()
                } else {
                    meldingOk = false
                    melding = r?.fout ?? "Bewaren mislukt."
                }
            }
        }
    }

    private func cloudOptiesVoor(_ sleutel: String) -> [String] {
        if let d = tabData, let opties = d["cloud_opties"] as? [String: [String]],
           let lijst = opties[sleutel], !lijst.isEmpty {
            return lijst
        }
        return [cloudDefaultVoor(sleutel)]
    }

    private func cloudDefaultVoor(_ sleutel: String) -> String {
        cloudOptiesVoor(sleutel).first ?? ""
    }

    private func bindingCloud(_ sleutel: String, _ opties: [String]) -> Binding<String> {
        Binding(
            get: { gekozenCloudModel[sleutel] ?? opties.first ?? "" },
            set: { gekozenCloudModel[sleutel] = $0 })
    }

    private func kleurVoor(_ status: String) -> Color {
        switch status {
        case "geinstalleerd": return .green
        case "vergrendeld": return .gray
        default: return .orange
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

    // MARK: LaunchAgent (auto-verfrissen 48u)

    private var plistPad: String {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        return home + "/Library/LaunchAgents/nl.growkit.cyberseed-verfris.plist"
    }

    private func launchAgentStatus() {
        let r = Process()
        r.executableURL = URL(fileURLWithPath: "/bin/bash")
        r.arguments = ["-c",
            "launchctl print gui/$(id -u)/nl.growkit.cyberseed-verfris >/dev/null 2>&1 && echo AAN"]
        let pipe = Pipe(); r.standardOutput = pipe
        try? r.run(); r.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        launchAgentAan = String(decoding: data, as: UTF8.self).contains("AAN")
    }

    private func wisselLaunchAgent() {
        let fm = FileManager.default
        let plist = plistPad
        if launchAgentAan {
            _ = shell("launchctl bootout gui/$(id -u)/nl.growkit.cyberseed-verfris")
            try? fm.removeItem(atPath: plist)
            launchAgentAan = false
            meldingOk = true
            melding = "Auto-verfrissen uit."
        } else {
            let home = fm.homeDirectoryForCurrentUser.path
            let plistInhoud = """
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>nl.growkit.cyberseed-verfris</string>
  <key>ProgramArguments</key><array>
    <string>\(interpreter)</string>
    <string>\(repoPad)/scripts/cyberseed_verfris.py</string>
  </array>
  <key>StartInterval</key><integer>172800</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>\(home)/.growkit/cyberseed/cron.log</string>
  <key>StandardErrorPath</key><string>\(home)/.growkit/cyberseed/cron.log</string>
</dict></plist>
"""
            try? fm.createDirectory(atPath: (plist as NSString).deletingLastPathComponent,
                                    withIntermediateDirectories: true)
            try? plistInhoud.write(toFile: plist, atomically: true, encoding: .utf8)
            _ = shell("launchctl bootstrap gui/$(id -u) \(plist)")
            launchAgentAan = true
            meldingOk = true
            melding = "Auto-verfrissen aan — elke 48 uur."
        }
    }

    @discardableResult
    private func shell(_ cmd: String) -> String {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = ["-c", cmd]
        let pipe = Pipe(); p.standardOutput = pipe; p.standardError = pipe
        try? p.run(); p.waitUntilExit()
        return String(decoding: pipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
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
            let tabR = await roep("cyberseedinstellingen")
            await MainActor.run {
                launchAgentStatus()
                if let tabR, tabR.ok { tabData = tabR.data }
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
            var invoerD: [String: Any] = ["bericht": tekst, "van": van,
                                          "naam": gekozenNaam,
                                          "modus": gekozenModus]
            if gekozenModus == "cloud", let cm = gekozenCloudModel[gekozenNaam] {
                invoerD["cloud_model"] = cm
            }
            let r = await roep("cyberseedchat", invoerD)
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