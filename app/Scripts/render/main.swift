// Render de drie v1-schermen als PNG-bewijs, rechtstreeks uit de echte
// SwiftUI-views (ImageRenderer, macOS 13+). Geen schermtoestemming nodig.
// Gebruik: swiftc -o /tmp/render app/Scripts/render/main.swift \
//   app/Sources/{Thema,Bouwstenen,Runner,StatusView,PlantView,RatificeerView}.swift && /tmp/render

import AppKit
import SwiftUI

MainActor.assumeIsolated {
let repoRoot = URL(fileURLWithPath: #filePath)
    .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()

// Huisstijl-fonts registreren uit de repo (Bundle.main is hier het CLI-binary).
for naam in ["Fraunces.ttf", "Fraunces-Italic.ttf", "Inter.ttf", "Inter-Italic.ttf"] {
    let url = repoRoot.appendingPathComponent("app/Fonts").appendingPathComponent(naam)
    CTFontManagerRegisterFontURLs([url as CFURL] as CFArray, .process, true, nil)
}

let runner = Runner()
let uitvoerMap = repoRoot.appendingPathComponent("docs/superpowers/bewijs/fase-6-schermen")
try? FileManager.default.createDirectory(at: uitvoerMap, withIntermediateDirectories: true)

@MainActor func render(_ naam: String, _ view: some View) {
    let inhoud = view
        .frame(width: 880, height: 620)
        .background(Thema.kleur(.papier))
    let renderer = ImageRenderer(content: inhoud)
    renderer.scale = 2
    guard let img = renderer.nsImage,
          let tiff = img.tiffRepresentation,
          let rep = NSBitmapImageRep(data: tiff),
          let png = rep.representation(using: .png, properties: [:]) else {
        print("RENDER FAAL: \(naam)")
        exit(1)
    }
    let doel = uitvoerMap.appendingPathComponent(naam)
    try! png.write(to: doel)
    print("gerenderd: \(doel.path)")
}

render("status.png", StatusView(runner: runner,
                                repoPad: .constant(Runner.standaardRepoPad),
                                interpreter: .constant(Runner.standaardInterpreter)))
render("plant.png", PlantView(runner: runner,
                              repoPad: .constant(Runner.standaardRepoPad),
                              interpreter: .constant(Runner.standaardInterpreter)))
render("ratificatie.png", RatificeerView(runner: runner,
                                         repoPad: .constant(Runner.standaardRepoPad),
                                         interpreter: .constant(Runner.standaardInterpreter)))
print("RENDER OK: drie schermen")
}
