// GraafView (fase A+) — het hele brein als kennisgraaf, in de stijl van
// PAC's Brain Graph maar native. Centrum = GrowKit, hubs = secties,
// bladeren = documenten. Pan met sleep, zoom met scroll/pijltjes,
// fullscreen met de knop; klik op een document opent het in-app.

import SwiftUI

// MARK: - Model

struct GraafKnoop: Identifiable {
    let id: String
    let label: String
    let soort: String
    var sectie: String?
    var pad: String?
}

struct GraafLink: Identifiable {
    let bron: String
    let doel: String
    var id: String { bron + "->" + doel }
}

final class GraafStore: ObservableObject {
    @Published var knopen: [GraafKnoop] = []
    @Published var links: [GraafLink] = []
    @Published var posities: [String: CGPoint] = [:]
    @Published var geladen = false
    @Published var fout: String?
    @Published var openDocument: (pad: String, titel: String, inhoud: String)? = nil

    func laad(runner: Runner, repoPad: String, interpreter: String) {
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "graaf", invoer: ["actie": "graaf"])
            await MainActor.run {
                guard let r, r.ok,
                      let kn = r.data["knopen"] as? [[String: Any]],
                      let ve = r.data["verbindingen"] as? [[String: Any]] else {
                    fout = r?.fout ?? "Graaf onbereikbaar."
                    geladen = true
                    return
                }
                fout = nil
                knopen = kn.map { k in
                    GraafKnoop(id: k["id"] as? String ?? "",
                               label: k["label"] as? String ?? "",
                               soort: k["soort"] as? String ?? "document",
                               sectie: k["sectie"] as? String,
                               pad: k["pad"] as? String)
                }
                links = ve.map { l in
                    GraafLink(bron: l["bron"] as? String ?? "",
                              doel: l["doel"] as? String ?? "")
                }
                verdeelBegin()
                geladen = true
            }
        }
    }

    /// Beginverdeling: hubs in een ring, documenten in een spiraal rond
    /// hun hub, functies boven het centrum. De simulatie laat het daarna
    /// natuurlijk vallen.
    private func verdeelBegin() {
        var pos: [String: CGPoint] = [:]
        let centrum = CGPoint(x: 0, y: 0)
        pos["centrum"] = centrum

        let functies = knopen.filter { $0.soort == "functie" }
        for (i, f) in functies.enumerated() {
            let hoek = Double(i) / Double(max(functies.count, 1)) * 2 * .pi - .pi / 2
            pos[f.id] = CGPoint(x: CGFloat(cos(hoek)) * 110, y: CGFloat(sin(hoek)) * 110)
        }

        let hubs = knopen.filter { $0.soort == "hub" }
        for (i, h) in hubs.enumerated() {
            let hoek = Double(i) / Double(max(hubs.count, 1)) * 2 * .pi
            let hubPos = CGPoint(x: CGFloat(cos(hoek)) * 320, y: CGFloat(sin(hoek)) * 320)
            pos[h.id] = hubPos

            let bladeren = knopen.filter { $0.soort == "document" && $0.sectie == h.label }
            for (j, blad) in bladeren.enumerated() {
                let ring = Double(1 + j / 14)
                let bh = Double(j % 14) / Double(14) * 2 * .pi + Double(i)
                let r = 90.0 + ring * 55.0
                pos[blad.id] = CGPoint(x: hubPos.x + CGFloat(cos(bh)) * r,
                                       y: hubPos.y + CGFloat(sin(bh)) * r)
            }
        }
        posities = pos
    }

    func openKnoop(_ knoop: GraafKnoop, runner: Runner, repoPad: String, interpreter: String) {
        guard knoop.soort == "document", let pad = knoop.pad else { return }
        Task {
            let r = try? await runner.roep(repoPad: repoPad, interpreter: interpreter,
                                           commando: "graaf",
                                           invoer: ["actie": "document", "pad": pad])
            await MainActor.run {
                if let r, r.ok, let inhoud = r.data["inhoud"] as? String {
                    openDocument = (pad: pad, titel: knoop.label, inhoud: inhoud)
                }
            }
        }
    }
}

// MARK: - View

struct GraafView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String
    var compactVoorbeeld: Bool = false
    @StateObject private var store = GraafStore()
    @State private var zoom: CGFloat = 0.55
    @State private var pan: CGSize = .zero
    @State private var sleepHuidig: CGSize = .zero
    @State private var fullscreen = false

    var body: some View {
        VStack(spacing: 0) {
            if let doc = store.openDocument {
                documentLezer(doc)
            } else if fullscreen {
                graafCanvas
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Thema.kleur(.papier))
                    .overlay(alignment: .topTrailing) { bediening }
            } else if compactVoorbeeld {
                graafCanvas
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Thema.kleur(.papier))
                    .overlay(alignment: .topTrailing) { miniBediening }
            } else {
                kop
                graafCanvas
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Thema.kleur(.papier))
                    .overlay(alignment: .topTrailing) { bediening }
            }
        }
        .onAppear {
            if !store.geladen && store.knopen.isEmpty {
                store.laad(runner: runner, repoPad: repoPad, interpreter: interpreter)
            }
        }
        .onChange(of: store.geladen) { _ in
            // compact-voorbeeld op Home: begin ingezoomd zodat de hubs zichtbaar zijn
            if store.geladen && compactVoorbeeld {
                zoom = 0.42
                pan = .zero
            }
        }
    }

    private var miniBediening: some View {
        VStack(spacing: 8) {
            PillKnop(titel: "⛶") { fullscreen = true }
        }
        .padding(10)
    }

    private var kop: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("HUIS · KNOWLEDGE GRAPH").font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                .foregroundStyle(Thema.kleur(.gedempt))
            HStack(alignment: .firstTextBaseline) {
                Text("Alles, ").font(Thema.display(30))
                Text("in kaart.").font(Thema.display(30, cursief: true))
                    .foregroundStyle(Thema.kleur(.zacht))
                Spacer()
                PillKnop(titel: "Volledig scherm", gevuld: false) { fullscreen = true }
            }
            Text("Het Agent Family Brain — elk document, elke inhoud. Sleep om te bewegen, scroll om te zoomen, klik een document om het te lezen.")
                .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
        }
        .padding(.horizontal, 28).padding(.top, 20).padding(.bottom, 8)
    }

    private var bediening: some View {
        VStack(spacing: 8) {
            if !fullscreen {
                PillKnop(titel: "⛶") { fullscreen = true }
            } else {
                PillKnop(titel: "✕") { fullscreen = false }
            }
            PillKnop(titel: "+") { zoom = min(zoom * 1.25, 4) }
            PillKnop(titel: "−") { zoom = max(zoom / 1.25, 0.15) }
            PillKnop(titel: "⌂") { zoom = 0.55; pan = .zero }
        }
        .padding(12)
    }

    private var graafCanvas: some View {
        GeometryReader { geo in
            let midden = CGPoint(x: geo.size.width / 2, y: geo.size.height / 2)
            ZStack {
                Canvas { context, _ in
                    // verbindingen
                    for link in store.links {
                        guard let a = store.posities[link.bron],
                              let b = store.posities[link.doel] else { continue }
                        var pad = Path()
                        pad.move(to: punt(a, midden))
                        pad.addLine(to: punt(b, midden))
                        context.stroke(pad, with: .color(Thema.kleur(.lijn)), lineWidth: 0.6)
                    }
                }
                // knopen (SwiftUI-views zodat ze klikbaar zijn)
                ForEach(store.knopen) { knoop in
                    if let pos = store.posities[knoop.id] {
                        graafKnoop(knoop)
                            .position(punt(pos, midden))
                    }
                }
            }
            .scaleEffect(zoom)
            .offset(CGSize(width: pan.width + sleepHuidig.width,
                           height: pan.height + sleepHuidig.height))
            .gesture(panGesture)
            .simultaneousGesture(magnificatieGesture)
            .clipped()
        }
    }

    private var magnificatieGesture: some Gesture {
        MagnificationGesture()
            .onChanged { schaal in
                zoom = min(max(beginZoom * schaal, 0.15), 4)
            }
            .onEnded { _ in beginZoom = zoom }
    }
    @State private var beginZoom: CGFloat = 0.55

    private func punt(_ p: CGPoint, _ midden: CGPoint) -> CGPoint {
        CGPoint(x: midden.x + p.x, y: midden.y + p.y)
    }

    private var panGesture: some Gesture {
        DragGesture()
            .onChanged { g in sleepHuidig = g.translation }
            .onEnded { g in
                pan = CGSize(width: pan.width + g.translation.width,
                             height: pan.height + g.translation.height)
                sleepHuidig = .zero
            }
    }

    @ViewBuilder
    private func graafKnoop(_ knoop: GraafKnoop) -> some View {
        switch knoop.soort {
        case "centrum":
            VStack(spacing: 2) {
                Image(systemName: "leaf").font(.system(size: 16))
                Text("GrowKit").font(Thema.display(14))
            }
            .padding(10)
            .background(Circle().fill(Thema.kleur(.papier)))
            .overlay(Circle().stroke(Thema.kleur(.inkt), lineWidth: 1.5))
        case "functie":
            Text(knoop.label)
                .font(Thema.tekst(10, gewicht: .semibold))
                .padding(.horizontal, 10).padding(.vertical, 5)
                .background(Capsule().fill(Thema.kleur(.papier)))
                .overlay(Capsule().stroke(Thema.kleur(.inkt), lineWidth: 1))
                .shadow(color: .black.opacity(0.06), radius: 2, y: 1)
        case "hub":
            Text(knoop.label)
                .font(Thema.display(13, cursief: true))
                .padding(.horizontal, 12).padding(.vertical, 6)
                .background(Capsule().fill(Thema.kleur(.papierZacht)))
                .overlay(Capsule().stroke(Thema.kleur(.lijn)))
        default:
            Button {
                store.openKnoop(knoop, runner: runner, repoPad: repoPad, interpreter: interpreter)
            } label: {
                Text(knoop.label)
                    .font(Thema.tekst(9)).lineLimit(1)
                    .frame(width: 130)
                    .padding(.vertical, 3)
                    .background(Thema.kleur(.papier).opacity(0.92))
                    .overlay(RoundedRectangle(cornerRadius: 3).stroke(Thema.kleur(.lijn)))
            }
            .buttonStyle(.plain)
            .help(knoop.pad ?? knoop.label)
        }
    }

    // MARK: Documentlezer

    private func documentLezer(_ doc: (pad: String, titel: String, inhoud: String)) -> some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(doc.titel).font(Thema.display(20))
                    Text(doc.pad).font(Thema.tekst(9)).tracking(0.5)
                        .foregroundStyle(Thema.kleur(.gedempt))
                }
                Spacer()
                PillKnop(titel: "Terug naar de graaf", gevuld: true, compact: true) {
                    store.openDocument = nil
                }
            }
            .padding(.horizontal, 28).padding(.vertical, 14)

            Rectangle().fill(Thema.kleur(.lijn)).frame(height: 1)

            ScrollView {
                Text(doc.inhoud)
                    .font(Thema.tekst(12))
                    .foregroundStyle(Thema.kleur(.inkt))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(28)
                    .textSelection(.enabled)
            }
        }
        .background(Thema.kleur(.papier))
    }
}
