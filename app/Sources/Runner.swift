// Runner — roept adapter.py rechtstreeks aan via Process, met time-out.
// Contract: JSON in via stdin, precies één JSON-document uit op stdout.

import Foundation

struct AdapterResultaat {
    let ok: Bool
    let data: [String: Any]
    let vragen: [[String: Any]]
    let fout: String?
    let stappen: [[String: Any]]
    let exitCode: Int32
}

enum AdapterFout: Error, LocalizedError {
    case geenJSON(String)
    case proces(String)

    var errorDescription: String? {
        switch self {
        case .geenJSON(let details): return "Adapter-uitvoer is geen JSON: \(details)"
        case .proces(let details): return "Adapter-proces faalde: \(details)"
        }
    }
}

final class Runner: ObservableObject {
    static let standaardRepoPad = "~/Documents/Code 7/growkit"
    static let standaardInterpreter = "/opt/homebrew/bin/python3.13"

    @Published var bezig = false
    @Published var laatsteFout: String?

    private func voerUit(repoPad: String, interpreter: String,
                         arguments: [String], stdinData: String,
                         timeOut: TimeInterval = 120) throws -> AdapterResultaat {
        let repo = NSString(string: repoPad).expandingTildeInPath
        let adapter = URL(fileURLWithPath: repo).appendingPathComponent("adapter.py")
        guard FileManager.default.fileExists(atPath: adapter.path) else {
            throw AdapterFout.proces("adapter.py niet gevonden in \(repo) — stel het repo-pad in Instellingen in")
        }
        let proces = Process()
        proces.executableURL = URL(fileURLWithPath: interpreter)
        proces.arguments = arguments
        proces.currentDirectoryURL = URL(fileURLWithPath: repo)

        let stdout = Pipe()
        let stderr = Pipe()
        let stdin = Pipe()
        proces.standardOutput = stdout
        proces.standardError = stderr
        proces.standardInput = stdin

        try proces.run()
        stdin.fileHandleForWriting.write(stdinData.data(using: .utf8)!)
        stdin.fileHandleForWriting.closeFile()

        let deadline = Date().addingTimeInterval(timeOut)
        while proces.isRunning && Date() < deadline {
            Thread.sleep(forTimeInterval: 0.05)
        }
        if proces.isRunning {
            proces.terminate()
            throw AdapterFout.proces("time-out na \(Int(timeOut))s")
        }

        let uitData = stdout.fileHandleForReading.readDataToEndOfFile()
        guard let tekst = String(data: uitData, encoding: .utf8),
              let json = try? JSONSerialization.jsonObject(with: uitData) as? [String: Any] else {
            let voorproef = String(data: uitData.prefix(200), encoding: .utf8) ?? "<niet-tekst>"
            throw AdapterFout.geenJSON(voorproef)
        }
        return AdapterResultaat(
            ok: (json["ok"] as? Bool) ?? false,
            data: (json["data"] as? [String: Any]) ?? [:],
            vragen: (json["vragen"] as? [[String: Any]]) ?? [],
            fout: json["fout"] as? String,
            stappen: (json["stappen"] as? [[String: Any]]) ?? [],
            exitCode: proces.terminationStatus)
    }

    /// Adapter-aanroep: leest JSON, retourneert het resultaat of gooit een fout.
    func roep(repoPad: String, interpreter: String,
              commando: String, invoer: [String: Any],
              timeOut: TimeInterval = 120) async throws -> AdapterResultaat {
        await MainActor.run { self.bezig = true; self.laatsteFout = nil }
        defer { Task { await MainActor.run { self.bezig = false } } }
        let resultaat = try voerUit(repoPad: repoPad, interpreter: interpreter,
                                    arguments: [adapterPath(repoPad: repoPad), commando],
                                    stdinData: jsonToString(invoer), timeOut: timeOut)
        if !resultaat.ok, let fout = resultaat.fout {
            await MainActor.run { self.laatsteFout = fout }
        }
        return resultaat
    }

    private func adapterPath(repoPad: String) -> String {
        let repo = NSString(string: repoPad).expandingTildeInPath
        return URL(fileURLWithPath: repo).appendingPathComponent("adapter.py").path
    }

    private func jsonToString(_ invoer: [String: Any]) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: invoer, options: []) else {
            return "{}"
        }
        return String(data: data, encoding: .utf8) ?? "{}"
    }
}
