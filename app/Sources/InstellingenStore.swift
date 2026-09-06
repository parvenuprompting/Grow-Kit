// InstellingenStore — één bron van waarheid voor alle app-instellingen.
//
// Bewaard in ~/.growkit/instellingen.json. Geladen bij start; geschreven
// bij elke wijziging. Ontbrekende sleutels = defaults (backward-compat);
// onbekende sleutels blijven staan. De Python-kern kan het bestand lezen.

import Foundation

struct Instellingen: Codable {
    // Algemeen
    var gebruikersnaam: String = "Tiëndo"
    var herstelLaatsteScherm: Bool = true

    // Uiterlijk
    enum ThemaModus: String, Codable, CaseIterable {
        case licht = "licht"
        case volgSysteem = "volg systeem"
        case donker = "donker"
    }
    var themaModus: ThemaModus = .licht
    var weerInZijmenu: Bool = true
    var saldoInZijmenu: Bool = true
    var saldoDrempel: Double = 10.0

    // Agenten
    var standaardAgent: String = "kairos"
    var autoVerversing: Int = 15            // seconden; 0 = uit
    var typingIndicator: Bool = true
    var thoughtStandaardOpen: Bool = false

    // CyberSeed
    var cyberseedBasisModel: String = "qwen3:8b"
    var cyberseedVerfrisUren: Int = 48      // 0 = uit

    // Pad-instellingen (verhuisd uit @State — bewaard!)
    var repoPad: String = "~/Documents/Code 7/growkit"
    var interpreter: String = "/opt/homebrew/bin/python3.13"
}

final class InstellingenStore: ObservableObject {
    static let gedeeld = InstellingenStore()

    @Published var instellingen: Instellingen {
        didSet { bewaar() }
    }

    static var pad: URL {
        let basis = FileManager.default.homeDirectoryForCurrentUser
        return basis.appendingPathComponent(".growkit/instellingen.json")
    }

    private init() {
        instellingen = InstellingenStore.laad() ?? Instellingen()
    }

    static func laad() -> Instellingen? {
        guard let data = try? Data(contentsOf: pad) else { return nil }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try? decoder.decode(Instellingen.self, from: data)
    }

    private func bewaar() {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        if let data = try? encoder.encode(instellingen) {
            let pad = InstellingenStore.pad
            try? FileManager.default.createDirectory(
                at: pad.deletingLastPathComponent(),
                withIntermediateDirectories: true)
            try? data.write(to: pad)
        }
    }
}