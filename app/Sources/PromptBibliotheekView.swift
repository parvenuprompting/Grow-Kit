// PromptBibliotheekView — de gecureerde prompts uit de privé-repo
// audit-prompt-bibliotheek, letterlijk en alleen-lezen in GrowKit.
// Zoeken, filteren op domein/sectie, openen in detail; kopiëren met
// variabelen ingevuld. Curation gebeurt in de bron-repo — hier niets
// schrijven, conform de zero-trust-werkwijze.
//
// Editorial Monochrome — geen NavigationSplitView (die dwingt donkere
// sidebar op macOS). Twee kolommen in HStack met witte achtergrond.

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
        HStack(alignment: .top, spacing: 0) {
            // Linkerkolom: zoeken + promptlijst
            ScrollView {
                VStack(alignment: .leading, spacing: 10) {
                    kopKlein
                    zoekveld
                    sectieFilter
                    if fout.isEmpty {
                        ForEach(gefilterd) { p in
                            promptRij(p)
                        }
                    } else if !geladen {
                        HStack { Spacer(); ProgressView().scaleEffect(0.7); Spacer() }
                            .padding(.top, 40)
                    }
                }
                .padding(20)
            }
            .frame(width: 320)
            .background(Thema.kleur(.papier))
            .overlay(alignment: .trailing) { Rectangle().fill(Thema.kleur(.lijn)).frame(width: 1) }

            // Rechterkolom: detail
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    if let p = geselecteerd {
                        detailPrompt(p)
                    } else {
                        leeg
                    }
                }
                .padding(28)
            }
            .background(Thema.kleur(.papier))
        }
        .background(Thema.kleur(.papier))
        .onAppear { if !geladen { laad() } }
    }

    // MARK: - Kop (klein, voor de lijst)

    private var kopKlein: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("08 PROMPTS").font(Thema.tekst(9, gewicht: .semibold)).tracking(2.5)
                .foregroundStyle(Thema.kleur(.gedempt))
            Text("Gecureerde bibliotheek").font(Thema.display(22))
        }
    }

    private var kopBalk: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("08 PROMPTS · GECUREERDE BIBLIOTHEEK").font(Thema.tekst(9, gewicht: .semibold)).tracking(2.5)
                .foregroundStyle(Thema.kleur(.gedempt))
            Text("Gecureerde bibliotheek").font(Thema.display(28))
            Text("Letterlijk uit de privé-bibliotheek, alleen te lezen. Kies een prompt, vul de variabelen in en kopieer hem naar je agent.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    // MARK: - Zoekveld & filters

    private var zoekveld: some View {
        HStack(spacing: 8) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(Thema.kleur(.gedempt))
            Veld(placeholder: "Zoek in titel, tags, rol of tekst…", tekst: $zoekTekst, lettergrootte: 12, breed: true)
            if !zoekTekst.isEmpty {
                Button(action: { zoekTekst = "" }) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
                .buttonStyle(.plain)
            }
        }
        .padding(8)
        .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
        .background(Thema.kleur(.papierZacht))
    }

    private var sectieFilter: some View {
        HStack(spacing: 8) {
            ForEach(["alles", "public", "custom_infra"], id: \.self) { s in
                let gekozen = gekozenSectie == s
                Button(action: { gekozenSectie = s }) {
                    Text(s == "alles" ? "Alles" : (s == "public" ? "Publiek" : "Infra"))
                        .font(Thema.tekst(10, gewicht: .semibold)).tracking(0.8)
                        .padding(.horizontal, 8).padding(.vertical, 4)
                        .fixedSize()
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

    // MARK: - Filtering

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

    // MARK: - Lijst

    private func promptRij(_ p: PromptItem) -> some View {
        let gekozen = geselecteerd?.id == p.id
        return Button(action: { kies(p) }) {
            VStack(alignment: .leading, spacing: 2) {
                Text(p.title)
                    .font(Thema.tekst(12, gewicht: .semibold))
                    .foregroundStyle(Thema.kleur(gekozen ? .inkt : .zacht))
                    .lineLimit(1)
                Text(p.domainTitle)
                    .font(Thema.tekst(9)).tracking(0.6)
                    .foregroundStyle(Thema.kleur(gekozen ? .inkt : .gedempt))
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 8).padding(.horizontal, 12)
            .background(gekozen ? Thema.kleur(.inkt).opacity(0.06) : Thema.kleur(.papier))
            .overlay(alignment: .leading) {
                if gekozen { Rectangle().fill(Thema.kleur(.inkt)).frame(width: 2) }
            }
            .overlay(alignment: .bottom) { Rectangle().fill(Thema.kleur(.lijn)).frame(height: 0.5) }
        }
        .buttonStyle(.plain)
    }

    // MARK: - Lege staat

    private var leeg: some View {
        VStack(alignment: .leading, spacing: 10) {
            kopBalk
            if !fout.isEmpty {
                Kaart(kop: "Bibliotheek onbereikbaar", rechterKop: "FOUT") {
                    Text(fout).font(Thema.tekst(12))
                }
            } else if geladen {
                Text("Kies links een prompt — \(prompts.count) gecureerde prompts beschikbaar.")
                    .font(Thema.tekst(13)).foregroundStyle(Thema.kleur(.zacht))
            } else if bezig {
                HStack { ProgressView().scaleEffect(0.8) }
            }
        }
    }

    // MARK: - Detail

    private func detailPrompt(_ p: PromptItem) -> some View {
        VStack(alignment: .leading, spacing: 20) {
            kopBalk

            // Metadata-regel
            HStack(spacing: 0) {
                Text(p.domainTitle).font(Thema.tekst(11, gewicht: .medium))
                Text(" · ").foregroundStyle(Thema.kleur(.gedempt))
                Text(p.complexity).font(Thema.tekst(11))
                    .foregroundStyle(Thema.kleur(.zacht))
                Text(" · rol: ").foregroundStyle(Thema.kleur(.gedempt))
                Text(p.role).font(Thema.tekst(11))
                    .foregroundStyle(Thema.kleur(.zacht))
            }

            // Bereik
            if !p.scope.isEmpty {
                Kaart(kop: "Bereik", rechterKop: p.targetAudience.uppercased()) {
                    Text(p.scope)
                        .font(Thema.tekst(13)).lineSpacing(4)
                        .foregroundStyle(Thema.kleur(.inkt))
                }
            }

            // Variabelen
            if !p.variables.isEmpty {
                Kaart(kop: "Variabelen", rechterKop: "\(p.variables.count) VELDEN") {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(p.variables.indices, id: \.self) { i in
                            let v = p.variables[i]
                            if let key = v["key"] as? String {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(v["label"] as? String ?? key)
                                        .font(Thema.tekst(10, gewicht: .semibold))
                                        .tracking(0.5)
                                        .foregroundStyle(Thema.kleur(.gedempt))
                                    Veld(placeholder: v["placeholder"] as? String ?? "",
                                         tekst: Binding(
                                            get: { variabelen[key] ?? "" },
                                            set: { variabelen[key] = $0 }),
                                         lettergrootte: 12, breed: true)
                                        .padding(8)
                                        .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                                        .background(Thema.kleur(.papierZacht))
                                }
                            }
                        }
                    }
                }
            }

            // De prompttekst
            Kaart(kop: "De prompt", rechterKop: gekopieerd ? "GEKOPIEERD ✓" : "LETTERLIJK") {
                VStack(alignment: .leading, spacing: 12) {
                    ScrollView {
                        Text(ingevuld(p))
                            .font(Thema.tekst(13)).lineSpacing(5)
                            .foregroundStyle(Thema.kleur(.inkt))
                            .textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .frame(maxHeight: 400)
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

            // Tags onderaan
            if !p.tags.isEmpty {
                HStack(spacing: 6) {
                    ForEach(p.tags, id: \.self) { tag in
                        Text(tag)
                            .font(Thema.tekst(10))
                            .padding(.horizontal, 8).padding(.vertical, 3)
                            .overlay(Capsule().stroke(Thema.kleur(.lijn)))
                            .foregroundStyle(Thema.kleur(.gedempt))
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