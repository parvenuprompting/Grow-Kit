// Statusbalk (Fase A) — lokale tijd, datum en weer, Editorial Monochrome.
// Weer via Open-Meteo (geen key); klok via de systeemtijd.

import SwiftUI

struct WeerData {
    let temperatuur: Double
    let omschrijving: String
    let icoon: String
}

final class StatusBalkStore: ObservableObject {
    @Published var tijd: String = ""
    @Published var datum: String = ""
    @Published var weer: WeerData? = nil
    private var timer: Timer?

    func start() {
        timer?.invalidate()
        vernieuw()
        timer = Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            self?.vernieuw()
        }
    }

    func stop() { timer?.invalidate(); timer = nil }

    func vernieuw() {
        let format = DateFormatter()
        format.locale = Locale(identifier: "nl_NL")
        format.timeZone = TimeZone.current
        format.dateFormat = "HH:mm"
        tijd = format.string(from: Date())
        format.dateFormat = "EEEE d MMMM"
        datum = format.string(from: Date())

        // Weer: Waddinxveen (huisbasis). Open-Meteo, geen sleutel nodig.
        Task {
            let url = URL(string: "https://api.open-meteo.com/v1/forecast?latitude=52.04&longitude=4.66&current=temperature_2m,weather_code")!
            if let (data, _) = try? await URLSession.shared.data(from: url),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let huidig = json["current"] as? [String: Any],
               let temp = huidig["temperature_2m"] as? Double,
               let code = huidig["weather_code"] as? Int {
                await MainActor.run {
                    weer = WeerData(temperatuur: temp,
                                    omschrijving: Self.omschrijving(code),
                                    icoon: Self.icoon(code))
                }
            }
        }
    }

    static func omschrijving(_ code: Int) -> String {
        switch code {
        case 0: return "helder"
        case 1, 2: return "licht bewolkt"
        case 3: return "bewolkt"
        case 45, 48: return "mist"
        case 51...57: return "motregen"
        case 61...67, 80...82: return "regen"
        case 71...77, 85, 86: return "sneeuw"
        case 95...99: return "onweer"
        default: return "weer onbekend"
        }
    }

    static func icoon(_ code: Int) -> String {
        switch code {
        case 0: return "sun.max"
        case 1, 2: return "cloud.sun"
        case 3: return "cloud"
        case 45, 48: return "cloud.fog"
        case 51...57: return "cloud.drizzle"
        case 61...67, 80...82: return "cloud.rain"
        case 71...77, 85, 86: return "cloud.snow"
        case 95...99: return "cloud.bolt.rain"
        default: return "cloud"
        }
    }
}

struct StatusBalk: View {
    @StateObject private var store = StatusBalkStore()

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: "clock").font(.system(size: 10))
                .foregroundStyle(Thema.kleur(.gedempt))
            Text("\(store.datum) · \(store.tijd)")
                .font(Thema.tekst(10)).tracking(0.5)
                .foregroundStyle(Thema.kleur(.zacht))
            if let weer = store.weer {
                Image(systemName: weer.icoon).font(.system(size: 10))
                    .foregroundStyle(Thema.kleur(.zacht))
                Text("\(String(format: "%.0f", weer.temperatuur))° — \(weer.omschrijving)")
                    .font(Thema.tekst(10)).tracking(0.5)
                    .foregroundStyle(Thema.kleur(.zacht))
            }
            Spacer()
        }
        .padding(.horizontal, 28).padding(.vertical, 4)
        .onAppear { store.start() }
        .onDisappear { store.stop() }
    }
}

// Fase A-mock: de toekomstige schermen, grijs en niet aanklikbaar.
struct MockScherm: View {
    let icoon: String
    let titel: String
    let belofte: String
    let komendeStappen: [String]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("IN BOUW · FASE B").font(Thema.tekst(9, gewicht: .semibold)).tracking(2)
                        .foregroundStyle(Thema.kleur(.gedempt))
                    HStack(spacing: 10) {
                        Image(systemName: icoon).font(.system(size: 26))
                            .foregroundStyle(Thema.kleur(.gedempt))
                        Text(titel).font(Thema.display(30))
                    }
                    Text(belofte)
                        .font(Thema.tekst(12)).foregroundStyle(Thema.kleur(.zacht))
                        .fixedSize(horizontal: false, vertical: true)
                }

                Kaart(kop: "Wat dit wordt", rechterKop: "IN HET BESTUURSVISIE") {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(Array(komendeStappen.enumerated()), id: \.offset) { i, stap in
                            HStack(alignment: .firstTextBaseline, spacing: 12) {
                                Text(String(format: "%02d", i + 1))
                                    .font(Thema.tekst(10, gewicht: .semibold)).tracking(0.5)
                                    .foregroundStyle(Thema.kleur(.gedempt))
                                    .frame(width: 26, alignment: .leading)
                                Text(stap).font(Thema.tekst(12))
                                    .foregroundStyle(Thema.kleur(.zacht))
                            }
                            if i < komendeStappen.count - 1 {
                                Rectangle().fill(Thema.kleur(.lijn)).frame(height: 0.5)
                            }
                        }
                    }
                }

                Text("Dit scherm is een schets van de visie — de functie wordt in een volgende bouwronde live gebouwd. Alles loopt via de adapter: de poort, motor en het faalcontract blijven de bewakers.")
                    .font(Thema.tekst(10)).foregroundStyle(Thema.kleur(.gedempt))
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(24)
        }
        .background(Thema.kleur(.papier))
    }
}
