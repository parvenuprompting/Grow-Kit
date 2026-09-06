// GidsView — het AI Gids-scherm (LEREN): kerninzichten uit Tiëndo's
// eigen Drive-documenten, elk met bronvermelding. Zoeken over titel,
// inhoud en bron; thema's ingeklapbaar. Puur lezend — kennis, geen
// uitvoer. Editorial monochrome, lichte modus.

import SwiftUI

struct GidsView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    @State private var themas: [[String: Any]] = []
    @State private var zoekresultaten: [[String: Any]] = []
    @State private var zoekTerm = ""
    @State private var aanHetZoeken = false
    @State private var ingeklapt: Set<String> = []
    @State private var fout: String?
    @State private var geladen = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                kop
                zoekBalk
                if let fout { foutKaart(fout) }
                if aanHetZoeken {
                    Text("Zoeken…").font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.gedempt))
                } else if !zoekTerm.isEmpty {
                    resultatenLijst
                } else {
                    themasLijst
                }
                if !zoekTerm.isEmpty && zoekresultaten.isEmpty && !aanHetZoeken {
                    Text("Niets gevonden voor '\(zoekTerm)'.")
                        .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.gedempt))
                }
                Spacer(minLength: 16)
            }
            .padding(28)
        }
        .background(Thema.kleur(.papier))
        .onAppear { laad() }
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("AI Gids")
                .font(Thema.display(30))
            Text("Kerninzichten uit je eigen Drive-documenten — de architect-mindset, zero-trust, machine-bewijs en effectief leren. Elk inzicht noemt zijn bron: een feit zonder bron is een aanname.")
                .font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var zoekBalk: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("ZOEKEN IN DE GIDS")
                .font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            HStack(spacing: 10) {
                Veld(placeholder: "bijv. bewijs, hefboom, faalcontract…", tekst: $zoekTerm)
                    .padding(10)
                    .overlay(Rectangle().stroke(Thema.kleur(.lijn)))
                    .background(Thema.kleur(.papierZacht))
                    .onSubmit { zoek() }
                if !zoekTerm.isEmpty {
                    PillKnop(titel: "Wis", gevuld: false, compact: true) {
                        zoekTerm = ""
                        zoekresultaten = []
                    }
                }
            }
        }
    }

    private var themasLijst: some View {
        VStack(alignment: .leading, spacing: 14) {
            ForEach(themas.indices, id: \.self) { i in
                themaKaart(themas[i])
            }
        }
    }

    private var resultatenLijst: some View {
        Kaart(kop: "Zoekresultaten",
              rechterKop: "\(zoekresultaten.count) GEVONDEN") {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(zoekresultaten.indices, id: \.self) { i in
                    inzichtRij(zoekresultaten[i])
                }
                if zoekresultaten.isEmpty {
                    Text("Niets gevonden.").font(Thema.tekst(12))
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
            }
        }
    }

    private func themaKaart(_ thema: [String: Any]) -> some View {
        let naam = thema["thema"] as? String ?? "?"
        let inzichten = thema["inzichten"] as? [[String: Any]] ?? []
        let isIngeklapt = ingeklapt.contains(naam)
        return Kaart(kop: naam, rechterKop: "\(inzichten.count) INZICHTEN") {
            VStack(alignment: .leading, spacing: 0) {
                if isIngeklapt {
                    PillKnop(titel: "Uitklappen", gevuld: false, compact: true) {
                        ingeklapt.remove(naam)
                    }
                } else {
                    ForEach(inzichten.indices, id: \.self) { j in
                        inzichtRij(inzichten[j])
                    }
                    PillKnop(titel: "Inklappen", gevuld: false, compact: true) {
                        ingeklapt.insert(naam)
                    }
                    .padding(.top, 10)
                }
            }
        }
    }

    private func inzichtRij(_ i: [String: Any]) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(i["titel"] as? String ?? "")
                .font(Thema.tekst(14, gewicht: .medium))
                .foregroundStyle(Thema.kleur(.inkt))
            Text(i["inhoud"] as? String ?? "")
                .font(Thema.tekst(12))
                .foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
            HStack(spacing: 6) {
                Image(systemName: "book.closed")
                    .font(.system(size: 9))
                    .foregroundStyle(Thema.kleur(.gedempt))
                Text("Bron: \(i["bron"] as? String ?? "")")
                    .font(Thema.tekst(10))
                    .foregroundStyle(Thema.kleur(.gedempt))
                if let toepassing = i["toepassing"] as? String, !toepassing.isEmpty {
                    Spacer()
                    Text(toepassing)
                        .font(Thema.tekst(10))
                        .foregroundStyle(Thema.kleur(.gedempt))
                        .lineLimit(2)
                        .truncationMode(.tail)
                        .frame(maxWidth: 320, alignment: .trailing)
                }
            }
        }
        .padding(.vertical, 10)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
        }
    }

    private func foutKaart(_ melding: String) -> some View {
        Kaart(kop: "Let op", rechterKop: "FOUT") {
            Text(melding).font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
        }
    }

    // MARK: - Adapter

    private func laad() {
        fout = nil
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "gids", invoer: [:])
            await MainActor.run {
                guard let r else { fout = "Adapter niet bereikbaar."; return }
                if r.ok, let gids = r.data["gids"] as? [String: Any] {
                    themas = gids["thema's"] as? [[String: Any]] ?? []
                    geladen = true
                } else {
                    fout = r.fout ?? "Gids laden mislukt."
                }
            }
        }
    }

    private func zoek() {
        let term = zoekTerm.trimmingCharacters(in: .whitespaces)
        guard !term.isEmpty else { zoekresultaten = []; return }
        aanHetZoeken = true
        fout = nil
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "gids", invoer: ["zoek": term])
            await MainActor.run {
                aanHetZoeken = false
                guard let r else { fout = "Adapter niet bereikbaar."; return }
                if r.ok {
                    zoekresultaten = r.data["inzichten"] as? [[String: Any]] ?? []
                } else {
                    fout = r.fout ?? "Zoeken mislukt."
                }
            }
        }
    }
}
