// OnboardingView (slice H) — het geboortemoment van het geheugen.
//
// Geen formulier: de eerste goedkeuringen. Concept → mens bekrachtigt →
// pas dán opslag (regel 6). Alles mag leeg blijven ("Later invullen").
// De opslag gebeurt via de adapter (kern/growkit_profiel.py) — append-only.

import SwiftUI

struct OnboardingView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    @Binding var isZichtbaar: Bool

    @State private var naam = ""
    @State private var rol = ""
    @State private var doel = ""
    @State private var taal = "NL"
    @State private var moment = ""
    @State private var agenten = ""
    @State private var concept: [String: Any]? = nil
    @State private var bezig = false
    @State private var fout: String?
    @State private var afgerond = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    kop
                    if afgerond {
                        welkomKaart
                    } else if let concept = concept {
                        bevestigingsKaart(concept)
                    } else {
                        vragenKaart
                    }
                    if let fout = fout {
                        Text(fout).font(Thema.tekst(12)).foregroundStyle(.red)
                    }
                }
                .padding(28)
            }
        }
        .background(Thema.kleur(.papier))
        .onAppear { laadBestaand() }
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("GEHEUGEN · GEBOORTEMOMENT").font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            Text("Wie ben ik, curator?").font(Thema.display(30))
            Text("Dit is de eerste goedkeuringen: wat GrowKit over je weet, begint hier — met jouw toestemming. Alles mag leeg blijven.")
                .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var vragenKaart: some View {
        Kaart(kop: "Vijf vragen", rechterKop: "SKIP IS EEN RECHT") {
            VStack(alignment: .leading, spacing: 16) {
                invoerVeld("Hoe mogen we je noemen?", tekst: $naam, verplicht: true)
                invoerVeld("Wat doe je? (rol/werk)", tekst: $rol)
                invoerVeld("Wat wil je bereiken met GrowKit? (1 zin)", tekst: $doel)
                HStack(spacing: 18) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("TAAL").font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                            .foregroundStyle(Thema.kleur(.gedempt))
                        Picker("", selection: $taal) {
                            Text("Nederlands").tag("NL")
                            Text("English").tag("EN")
                        }.pickerStyle(.segmented).frame(width: 200)
                    }
                    VStack(alignment: .leading, spacing: 4) {
                        Text("OVERZICHT MOMENT").font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                            .foregroundStyle(Thema.kleur(.gedempt))
                        TextField("bijv. ochtend", text: $moment)
                            .foregroundStyle(Thema.kleur(.inkt))
                            .textFieldStyle(.plain).font(Thema.tekst(12)).frame(width: 140)
                    }
                }
                invoerVeld("Naam van je agent(en)? (optioneel)", tekst: $agenten)

                HStack {
                    PillKnop(titel: "Later invullen") { isZichtbaar = false }
                    Spacer()
                    PillKnop(titel: "Dit is mijn verhaal →", gevuld: true) { maakConcept() }
                }
            }
        }
    }

    private func bevestigingsKaart(_ concept: [String: Any]) -> some View {
        Kaart(kop: "Ik heb dit begrepen", rechterKop: "BEKRACHTIG AUB") {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(concept.sorted(by: { $0.key < $1.key }), id: \.key) { k, v in
                    HStack(alignment: .firstTextBaseline, spacing: 12) {
                        Text(k.uppercased())
                            .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.4)
                            .foregroundStyle(Thema.kleur(.gedempt))
                            .frame(width: 90, alignment: .leading)
                        Text("\(v)").font(Thema.tekst(13))
                    }
                }
                Text("Klopt dit? Pas na jouw bekrachtiging wordt dit geheugen.")
                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.zacht))
                    .padding(.top, 4)
                HStack {
                    PillKnop(titel: "Nee, terug") { self.concept = nil }
                    Spacer()
                    PillKnop(titel: "Ik onthoud dit ✓", gevuld: true) { bekrachtig() }
                }
            }
        }
    }

    private var welkomKaart: some View {
        Kaart(kop: "Onthouden", rechterKop: "APPEND-ONLY") {
            VStack(alignment: .leading, spacing: 8) {
                Text("Welkom\(naam.isEmpty ? "" : ", \(naam)"). Ik onthoud dit.")
                    .font(Thema.display(20))
                Text("Je profiel staat lokaal, als geheugen-knoop met datum per regel. Wijzigingen overschrijven nooit — ze worden een nieuwe regel. Je kunt alles altijd inzien, wijzigen of vergeten.")
                    .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                PillKnop(titel: "Aan het werk") { isZichtbaar = false }
            }
        }
    }

    private func invoerVeld(_ label: String, tekst: Binding<String>, verplicht: Bool = false) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(label.uppercased())
                    .font(Thema.tekst(9, gewicht: .semibold)).tracking(1.5)
                    .foregroundStyle(Thema.kleur(.gedempt))
                if verplicht {
                    Text("VERPLICHT").font(Thema.tekst(8, gewicht: .semibold)).tracking(1)
                        .foregroundStyle(Thema.kleur(.inkt))
                }
            }
            TextField("", text: tekst)
                .foregroundStyle(Thema.kleur(.inkt))
                .textFieldStyle(.plain).font(Thema.tekst(13))
                .padding(.bottom, 4)
                .overlay(alignment: .bottom) {
                    Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)
                }
        }
    }

    // MARK: Adapter

    private func laadBestaand() {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "profiel", invoer: ["actie": "lees"])
            // hervatvlag: waar was ik? (stap 1 = invullen, stap 2 = bekrachtigen)
            let h = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "hervatvlag",
                                           invoer: ["actie": "hervat", "wizard": "onboarding",
                                                    "stappen": ["invullen", "bekrachtigen"]])
            await MainActor.run {
                if let r, r.ok, let p = r.data["profiel"] as? [String: Any] {
                    naam = p["naam"] as? String ?? ""
                    rol = p["rol"] as? String ?? ""
                    doel = p["doel"] as? String ?? ""
                    taal = p["taal"] as? String ?? "NL"
                    moment = p["moment"] as? String ?? ""
                    agenten = p["agenten"] as? String ?? ""
                    afgerond = !naam.isEmpty || !rol.isEmpty
                }
                // wizard al klaar (of profiel bestaat) → niet opnieuw tonen
                if let h, h.ok, h.data["klaar"] as? Bool == true {
                    afgerond = true
                }
            }
        }
    }

    private func maakConcept() {
        bezig = true; fout = nil
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "profiel",
                                           invoer: ["actie": "concept", "naam": naam,
                                                    "rol": rol, "doel": doel,
                                                    "taal": taal, "moment": moment,
                                                    "agenten": agenten])
            await MainActor.run {
                bezig = false
                if let r, r.ok, let c = r.data["concept"] as? [String: Any] {
                    concept = c
                } else {
                    fout = r?.fout ?? "Concept mislukt."
                }
            }
        }
    }

    private func bekrachtig() {
        guard let concept = concept else { return }
        bezig = true; fout = nil
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "profiel",
                                           invoer: ["actie": "bekrachtig",
                                                    "concept": concept])
            var geslaagd = false
            await MainActor.run {
                bezig = false
                if let r, r.ok {
                    geslaagd = true
                    afgerond = true
                    self.concept = nil
                } else {
                    fout = r?.fout ?? "Opslag mislukt."
                }
            }
            if geslaagd {
                // hervatvlag: beide stappen af — de wizard is klaar
                _ = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "hervatvlag",
                                           invoer: ["actie": "rond_af", "wizard": "onboarding",
                                                    "stap": "invullen"])
                _ = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "hervatvlag",
                                           invoer: ["actie": "rond_af", "wizard": "onboarding",
                                                    "stap": "bekrachtigen"])
            }
        }
    }
}
