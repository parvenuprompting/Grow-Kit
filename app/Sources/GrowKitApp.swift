// GrowKit — de app die het harnas bedient (fase 6).
// De app is een bedienaar, nooit een machthebber: alle acties lopen via
// adapter.py, dat dezelfde poort, motor en faalcontract afdwingt.
// De app opent standaard in fullscreen (elke start, uitschakelbaar met ESC).

import SwiftUI

@main
struct GrowKitApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @State private var geselecteerd: ContentView.Modi = .home
    @State private var toonInstellingen = false
    @State private var toonOver = false
    @State private var toonOnboarding = false
    @State private var onboardingGecheckt = false
    @State private var laadSchermWeg = false

    var body: some Scene {
        WindowGroup {
            ContentView(geselecteerd: $geselecteerd,
                        toonInstellingen: $toonInstellingen,
                        toonOver: $toonOver)
                .frame(minWidth: 880, minHeight: 620)
                .background(Thema.kleur(.papier))
                .sheet(isPresented: $toonOver) { OverView() }
                .sheet(isPresented: $toonOnboarding) {
                    OnboardingView(runner: Runner(), repoPad: .constant(""),
                                   interpreter: .constant(""),
                                   isZichtbaar: $toonOnboarding)
                }
                .task {
                    guard !onboardingGecheckt else { return }
                    onboardingGecheckt = true
                    let r = try? await Runner().roep(
                        repoPad: "", interpreter: "",
                        commando: "profiel", invoer: ["actie": "lees"])
                    if let r, r.ok, r.data["bestaat"] as? Bool != true {
                        toonOnboarding = true
                    }
                }
                // Laadscherm als overlay óp het venster: het venster wordt
                // meteen de juiste grootte, geen kleine-groot-kleine-dans.
                .overlay {
                    if !laadSchermWeg {
                        LaadScherm()
                            .transition(.opacity)
                            .task {
                                // 2 seconden zichtbaar, dan 0.4s uitfaden.
                                try? await Task.sleep(nanoseconds: 2_000_000_000)
                                withAnimation(.easeOut(duration: 0.4)) {
                                    laadSchermWeg = true
                                }
                            }
                    }
                }
        }
        .commands {
            AppMenu(geselecteerd: $geselecteerd,
                    openInstellingen: { toonInstellingen = true },
                    openOver: { toonOver = true })
        }
        .windowStyle(.automatic)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var fullscreenToegepast = false

    func applicationDidBecomeActive(_ notification: Notification) {
        // Fullscreen pas ná het laadscherm (2,4s) — anders danst het venster.
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.4) { [weak self] in
            guard let self, self.fullscreenToegepast else { return }
            if let venster = NSApp.windows.first,
               !venster.styleMask.contains(.fullScreen) {
                venster.toggleFullScreen(nil)
            }
        }
        fullscreenToegepast = true
    }
}
