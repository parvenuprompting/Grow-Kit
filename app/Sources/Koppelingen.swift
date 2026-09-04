// Koppelingen — providers en breinen van deze machine.
// Opslag: ~/.growkit/koppelingen.json (buiten de repo, per-machine) — API-sleutels
// verlaten GrowKit nooit en komen nooit in de repo, het logboek of de chat.

import Foundation

struct ProviderKoppeling: Identifiable, Codable, Equatable {
    var id: String { naam }
    var naam: String
    var type: String            // "http" of "cli"
    var endpoint: String
    var model: String
    var apiSleutel: String      // uitsluitend lokaal; nooit in de repo of chat
}

struct BreinKoppeling: Identifiable, Codable, Equatable {
    var id: String { naam }
    var naam: String
    var pad: String
    var remote: String          // git-remote voor cross-machine sync (fase 5.1)
}

struct KoppelingenDocument: Codable {
    var providers: [ProviderKoppeling] = []
    var breinen: [BreinKoppeling] = []
    var actieveProvider: String = KoppelingenStore.standaardProvider
    var actiefBrein: String = "Agent-Brain"
}

final class KoppelingenStore: ObservableObject {
    static let standaardProvider = "Agent-Brain (lokaal)"

    @Published var providers: [ProviderKoppeling] = [] {
        didSet { opsla() }
    }
    @Published var breinen: [BreinKoppeling] = [] {
        didSet { opsla() }
    }
    @Published var actieveProvider: String = KoppelingenStore.standaardProvider {
        didSet { opsla() }
    }
    @Published var actiefBrein: String = "Agent-Brain" {
        didSet { opsla() }
    }
    @Published var laadFout: String?

    /// Onze eigen ontworpen brein-provider is de standaard van het oerwoud.
    static let standaardBreinen: [BreinKoppeling] = [
        BreinKoppeling(naam: "Agent-Brain",
                       pad: "~/Projects/Agent-Brain",
                       remote: "github.com/parvenuprompting/Agent-Family-Brain")
    ]

    private var documentPad: URL {
        URL(fileURLWithPath: NSHomeDirectory())
            .appendingPathComponent(".growkit")
            .appendingPathComponent("koppelingen.json")
    }

    init() {
        laad()
    }

    func laad() {
        let pad = documentPad
        guard FileManager.default.fileExists(atPath: pad.path) else {
            breinen = Self.standaardBreinen
            actiefBrein = "Agent-Brain"
            return
        }
        do {
            let data = try Data(contentsOf: pad)
            let document = try JSONDecoder().decode(KoppelingenDocument.self, from: data)
            providers = document.providers
            breinen = document.breinen.isEmpty ? Self.standaardBreinen : document.breinen
            actieveProvider = document.actieveProvider
            actiefBrein = document.actiefBrein
            laadFout = nil
        } catch {
            laadFout = "koppelingen.json is corrupt — roep de mens, nooit auto-repareren: \(error.localizedDescription)"
        }
    }

    func opsla() {
        let document = KoppelingenDocument(providers: providers, breinen: breinen,
                                           actieveProvider: actieveProvider,
                                           actiefBrein: actiefBrein)
        let pad = documentPad
        do {
            try pad.path.withCString { _ in () }
            try FileManager.default.createDirectory(at: pad.deletingLastPathComponent(),
                                                    withIntermediateDirectories: true)
            let data = try JSONEncoder().encode(document)
            try data.write(to: pad, options: .atomic)
            laadFout = nil
        } catch {
            laadFout = "koppelingen.json kon niet worden opgeslagen: \(error.localizedDescription)"
        }
    }

    /// De keuze die de chatbalk toont: geconfigureerde providers + ons eigen brein.
    var providerKeuzes: [String] {
        [Self.standaardProvider] + providers.map(\.naam)
    }
}
