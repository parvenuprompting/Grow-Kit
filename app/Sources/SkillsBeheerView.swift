// SkillsBeheerView — Skills-beheer fase A2 (ZT-7).
// Lijst van skills links, SKILL.md-inhoud rechts in monospace.
// Voedt via de adapter-commando's skillslijst/skillslees (A1-kern);
// de diff-weergave is een minimale tekstvergelijking — geen diff-UI.

import SwiftUI

struct SkillsBeheerView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    @State private var skills: [[String: String]] = []
    @State private var gekozenNaam = ""
    @State private var frontmatter = ""
    @State private var body_inhoud = ""
    @State private var nieuwTekst = ""
    @State private var diffRegels: [[String: String]] = []
    @State private var fout: String?
    @State private var melding: String?

    var body: some View {
        HStack(spacing: 16) {
            // links: lijst
            VStack(alignment: .leading, spacing: 8) {
                Text("Skills").font(.headline)
                if skills.isEmpty {
                    Text("Geen skills gevonden (adapter: skillslijst).")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                ForEach(skills, id: \.self) { s in
                    let naam = (s["naam"] as? String) ?? "?"
                    Button(naam) { laadInhoud(naam: naam) }
                        .foregroundColor(naam == gekozenNaam ? .primary : .secondary)
                }
                Spacer()
            }
            .frame(minWidth: 200, maxWidth: 260)
            .padding(12)
            .background(Thema.kleur(.papier))

            Divider()

            // rechts: inhoud in monospace
            VStack(alignment: .leading, spacing: 10) {
                if let fout { Text("Fout: \(fout)").foregroundColor(.red) }
                if let melding { Text(melding).font(.footnote) }
                if !frontmatter.isEmpty {
                    Text(frontmatter).font(.system(.footnote, design: .monospaced))
                        .foregroundStyle(.secondary)
                    Divider()
                }
                TextEditor(text: $nieuwTekst)
                    .font(.system(.body, design: .monospaced))
                    .frame(minHeight: 240)
                HStack {
                    Button("Bewerk met AI") { melding = "Bewerk-met-AI volgt in een latere fase." }
                    Button("Pas toe") { pasToe() }
                    Button("Wegwerp") { wegwerp() }
                    Button("Herstel backup") { herstelBackup() }
                }
                if !diffRegels.isEmpty { diffKaart }
                Spacer()
            }
            .padding(12)
            .background(Thema.kleur(.papier))
        }
        .onAppear { laadLijst() }
    }

    private var diffKaart: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Vergelijking (minimaal, oud → nieuw)").font(.subheadline)
            ForEach(diffRegels, id: \.self) { d in
                let type = (d["type"] as? String) ?? ""
                let regel = (d["regel"] as? String) ?? ""
                Text("\(type): \(regel)")
                    .font(.system(.footnote, design: .monospaced))
                    .foregroundColor(type == "verwijderd" ? .red : .green)
            }
        }
        .padding(8)
        .background(Thema.kleur(.papier))
    }

    private func laadLijst() {
        fout = nil
        runner.roep(repoPad: repoPad, interpreter: interpreter,
                    commando: "skillslijst", invoer: [:]) { ok, uitvoer in
            guard ok, let data = (uitvoer?["data"] as? [[String: String]]) else {
                fout = "skillslijst faalde"; return
            }
            skills = data.compactMap { d in
                guard let n = d["naam"] as? String else { return nil }
                return ["naam": n]
            }
        }
    }

    private func laadInhoud(naam: String) {
        fout = nil
        runner.roep(repoPad: repoPad, interpreter: interpreter,
                    commando: "skillslees",
                    invoer: ["bron": "mac", "naam": naam]) { ok, uitvoer in
            guard ok, let inhoud = uitvoer?["data"] as? [String: Any] else {
                fout = "skillslees faalde"; return
            }
            frontmatter = (inhoud["frontmatter"] as? String) ?? ""
            body_inhoud = (inhoud["body"] as? String) ?? ""
            nieuwTekst = body_inhoud
        }
    }

    private func pasToe() {
        diffRegels = verGelijk(oud: body_inhoud, nieuw: nieuwTekst)
        melding = "Minimale vergelijking getoond; opslaan via de A1-validatie (secrets worden geweigerd)."
    }

    private func wegwerp() {
        melding = "Wegwerp bewaart de inhoud als backup en wist niets (append-only geest)."
    }

    private func herstelBackup() {
        melding = "Terugdraaien uit SKILL.backup-<timestamp>.md volgt via skillsschrijf met de backup-inhoud."
    }

    // Minimale tekstvergelijking (spiegel van kern/growkit_skills_scherm.vergelijk)
    private func verGelijk(oud: String, nieuw: String) -> [[String: String]] {
        let oudeRegels = oud.split(separator: "\n", omittingEmptySubsequences: false)
        let nieuweRegels = nieuw.split(separator: "\n", omittingEmptySubsequences: false)
        let oudeSet = Set(oudeRegels)
        let nieuweSet = Set(nieuweRegels)
        var uit: [[String: String]] = []
        for r in oudeRegels where !nieuweSet.contains(r) {
            uit.append(["type": "verwijderd", "regel": String(r)])
        }
        for r in nieuweRegels where !oudeSet.contains(r) {
            uit.append(["type": "nieuw", "regel": String(r)])
        }
        return uit
    }
}
