// PromptBibliotheekView — de gecureerde prompts uit de privé-repo
// audit-prompt-bibliotheek, letterlijk en alleen-lezen in GrowKit.
// Zoeken, filteren op domein/sectie, openen in detail; kopiëren met
// variabelen ingevuld. Curation gebeurt in de bron-repo — hier niets
// schrijven, conform de zero-trust-werkwijze.

import SwiftUI

struct PromptItem: Identifiable {
    let id: String
    let domainId: Int
    let domainTitle: String
    let title: String
    let role: String
    let scope: String
    let prioritizationCriteria: String
    let targetAudience: String
    let section: String
    let complexity: String
    let tags: [String]
    let variables: [[String: Any]]
    let content: String

    static func uit(_ d: [String: Any]) -> PromptItem? {
        guard let id = d["id"] as? String,
              let content = d["content"] as? String else { return nil }
        return PromptItem(
            id: id,
            domainId: d["domainId"] as? Int ?? 0,
            domainTitle: d["domainTitle"] as? String ?? "",
            title: d["title"] as? String ?? id,
            role: d["role"] as? String ?? "",
            scope: d["scope"] as? String ?? "",
            prioritizationCriteria: d["prioritizationCriteria"] as? String ?? "",
            targetAudience: d["targetAudience"] as? String ?? "",
            section: d["section"] as? String ?? "public",
            complexity: d["complexity"] as? String ?? "",
            tags: d["tags"] as? [String] ?? [],
            variables: d["variables"] as? [[String: Any]] ?? [],
            content: content)
    }
}

struct PromptBibliotheekView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    @State private var prompts: [PromptItem] = []
    @State private var geladen = false
    @State private var bezig = false
    @State private var fout = ""
    @State private var zoekTekst = ""
    @State private var gekozenSectie = "alles"
    @State private var geselecteerd: PromptItem? = nil
    @State private var variabelen: [String: String] = [:]
    @State private var gekopieerd = false

    var body: some View {
        NavigationSplitView {
            // Lijst-kolom
            ScrollView {
                VStack(alignment: .leading, spacing: 10) {
                    zoekveld
                    sectieFilter
                    if fout.isEmpty {
                        ForEach(gefilterd) { p in
                            promptRij(p)
                        }
                    }
                }
                .padding(16)
            }
            .navigationSplitViewColumnWidth(min: 280, ideal: 320)
        } detail: {
            // Detail-kolom
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    if let p = geselecteerd {
                        detailPrompt(p)
                    } else {
                        leeg
                    }
                }
                .padding(24)
            }
        }
        .background(Thema.kleur(.papier))
        .onAppear { if !geladen { laad() } }
    }

    private var kopBalk: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Prompt-bibliotheek").font(Thema.display(30))
            Text("De gecureerde audit-prompts — letterlijk uit de privé-bibliotheek, alleen te lezen. Kies een prompt, vul de variabelen in en kopieer hem naar je agent.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var zoekveld: some View {
        HStack(spacing: 8) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(Thema.kleur(.gedempt))
            TextField("Zoek in titel, tags, rol of tekst…", text: $zoekTekst)
                .textFieldStyle(.plain)
                .font(Thema.tekst(12))
            if !zoekTekst.isEmpty {
                Button(action: { zoekTekst = "" }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
                .buttonStyle(.plain)
            }
        }
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 6).fill(Thema.kleur(.papierZacht)))
        .overlay(RoundedRectangle(cornerRadius: 6).stroke(Thema.kleur(.lijn)))
    }

    private var sectieFilter: some View {
        HStack(spacing: 8) {
            ForEach(["alles", "public", "custom_infra"], id: \.self) { s in
                let gekozen = gekozenSectie == s
                Button(action: { gekozenSectie = s }) {
                    Text(s == "alles" ? "Alles" : (s == "public" ? "Publiek" : "Infra"))
                        .font(Thema.tekst(10, gewicht: .semibold)).tracking(0.8)
                        .padding(.horizontal, 10).padding(.vertical, 4)
                        .background(RoundedRectangle(cornerRadius: 4)
                            .fill(gekozen ? Thema.kleur(.inkt) : Thema.kleur(.papierZacht)))
                        .foregroundStyle(gekozen ? Thema.kleur(.papier) : Thema.kleur(.gedempt))
                }
                .buttonStyle(.plain)
            }
            Spacer()
            Text("\(gefilterd.count) prompts")
                .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
        }
    }

    private var gefilterd: [PromptItem] {
        var lijst = prompts
        if gekozenSectie != "alles" {
            lijst = lijst.filter { $0.section == gekozenSectie }
        }
        let naald = zoekTekst.lowercased().trimmingCharacters(in: .whitespaces)
        if !naald.isEmpty {
            lijst = lijst.filter { p in
                let hooi = ([p.title, p.role, p.scope, p.complexity] + p.tags.map { $0 })
                    .joined(separator: " ").lowercased()
                return hooi.contains(naald)
            }
        }
        return lijst
    }

    private func promptRij(_ p: PromptItem) -> some View {
        let gekozen = geselecteerd?.id == p.id
        return Button(action: { kies(p) }) {
            VStack(alignment: .leading, spacing: 3) {
                Text(p.title).font(Thema.tekst(12, gewicht: .semibold))
                    .foregroundStyle(Thema.kleur(gekozen ? .inkt : .zacht))
                    .lineLimit(1)
                Text(p.domainTitle).font(Thema.tekst(9)).tracking(0.6)
                    .foregroundStyle(Thema.kleur(.gedempt))
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .background(RoundedRectangle(cornerRadius: 6)
                .fill(gekozen ? Thema.kleur(.lijn).opacity(0.4) : Thema.kleur(.papierZacht)))
            .overlay(RoundedRectangle(cornerRadius: 6)
                .stroke(gekozen ? Thema.kleur(.inkt) : Thema.kleur(.lijn)))
        }
        .buttonStyle(.plain)
    }

    private var leeg: some View {
        VStack(alignment: .leading, spacing: 10) {
            kopBalk
            if !fout.isEmpty {
                Kaart(kop: "Bibliotheek onbereikbaar", rechterKop: "FOUT") {
                    Text(fout).font(Thema.tekst(12))
                }
            } else if geladen {
                Text("Kies links een prompt — \(prompts.count) gecureerde prompts beschikbaar.")
                    .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
            } else if bezig {
                ProgressView().scaleEffect(0.8)
            }
        }
    }

    private func detailPrompt(_ p: PromptItem) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            kopBalk
            VStack(alignment: .leading, spacing: 4) {
                Text(p.title).font(Thema.display(22))
                Text("\(p.domainTitle) · \(p.complexity) · rol: \(p.role)")
                    .font(Thema.tekst(10)).tracking(0.5)
                    .foregroundStyle(Thema.kleur(.gedempt))
            }
            if !p.scope.isEmpty {
                Kaart(kop: "Bereik", rechterKop: p.targetAudience.uppercased()) {
                    Text(p.scope).font(Thema.tekst(12)).lineSpacing(3)
                }
            }
            if !p.variables.isEmpty {
                Kaart(kop: "Variabelen", rechterKop: "\(p.variables.count) VELDEN") {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(p.variables.indices, id: \.self) { i in
                            let v = p.variables[i]
                            if let key = v["key"] as? String {
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(v["label"] as? String ?? key)
                                        .font(Thema.tekst(10, gewicht: .semibold))
                                        .tracking(0.5)
                                        .foregroundStyle(Thema.kleur(.gedempt))
                                    TextField(v["placeholder"] as? String ?? "",
                                              text: Binding(
                                                get: { variabelen[key] ?? "" },
                                                set: { variabelen[key] = $0 }))
                                        .textFieldStyle(.plain)
                                        .font(Thema.tekst(12))
                                        .padding(6)
                                        .background(RoundedRectangle(cornerRadius: 4)
                                            .fill(Thema.kleur(.papier)))
                                        .overlay(RoundedRectangle(cornerRadius: 4)
                                            .stroke(Thema.kleur(.lijn)))
                                }
                            }
                        }
                    }
                }
            }
            Kaart(kop: "De prompt", rechterKop: gekopieerd ? "GEKOPIEERD ✓" : "LETTERLIJK") {
                VStack(alignment: .leading, spacing: 10) {
                    Text(ingevuld(p))
                        .font(Thema.tekst(12)).lineSpacing(3)
                        .textSelection(.enabled)
                    HStack {
                        PillKnop(titel: "Kopieer prompt", gevuld: true) {
                            kopieer(ingevuld(p))
                        }
                        Spacer()
                        Text("Bron: audit-prompt-bibliotheek (privé-repo)")
                            .font(Thema.tekst(9)).foregroundStyle(Thema.kleur(.gedempt))
                    }
                }
            }
        }
    }

    /// Variabelen letterlijk invullen: {{key}} → ingevulde waarde.
    private func ingevuld(_ p: PromptItem) -> String {
        var tekst = p.content
        for (key, waarde) in variabelen where !waarde.trimmingCharacters(in: .whitespaces).isEmpty {
            tekst = tekst.replacingOccurrences(of: "{{\(key)}}", with: waarde)
        }
        return tekst
    }

    private func kopieer(_ tekst: String) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(tekst, forType: .string)
        gekopieerd = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { gekopieerd = false }
    }

    private func kies(_ p: PromptItem) {
        geselecteerd = p
        variabelen = [:]
    }

    private func laad() {
        bezig = true
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "prompts", invoer: [:])
            await MainActor.run {
                bezig = false
                geladen = true
                guard let r, r.ok,
                      let lijst = r.data["prompts"] as? [[String: Any]] else {
                    fout = r?.fout ?? "Prompt-bibliotheek onbereikbaar."
                    return
                }
                fout = ""
                prompts = lijst.compactMap(PromptItem.uit)
            }
        }
    }
}
