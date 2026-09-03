// Ratificatie-scherm — taak 7 vult dit in.

import SwiftUI

struct RatificeerView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    var body: some View {
        PlaceholderView(titel: "Ratificatie",
                        tekst: "Taak 7 bouwt dit scherm: lijst → goedkeuren of afkeuren mét reden.")
    }
}
