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
            VStack(spacing: 18) {
                ZStack {
                    Circle()
                        .stroke(Thema.kleur(.lijn), lineWidth: 1)
                        .frame(width: 74, height: 74)
                        .scaleEffect(verschenen ? 1.0 : 0.7)
                    Image(systemName: "leaf")
                        .font(.system(size: 30, weight: .light))
                        .foregroundStyle(Thema.kleur(.inkt))
                        .scaleEffect(verschenen ? 1.0 : 0.5)
                        .opacity(verschenen ? 1 : 0)
                }
                HStack(spacing: 0) {
                    Text("Grow").font(Thema.display(18))
                    Text("Kit").font(Thema.display(18, cursief: true))
                        .foregroundStyle(Thema.kleur(.zacht))
                }
                .opacity(verschenen ? 1 : 0)
                .offset(y: verschenen ? 0 : 6)
            }
        }
        .opacity(vervaagd ? 0 : 1)
        .allowsHitTesting(false)
        .onAppear {
            withAnimation(.spring(response: 0.45, dampingFraction: 0.75)) {
                verschenen = true
            }
            // Na één seconde zacht uitfaden (0.4s), daarna volledig weg.
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
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
