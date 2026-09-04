// Spraakmemo — microfoonopname + lokale macOS-spraakherkenning (SFSpeechRecognizer).
// Geen API-sleutel, geen leverancier: de audio verlaat de machine niet.
// De herkende tekst landt in het chat-invoerveld; de curator leest en stuurt zelf.

import AVFoundation
import Foundation
import Speech

@MainActor
final class SpraakMemo: NSObject, ObservableObject {
    @Published var neemtOp = false
    @Published var transcript = ""
    @Published var fout: String?

    private let audioEngine = AVAudioEngine()
    private let herkenning: SFSpeechRecognizer?
    private var audioVerzoek: SFSpeechAudioBufferRecognitionRequest?
    private var taak: SFSpeechRecognitionTask?

    override init() {
        herkenning = SFSpeechRecognizer(locale: Locale(identifier: "nl-NL"))
        super.init()
    }

    func wisselOpname() {
        if neemtOp { stop() } else { start() }
    }

    private func start() {
        fout = nil
        transcript = ""
        SFSpeechRecognizer.requestAuthorization { [weak self] status in
            guard status == .authorized else {
                Task { @MainActor in
                    self?.fout = "Geen toestemming voor spraakherkenning — geef die in Systeeminstellingen → Privacy & Beveiliging."
                }
                return
            }
            Task { @MainActor in self?.beginOpname() }
        }
    }

    private func beginOpname() {
        do {
            let request = SFSpeechAudioBufferRecognitionRequest()
            request.shouldReportPartialResults = true
            if herkenning?.supportsOnDeviceRecognition == true {
                request.requiresOnDeviceRecognition = true   // audio verlaat de machine niet
            }

            let invoer = audioEngine.inputNode
            let formaat = invoer.outputFormat(forBus: 0)
            invoer.installTap(onBus: 0, bufferSize: 2048, format: formaat) { buffer, _ in
                request.append(buffer)
            }
            audioEngine.prepare()
            try audioEngine.start()

            self.audioVerzoek = request
            neemtOp = true

            taak = herkenning?.recognitionTask(with: request) { [weak self] resultaat, _ in
                guard let resultaat else { return }
                let tekst = resultaat.bestTranscription.formattedString
                Task { @MainActor in self?.transcript = tekst }
            }
        } catch {
            fout = "Opname kon niet beginnen: \(error.localizedDescription)"
            stop()
        }
    }

    /// Stop de opname en geef het transcript terug (leeg als er niets herkend is).
    func stop() -> String {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        audioVerzoek?.endAudio()
        taak?.cancel()
        taak = nil
        audioVerzoek = nil
        neemtOp = false
        return transcript.trimmingCharacters(in: .whitespaces)
    }
}