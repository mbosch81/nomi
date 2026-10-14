// Local OCR helper. Distributed as a compiled executable inside Nomi.app.
import Foundation
import Vision
import CoreML

func fail(_ code: Int32) -> Never {
    // Never print document text, filesystem paths or system diagnostics.
    FileHandle.standardError.write(Data("Apple Vision OCR failed.\n".utf8))
    exit(code)
}

let arguments = CommandLine.arguments
if arguments.count != 3 { fail(2) }

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.revision = VNRecognizeTextRequestRevision3
// A stable OCR revision and explicit CPU execution avoid first-use GPU/ANE
// initialization stalls in a short-lived, cancellable command-line process.
if let cpu = MLComputeDevice.allComputeDevices.first(where: {
    if case .cpu = $0 { return true }
    return false
}) {
    request.setComputeDevice(cpu, for: .main)
}
request.usesLanguageCorrection = true
let languages = arguments[2].split(separator: "+").map(String.init)
do {
    let supported = try request.supportedRecognitionLanguages()
    guard !languages.isEmpty, languages.allSatisfy({ supported.contains($0) }) else { fail(3) }
    request.recognitionLanguages = languages
    let handler = VNImageRequestHandler(url: URL(fileURLWithPath: arguments[1]), options: [:])
    try handler.perform([request])
    // Vision observations are returned in reading order; preserve their lines.
    let lines = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
    FileHandle.standardOutput.write(Data(lines.joined(separator: "\n").utf8))
} catch {
    fail(1)
}
