// AppMenu — de echte menu-balk van de app (enterprise-laag).
//
// Bedienaar-principe: elk menu-item doet iets reëels — scherm wisselen,
// instellingen openen, hervatten, governor verversen — of roept de
// bestaande modus aan. Niets is decoratief: elk item is een kortere weg
// naar een functie die er al was.

import SwiftUI

struct AppMenu: Commands {
    // Binding naar de hoofdmodus van ContentView.
    @Binding var geselecteerd: ContentView.Modi
    // Open/sluit-acties die ContentView bezit.
    let openInstellingen: () -> Void
    let openOver: () -> Void

    var body: some Commands {
        // GROWKIT — het hoofdmenu
        CommandGroup(replacing: .appInfo) {
            Button("Over GrowKit") { openOver() }
                .keyboardShortcut("i", modifiers: [.command])
            Divider()
            Button("Instellingen…") { openInstellingen() }
                .keyboardShortcut(",")
            Divider()
            Button("Quit GrowKit") { NSApplication.shared.terminate(nil) }
                .keyboardShortcut("q")
        }

        // FILE — nieuwe boom, taken, repo openen
        CommandGroup(replacing: .newItem) {
            Button("Nieuwe Boom…") { geselecteerd = .planten }
                .keyboardShortcut("n")
            Button("Nieuwe Taak…") { geselecteerd = .taak }
                .keyboardShortcut("n", modifiers: [.command, .shift])
            Divider()
            Button("Hervat Restdraai") { geselecteerd = .hervatten }
                .keyboardShortcut("r", modifiers: [.command, .shift])
            Divider()
            Button("Repo-map openen in Finder") { openRepoInFinder() }
                .keyboardShortcut("o", modifiers: [.command])
        }

        // VIEW — de schermen met sneltoetsen (⌘1 t/m ⌘9)
        CommandGroup(replacing: .toolbar) {
            Button("Thuis") { geselecteerd = .home }
                .keyboardShortcut("1", modifiers: .command)
            Button("Status") { geselecteerd = .status }
                .keyboardShortcut("2", modifiers: .command)
            Button("Planten") { geselecteerd = .planten }
                .keyboardShortcut("3", modifiers: .command)
            Button("Goedkeuringen") { geselecteerd = .goedkeuringen }
                .keyboardShortcut("4", modifiers: .command)
            Button("Dialoog") { geselecteerd = .dialoog }
                .keyboardShortcut("5", modifiers: .command)
            Button("Agenten (Governor)") { geselecteerd = .agenten }
                .keyboardShortcut("6", modifiers: .command)
            Button("Hervatten") { geselecteerd = .hervatten }
                .keyboardShortcut("7", modifiers: .command)
            Button("Taak") { geselecteerd = .taak }
                .keyboardShortcut("8", modifiers: .command)
            Divider()
            Button("Rondleiding") { geselecteerd = .rondleiding }
                .keyboardShortcut("0", modifiers: .command)
            Button("Uitleg") { geselecteerd = .uitleg }
                .keyboardShortcut("/", modifiers: .command)
        }

        // HELP
        CommandGroup(replacing: .help) {
            Button("GrowKit Uitleg") { geselecteerd = .uitleg }
            Button("Rondleiding door de vijf schermen") { geselecteerd = .rondleiding }
            Divider()
            Button("Agenten-governor") { geselecteerd = .agenten }
        }
    }

    private func openRepoInFinder() {
        let pad = NSString(string: UserDefaults.standard.string(forKey: "growkitRepoPad") ?? "")
            .expandingTildeInPath
        NSWorkspace.shared.open(URL(fileURLWithPath: pad))
    }
}
