import AppKit
import AVFoundation
import CoreGraphics
import Darwin
import IOSurface
import Speech

private let headerBytes = 64
private let captureAspect: CGFloat = 1600.0 / 1258.0
private let horizontalContentInset: CGFloat = 24
private let verticalContentInset: CGFloat = 20
@_silgen_name("shm_open") private func posixShmOpen(_ name: UnsafePointer<CChar>, _ flags: Int32, _ mode: mode_t) -> Int32
@_silgen_name("ftruncate") private func posixFtruncate(_ fd: Int32, _ length: off_t) -> Int32

final class CharacterLetteringRow: NSView {
    private weak var item: NSMenuItem?
    init(item: NSMenuItem, image: NSImage, label: String, suffix: String, selected: Bool) {
        self.item = item
        super.init(frame: NSRect(x: 0, y: 0, width: 288, height: 56))
        let artwork = NSImageView(frame: NSRect(x: 32, y: 4, width: 144, height: 48))
        artwork.image = image; artwork.imageScaling = .scaleNone
        addSubview(artwork)
        if selected {
            let check = NSTextField(labelWithString: "✓")
            check.frame = NSRect(x: 8, y: 18, width: 20, height: 20)
            check.textColor = .systemCyan; addSubview(check)
        }
        let text = NSTextField(labelWithString: suffix)
        text.frame = NSRect(x: 184, y: 18, width: 100, height: 20)
        text.font = .systemFont(ofSize: 12); text.textColor = .white
        addSubview(text)
        let button = NSButton(frame: bounds)
        button.title = ""; button.isBordered = false; button.isTransparent = true
        button.target = self; button.action = #selector(activate)
        button.setAccessibilityLabel(label); button.toolTip = label
        button.isEnabled = item.isEnabled
        addSubview(button)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
    @objc private func activate() {
        guard let item, let action = item.action else { return }
        item.menu?.cancelTracking()
        DispatchQueue.main.async { NSApp.sendAction(action, to: item.target, from: item) }
    }
}

final class DragSurfaceView: NSView { override var mouseDownCanMoveWindow: Bool { true } }
final class LiquidGlassHighlightView: NSView {
    override var isOpaque: Bool { false }
    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)
        let shape = NSBezierPath(roundedRect: bounds.insetBy(dx: 1, dy: 1), xRadius: 13, yRadius: 13)
        NSGraphicsContext.saveGraphicsState()
        shape.addClip()
        NSGradient(colorsAndLocations:
            (NSColor.white.withAlphaComponent(0.48), 0.0),
            (NSColor.white.withAlphaComponent(0.10), 0.22),
            (NSColor.systemCyan.withAlphaComponent(0.07), 0.58),
            (NSColor.systemIndigo.withAlphaComponent(0.10), 1.0)
        )?.draw(in: bounds, angle: -62)
        NSGraphicsContext.restoreGraphicsState()
        NSColor.white.withAlphaComponent(0.55).setStroke()
        shape.lineWidth = 1
        shape.stroke()
    }
}
enum ConversationZoomGeometry {
    static func horizontalShift(body: NSRect, workArea: NSRect, chatWidth: CGFloat, chatOnRight: Bool) -> CGFloat {
        let safe = workArea.insetBy(dx: 8, dy: 8), reserve = chatWidth + 12
        guard body.width + reserve <= safe.width else { return 0 }
        let left = safe.minX + (chatOnRight ? 0 : reserve)
        let right = safe.maxX - body.width - (chatOnRight ? reserve : 0)
        return min(max(body.minX, left), right) - body.minX
    }
}

enum OverlayDragGeometry {
    static func recoveredOrigin(window: NSRect, body: NSRect, workArea: NSRect) -> NSPoint {
        let safe = workArea.insetBy(dx: 8, dy: 8)
        let head = min(body.height, min(140, max(72, body.height * 0.22)))
        let x = body.width > safe.width ? safe.midX-body.width/2 : min(max(body.minX,safe.minX),safe.maxX-body.width)
        let top = min(max(body.maxY,safe.minY+head),safe.maxY)
        return NSPoint(x: window.minX+x-body.minX, y: window.minY+top-body.maxY)
    }
    static func progress(_ t: Double) -> Double { let t = min(max(t,0),1); return 1-pow(1-t,3) }
}

final class InteractiveOverlayWindow: NSWindow {
    var preservesResizeAnchor = false
    private(set) var isPointerDragging = false
    private var pointerStart = NSPoint.zero
    private var originStart = NSPoint.zero
    var onDragBegin: (() -> Void)?
    var onDragEnd: (() -> Void)?
    var onDoubleClick: (() -> Void)?
    override func sendEvent(_ event: NSEvent) {
        switch event.type {
        case .leftMouseDown:
            guard !ignoresMouseEvents else { super.sendEvent(event); return }
            beginPointerDrag(at: NSEvent.mouseLocation)
            if event.clickCount == 2 { onDoubleClick?() }
        case .leftMouseDragged where isPointerDragging:
            updatePointerDrag(at: NSEvent.mouseLocation)
        case .leftMouseUp where isPointerDragging:
            endPointerDrag()
        default: super.sendEvent(event)
        }
    }
    func beginPointerDrag(at point: NSPoint) {
        onDragBegin?(); makeKey(); pointerStart = point; originStart = frame.origin; isPointerDragging = true
    }
    func updatePointerDrag(at point: NSPoint) {
        guard isPointerDragging else { return }
        setFrameOrigin(NSPoint(x: originStart.x+point.x-pointerStart.x, y: originStart.y+point.y-pointerStart.y))
    }
    func endPointerDrag() { isPointerDragging = false; onDragEnd?() }
    override func constrainFrameRect(_ frameRect: NSRect, to screen: NSScreen?) -> NSRect {
        (preservesResizeAnchor || isPointerDragging) ? frameRect : super.constrainFrameRect(frameRect, to: screen)
    }
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}

final class OverlayActionButton: NSButton {
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override func sendAction(_ action: Selector?, to target: Any?) -> Bool {
        fputs("overlay action: \(action.map(NSStringFromSelector) ?? "none")\n", stderr)
        let delivered = super.sendAction(action, to: target)
        fputs("overlay delivered: \(delivered) target: \(String(describing: target))\n", stderr)
        return delivered
    }
}
final class QuickChatPanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}
final class DragImageView: NSImageView {
    override var mouseDownCanMoveWindow: Bool { true }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    var onHorizontalRotationDelta: ((CGFloat) -> Void)?
    private var lastRightDragX: CGFloat?

    override func rightMouseDown(with event: NSEvent) {
        window?.makeKey()
        lastRightDragX = convert(event.locationInWindow, from: nil).x
    }

    override func rightMouseDragged(with event: NSEvent) {
        let x = convert(event.locationInWindow, from: nil).x
        if let previous = lastRightDragX { onHorizontalRotationDelta?(x - previous) }
        lastRightDragX = x
    }

    override func rightMouseUp(with event: NSEvent) { lastRightDragX = nil }
}

final class SharedOverlayControlWriter {
    private static let bytes = 64
    private static let magic: UInt32 = 0x47484354 // GHCT
    private var fd: Int32 = -1
    private var address: UnsafeMutableRawPointer?

    deinit { if let address { munmap(address, Self.bytes) }; if fd >= 0 { close(fd) } }

    private func connect() -> Bool {
        if address != nil { return true }
        fd = "/gahyeon_overlay_control_v001".withCString { posixShmOpen($0, O_RDWR, 0) }
        var info = stat()
        guard fd >= 0, fstat(fd, &info) == 0, info.st_size >= Self.bytes else {
            if fd >= 0 { close(fd) }; fd = -1; return false
        }
        let mappedResult = mmap(nil, Self.bytes, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0)
        guard let mapped = mappedResult, mapped != MAP_FAILED else { close(fd); fd = -1; return false }
        address = mapped
        mapped.storeBytes(of: Self.magic, toByteOffset: 0, as: UInt32.self)
        mapped.storeBytes(of: UInt32(1), toByteOffset: 4, as: UInt32.self)
        return true
    }

    func selectCharacter(_ index: UInt32) -> Bool {
        guard index < 8, connect(), let address,
              address.load(fromByteOffset: 44, as: UInt32.self) == 0x524F5354 else { return false }
        address.storeBytes(of: index, toByteOffset: 32, as: UInt32.self)
        return true
    }
    func appliedCharacter() -> UInt32? {
        guard connect(), let address,
              address.load(fromByteOffset: 44, as: UInt32.self) == 0x524F5354 else { return nil }
        return address.load(fromByteOffset: 36, as: UInt32.self)
    }

    func publish(yaw: Float, reset: Bool = false) {
        guard connect(), let address else { return }
        address.storeBytes(of: Self.magic, toByteOffset: 0, as: UInt32.self)
        address.storeBytes(of: UInt32(1), toByteOffset: 4, as: UInt32.self)
        address.storeBytes(of: yaw, toByteOffset: 8, as: Float.self)
        let sequence = address.load(fromByteOffset: 16, as: UInt64.self) &+ 1
        address.storeBytes(of: sequence, toByteOffset: 16, as: UInt64.self)
        if reset {
            let resetSequence = address.load(fromByteOffset: 24, as: UInt64.self) &+ 1
            address.storeBytes(of: resetSequence, toByteOffset: 24, as: UInt64.self)
        }
    }
}

final class SharedIOSurfaceReader {
    private var fd: Int32 = -1
    private var address: UnsafeMutableRawPointer?
    private var lastSequence: UInt64 = 0
    private var surfaceID: UInt32 = 0
    private var surface: IOSurfaceRef?
    deinit { if let address { munmap(address, 64) }; if fd >= 0 { close(fd) } }
    private func connect() -> Bool {
        if address != nil { return true }
        fd = "/gahyeon_iosurface_v001".withCString { posixShmOpen($0, O_RDONLY, 0) }
        guard fd >= 0 else { return false }
        let mapped = mmap(nil, 64, PROT_READ, MAP_SHARED, fd, 0)
        guard mapped != MAP_FAILED else { close(fd); fd = -1; return false }
        address = mapped; return true
    }
    func nextSurface() -> (IOSurfaceRef, Int, Int, CGRect)? {
        guard connect(), let base = address else { return nil }
        let magic = base.load(fromByteOffset: 0, as: UInt32.self)
        let id = base.load(fromByteOffset: 8, as: UInt32.self)
        let width = Int(base.load(fromByteOffset: 12, as: UInt32.self))
        let height = Int(base.load(fromByteOffset: 16, as: UInt32.self))
        let sequence = base.load(fromByteOffset: 40, as: UInt64.self)
        guard magic == 0x4748494f, id != 0, sequence != 0, sequence != lastSequence else { return nil }
        if id != surfaceID { surface = IOSurfaceLookup(id); surfaceID = id }
        guard let surface else { return nil }
        let minX = CGFloat(base.load(fromByteOffset: 20, as: UInt32.self))
        let minY = CGFloat(base.load(fromByteOffset: 24, as: UInt32.self))
        let maxX = CGFloat(base.load(fromByteOffset: 28, as: UInt32.self))
        let maxY = CGFloat(base.load(fromByteOffset: 32, as: UInt32.self))
        lastSequence = sequence
        let crop = CGRect(x: minX / CGFloat(width), y: 1 - maxY / CGFloat(height),
                          width: (maxX - minX) / CGFloat(width), height: (maxY - minY) / CGFloat(height))
        return (surface, Int(maxX-minX), Int(maxY-minY), crop)
    }
}

final class SharedRGBAReader {
    private var fd: Int32 = -1
    private var address: UnsafeMutableRawPointer?
    private var size = 0
    private var lastSequence: UInt64 = 0

    deinit {
        if let address { munmap(address, size) }
        if fd >= 0 { close(fd) }
    }

    private func connect() -> Bool {
        if address != nil { return true }
        fd = "/gahyeon_rgba_v003".withCString { posixShmOpen($0, O_RDONLY, 0) }
        guard fd >= 0 else { return false }
        var info = stat()
        guard fstat(fd, &info) == 0 else { close(fd); fd = -1; return false }
        size = Int(info.st_size)
        let mapped = mmap(nil, size, PROT_READ, MAP_SHARED, fd, 0)
        guard mapped != MAP_FAILED else { close(fd); fd = -1; return false }
        address = mapped
        return true
    }

    func nextImage() -> CGImage? {
        guard connect(), let base = address else { return nil }
        let magic = base.load(fromByteOffset: 0, as: UInt32.self)
        let width = Int(base.load(fromByteOffset: 8, as: UInt32.self))
        let height = Int(base.load(fromByteOffset: 12, as: UInt32.self))
        let stride = Int(base.load(fromByteOffset: 16, as: UInt32.self))
        let active = Int(base.load(fromByteOffset: 20, as: UInt32.self))
        let sequence = base.load(fromByteOffset: 24, as: UInt64.self)
        let minX = Int(base.load(fromByteOffset: 40, as: UInt32.self))
        let minY = Int(base.load(fromByteOffset: 44, as: UInt32.self))
        let maxX = Int(base.load(fromByteOffset: 48, as: UInt32.self))
        let maxY = Int(base.load(fromByteOffset: 52, as: UInt32.self))
        guard magic == 0x47485247, width > 0, height > 0, stride == width * 4,
              sequence != 0, sequence != lastSequence else { return nil }
        let byteCount = stride * height
        let offset = headerBytes + active * byteCount
        guard offset + byteCount <= size else { return nil }
        let data = Data(bytes: base.advanced(by: offset), count: byteCount)
        guard sequence == base.load(fromByteOffset: 24, as: UInt64.self),
              active == Int(base.load(fromByteOffset: 20, as: UInt32.self)),
              let provider = CGDataProvider(data: data as CFData) else { return nil }
        lastSequence = sequence
        guard let image = CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32,
            bytesPerRow: stride, space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue),
            provider: provider, decode: nil, shouldInterpolate: true, intent: .defaultIntent) else { return nil }
        let left = max(0, minX - 80), top = max(0, minY - 50)
        let right = min(width - 1, maxX + 80), bottom = min(height - 1, maxY + 50)
        guard right > left, bottom > top else { return image }
        return image.cropping(to: CGRect(x: left, y: top, width: right - left + 1, height: bottom - top + 1)) ?? image
    }
}

final class DesktopCoreClient {
    struct MessageResponse: Decodable { let runId: String; let content: String }
    struct SpeechStatus: Decodable {
        let transcriptionReady: Bool
        let synthesisReady: Bool
        let expressiveSynthesisReady: Bool
    }

    private let root = URL(string: ProcessInfo.processInfo.environment["GAHYEON_CORE_URL"]
        ?? "http://127.0.0.1:8080/api")!
    private let installationId: String = {
        if let value = UserDefaults.standard.string(forKey: "installationId") { return value }
        let value = "mac-" + UUID().uuidString.lowercased()
        UserDefaults.standard.set(value, forKey: "installationId")
        return value
    }()
    private let sessionId: String = {
        if let value = UserDefaults.standard.string(forKey: "sessionId") { return value }
        let value = "desktop-" + UUID().uuidString.lowercased()
        UserDefaults.standard.set(value, forKey: "sessionId")
        return value
    }()

    func speechStatus(completion: @escaping (Result<SpeechStatus, Error>) -> Void) {
        request(path: "/gahyeon/desktop/speech/status", method: "GET", body: nil, completion: completion)
    }

    func send(message: String, characterId: String, completion: @escaping (Result<MessageResponse, Error>) -> Void) {
        let body: [String: Any] = [
            "requestId": "mac:" + UUID().uuidString.lowercased(), "installationId": installationId,
            "displayName": NSFullUserName().isEmpty ? "사용자" : NSFullUserName(),
            "characterId": characterId, "message": message,
        ]
        request(path: "/gahyeon/desktop/conversations/\(sessionId)/messages", method: "POST",
                body: try? JSONSerialization.data(withJSONObject: body), completion: completion)
    }

    func speechData(path: String, data: Data, mediaType: String,
                    completion: @escaping (Result<Data, Error>) -> Void) {
        var request = URLRequest(url: root.appendingPathComponent("gahyeon/desktop/speech/" + path))
        request.httpMethod = "POST"; request.httpBody = data; request.timeoutInterval = 60
        request.setValue(mediaType, forHTTPHeaderField: "Content-Type")
        if let token = ProcessInfo.processInfo.environment["GAHYEON_CLIENT_TOKEN"], !token.isEmpty {
            request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        }
        URLSession.shared.dataTask(with: request) { data, response, error in
            let result: Result<Data, Error>
            if let error { result = .failure(error) }
            else if let response = response as? HTTPURLResponse, (200..<300).contains(response.statusCode), let data {
                result = .success(data)
            } else {
                result = .failure(NSError(domain: "GahyeonCore", code: (response as? HTTPURLResponse)?.statusCode ?? -1,
                    userInfo: [NSLocalizedDescriptionKey: "음성 서버 요청에 실패했습니다."]))
            }
            DispatchQueue.main.async { completion(result) }
        }.resume()
    }

    private func request<T: Decodable>(path: String, method: String, body: Data?,
                                       completion: @escaping (Result<T, Error>) -> Void) {
        var request = URLRequest(url: root.appendingPathComponent(path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))))
        request.httpMethod = method; request.httpBody = body
        // Multi-step research includes several provider and source-fetch round trips.
        request.timeoutInterval = method == "POST" && path.hasPrefix("/gahyeon/desktop/conversations/") ? 180 : 20
        if let token = ProcessInfo.processInfo.environment["GAHYEON_CLIENT_TOKEN"], !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if body != nil { request.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        URLSession.shared.dataTask(with: request) { data, response, error in
            let result: Result<T, Error>
            if let error { result = .failure(error) }
            else if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                result = .failure(NSError(domain: "GahyeonCore", code: http.statusCode,
                    userInfo: [NSLocalizedDescriptionKey: "Core HTTP \(http.statusCode)"]))
            } else {
                do { result = .success(try JSONDecoder().decode(T.self, from: data ?? Data())) }
                catch { result = .failure(error) }
            }
            DispatchQueue.main.async { completion(result) }
        }.resume()
    }
}

final class NativeSpeechInput {
    private let engine = AVAudioEngine()
    private let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "ko-KR"))
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?
    private(set) var recording = false

    func toggle(onText: @escaping (String, Bool) -> Void, onError: @escaping (String) -> Void) {
        recording ? stop() : start(onText: onText, onError: onError)
    }

    func stop() {
        guard recording else { return }
        engine.stop(); engine.inputNode.removeTap(onBus: 0); request?.endAudio()
        recording = false
    }

    private func start(onText: @escaping (String, Bool) -> Void, onError: @escaping (String) -> Void) {
        SFSpeechRecognizer.requestAuthorization { [weak self] status in
            DispatchQueue.main.async {
                guard let self, status == .authorized else { onError("음성 인식 권한이 필요합니다."); return }
                AVCaptureDevice.requestAccess(for: .audio) { allowed in
                    DispatchQueue.main.async {
                        guard allowed else { onError("마이크 권한이 필요합니다."); return }
                        self.begin(onText: onText, onError: onError)
                    }
                }
            }
        }
    }

    private func begin(onText: @escaping (String, Bool) -> Void, onError: @escaping (String) -> Void) {
        task?.cancel(); task = nil
        let request = SFSpeechAudioBufferRecognitionRequest(); request.shouldReportPartialResults = true
        self.request = request
        let node = engine.inputNode, format = node.outputFormat(forBus: 0)
        node.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in request.append(buffer) }
        task = recognizer?.recognitionTask(with: request) { [weak self] result, error in
            if let result { DispatchQueue.main.async { onText(result.bestTranscription.formattedString, result.isFinal) } }
            if let error { DispatchQueue.main.async { self?.stop(); onError(error.localizedDescription) } }
        }
        do { engine.prepare(); try engine.start(); recording = true }
        catch { node.removeTap(onBus: 0); onError(error.localizedDescription) }
    }
}

// MARK: - Bounded speech segments
func desktopSpeechSegments(_ text: String) -> [String] {
    var clean = text.replacingOccurrences(of: #"\[([^\]]+)\]\(https?://[^\s)]+\)"#, with: "$1", options: .regularExpression)
    clean = clean.replacingOccurrences(of: #"https?://\S+"#, with: "", options: .regularExpression)
    clean = clean.replacingOccurrences(of: #"(?m)^\s*\|?[-:| ]{3,}\|?\s*$"#, with: "", options: .regularExpression)
    clean = clean.replacingOccurrences(of: #"[*#`|>]"#, with: " ", options: .regularExpression)
    var result: [String] = [], part = ""
    for character in clean {
        part.append(character)
        if part.unicodeScalars.count >= 180 || (character == " " && part.count >= 100) || ((character == "!" || character == "?" || character == "\n") && part.count >= 12) {
            let value = part.trimmingCharacters(in: .whitespacesAndNewlines)
            if !value.isEmpty { result.append(value) }
            part = ""
        }
    }
    let remaining = part.trimmingCharacters(in: .whitespacesAndNewlines)
    if !remaining.isEmpty { result.append(remaining) }
    return result
}

final class DesktopSegmentedSpeech: NSObject, AVAudioPlayerDelegate {
    private let core: DesktopCoreClient
    private let current: () -> Bool
    private let deliver: (AVAudioPlayer) -> Void
    private let failure: (Error) -> Void
    private var segments: [String] = []
    private var ready: [Int: Data] = [:]
    private var index = 0
    private var playing = false
    private var failed = false
    private let started = ProcessInfo.processInfo.systemUptime
    init(core: DesktopCoreClient, current: @escaping () -> Bool,
         deliver: @escaping (AVAudioPlayer) -> Void, failure: @escaping (Error) -> Void) {
        self.core = core; self.current = current; self.deliver = deliver; self.failure = failure
    }
    func start(_ text: String) { segments = desktopSpeechSegments(text); fetch(0) }
    private func fetch(_ target: Int) {
        guard current(), !failed, target < segments.count else { return }
        let payload: [String: Any] = ["index": target, "text": segments[target], "voiceProfile": "gahyeon.assistant"]
        guard let body = try? JSONSerialization.data(withJSONObject: payload) else { return }
        core.speechData(path: "synthesis", data: body, mediaType: "application/json") { [weak self] result in
            guard let self, self.current(), !self.failed else { return }
            do { self.ready[target] = try result.get(); self.playReady() }
            catch { self.failed = true; self.failure(error) }
        }
    }
    private func playReady() {
        guard current(), !failed, !playing, let data = ready.removeValue(forKey: index) else { return }
        do {
            let player = try AVAudioPlayer(data: data)
            player.delegate = self; player.prepareToPlay()
            deliver(player)
            guard player.play() else { throw NSError(domain: "AudioPlayback", code: 1) }
            playing = true
            if index == 0 { fputs("LATENCY_AUDIO first_play_ms=\((ProcessInfo.processInfo.systemUptime-started)*1000)\n", stderr) }
            fetch(index + 1) // One bounded prefetch while this segment plays.
        } catch { failed = true; failure(error) }
    }
    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        guard current(), !failed else { return }
        guard flag else { failed = true; failure(NSError(domain: "AudioPlayback", code: 2)); return }
        playing = false; index += 1; playReady()
    }
}
// MARK: - End bounded speech segments

final class ServerMicrophoneRecorder: NSObject, AVAudioRecorderDelegate {
    private var recorder: AVAudioRecorder?
    private var completion: ((Result<Data, Error>) -> Void)?
    private var file: URL?
    private var timeout: Timer?
    var recording: Bool { recorder?.isRecording ?? false }

    func start(state: @escaping (Bool) -> Void, completion: @escaping (Result<Data, Error>) -> Void) {
        AVCaptureDevice.requestAccess(for: .audio) { [weak self] allowed in
            DispatchQueue.main.async {
                guard let self else { return }
                guard allowed else {
                    state(false)
                    completion(.failure(NSError(domain: "Microphone", code: 1,
                        userInfo: [NSLocalizedDescriptionKey: "마이크 권한이 필요합니다."])))
                    return
                }
                do {
                    let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".wav")
                    self.file = url; self.completion = completion
                    self.recorder = try AVAudioRecorder(url: url, settings: [
                        AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: 16000,
                        AVNumberOfChannelsKey: 1, AVLinearPCMBitDepthKey: 16,
                        AVLinearPCMIsFloatKey: false, AVLinearPCMIsBigEndianKey: false])
                    guard self.recorder?.record() == true else { throw NSError(domain: "Microphone", code: 2) }
                    state(true)
                    self.timeout = Timer.scheduledTimer(withTimeInterval: 30, repeats: false) { [weak self] _ in
                        self?.stop(); state(false)
                    }
                } catch { state(false); self.clean(); completion(.failure(error)) }
            }
        }
    }
    func stop() {
        guard recording else { return }
        recorder?.stop(); timeout?.invalidate(); timeout = nil
        let callback = completion
        do {
            guard let file else { throw NSError(domain: "Microphone", code: 3) }
            let data = try Data(contentsOf: file)
            clean(); callback?(.success(data))
        } catch { clean(); callback?(.failure(error)) }
    }
    private func clean() {
        recorder = nil; completion = nil
        if let file { try? FileManager.default.removeItem(at: file) }
        file = nil
    }
    deinit { recorder?.stop(); timeout?.invalidate(); if let file { try? FileManager.default.removeItem(at: file) } }
}

final class ConversationSurface: NSView {
    var lines = true
    override func draw(_ dirtyRect: NSRect) {
        NSColor(calibratedRed: 0.141, green: 0.157, blue: 0.188, alpha: 0.97).setFill()
        let shape = NSBezierPath(roundedRect: bounds.insetBy(dx: 0.5, dy: 0.5), xRadius: 16, yRadius: 16)
        shape.fill(); NSColor.white.withAlphaComponent(0.12).setStroke(); shape.lineWidth = 1; shape.stroke()
        if lines {
            let path = NSBezierPath(); path.move(to: NSPoint(x: 16, y: bounds.height - 48)); path.line(to: NSPoint(x: bounds.width - 16, y: bounds.height - 48))
            path.move(to: NSPoint(x: 16, y: 100)); path.line(to: NSPoint(x: bounds.width - 16, y: 100))
            NSColor.white.withAlphaComponent(0.08).setStroke(); path.stroke()
        }
    }
}
final class ConversationActionButton: NSButton {
    private var hoverArea: NSTrackingArea?
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override func updateTrackingAreas() {
        super.updateTrackingAreas(); if let hoverArea { removeTrackingArea(hoverArea) }
        let area = NSTrackingArea(rect: bounds, options: [.mouseEnteredAndExited, .activeAlways, .inVisibleRect], owner: self)
        addTrackingArea(area); hoverArea = area
    }
    override func mouseEntered(with event: NSEvent) { layer?.backgroundColor = NSColor.white.withAlphaComponent(0.12).cgColor }
    override func mouseExited(with event: NSEvent) { layer?.backgroundColor = NSColor.clear.cgColor }
}
final class RosterCardButton: NSButton {
    override var isFlipped: Bool { false }
    var preview: NSImage?
    var lettering: NSImage?
    var source = NSRect.zero
    var selected = false
    private var hover = false
    private var hoverArea: NSTrackingArea?
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override func updateTrackingAreas() {
        super.updateTrackingAreas(); if let hoverArea { removeTrackingArea(hoverArea) }
        let area = NSTrackingArea(rect: bounds, options: [.mouseEnteredAndExited, .activeAlways, .inVisibleRect], owner: self)
        addTrackingArea(area); hoverArea = area
    }
    override func mouseEntered(with event: NSEvent) { hover = true; needsDisplay = true }
    override func mouseExited(with event: NSEvent) { hover = false; needsDisplay = true }
    override func draw(_ dirtyRect: NSRect) {
        let shape = NSBezierPath(roundedRect: bounds.insetBy(dx: 1, dy: 1), xRadius: 12, yRadius: 12)
        NSColor.white.withAlphaComponent(isHighlighted ? 0.16 : hover ? 0.10 : 0.035).setFill(); shape.fill()
        (selected ? NSColor(calibratedRed: 0.51, green: 0.85, blue: 0.86, alpha: 1) : NSColor.white.withAlphaComponent(0.10)).setStroke()
        shape.lineWidth = selected ? 2 : 1; shape.stroke()
        if let preview, source.width > 0 {
            let factor = min(124 / source.width, 74 / source.height)
            let size = NSSize(width: source.width * factor, height: source.height * factor)
            preview.draw(in: NSRect(x: (bounds.width-size.width)/2, y: 34, width: size.width, height: size.height), from: source, operation: .sourceOver, fraction: isEnabled ? 1 : 0.4)
        }
        lettering?.draw(in: NSRect(x: 14, y: 3, width: bounds.width-28, height: 32), from: .zero, operation: .sourceOver, fraction: isEnabled ? 1 : 0.4)
        if selected { ("✓" as NSString).draw(at: NSPoint(x: 12, y: bounds.height-25), withAttributes: [.font: NSFont.systemFont(ofSize: 13, weight: .semibold), .foregroundColor: NSColor.systemCyan]) }
        if window?.firstResponder === self { NSColor.keyboardFocusIndicatorColor.setStroke(); shape.stroke() }
    }
}
private enum ConversationDesign {
    static let data = (try? Data(contentsOf: URL(fileURLWithPath: "config/desktop-conversation-design.json"))) ?? Data()
    static let values = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:]
    static func number(_ key: String, _ fallback: CGFloat) -> CGFloat { (values[key] as? NSNumber).map { CGFloat(truncating: $0) } ?? fallback }
}

final class OverlayController: NSObject, NSApplicationDelegate {
    private let gpuEnabled = ProcessInfo.processInfo.environment["GAHYEON_GPU_IOSURFACE"] == "1"
    private let gpuReader = SharedIOSurfaceReader()
    private let reader = SharedRGBAReader()
    private let controlWriter = SharedOverlayControlWriter()
    private let core = DesktopCoreClient()
    private let serverMicrophone = ServerMicrophoneRecorder()
    private var microphonePending = false
    private var serverAudio: AVAudioPlayer?
    private var segmentedSpeech: DesktopSegmentedSpeech?
    private var speechGeneration = 0

    private let imageView = DragImageView()
    private var window: NSWindow?
    private var panel: NSPanel?
    private var controlBubble: NSPanel?
    private var chatPanel: NSPanel?
    private var chatHistory: NSTextView?
    private var chatInput: NSTextField?
    private var chatScroll: NSScrollView?
    private var chatHistoryButton: NSButton?
    private var chatExpanded = false
    private var pickerPanel: NSPanel?
    private var chatHeader: NSView?
    private var activityLabel: NSTextField?
    private var reactionStarted: CFAbsoluteTime = -100
    private var lastInteractionTick: CFAbsoluteTime = 0
    private var publishedReactionYaw: Float = .greatestFiniteMagnitude
    private var lastBaseYaw: CGFloat = .nan
    private var interactionPhase = ""
    private var quickChatLayoutBusy = false
    private var nextIdleReaction = CFAbsoluteTimeGetCurrent() + 45
    private var reducedMotion = UserDefaults.standard.bool(forKey: "reducedCharacterMotion")
    private var connectionLabel: NSTextField?
    private var micButton: NSButton?
    private var soundButton: NSButton?
    private var pinButton: NSButton?
    private var pauseButton: NSButton?
    private var controlsToggleButton: NSButton?
    private var modelPopup: NSPopUpButton?
    private var animationPopup: NSPopUpButton?
    private var statusItem: NSStatusItem?
    private var timer: Timer?
    private var clickThrough = false
    private var controlsExpanded = false
    private var alwaysOnTop = true
    private var paused = false
    private var recoveryTimer: Timer?
    private var layoutSize = NSSize.zero
    private var pointerMonitor: Any?
    private var bodyBounds = CGRect(x: 0, y: 0, width: 1, height: 1)
    private var bodySide: CGFloat = 1
    private var scale: CGFloat = 1
    private var characterYaw: CGFloat = 0
    private var baseSize = NSSize(width: 815, height: 640)
    private var frameCount = 0
    private var fpsStart = CFAbsoluteTimeGetCurrent()
    private var fittedToCharacter = false
    private var soundEnabled = false
    private var selectedCharacter = ProcessInfo.processInfo.environment["GAHYEON_CHARACTER_ID"] ?? "gahyeon"
    private var selectedAnimationIndex = UserDefaults.standard.integer(forKey: "selectedAnimationIndex")

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        if UserDefaults.standard.integer(forKey: "layoutVersion") < 9 {
            ["overlayX", "overlayY", "overlayScale"].forEach { UserDefaults.standard.removeObject(forKey: $0) }
            UserDefaults.standard.set(9, forKey: "layoutVersion")
        }
        installMenu(); createWindow(); refreshCoreStatus()
        positionPanel()
        createChatPanel()
        characterYaw = CGFloat(UserDefaults.standard.double(forKey: "overlayYaw"))
        if !(-75...75).contains(characterYaw) { characterYaw = 0 }
        controlWriter.publish(yaw: Float(characterYaw))
        timer = Timer(timeInterval: 1.0 / 60.0, repeats: true) { [weak self] _ in self?.displayFrame() }
        RunLoop.main.add(timer!, forMode: .common)
    }

    private func displayFrame() {
        updateInteraction()
        // Reuse the last rendered image while moving; avoid CPU readback competing with pointer events.
        if (window as? InteractiveOverlayWindow)?.isPointerDragging == true || recoveryTimer != nil { return }
        if !paused, gpuEnabled, let (surface, width, height, crop) = gpuReader.nextSurface() {
            if !fittedToCharacter { fitWindowToDimensions(width: width, height: height); fittedToCharacter = true }
            imageView.image = nil; imageView.wantsLayer = true
            imageView.layer?.contents = surface
            imageView.layer?.contentsRect = crop
            imageView.layer?.contentsGravity = .resizeAspect
            countFrame(); return
        }
        guard !paused, let frame = reader.nextImage() else { return }
        if !fittedToCharacter { measureBody(frame); fitWindowToCharacter(frame); fittedToCharacter = true }
        imageView.image = NSImage(cgImage: frame, size: NSSize(width: frame.width, height: frame.height))
        countFrame()
    }

    private func countFrame() {
        frameCount += 1
        let now = CFAbsoluteTimeGetCurrent(), elapsed = now - fpsStart
        if elapsed >= 2 { fputs(String(format: "direct-alpha measured fps: %.1f\n", Double(frameCount) / elapsed), stderr); frameCount = 0; fpsStart = now }
    }

    private func measureBody(_ frame: CGImage) {
        let width = frame.width, height = frame.height
        var pixels = [UInt8](repeating: 0, count: width * height * 4)
        pixels.withUnsafeMutableBytes { bytes in
            guard let context = CGContext(data: bytes.baseAddress, width: width, height: height, bitsPerComponent: 8, bytesPerRow: width * 4, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return }
            context.draw(frame, in: CGRect(x: 0, y: 0, width: width, height: height))
        }
        var left = width, right = 0, top = height, bottom = 0, side = 0
        for y in 0..<height { for x in 0..<width where pixels[(y * width + x) * 4 + 3] > 24 {
            left = min(left, x); right = max(right, x); top = min(top, y); bottom = max(bottom, y)
        } }
        guard right > left, bottom > top else { return }
        let mid = (top + bottom) / 2, band = max(18, (bottom - top) / 12)
        for y in max(0,mid-band)...min(height-1,mid+band) { for x in 0..<width where pixels[(y * width + x) * 4 + 3] > 24 { side = max(side, x) } }
        bodyBounds = CGRect(x: CGFloat(left)/CGFloat(width), y: CGFloat(height-bottom-1)/CGFloat(height), width: CGFloat(right-left+1)/CGFloat(width), height: CGFloat(bottom-top+1)/CGFloat(height))
        bodySide = CGFloat(max(left, side) + 1) / CGFloat(width)
    }
    private func bodyFrameOnScreen() -> NSRect {
        guard let window else { return .zero }
        let frame = imageView.convert(imageView.bounds, to: nil)
        return NSRect(x: window.frame.minX + frame.minX + frame.width * bodyBounds.minX,
                      y: window.frame.minY + frame.minY + frame.height * bodyBounds.minY,
                      width: frame.width * bodyBounds.width, height: frame.height * bodyBounds.height)
    }

    private func fitWindowToCharacter(_ frame: CGImage) {
        fitWindowToDimensions(width: frame.width, height: frame.height)
    }

    private func fitWindowToDimensions(width: Int, height: Int) {
        guard let window, let screen = window.screen ?? NSScreen.main else { return }
        let contentHeight = min(screen.visibleFrame.height * 0.78, 720)
        let contentWidth = contentHeight * CGFloat(width) / CGFloat(height)
        baseSize = NSSize(width: contentWidth + horizontalContentInset * 2,
                          height: contentHeight + verticalContentInset * 2)
        let center = NSPoint(x: window.frame.midX, y: window.frame.midY)
        let size = NSSize(width: baseSize.width * scale, height: baseSize.height * scale)
        let target = NSRect(x: center.x - size.width / 2, y: center.y - size.height / 2,
                            width: size.width, height: size.height)
        window.setFrame(window.constrainFrameRect(target, to: screen), display: true)
        positionPanel()
    }

    private func createWindow() {
        guard let screen = NSScreen.main else { return }
        let height = min(screen.visibleFrame.height * 0.65, 640)
        let width = (height - verticalContentInset * 2) * captureAspect + horizontalContentInset * 2
        baseSize = NSSize(width: width, height: height)
        scale = CGFloat(UserDefaults.standard.double(forKey: "overlayScale")); if !(0.6...1.4).contains(scale) { scale = 1 }
        let size = NSSize(width: width * scale, height: height * scale)
        let savedX = UserDefaults.standard.double(forKey: "overlayX"), savedY = UserDefaults.standard.double(forKey: "overlayY")
        let restored = savedX != 0 || savedY != 0
        let frame = NSRect(x: restored ? savedX : screen.visibleFrame.midX - size.width / 2,
                           y: restored ? savedY : screen.visibleFrame.maxY - size.height - 50,
                           width: size.width, height: size.height)
        let value = InteractiveOverlayWindow(contentRect: frame, styleMask: [.borderless], backing: .buffered, defer: false)
        value.setFrame(value.constrainFrameRect(frame, to: screen), display: false)
        value.isOpaque = false; value.backgroundColor = .clear; value.hasShadow = false; value.level = .floating
        value.isMovableByWindowBackground = true; value.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
        imageView.imageScaling = .scaleProportionallyUpOrDown; imageView.menu = statusItem?.menu
        imageView.onHorizontalRotationDelta = { [weak self] delta in self?.rotateCharacter(horizontalDelta: delta) }
        let surface = DragSurfaceView(frame: NSRect(origin: .zero, size: frame.size))
        imageView.frame = surface.bounds.insetBy(dx: horizontalContentInset, dy: verticalContentInset)
        imageView.autoresizingMask = [.width, .height]
        surface.addSubview(imageView)
        let reactionClick = NSClickGestureRecognizer(target: self, action: #selector(reactToCharacter))
        reactionClick.numberOfClicksRequired = 2; reactionClick.delaysPrimaryMouseButtonEvents = false
        imageView.addGestureRecognizer(reactionClick)
        value.contentView = surface
        value.onDragBegin = { [weak self] in self?.cancelRecovery() }
        value.onDragEnd = { [weak self] in self?.recoverAfterDrag() }
        value.onDoubleClick = { [weak self] in self?.reactToCharacter() }
        NotificationCenter.default.addObserver(self, selector: #selector(didMove), name: NSWindow.didMoveNotification, object: value)
        value.orderFrontRegardless(); window = value; createPanel()
        pointerMonitor = NSEvent.addLocalMonitorForEvents(matching: [.scrollWheel, .magnify]) { [weak self, weak value] event in
            guard let self, let value, event.window === value, !self.clickThrough else { return event }
            if event.type == .magnify { self.applyScale(self.scale * (1 + event.magnification)) }
            else if event.momentumPhase.isEmpty {
                self.zoomFromScroll(delta: event.scrollingDeltaY, precise: event.hasPreciseScrollingDeltas, inverted: event.isDirectionInvertedFromDevice)
            }
            return nil
        }
    }

    private func installMenu() {
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        item.button?.image = NSImage(systemSymbolName: "person.crop.circle", accessibilityDescription: "Gahyeon")
        let menu = NSMenu()
        [("가현 보이기/숨기기", #selector(toggleVisibility)), ("직접 드래그 잠금", #selector(toggleClickThrough)),
         ("항상 위", #selector(toggleAlwaysOnTop)), ("애니메이션 화면 일시정지", #selector(togglePause))].forEach {
            menu.addItem(withTitle: $0.0, action: $0.1, keyEquivalent: "")
        }
        menu.addItem(.separator()); menu.addItem(withTitle: "크게", action: #selector(larger), keyEquivalent: "+")
        menu.addItem(withTitle: "작게", action: #selector(smaller), keyEquivalent: "-")
        menu.addItem(withTitle: "정위치 (위치·크기·회전)", action: #selector(resetPlacement), keyEquivalent: "0")
        menu.addItem(.separator()); menu.addItem(withTitle: "가현 종료", action: #selector(quit), keyEquivalent: "q")
        menu.items.forEach { $0.target = self }; item.menu = menu; statusItem = item; refreshMenu()
    }

    private func createPanel() {
        let value = NSPanel(contentRect: NSRect(x: 0, y: 0, width: 1, height: 1), styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        value.isOpaque = false; value.backgroundColor = .clear
        panel = value; createControlBubble(); value.orderOut(nil)
    }

    private func createControlBubble() {
        guard let panel else { return }
        let frame = NSRect(x: panel.frame.maxX - 36, y: panel.frame.minY - 42, width: 36, height: 36)
        let value = NSPanel(contentRect: frame, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        value.isOpaque = false; value.backgroundColor = .clear; value.level = .floating
        value.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
        let effect = liquidGlassEffect(frame: NSRect(origin: .zero, size: frame.size), radius: 18)
        let button = islandButton("message", #selector(toggleChat), "채팅 열기")
        controlsToggleButton = button
        button.frame = effect.bounds.insetBy(dx: 3, dy: 3); button.autoresizingMask = [.width, .height]
        effect.addSubview(button); value.contentView = effect; value.orderFrontRegardless(); controlBubble = value
    }

    private func liquidGlassEffect(frame: NSRect, radius: CGFloat) -> NSVisualEffectView {
        let effect = NSVisualEffectView(frame: frame)
        effect.material = .underWindowBackground; effect.blendingMode = .behindWindow; effect.state = .active
        effect.wantsLayer = true; effect.layer?.backgroundColor = NSColor.black.withAlphaComponent(0.10).cgColor
        effect.layer?.cornerRadius = radius; effect.layer?.masksToBounds = true
        let highlight = LiquidGlassHighlightView(frame: effect.bounds)
        highlight.autoresizingMask = [.width, .height]
        effect.addSubview(highlight)
        return effect
    }

    private func islandButton(_ symbol: String, _ action: Selector, _ tooltip: String,
                              tint: NSColor = .white) -> NSButton {
        let image = NSImage(systemSymbolName: symbol, accessibilityDescription: tooltip)?
            .withSymbolConfiguration(NSImage.SymbolConfiguration(pointSize: 14, weight: .medium))
        let button = ConversationActionButton(image: image ?? NSImage(), target: self, action: action)
        button.toolTip = tooltip; button.isBordered = false; button.contentTintColor = tint
        button.wantsLayer = true; button.layer?.cornerRadius = 7; button.layer?.borderWidth = 0
        button.layer?.backgroundColor = NSColor.clear.cgColor
        button.setAccessibilityLabel(tooltip)
        button.widthAnchor.constraint(equalToConstant: 30).isActive = true
        button.heightAnchor.constraint(equalToConstant: 30).isActive = true
        return button
    }

    private func label(_ text: String, size: CGFloat, weight: NSFont.Weight, color: NSColor) -> NSTextField {
        let value = NSTextField(labelWithString: text); value.font = .systemFont(ofSize: size, weight: weight); value.textColor = color; return value
    }

    private func iconButton(_ symbol: String, _ action: Selector, _ tooltip: String) -> NSButton {
        let button = NSButton(image: NSImage(systemSymbolName: symbol, accessibilityDescription: tooltip)!, target: self, action: action)
        button.bezelStyle = .texturedRounded; button.toolTip = tooltip; return button
    }

    private func actionTile(_ symbol: String, _ title: String, _ detail: String, _ action: Selector) -> NSButton {
        let button = NSButton(title: "\(title)\n\(detail)", target: self, action: action); button.isBordered = false
        let configuration = NSImage.SymbolConfiguration(pointSize: 23, weight: .medium)
        button.image = NSImage(systemSymbolName: symbol, accessibilityDescription: title)?.withSymbolConfiguration(configuration)
        button.imagePosition = .imageAbove; button.imageHugsTitle = true; button.font = .systemFont(ofSize: 12, weight: .semibold)
        button.contentTintColor = .white; button.wantsLayer = true; button.layer?.cornerRadius = 18
        button.layer?.borderWidth = 1; button.layer?.borderColor = NSColor.white.withAlphaComponent(0.20).cgColor
        button.layer?.backgroundColor = NSColor.white.withAlphaComponent(0.07).cgColor
        return button
    }

    @objc private func didMove() { layoutQuickChat() }
    private func savePlacement() {
        guard let window else { return }
        UserDefaults.standard.set(window.frame.minX, forKey: "overlayX")
        UserDefaults.standard.set(window.frame.minY, forKey: "overlayY")
    }
    private func cancelRecovery() {
        recoveryTimer?.invalidate(); recoveryTimer = nil
        (window as? InteractiveOverlayWindow)?.preservesResizeAnchor = false
    }
    private func recoverAfterDrag() {
        guard let window, let screen = NSScreen.screens.first(where: { $0.frame.contains(NSEvent.mouseLocation) }) ?? window.screen ?? NSScreen.main else { return }
        cancelRecovery()
        let start = window.frame.origin
        let target = OverlayDragGeometry.recoveredOrigin(window: window.frame, body: bodyFrameOnScreen(), workArea: screen.visibleFrame)
        guard hypot(target.x-start.x,target.y-start.y)>0.5 else { savePlacement(); return }
        (window as? InteractiveOverlayWindow)?.preservesResizeAnchor = true
        if reducedMotion || NSWorkspace.shared.accessibilityDisplayShouldReduceMotion {
            window.setFrameOrigin(target); cancelRecovery(); savePlacement(); return
        }
        let began = CFAbsoluteTimeGetCurrent()
        let animation = Timer(timeInterval: 1.0/60.0, repeats: true) { [weak self, weak window] tick in
            guard let self, let window else { tick.invalidate(); return }
            let t = (CFAbsoluteTimeGetCurrent()-began)/0.28, f = OverlayDragGeometry.progress(t)
            window.setFrameOrigin(NSPoint(x: start.x+(target.x-start.x)*f, y: start.y+(target.y-start.y)*f))
            if t >= 1 { self.cancelRecovery(); self.savePlacement() }
        }
        recoveryTimer = animation; RunLoop.main.add(animation, forMode: .common)
    }
    private func positionPanel() {
        guard let window, let panel, let screen = window.screen ?? NSScreen.main else { return }
        let inset: CGFloat = 14
        let x = min(max(window.frame.maxX - panel.frame.width - inset, screen.visibleFrame.minX + 8),
                    screen.visibleFrame.maxX - panel.frame.width - 8)
        let y = min(max(window.frame.minY + inset + 42, screen.visibleFrame.minY + 50),
                    screen.visibleFrame.maxY - panel.frame.height - 8)
        panel.setFrameOrigin(NSPoint(x: x, y: y))
        controlBubble?.setFrameOrigin(NSPoint(x: panel.frame.maxX - 36, y: panel.frame.minY - 42))
        layoutQuickChat()
    }
    private func zoomFromScroll(delta: CGFloat, precise: Bool, inverted: Bool) {
        let sensitivity: CGFloat = precise ? 0.003 : 0.045
        let amount = delta * (inverted ? -1 : 1) * sensitivity
        applyScale(scale * exp(min(max(amount, -0.2), 0.2)))
    }
    private func applyScale(_ value: CGFloat) {
        guard let window, (window as? InteractiveOverlayWindow)?.isPointerDragging != true else { return }
        cancelRecovery()
        let body = bodyFrameOnScreen()
        let chatOnRight = (chatPanel?.frame.midX ?? body.maxX) >= body.midX
        (window as? InteractiveOverlayWindow)?.preservesResizeAnchor = true
        defer { (window as? InteractiveOverlayWindow)?.preservesResizeAnchor = false }
        scale = min(max(value, 0.65), 1.35)
        let size = NSSize(width: baseSize.width * scale, height: baseSize.height * scale)
        let localCenter = NSPoint(x: horizontalContentInset + (size.width-horizontalContentInset*2)*bodyBounds.midX,
                                  y: verticalContentInset + (size.height-verticalContentInset*2)*bodyBounds.midY)
        var target = NSRect(x: body.midX-localCenter.x, y: body.midY-localCenter.y, width: size.width, height: size.height)
        if let chatPanel, chatPanel.isVisible, let screen = window.screen ?? NSScreen.main {
            let resizedBody = NSRect(x: target.minX+horizontalContentInset+(size.width-horizontalContentInset*2)*bodyBounds.minX,
                                     y: body.minY, width: (size.width-horizontalContentInset*2)*bodyBounds.width, height: body.height)
            target.origin.x += ConversationZoomGeometry.horizontalShift(body: resizedBody, workArea: screen.visibleFrame, chatWidth: chatPanel.frame.width, chatOnRight: chatOnRight)
        }
        window.setFrame(target, display: true, animate: false)
        UserDefaults.standard.set(Double(scale), forKey: "overlayScale"); positionPanel(); savePlacement()
    }
    private func rotateCharacter(horizontalDelta: CGFloat) { characterYaw = min(max(characterYaw - horizontalDelta * 0.35, -75), 75); UserDefaults.standard.set(Double(characterYaw), forKey: "overlayYaw"); controlWriter.publish(yaw: Float(characterYaw)) }
    @objc private func larger() { applyScale(scale + 0.1) }; @objc private func smaller() { applyScale(scale - 0.1) }
    @objc private func toggleClickThrough() { clickThrough.toggle(); window?.ignoresMouseEvents = clickThrough; refreshMenu() }
    @objc private func toggleAlwaysOnTop() {
        alwaysOnTop.toggle()
        for value in [window, panel, controlBubble, chatPanel, pickerPanel] { value?.level = alwaysOnTop ? .floating : .normal }
        pinButton?.contentTintColor = alwaysOnTop ? .systemCyan : .secondaryLabelColor
        refreshMenu()
    }
    @objc private func togglePause() {
        paused.toggle()
        let title = paused ? "애니메이션 화면 재개" : "애니메이션 화면 일시정지"
        pauseButton?.image = NSImage(systemSymbolName: paused ? "play" : "pause", accessibilityDescription: title)
        pauseButton?.toolTip = title
        refreshMenu()
    }
    @objc private func toggleControls() {
        guard let view = chatHeader else { return }
        let menu = NSMenu(); menu.autoenablesItems = false
        for (title, action) in [("캐릭터 선택", #selector(cycleCharacterModel)), ("캐릭터 반응", #selector(reactToCharacter)), ("동작 줄이기", #selector(toggleReducedMotion)), ("항상 위", #selector(toggleAlwaysOnTop)), ("애니메이션 화면 일시정지", #selector(togglePause)), ("정위치 (위치·크기·회전)", #selector(resetPlacement)), ("화면 새로고침", #selector(refreshIsland)), ("가현 종료", #selector(quit))] {
            let item = NSMenuItem(title: title, action: action, keyEquivalent: ""); item.target = self
            if action == #selector(toggleAlwaysOnTop) { item.state = alwaysOnTop ? .on : .off }
            if action == #selector(togglePause) { item.state = paused ? .on : .off }
            if action == #selector(toggleReducedMotion) { let systemReduced = NSWorkspace.shared.accessibilityDisplayShouldReduceMotion; item.state = reducedMotion || systemReduced ? .on : .off; item.isEnabled = !systemReduced }
            menu.addItem(item)
        }
        menu.popUp(positioning: nil, at: NSPoint(x: view.bounds.width - 64, y: 0), in: view)
    }

    @objc private func refreshIsland() { fittedToCharacter = false; refreshCoreStatus() }
    @objc private func toggleSound() {
        soundEnabled.toggle()
        speechGeneration += 1
        if !soundEnabled { serverAudio?.stop(); serverAudio = nil }
        soundButton?.image = NSImage(systemSymbolName: soundEnabled ? "speaker.wave.2" : "speaker.slash", accessibilityDescription: "스피커")
        soundButton?.setAccessibilityValue(soundEnabled ? "켜짐" : "꺼짐")
    }
    @objc private func toggleMicrophone() {
        if serverMicrophone.recording {
            serverMicrophone.stop()
            micButton?.contentTintColor = .systemOrange
            return
        }
        guard !microphonePending else { return }
        microphonePending = true
        speechGeneration += 1
        serverAudio?.stop()
        serverMicrophone.start(state: { [weak self] active in
            self?.micButton?.contentTintColor = active ? .systemCyan : .systemOrange
            self?.micButton?.toolTip = active ? "마이크 끄기" : "음성 처리 중"
        }, completion: { [weak self] result in
            guard let self else { return }
            switch result {
            case .failure(let error): self.finishMicrophone(error: error)
            case .success(let wav):
                self.core.speechData(path: "transcriptions", data: wav, mediaType: "audio/wav") { [weak self] result in
                    guard let self else { return }
                    do {
                        let data = try result.get()
                        let payload = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                        let text = (payload?["transcript"] as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
                        self.finishMicrophone(error: nil)
                        guard !text.isEmpty else { return }
                        if self.chatPanel == nil { self.createChatPanel() }
                        self.chatInput?.stringValue = text
                        self.sendChat()
                    } catch { self.finishMicrophone(error: error) }
                }
            }
        })
    }
    private func finishMicrophone(error: Error?) {
        microphonePending = false
        micButton?.contentTintColor = error == nil ? .systemGreen : .systemRed
        micButton?.toolTip = "마이크 켜기"
        if let error { appendChat(role: "시스템", text: error.localizedDescription) }
    }
    @objc private func focusModelPicker() {
        modelPopup?.window?.makeKey(); modelPopup?.performClick(nil)
    }
    @objc private func focusAnimationPicker() {
        animationPopup?.window?.makeKey(); animationPopup?.performClick(nil)
    }
    @objc private func cycleCharacterModel() {
        if let pickerPanel, pickerPanel.isVisible { pickerPanel.orderOut(nil); return }
        let width = ConversationDesign.number("pickerWidth", 340), height = ConversationDesign.number("pickerHeight", 556)
        let value = QuickChatPanel(contentRect: NSRect(x: 0, y: 0, width: width, height: height), styleMask: [.borderless], backing: .buffered, defer: false)
        value.title = "캐릭터 선택"; value.isReleasedWhenClosed = false; value.isOpaque = false; value.backgroundColor = .clear
        value.level = alwaysOnTop ? .floating : .normal; value.appearance = NSAppearance(named: .darkAqua)
        value.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]; value.hidesOnDeactivate = false
        let root = ConversationSurface(frame: NSRect(x: 0, y: 0, width: width, height: height)); root.lines = false
        let title = label("캐릭터 선택", size: 13, weight: .semibold, color: .white); title.frame = NSRect(x: 16, y: height-32, width: 160, height: 20); root.addSubview(title)
        let close = islandButton("xmark", #selector(closeCharacterPicker), "닫기"); close.keyEquivalent = "\u{1b}"; close.frame = NSRect(x: width-42, y: height-38, width: 30, height: 30); root.addSubview(close)
        let labels = ["가현", "재재", "도적", "해적", "격투가", "격투가 (가면 없음)", "아이", "해커"]
        let chosen = Int(controlWriter.appliedCharacter() ?? manifestModelIndex())
        let previewData = try? Data(contentsOf: URL(fileURLWithPath: "assets/character-previews/v001/manifest.json"))
        let previewManifest = previewData.flatMap { try? JSONSerialization.jsonObject(with: $0) } as? [String: Any]
        let assets = previewManifest?["assets"] as? [[String: Any]] ?? []
        for (slot, index) in [0,1,2,3,4,6,7].enumerated() {
            let selected = chosen == index || (index == 4 && chosen == 5)
            let assetIndex = selected && chosen == 5 ? 5 : index
            let button = RosterCardButton(frame: NSRect(x: 10+CGFloat(slot%2)*164, y: height-44-CGFloat(slot/2+1)*116-CGFloat(slot/2)*8, width: 156, height: 116))
            button.title = ""; button.isBordered = false; button.tag = assetIndex; button.target = self; button.action = #selector(selectRosterCard(_:))
            button.selected = selected; button.lettering = characterLettering(modelIds[index]); button.setAccessibilityLabel(labels[index]); button.toolTip = labels[index]
            button.isEnabled = controlWriter.appliedCharacter() != nil || installedModel(index)
            if let asset = assets.first(where: { $0["id"] as? String == modelIds[assetIndex] }), let path = asset["path"] as? String, let image = NSImage(contentsOfFile: path), let b = asset["alphaBounds"] as? [Double] {
                button.preview = image
                let h = (b[3]-b[1])*0.58
                button.source = NSRect(x: b[0], y: image.size.height-b[1]-h, width: b[2]-b[0], height: h)
            }
            root.addSubview(button)
        }
        if chosen == 4 || chosen == 5 {
            let variant = NSButton(checkboxWithTitle: "가면 없음", target: self, action: #selector(selectFighterVariant(_:)))
            variant.state = chosen == 5 ? .on : .off; variant.frame = NSRect(x: 16, y: 8, width: 140, height: 24); root.addSubview(variant)
        }
        value.contentView = root; pickerPanel = value
        let bounds = (window?.screen ?? NSScreen.main)!.visibleFrame.insetBy(dx: 8, dy: 8)
        let anchor = chatPanel?.frame ?? window!.frame
        value.setFrameOrigin(NSPoint(x: min(max(anchor.minX, bounds.minX), bounds.maxX-width), y: min(max(anchor.maxY-height, bounds.minY), bounds.maxY-height)))
        value.makeKeyAndOrderFront(nil)
    }
    @objc private func closeCharacterPicker() { pickerPanel?.orderOut(nil) }
    @objc private func selectRosterCard(_ sender: NSButton) {
        closeCharacterPicker()
        guard sender.tag != Int(controlWriter.appliedCharacter() ?? manifestModelIndex()) else { return }
        let item = NSMenuItem(); item.tag = sender.tag; selectCharacterModel(item)
    }
    @objc private func selectFighterVariant(_ sender: NSButton) {
        closeCharacterPicker(); let item = NSMenuItem(); item.tag = sender.state == .on ? 5 : 4; selectCharacterModel(item)
    }

    private func characterLettering(_ id: String) -> NSImage? {
        let key = id == "fighter-unmasked" ? "fighter" : id
        guard let data = try? Data(contentsOf: URL(fileURLWithPath: "assets/character-lettering/v001/manifest.json")),
              let manifest = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let assets = manifest["assets"] as? [[String: Any]],
              let asset = assets.first(where: { $0["id"] as? String == key }),
              let path = asset["path"] as? String,
              let bounds = asset["alphaBounds"] as? [Double], bounds.count == 4,
              let original = NSImage(contentsOfFile: path) else { return nil }
        let source = NSRect(x: bounds[0], y: original.size.height - bounds[3],
                            width: bounds[2] - bounds[0], height: bounds[3] - bounds[1])
        let result = NSImage(size: NSSize(width: 144, height: 48))
        let factor = min(136 / source.width, 40 / source.height)
        let size = NSSize(width: source.width * factor, height: source.height * factor)
        result.lockFocus()
        original.draw(in: NSRect(x: (144 - size.width) / 2, y: (48 - size.height) / 2,
                                width: size.width, height: size.height), from: source,
                      operation: .sourceOver, fraction: 1)
        result.unlockFocus()
        result.isTemplate = false
        return result
    }
    private let modelIds = ["gahyeon", "zeze", "rogue", "pirate", "fighter", "fighter-unmasked", "child", "hacker"]
    private func installedModel(_ index: Int) -> Bool {
        guard modelIds.indices.contains(index),
              let data = try? Data(contentsOf: URL(fileURLWithPath: "config/character-model-roster.json")),
              let roster = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let entries = roster["characters"] as? [[String: Any]],
              let model = entries.first(where: { $0["id"] as? String == modelIds[index] }),
              let map = model["runtimeMap"] as? String, map.hasPrefix("/Game/") else { return false }
        return FileManager.default.fileExists(atPath: "unreal/GahyeonDesktopMetaHumanPOC/Content/" + String(map.dropFirst(6)) + ".umap")
    }
    private func manifestModelIndex() -> UInt32 {
        guard let data = try? Data(contentsOf: URL(fileURLWithPath: "config/canonical-character-runtime.json")),
              let manifest = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let mac = manifest["macos"] as? [String: Any], let id = mac["characterModelId"] as? String,
              let index = modelIds.firstIndex(of: id) else { return 0 }
        return UInt32(index)
    }
    @objc private func selectCharacterModel(_ item: NSMenuItem) {
        guard modelIds.indices.contains(item.tag) else { return }
        if controlWriter.appliedCharacter() != nil {
            if controlWriter.selectCharacter(UInt32(item.tag)) { fittedToCharacter = false }
            else { appendChat(role: "시스템", text: "캐릭터 런타임에 연결할 수 없습니다.") }
            return
        }
        guard installedModel(item.tag) else { return }
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        task.arguments = ["scripts/select_canonical_macos_character.py", modelIds[item.tag]]
        task.currentDirectoryURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        task.standardOutput = FileHandle.nullDevice; task.standardError = FileHandle.nullDevice
        task.terminationHandler = { [weak self] process in
            if process.terminationStatus != 0 { DispatchQueue.main.async {
                self?.appendChat(role: "시스템", text: "캐릭터 전환에 실패했습니다.")
            } }
        }
        do { try task.run() } catch { appendChat(role: "시스템", text: error.localizedDescription) }
    }
    @objc private func cycleAnimation() {
        let names = ["대기", "걷기", "달리기", "인사"]
        selectedAnimationIndex = (selectedAnimationIndex + 1) % names.count
        UserDefaults.standard.set(selectedAnimationIndex, forKey: "selectedAnimationIndex")
        connectionLabel?.stringValue = "애니메이션 선택 · \(names[selectedAnimationIndex])"
    }
    @objc private func toggleChat() {
        if chatPanel == nil { createChatPanel(); return }
        if chatPanel!.isVisible { chatPanel?.orderOut(nil); closeCharacterPicker(); controlBubble?.orderFrontRegardless() }
        else { layoutQuickChat(); chatPanel?.makeKeyAndOrderFront(nil); controlBubble?.orderOut(nil) }
    }
    private func createChatPanel() {
        let value = QuickChatPanel(contentRect: NSRect(x: 0, y: 0, width: 360, height: 280), styleMask: [.borderless], backing: .buffered, defer: false)
        value.title = "가현 채팅"; value.level = alwaysOnTop ? .floating : .normal; value.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        value.hidesOnDeactivate = false; value.isReleasedWhenClosed = false; value.isOpaque = false; value.backgroundColor = .clear; value.hasShadow = true
        value.appearance = NSAppearance(named: .darkAqua)
        let root = ConversationSurface(frame: NSRect(x: 0, y: 0, width: 360, height: 280)); root.autoresizingMask = [.width, .height]
        let header = NSView(frame: NSRect(x: 0, y: 236, width: 360, height: 44)); chatHeader = header; root.addSubview(header)
        let character = islandButton("person.crop.circle", #selector(cycleCharacterModel), "캐릭터 선택"); character.frame = NSRect(x: 12, y: 7, width: 30, height: 30); header.addSubview(character)
        let title = label("가현", size: 14, weight: .semibold, color: .white); title.frame = NSRect(x: 50, y: 12, width: 180, height: 22); header.addSubview(title)
        let more = islandButton("ellipsis", #selector(toggleControls), "더 보기"); more.frame = NSRect(x: 278, y: 7, width: 30, height: 30); header.addSubview(more)
        let close = islandButton("xmark", #selector(toggleChat), "채팅 닫기"); close.frame = NSRect(x: 318, y: 7, width: 30, height: 30); header.addSubview(close)
        let scroll = NSScrollView(); scroll.hasVerticalScroller = true; scroll.drawsBackground = false; scroll.scrollerStyle = .overlay
        let history = NSTextView(); history.isEditable = false; history.drawsBackground = false; history.font = .systemFont(ofSize: 13)
        history.isVerticallyResizable = true; history.isHorizontallyResizable = false; history.textContainer?.widthTracksTextView = true
        history.autoresizingMask = [.width]; history.textColor = .white; history.textContainerInset = NSSize(width: 0, height: 8)
        scroll.documentView = history; chatHistory = history; chatScroll = scroll; root.addSubview(scroll)
        let input = NSTextField(); input.placeholderString = "가현에게 메시지 보내기"; input.target = self; input.action = #selector(sendChat); chatInput = input
        input.frame = NSRect(x: 16, y: 57, width: 286, height: 28); input.isBordered = false; input.drawsBackground = false; input.font = .systemFont(ofSize: 14); input.textColor = .white
        input.setAccessibilityLabel("가현에게 메시지 보내기"); root.addSubview(input)
        let send = islandButton("arrow.up", #selector(sendChat), "보내기", tint: NSColor(calibratedRed: 0.51, green: 0.85, blue: 0.86, alpha: 1)); send.frame = NSRect(x: 318, y: 53, width: 30, height: 30); root.addSubview(send)
        let mic = islandButton("mic.slash", #selector(toggleMicrophone), "마이크 켜기"); mic.frame = NSRect(x: 12, y: 12, width: 30, height: 30); micButton = mic; root.addSubview(mic)
        let sound = islandButton(soundEnabled ? "speaker.wave.2" : "speaker.slash", #selector(toggleSound), "스피커 켜기 또는 끄기"); sound.frame = NSRect(x: 50, y: 12, width: 30, height: 30); soundButton = sound; root.addSubview(sound)
        let react = islandButton("sparkles", #selector(reactToCharacter), "캐릭터 반응"); react.frame = NSRect(x: 88, y: 12, width: 30, height: 30); root.addSubview(react)
        let status = label("", size: 12, weight: .regular, color: .secondaryLabelColor); status.frame = NSRect(x: 130, y: 17, width: 175, height: 20); activityLabel = status; root.addSubview(status)
        let expand = islandButton("chevron.up", #selector(toggleChatHistory), "대화 펼치기"); expand.frame = NSRect(x: 318, y: 12, width: 30, height: 30); chatHistoryButton = expand; root.addSubview(expand)
        value.contentView = root; chatPanel = value; layoutQuickChat(); value.orderFrontRegardless(); controlBubble?.orderOut(nil)
    }
    @objc private func toggleChatHistory() { chatExpanded.toggle(); layoutQuickChat() }
    private func layoutQuickChat() {
        guard !quickChatLayoutBusy, let chatPanel, let window, let screen = window.screen ?? NSScreen.main else { return }
        quickChatLayoutBusy = true; defer { quickChatLayoutBusy = false }
        let width = ConversationDesign.number("chatWidth", 360), height = ConversationDesign.number(chatExpanded ? "expandedHeight" : "chatHeight", chatExpanded ? 440 : 280)
        let bounds = screen.visibleFrame.insetBy(dx: 8, dy: 8)
        let body = bodyFrameOnScreen()
        // Position dependent surfaces only; moving their owner here fights native dragging and zoom.
        let right = body.maxX + 12, left = body.minX - 12 - width
        let preferred = right + width <= bounds.maxX ? right : left >= bounds.minX ? left : right
        let x = min(max(preferred, bounds.minX), bounds.maxX-width)
        let bottom = min(max(body.minY + body.height*0.22, bounds.minY), bounds.maxY-height)
        let target = NSRect(x: x, y: bottom, width: width, height: height)
        if chatPanel.frame.size != target.size { chatPanel.setFrame(target, display: true) }
        else if chatPanel.frame.origin != target.origin { chatPanel.setFrameOrigin(target.origin) }
        if layoutSize != NSSize(width: width, height: height) {
            layoutSize = NSSize(width: width, height: height)
        chatHeader?.frame = NSRect(x: 0, y: height-44, width: width, height: 44)
        chatScroll?.frame = NSRect(x: 16, y: 104, width: width-32, height: height-156)
        chatHistory?.setFrameSize(NSSize(width: width-32, height: max(height-156, chatHistory?.frame.height ?? 0)))
        chatPanel.contentView?.needsDisplay = true
        chatHistoryButton?.image = NSImage(systemSymbolName: chatExpanded ? "chevron.down" : "chevron.up", accessibilityDescription: chatExpanded ? "대화 접기" : "대화 펼치기")
        chatHistoryButton?.toolTip = chatExpanded ? "대화 접기" : "대화 펼치기"
        chatHistoryButton?.setAccessibilityLabel(chatExpanded ? "대화 접기" : "대화 펼치기")
        }
        let imageFrame = imageView.convert(imageView.bounds, to: nil)
        let bodyEdge = window.frame.minX + imageFrame.minX + imageFrame.width * bodySide
        let bubbleHeight = controlBubble?.frame.height ?? 36
        let bubbleRight = bodyEdge + 12
        let bubbleX = bubbleRight + 36 <= bounds.maxX ? bubbleRight : body.minX - 48
        controlBubble?.setFrameOrigin(NSPoint(x: min(max(bubbleX, bounds.minX), bounds.maxX-36), y: min(max(body.midY-bubbleHeight/2, bounds.minY), bounds.maxY-bubbleHeight)))
        if chatPanel.isVisible { controlBubble?.orderOut(nil) }
    }

    @objc private func sendChat() {
        guard let input = chatInput, !input.stringValue.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        speechGeneration += 1
        let generation = speechGeneration
        serverAudio?.stop()
        let message = input.stringValue.trimmingCharacters(in: .whitespacesAndNewlines); input.stringValue = ""; input.isEnabled = false
        appendChat(role: "나", text: message)
        let requestStarted = ProcessInfo.processInfo.systemUptime
        core.send(message: message, characterId: selectedCharacter) { [weak self] result in
            guard let self else { return }; input.isEnabled = true; input.window?.makeFirstResponder(input)
            switch result {
            case .success(let response):
                fputs("LATENCY_CHAT run=\(response.runId) reply_ms=\((ProcessInfo.processInfo.systemUptime-requestStarted)*1000)\n", stderr)
                self.appendChat(role: self.selectedCharacter == "diana" ? "다이애나" : "가현", text: response.content)
                if self.soundEnabled {
                    let playback = DesktopSegmentedSpeech(core: self.core,
                        current: { [weak self] in self?.soundEnabled == true && self?.speechGeneration == generation },
                        deliver: { [weak self] player in self?.serverAudio = player },
                        failure: { [weak self] error in self?.appendChat(role: "시스템", text: "음성 재생 실패: \(error.localizedDescription)") })
                    self.segmentedSpeech = playback
                    playback.start(response.content)
                }
            case .failure(let error):
                let failure = error as NSError
                let message = failure.domain == NSURLErrorDomain && failure.code == NSURLErrorTimedOut
                    ? "응답 대기 시간이 초과됐습니다."
                    : "Core 요청 실패: \(error.localizedDescription)"
                self.appendChat(role: "시스템", text: message)
            }
        }
    }
    private func appendChat(role: String, text: String) {
        if chatPanel == nil { createChatPanel() }
        guard let history = chatHistory else { return }
        history.textStorage?.append(NSAttributedString(string: "\(role)\n\(text)\n\n", attributes: [.font: NSFont.systemFont(ofSize: 13), .foregroundColor: NSColor.white]))
        layoutQuickChat()
        history.scrollToEndOfDocument(nil)
    }
    @objc private func changeCharacterModel() {
        guard let popup = modelPopup else { return }
        selectedCharacter = popup.indexOfSelectedItem == 1 ? "gahyeon" : "diana"
        UserDefaults.standard.set(selectedCharacter, forKey: "selectedCharacter")
        appendChat(role: "시스템", text: "대화 모델을 \(selectedCharacter == "diana" ? "다이애나" : "가현")으로 변경했습니다. 3D 캐릭터 교체는 해당 Unreal 런타임이 준비되면 함께 전환됩니다.")
    }
    @objc private func changeAnimation() {
        guard let animationPopup else { return }
        appendChat(role: "시스템", text: "애니메이션 선택: \(animationPopup.titleOfSelectedItem ?? "대기")")
    }
    @objc private func reactToCharacter() { reactionStarted = CFAbsoluteTimeGetCurrent(); nextIdleReaction = reactionStarted + 45 }
    @objc private func toggleReducedMotion() { reducedMotion.toggle(); UserDefaults.standard.set(reducedMotion, forKey: "reducedCharacterMotion") }
    private func renderMicrophoneState(listening: Bool) {
        let label = listening ? "마이크 끄기" : "마이크 켜기"
        guard micButton?.accessibilityLabel() != label else { return }
        micButton?.image = NSImage(systemSymbolName: listening ? "mic" : "mic.slash", accessibilityDescription: label)
        micButton?.contentTintColor = listening ? .systemCyan : .white
        micButton?.setAccessibilityLabel(label)
        micButton?.toolTip = label
    }
    private func updateInteraction() {
        let now = CFAbsoluteTimeGetCurrent(); if now-lastInteractionTick < 0.05 { return }; lastInteractionTick = now
        let phase = serverMicrophone.recording ? "듣는 중" : microphonePending ? "음성 처리 중" : chatInput?.isEnabled == false ? "응답 대기" : serverAudio?.isPlaying == true ? "말하는 중" : ""
        if phase != interactionPhase { interactionPhase = phase; activityLabel?.stringValue = phase }
        renderMicrophoneState(listening: serverMicrophone.recording)
        let disabled = paused || reducedMotion || NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
        if lastBaseYaw.isNaN || lastBaseYaw != characterYaw { lastBaseYaw = characterYaw; publishedReactionYaw = .greatestFiniteMagnitude; reactionStarted = -100; nextIdleReaction = now+45 }
        if now > nextIdleReaction && phase.isEmpty { reactionStarted = now; nextIdleReaction = now+45 }
        var offset: Double = 0
        let age = now-reactionStarted
        if !disabled {
            if age >= 0 && age < 1.4 { offset = sin(age/1.4 * .pi*2) * 10 * sin(age/1.4 * .pi) }
            else if phase == "듣는 중" { offset = 4 }
            else if phase == "응답 대기" { offset = sin(now*1.6)*1.5 }
            else if phase == "말하는 중" { offset = sin(now*3.2)*2.5 }
        }
        let target = Float(min(max(Double(characterYaw)+offset,-75),75))
        let eased = disabled || publishedReactionYaw == .greatestFiniteMagnitude ? target : publishedReactionYaw+(target-publishedReactionYaw)*0.22
        if abs(eased-publishedReactionYaw) > 0.02 || publishedReactionYaw == .greatestFiniteMagnitude {
            controlWriter.publish(yaw: eased); publishedReactionYaw = eased
        }
    }
    private func refreshCoreStatus() {
        core.speechStatus { [weak self] result in
            switch result {
            case .success(let status):
                self?.connectionLabel?.stringValue = "Core 연결됨 · STT \(status.transcriptionReady ? "준비" : "대기") · TTS \(status.synthesisReady ? "준비" : "대기")"
                self?.connectionLabel?.textColor = .systemGreen
            case .failure:
                self?.connectionLabel?.stringValue = "Core 연결 안 됨 · 로컬 STT/TTS 사용 가능"
                self?.connectionLabel?.textColor = .systemOrange
            }
        }
    }
    @objc private func toggleVisibility() {
        guard let window else { return }
        if window.isVisible { window.orderOut(nil); panel?.orderOut(nil); controlBubble?.orderOut(nil); chatPanel?.orderOut(nil); closeCharacterPicker() }
        else {
            window.orderFrontRegardless()
            chatPanel?.orderFrontRegardless(); controlBubble?.orderOut(nil)
        }
    }
    @objc private func resetPlacement() { guard let screen = NSScreen.main, let window else { return }; UserDefaults.standard.removeObject(forKey: "overlayX"); UserDefaults.standard.removeObject(forKey: "overlayY"); UserDefaults.standard.removeObject(forKey: "overlayYaw"); characterYaw = 0; controlWriter.publish(yaw: 0, reset: true); applyScale(1); window.setFrameOrigin(NSPoint(x: screen.visibleFrame.maxX-window.frame.width-18, y: screen.visibleFrame.minY+18)); positionPanel() }
    @objc private func quit() { NSApp.terminate(nil) }
    private func refreshMenu() { guard let items = statusItem?.menu?.items else { return }; items.first { $0.action == #selector(toggleClickThrough) }?.state = clickThrough ? .on : .off; items.first { $0.action == #selector(toggleAlwaysOnTop) }?.state = alwaysOnTop ? .on : .off; items.first { $0.action == #selector(togglePause) }?.state = paused ? .on : .off }
}

let app = NSApplication.shared
let controller = OverlayController()
app.delegate = controller
app.run()
