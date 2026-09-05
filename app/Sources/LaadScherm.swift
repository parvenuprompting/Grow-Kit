// Laadscherm (Fase A) — kort, mooi, modern: één seconde groeionte, dan weg.
// App-icoon groeit zacht uit met een dunne inkt-lijn die zich tekent,
// aansluitend vervaagt het scherm. Geen tekst, geen wachtwoorden.

import SwiftUI

struct LaadScherm: View {
    @State private var verschenen = false
    @State private var vervaagd = false

    var body: some View {
        ZStack {
            Thema.kleur(.papier).ignoresSafeArea()
            VStack(spacing: 16) {
                Image("LogoVolledig")
                    .resizable().scaledToFit()
                    .frame(width: 190, height: 190)
                    .clipShape(RoundedRectangle(cornerRadius: 18))
                    .shadow(color: .black.opacity(0.2), radius: 8, y: 3)
                    .scaleEffect(verschenen ? 1.0 : 0.75)
                    .opacity(verschenen ? 1 : 0)
            }
        }
        .opacity(vervaagd ? 0 : 1)
        .allowsHitTesting(false)
        .onAppear {
            withAnimation(.spring(response: 0.45, dampingFraction: 0.75)) {
                verschenen = true
            }
            // Na twee seconden zacht uitfaden (0.4s), daarna volledig weg.
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                withAnimation(.easeOut(duration: 0.4)) { vervaagd = true }
            }
        }
    }

    // Overlay-gebruik: LaadScherm().overlayOp(melding) boven de app zelf,
    // zodat het venster al klaarstaat terwijl het scherm vervaagt.
    static func overlayOp() -> some View {
        LaadScherm().allowsHitTesting(false)
    }
}
