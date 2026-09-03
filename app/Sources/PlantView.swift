// Plant-scherm — taak 7 vult dit in.

import SwiftUI

struct PlantView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    var body: some View {
        PlaceholderView(titel: "Planten",
                        tekst: "Taak 7 bouwt dit scherm: formulier → concept → bevestiging → motor.")
    }
}
