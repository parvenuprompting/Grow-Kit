// GrowKit — de app die het harnas bedient (fase 6).
// De app is een bedienaar, nooit een machthebber: alle acties lopen via
// adapter.py, dat dezelfde poort, motor en faalcontract afdwingt.
// De app opent standaard in fullscreen (elke start, uitschakelbaar met ESC).

import SwiftUI

@main
struct GrowKitApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 880, minHeight: 620)
                .background(Thema.kleur(.papier))
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
