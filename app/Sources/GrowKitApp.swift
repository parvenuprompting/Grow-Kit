// GrowKit — de app die het harnas bedient (fase 6).
// De app is een bedienaar, nooit een machthebber: alle acties lopen via
// adapter.py, dat dezelfde poort, motor en faalcontract afdwingt.

import SwiftUI

@main
struct GrowKitApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 880, minHeight: 620)
                .background(Thema.kleur(.papier))
        }
        .windowStyle(.automatic)
    }
}
