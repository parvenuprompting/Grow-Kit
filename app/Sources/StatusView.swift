// Status-scherm — taak 6 vult dit in.

import SwiftUI

struct StatusView: View {
    @ObservedObject var runner: Runner
    @Binding var repoPad: String
    @Binding var interpreter: String

    var body: some View {
        PlaceholderView(titel: "Status",
                        tekst: "Taak 6 bouwt dit scherm: identiteit, register, tellers en logboek.")
    }
}
