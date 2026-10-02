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
final class InteractiveOverlayWindow: NSWindow {
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
        guard fd >= 0, posixFtruncate(fd, off_t(Self.bytes)) == 0 else {
            if fd >= 0 { close(fd) }; fd = -1; return false
        }
        let mappedResult = mmap(nil, Self.bytes, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0)
        guard let mapped = mappedResult, mapped != MAP_FAILED else { close(fd); fd = -1; return false }
        address = mapped
        mapped.storeBytes(of: Self.magic, toByteOffset: 0, as: UInt32.self)
        mapped.storeBytes(of: UInt32(1), toByteOffset: 4, as: UInt32.self)
        return true
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

    private func request<T: Decodable>(path: String, method: String, body: Data?,
                                       completion: @escaping (Result<T, Error>) -> Void) {
        var request = URLRequest(url: URL(string: path, relativeTo: root)!)
        request.httpMethod = method; request.httpBody = body; request.timeoutInterval = 20
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

final class OverlayController: NSObject, NSApplicationDelegate {
    private let gpuEnabled = ProcessInfo.processInfo.environment["GAHYEON_GPU_IOSURFACE"] == "1"
    private let gpuReader = SharedIOSurfaceReader()
    private let reader = SharedRGBAReader()
    private let controlWriter = SharedOverlayControlWriter()
    private let core = DesktopCoreClient()
    private let speechInput = NativeSpeechInput()
    private let speechOutput = AVSpeechSynthesizer()
    private let imageView = DragImageView()
    private var window: NSWindow?
    private var panel: NSPanel?
    private var controlBubble: NSPanel?
    private var chatPanel: NSPanel?
    private var chatHistory: NSTextView?
    private var chatInput: NSTextField?
    private var connectionLabel: NSTextField?
    private var micButton: NSButton?
    private var soundButton: NSButton?
    private var controlsToggleButton: NSButton?
    private var modelPopup: NSPopUpButton?
    private var animationPopup: NSPopUpButton?
    private var statusItem: NSStatusItem?
    private var timer: Timer?
    private var clickThrough = false
    private var controlsExpanded = false
    private var alwaysOnTop = true
    private var paused = false
    private var scale: CGFloat = 1
    private var characterYaw: CGFloat = 0
    private var baseSize = NSSize(width: 815, height: 640)
    private var frameCount = 0
    private var fpsStart = CFAbsoluteTimeGetCurrent()
    private var fittedToCharacter = false
    private var soundEnabled = UserDefaults.standard.object(forKey: "voiceOutput") as? Bool ?? true
    private var selectedCharacter = UserDefaults.standard.string(forKey: "selectedCharacter") ?? "diana"
    private var selectedAnimationIndex = UserDefaults.standard.integer(forKey: "selectedAnimationIndex")

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        if UserDefaults.standard.integer(forKey: "layoutVersion") < 9 {
            ["overlayX", "overlayY", "overlayScale"].forEach { UserDefaults.standard.removeObject(forKey: $0) }
            UserDefaults.standard.set(9, forKey: "layoutVersion")
        }
        installMenu(); createWindow(); refreshCoreStatus()
        characterYaw = CGFloat(UserDefaults.standard.double(forKey: "overlayYaw"))
        if !(-75...75).contains(characterYaw) { characterYaw = 0 }
        controlWriter.publish(yaw: Float(characterYaw))
        timer = Timer.scheduledTimer(withTimeInterval: 1.0 / 60.0, repeats: true) { [weak self] _ in self?.displayFrame() }
    }

    private func displayFrame() {
        if !paused, gpuEnabled, let (surface, width, height, crop) = gpuReader.nextSurface() {
            if !fittedToCharacter { fitWindowToDimensions(width: width, height: height); fittedToCharacter = true }
            imageView.image = nil; imageView.wantsLayer = true
            imageView.layer?.contents = surface
            imageView.layer?.contentsRect = crop
            imageView.layer?.contentsGravity = .resizeAspect
            countFrame(); return
        }
        guard !paused, let frame = reader.nextImage() else { return }
        if !fittedToCharacter { fitWindowToCharacter(frame); fittedToCharacter = true }
        imageView.image = NSImage(cgImage: frame, size: NSSize(width: frame.width, height: frame.height))
        countFrame()
    }

    private func countFrame() {
        frameCount += 1
        let now = CFAbsoluteTimeGetCurrent(), elapsed = now - fpsStart
        if elapsed >= 2 { fputs(String(format: "direct-alpha measured fps: %.1f\n", Double(frameCount) / elapsed), stderr); frameCount = 0; fpsStart = now }
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
        let target = NSRect(x: center.x - baseSize.width / 2, y: center.y - baseSize.height / 2,
                            width: baseSize.width, height: baseSize.height)
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
        value.contentView = surface
        NotificationCenter.default.addObserver(self, selector: #selector(didMove), name: NSWindow.didMoveNotification, object: value)
        value.orderFrontRegardless(); window = value; createPanel()
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
        guard let window else { return }
        let frame = NSRect(x: window.frame.minX - 126, y: window.frame.midY - 58, width: 116, height: 116)
        let value = NSPanel(contentRect: frame, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        value.isOpaque = false; value.backgroundColor = .clear; value.hasShadow = false; value.level = .floating
        value.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
        let effect = liquidGlassEffect(frame: NSRect(origin: .zero, size: frame.size), radius: 15)
        let character = islandButton("person.crop.circle", #selector(cycleCharacterModel), "캐릭터 선택")
        let refresh = islandButton("arrow.clockwise", #selector(refreshIsland), "화면 새로고침")
        let reset = islandButton("scope", #selector(resetPlacement), "캐릭터 중앙 정렬")
        let background = islandButton("circle.lefthalf.filled", #selector(togglePause), "배경 전환")
        let pin = islandButton("pin", #selector(toggleAlwaysOnTop), "항상 위에 표시")
        let terminate = islandButton("power", #selector(quit), "캐릭터 종료", tint: .systemPink)
        let chat = islandButton("message", #selector(toggleChat), "채팅 열기")
        micButton = islandButton("mic", #selector(toggleMicrophone), "마이크 켜기 또는 끄기", tint: .systemGreen)
        soundButton = islandButton(soundEnabled ? "speaker.wave.2" : "speaker.slash", #selector(toggleSound), "스피커 켜기 또는 끄기", tint: .systemCyan)
        let grid = NSGridView(views: [
            [character, refresh, reset],
            [background, pin, terminate],
            [chat, micButton!, soundButton!],
        ])
        grid.rowSpacing = 4; grid.columnSpacing = 4; grid.translatesAutoresizingMaskIntoConstraints = false
        for row in 0..<3 { grid.row(at: row).height = 30 }
        effect.addSubview(grid); NSLayoutConstraint.activate([
            grid.leadingAnchor.constraint(equalTo: effect.leadingAnchor, constant: 9),
            grid.trailingAnchor.constraint(equalTo: effect.trailingAnchor, constant: -9),
            grid.topAnchor.constraint(equalTo: effect.topAnchor, constant: 9),
            grid.bottomAnchor.constraint(equalTo: effect.bottomAnchor, constant: -9),
        ])
        value.contentView = effect; panel = value; createControlBubble(); value.orderOut(nil)
    }

    private func createControlBubble() {
        guard let panel else { return }
        let frame = NSRect(x: panel.frame.maxX - 36, y: panel.frame.minY - 42, width: 36, height: 36)
        let value = NSPanel(contentRect: frame, styleMask: [.borderless, .nonactivatingPanel], backing: .buffered, defer: false)
        value.isOpaque = false; value.backgroundColor = .clear; value.level = .floating
        value.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
        let effect = liquidGlassEffect(frame: NSRect(origin: .zero, size: frame.size), radius: 18)
        let button = islandButton("chevron.up", #selector(toggleControls), "캐릭터 컨트롤 열기")
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
        let button = NSButton(image: image ?? NSImage(), target: self, action: action)
        button.toolTip = tooltip; button.isBordered = false; button.contentTintColor = tint
        button.wantsLayer = true; button.layer?.cornerRadius = 7; button.layer?.borderWidth = 1
        button.layer?.borderColor = NSColor.white.withAlphaComponent(0.26).cgColor
        button.layer?.backgroundColor = NSColor(calibratedRed: 0.08, green: 0.14, blue: 0.22, alpha: 0.47).cgColor
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

    @objc private func didMove() { guard let window else { return }; UserDefaults.standard.set(window.frame.origin.x, forKey: "overlayX"); UserDefaults.standard.set(window.frame.origin.y, forKey: "overlayY"); positionPanel() }
    private func positionPanel() {
        guard let window, let panel, let screen = window.screen ?? NSScreen.main else { return }
        let inset: CGFloat = 14
        let x = min(max(window.frame.maxX - panel.frame.width - inset, screen.visibleFrame.minX + 8),
                    screen.visibleFrame.maxX - panel.frame.width - 8)
        let y = min(max(window.frame.minY + inset + 42, screen.visibleFrame.minY + 50),
                    screen.visibleFrame.maxY - panel.frame.height - 8)
        panel.setFrameOrigin(NSPoint(x: x, y: y))
        controlBubble?.setFrameOrigin(NSPoint(x: panel.frame.maxX - 36, y: panel.frame.minY - 42))
    }
    private func applyScale(_ value: CGFloat) { guard let window else { return }; scale = min(max(value, 0.65), 1.35); let c = NSPoint(x: window.frame.midX, y: window.frame.midY), s = NSSize(width: baseSize.width * scale, height: baseSize.height * scale); window.setFrame(NSRect(x: c.x-s.width/2, y: c.y-s.height/2, width: s.width, height: s.height), display: true, animate: true); UserDefaults.standard.set(Double(scale), forKey: "overlayScale"); positionPanel() }
    private func rotateCharacter(horizontalDelta: CGFloat) { characterYaw = min(max(characterYaw + horizontalDelta * 0.35, -75), 75); UserDefaults.standard.set(Double(characterYaw), forKey: "overlayYaw"); controlWriter.publish(yaw: Float(characterYaw)) }
    @objc private func larger() { applyScale(scale + 0.1) }; @objc private func smaller() { applyScale(scale - 0.1) }
    @objc private func toggleClickThrough() { clickThrough.toggle(); window?.ignoresMouseEvents = clickThrough; refreshMenu() }
    @objc private func toggleAlwaysOnTop() { alwaysOnTop.toggle(); window?.level = alwaysOnTop ? .floating : .normal; panel?.level = alwaysOnTop ? .floating : .normal; refreshMenu() }
    @objc private func togglePause() { paused.toggle(); refreshMenu() }
    @objc private func toggleControls() {
        guard let panel else { return }
        controlsExpanded.toggle()
        if controlsExpanded { panel.orderFrontRegardless(); positionPanel() }
        else { panel.orderOut(nil) }
        let symbol = controlsExpanded ? "chevron.down" : "chevron.up"
        controlsToggleButton?.image = NSImage(systemSymbolName: symbol, accessibilityDescription: controlsExpanded ? "캐릭터 컨트롤 닫기" : "캐릭터 컨트롤 열기")
        controlsToggleButton?.toolTip = controlsExpanded ? "캐릭터 컨트롤 닫기" : "캐릭터 컨트롤 열기"
        controlBubble?.orderFrontRegardless()
    }
    @objc private func refreshIsland() { fittedToCharacter = false; refreshCoreStatus() }
    @objc private func toggleSound() {
        soundEnabled.toggle(); UserDefaults.standard.set(soundEnabled, forKey: "voiceOutput")
        if !soundEnabled { speechOutput.stopSpeaking(at: .immediate) }
        soundButton?.image = NSImage(systemSymbolName: soundEnabled ? "speaker.wave.2" : "speaker.slash", accessibilityDescription: "스피커")
    }
    @objc private func toggleMicrophone() {
        speechInput.toggle(onText: { [weak self] text, final in
            self?.chatInput?.stringValue = text
            self?.micButton?.contentTintColor = final ? .systemGreen : .systemOrange
            if final { self?.speechInput.stop() }
        }, onError: { [weak self] message in
            self?.micButton?.contentTintColor = .systemRed
            self?.appendChat(role: "시스템", text: message)
        })
        micButton?.contentTintColor = speechInput.recording ? .secondaryLabelColor : .systemGreen
    }
    @objc private func focusModelPicker() {
        modelPopup?.window?.makeKey(); modelPopup?.performClick(nil)
    }
    @objc private func focusAnimationPicker() {
        animationPopup?.window?.makeKey(); animationPopup?.performClick(nil)
    }
    @objc private func cycleCharacterModel() {
        selectedCharacter = selectedCharacter == "diana" ? "gahyeon" : "diana"
        UserDefaults.standard.set(selectedCharacter, forKey: "selectedCharacter")
        connectionLabel?.stringValue = "모델 선택 · \(selectedCharacter == "diana" ? "다이애나" : "가현")"
    }
    @objc private func cycleAnimation() {
        let names = ["대기", "걷기", "달리기", "인사"]
        selectedAnimationIndex = (selectedAnimationIndex + 1) % names.count
        UserDefaults.standard.set(selectedAnimationIndex, forKey: "selectedAnimationIndex")
        connectionLabel?.stringValue = "애니메이션 선택 · \(names[selectedAnimationIndex])"
    }
    @objc private func toggleChat() {
        if let chatPanel { chatPanel.isVisible ? chatPanel.orderOut(nil) : chatPanel.orderFrontRegardless(); return }
        createChatPanel()
    }
    private func createChatPanel() {
        guard let panel else { return }
        let frame = NSRect(x: panel.frame.minX - 390, y: panel.frame.minY, width: 380, height: 460)
        let value = NSPanel(contentRect: frame, styleMask: [.titled, .closable, .resizable, .utilityWindow], backing: .buffered, defer: false)
        value.title = "가현 채팅"; value.level = alwaysOnTop ? .floating : .normal; value.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        let root = NSStackView(); root.orientation = .vertical; root.spacing = 10; root.edgeInsets = NSEdgeInsets(top: 12, left: 12, bottom: 12, right: 12)
        let scroll = NSScrollView(); scroll.hasVerticalScroller = true
        let history = NSTextView(); history.isEditable = false; history.drawsBackground = false; history.font = .systemFont(ofSize: 13)
        scroll.documentView = history; chatHistory = history
        let row = NSStackView(); row.orientation = .horizontal; row.spacing = 8
        let input = NSTextField(); input.placeholderString = "가현에게 메시지 보내기"; input.target = self; input.action = #selector(sendChat); chatInput = input
        let send = NSButton(title: "보내기", target: self, action: #selector(sendChat))
        row.addArrangedSubview(input); row.addArrangedSubview(send)
        root.addArrangedSubview(scroll); root.addArrangedSubview(row)
        scroll.heightAnchor.constraint(greaterThanOrEqualToConstant: 330).isActive = true
        value.contentView = root; value.orderFrontRegardless(); value.makeKey(); chatPanel = value
        appendChat(role: "다이애나", text: "대화를 시작해요.")
    }
    @objc private func sendChat() {
        guard let input = chatInput, !input.stringValue.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        let message = input.stringValue.trimmingCharacters(in: .whitespacesAndNewlines); input.stringValue = ""; input.isEnabled = false
        appendChat(role: "나", text: message)
        core.send(message: message, characterId: selectedCharacter) { [weak self] result in
            guard let self else { return }; input.isEnabled = true; input.window?.makeFirstResponder(input)
            switch result {
            case .success(let response):
                self.appendChat(role: self.selectedCharacter == "diana" ? "다이애나" : "가현", text: response.content)
                if self.soundEnabled {
                    let utterance = AVSpeechUtterance(string: response.content)
                    utterance.voice = AVSpeechSynthesisVoice(language: "ko-KR")
                    self.speechOutput.speak(utterance)
                }
            case .failure(let error): self.appendChat(role: "시스템", text: "Core 연결 실패: \(error.localizedDescription)")
            }
        }
    }
    private func appendChat(role: String, text: String) {
        if chatPanel == nil { createChatPanel() }
        guard let history = chatHistory else { return }
        history.textStorage?.append(NSAttributedString(string: "\(role)\n\(text)\n\n", attributes: [.font: NSFont.systemFont(ofSize: 13)]))
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
        if window.isVisible { window.orderOut(nil); panel?.orderOut(nil); controlBubble?.orderOut(nil) }
        else {
            window.orderFrontRegardless()
            if controlsExpanded { panel?.orderFrontRegardless() } else { controlBubble?.orderFrontRegardless() }
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
