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

    var body: some Scene {
        WindowGroup {
            ContentView(geselecteerd: $geselecteerd,
                        toonInstellingen: $toonInstellingen,
                        toonOver: $toonOver)
                .frame(minWidth: 880, minHeight: 620)
                .background(Thema.kleur(.papier))
                .sheet(isPresented: $toonOver) { OverView() }
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
        guard !fullscreenToegepast, let venster = NSApp.windows.first else { return }
        fullscreenToegepast = true
        if !venster.styleMask.contains(.fullScreen) {
            venster.toggleFullScreen(nil)
        }
    }
}
