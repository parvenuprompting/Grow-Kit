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
    func verdeelBegin(aantal: Int? = nil) {
        // 16:9-bewuste spreiding: hub-ring breed en plat (ellips ~2.2:1),
        // documenten in brede banen rond hun hub. Alles past in het canvas.
        var pos: [String: CGPoint] = [:]
        pos["centrum"] = .zero

        // Functies: compacte kleine ring direct rond het centrum
        let functies = knopen.filter { $0.soort == "functie" }
        for (i, f) in functies.enumerated() {
            let hoek = Double(i) / Double(max(functies.count, 1)) * 2 * .pi - .pi / 2
            pos[f.id] = CGPoint(x: CGFloat(cos(hoek)) * 95, y: CGFloat(sin(hoek)) * 62)
        }

        // Hubs: brede ellips rond alles — links en rechts blijft ruimte over
        // voor de documentbanen, dus de hubs gaan op rx=520, ry=210.
        let hubs = knopen.filter { $0.soort == "hub" }
        for (i, h) in hubs.enumerated() {
            let hoek = Double(i) / Double(max(hubs.count, 1)) * 2 * .pi - .pi / 2
            let hubPos = CGPoint(x: CGFloat(cos(hoek)) * 520, y: CGFloat(sin(hoek)) * 210)
            pos[h.id] = hubPos

            // Documenten: brede banen rond hun hub — meer horizontaal dan
            // verticaal gespreid, gesorteerd langs de baan zodat er geen
            // kruisende war ontstaat.
            let bladeren = knopen.filter { $0.soort == "document" && $0.sectie == h.label }
            for (j, blad) in bladeren.enumerated() {
                let baan = Double(1 + j / 10)                      // max 10 per baan
                let plek = Double(j % 10) / Double(10) * 2 * .pi + Double(i) * 0.4
                let rx = 150.0 + baan * 105.0                      // brede baan
                let ry = rx * 0.42                                 // plat: 16:9-gevoel
                pos[blad.id] = CGPoint(x: hubPos.x + CGFloat(cos(plek)) * rx,
                                       y: hubPos.y + CGFloat(sin(plek)) * ry)
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
    @State private var zoom: CGFloat = 0.52
    @State private var pan: CGSize = .zero
    @State private var sleepHuidig: CGSize = .zero
    @State private var fullscreen = false
    // Tabs: "alles" of een sectie-naam (hub). Minder knopen per weergave
    // houdt de graaf leesbaar — de spiraal van 460 documenten was ruis.
    @State private var tab: String = "alles"
    @State private var hoverKnoop: String? = nil

    private var beschikbareTabs: [String] {
        var secties = ["alles"]
        secties += Set(store.knopen.compactMap { $0.sectie })
            .filter { $0 != "root" }
            .sorted()
        return secties
    }

    /// Knopen in de actieve tab: "alles" toont alleen het skelet (centrum,
    /// functies, hubs) — leesbaar op één blik; de documenten horen bij hun
    /// eigen sectie-tab. Anders: centrum + functies + hub + documenten.
    private var tabKnopen: [GraafKnoop] {
        if tab == "alles" {
            return store.knopen.filter { $0.soort != "document" }
        }
        let kern = store.knopen.filter { $0.soort == "centrum" || $0.soort == "functie" }
        let hubEnDocs = store.knopen.filter {
            $0.sectie == tab || ($0.soort == "hub" && $0.label == tab)
        }
        return kern + hubEnDocs
    }

    private var tabLinks: [GraafLink] {
        let ids = Set(tabKnopen.map { $0.id })
        return store.links.filter { ids.contains($0.bron) && ids.contains($0.doel) }
    }

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
                VStack(spacing: 0) {
                    tabBalk
                    ZStack(alignment: .topTrailing) {
                        if store.knopen.isEmpty {
                            VStack(spacing: 8) {
                                if let fout = store.fout {
                                    Text(fout).font(Thema.tekst(11)).foregroundStyle(.red)
                                }
                                Text("Brein-graaf laden…")
                                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                                PillKnop(titel: "Probeer opnieuw") {
                                    store.laad(runner: runner, repoPad: repoPad, interpreter: interpreter)
                                }
                            }
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                        } else {
                            graafCanvas
                        }
                        miniBediening
                    }
                }
                .background(Thema.kleur(.papier))
            } else {
                kop
                VStack(spacing: 0) {
                    tabBalk
                    ZStack(alignment: .topTrailing) {
                        if store.knopen.isEmpty {
                            VStack(spacing: 8) {
                                if let fout = store.fout {
                                    Text(fout).font(Thema.tekst(11)).foregroundStyle(.red)
                                }
                                Text(store.geladen
                                     ? "Geen data gekregen van de adapter."
                                     : "Brein-graaf laden…")
                                    .font(Thema.tekst(11)).foregroundStyle(Thema.kleur(.gedempt))
                                PillKnop(titel: "Probeer opnieuw") {
                                    store.laad(runner: runner, repoPad: repoPad, interpreter: interpreter)
                                }
                            }
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                        } else {
                            graafCanvas
                        }
                        bediening
                    }
                }
                .background(Thema.kleur(.papier))
            }
        }
        .task {
            // .task is betrouwbaarder dan onAppear in lazy containers
            if !store.geladen && store.knopen.isEmpty {
                store.laad(runner: runner, repoPad: repoPad, interpreter: interpreter)
            }
        }
        .onChange(of: store.geladen) { _ in
            // compact-voorbeeld op Home: beginnend zoom zodanig dat de brede
            // hub-ellips (rx 520) in het 16:9-canvas past.
            if store.geladen && compactVoorbeeld {
                zoom = 0.52
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

    /// Tab-balk: "Alles" + één tab per sectie (hub). Herpositionsseert de
    /// knopen zodra de tab wisselt, en zoomt uit bij grote tabbladen.
    private var tabBalk: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(beschikbareTabs, id: \.self) { naam in
                    let gekozen = tab == naam
                    Button(action: { wisselTab(naam) }) {
                        Text(naam == "alles" ? "Alles" : naam)
                            .font(Thema.tekst(10, gewicht: gekozen ? .semibold : .regular))
                            .padding(.horizontal, 10).padding(.vertical, 4)
                            .background(Capsule().fill(gekozen ? Thema.kleur(.inkt) : Thema.kleur(.papierZacht)))
                            .foregroundStyle(gekozen ? Thema.kleur(.papier) : Thema.kleur(.gedempt))
                            .overlay(Capsule().stroke(gekozen ? Thema.kleur(.inkt) : Thema.kleur(.lijn)))
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 12)
        }
        .frame(height: 30)
    }

    private func wisselTab(_ naam: String) {
        tab = naam
        // herverdeel: kleinere tab mag wat ruimere spreiding hebben
        store.verdeelBegin(aantal: tabKnopen.count)
        let fractie = Double(tabKnopen.count) / Double(max(store.knopen.count, 1))
        zoom = tab == "alles" ? 0.42 : min(max(0.55 + fractie, 0.55), 1.2)
        pan = .zero
        sleepHuidig = .zero
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
            PillKnop(titel: "⌂") { zoom = 0.52; pan = .zero }
        }
        .padding(12)
    }

    private var graafCanvas: some View {
        GeometryReader { geo in
            let midden = CGPoint(x: geo.size.width / 2, y: geo.size.height / 2)
            ZStack {
                Canvas { context, _ in
                    // verbindingen (alleen binnen de actieve tab)
                    for link in tabLinks {
                        guard let a = store.posities[link.bron],
                              let b = store.posities[link.doel] else { continue }
                        var pad = Path()
                        pad.move(to: puntGeschaald(a, midden))
                        pad.addLine(to: puntGeschaald(b, midden))
                        context.stroke(pad, with: .color(Thema.kleur(.lijn)), lineWidth: 0.6)
                    }
                }
                // knopen (SwiftUI-views zodat ze klikbaar zijn) — de POSITIE
                // schaalt mee met de zoom, de knoop zelf (tekst!) niet: labels
                // blijven op elke zoom leesbaar i.p.v. mee te krimpen.
                ForEach(tabKnopen) { knoop in
                    if let pos = store.posities[knoop.id] {
                        graafKnoop(knoop)
                            .position(puntGeschaald(pos, midden))
                    }
                }
            }
            .offset(CGSize(width: pan.width + sleepHuidig.width,
                           height: pan.height + sleepHuidig.height))
            .gesture(panGesture)
            .simultaneousGesture(magnificatieGesture)
            .clipped()
            // Defensief: de graaf draagt altijd zwarte tekst op wit — nooit
            // meer wit-op-wit, ongeacht de context waarin hij rendert.
            .foregroundStyle(Thema.kleur(.inkt))
        }
    }

    /// Positie geschaald met de zoom rond het midden van het canvas.
    private func puntGeschaald(_ p: CGPoint, _ midden: CGPoint) -> CGPoint {
        CGPoint(x: midden.x + p.x * zoom, y: midden.y + p.y * zoom)
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
        // Platte tekst zonder rand of vlak — editorial. Hover laat de tekst
        // oplichten van gedempt-grijs naar vol inkt.
        let isHover = hoverKnoop == knoop.id
        switch knoop.soort {
        case "centrum":
            Text("GrowKit")
                .font(Thema.display(22, cursief: true))
                .foregroundStyle(Thema.kleur(.inkt))
                .padding(8)
                .contentShape(Rectangle())
                .onHover { hoverKnoop = $0 ? knoop.id : nil }
        case "functie":
            Text(knoop.label)
                .font(Thema.tekst(11, gewicht: .semibold))
                .tracking(0.3)
                .foregroundStyle(Thema.kleur(.inkt))
                .padding(6)
                .contentShape(Rectangle())
                .onHover { hoverKnoop = $0 ? knoop.id : nil }
        case "hub":
            Text(knoop.label)
                .font(Thema.display(15, cursief: true))
                .foregroundStyle(Thema.kleur(isHover ? .inkt : .zacht))
                .padding(6)
                .contentShape(Rectangle())
                .onHover { hoverKnoop = $0 ? knoop.id : nil }
        default:
            Button {
                store.openKnoop(knoop, runner: runner, repoPad: repoPad, interpreter: interpreter)
            } label: {
                Text(knoop.label)
                    .font(Thema.tekst(10))
                    .foregroundStyle(Thema.kleur(isHover ? .inkt : .gedempt))
                    .lineLimit(1)
                    .frame(width: 170, alignment: .leading)
                    .padding(4)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .onHover { hoverKnoop = $0 ? knoop.id : nil }
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
