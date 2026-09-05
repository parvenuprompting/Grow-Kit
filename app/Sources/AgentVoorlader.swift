// AgentVoorlader — laadt de governor-data bij app-start zodat het Agenten-tab
// meteen vol is, niet pas na 15-20 seconden navigeren + laden.
// Gedeelde singleton, gelijk aan FamilieStatusStore.

import SwiftUI

final class AgentVoorlader: ObservableObject {
    static let gedeeld = AgentVoorlader()

    @Published var geladen = false
    @Published var fout: String?
    @Published var limieten: [String: Any] = [:]
    @Published var agents: [[String: Any]] = []
    @Published var taken: [String: Any] = [:]
    @Published var meldingen: [[String: Any]] = []
    @Published var familie: [[String: Any]] = []
    @Published var voorstellen: [[String: Any]] = []

    private var timer: Timer?

    func start(repoPad: String, interpreter: String, runner: Runner) {
        laad(repoPad: repoPad, interpreter: interpreter, runner: runner)
        guard timer == nil else { return }
        timer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            self?.laad(repoPad: repoPad, interpreter: interpreter, runner: runner)
        }
    }

    func laad(repoPad: String, interpreter: String, runner: Runner) {
        Task {
            async let r = try? runner.roep(repoPad: repoPad, interpreter: interpreter,
                                            commando: "governor",
                                            invoer: ["doel": "~/growkit-governor"])
            async let f = try? runner.roep(repoPad: repoPad, interpreter: interpreter,
                                            commando: "familie",
                                            invoer: ["actie": "status"])
            async let s = try? runner.roep(repoPad: repoPad, interpreter: interpreter,
                                            commando: "agentstatus", invoer: [:])
            async let o = try? runner.roep(repoPad: repoPad, interpreter: interpreter,
                                            commando: "observaties", invoer: [:])

            let (gov, fam, stat, obs) = await (r, f, s, o)

            await MainActor.run {
                if let obs, let lijst = obs.data["voorstellen"] as? [[String: Any]] {
                    voorstellen = lijst
                }
                if let fam, fam.ok, let famData = fam.data["familie"] as? [[String: Any]] {
                    familie = famData
                }
                if let stat, let agentsList = stat.data["agents"] as? [[String: Any]] {
                    var kaart: [String: String] = [:]
                    for a in agentsList {
                        if let naam = a["agent"] as? String,
                           let st = a["status"] as? String {
                            kaart[naam] = st
                        }
                    }
                    FamilieStatusStore.gedeeld.leeft = kaart
                }
                if let gov, gov.ok {
                    fout = nil
                    limieten = gov.data["limieten"] as? [String: Any] ?? [:]
                    agents = gov.data["agents"] as? [[String: Any]] ?? []
                    taken = gov.data["taken"] as? [String: Any] ?? [:]
                    meldingen = gov.data["observer_meldingen"] as? [[String: Any]] ?? []
                } else {
                    // Fout alleen bewaren bij de eerste laadpoging
                    if !geladen { fout = gov?.fout ?? "De adapter reageerde niet." }
                }
                geladen = true
            }
        }
    }
}