#if OVERAI_VALIDATION
import AppKit
import WebKit
import OverAICore

/// Explicit development mode: local synthetic content, no accounts or network requests.
@MainActor final class UploadLab {
    let window: NSPanel
    let session: BrowserSession
    private let source: FixtureDragButton
    init() {
        let file = FileManager.default.temporaryDirectory.appendingPathComponent("OverAI-upload-fixture.txt")
        try? Data("OverAI synthetic upload fixture".utf8).write(to: file)
        source = FixtureDragButton(file: file)
        session = BrowserSession(provider: .chatgpt, configuration: BrowserSession.configuration(persistent: false), loadImmediately: false)
        window = OverlayPanel(contentRect: NSRect(x: 0, y: 0, width: 760, height: 480),
                              styleMask: [.titled, .closable, .nonactivatingPanel], backing: .buffered, defer: false)
        window.title = "OverAI upload test — synthetic only"
        window.isReleasedWhenClosed = false
        window.hidesOnDeactivate = false
        let root = FileDropView(frame: NSRect(x: 0, y: 0, width: 760, height: 480))
        root.onFiles = { [weak session] in session?.requestAttachments($0) }
        let target = NSTextField(labelWithString: "Toolbar fallback:\nDrop below this label")
        target.frame = NSRect(x: 20, y: 240, width: 170, height: 55)
        root.addSubview(target)
        source.frame = NSRect(x: 20, y: 340, width: 170, height: 60)
        root.addSubview(source)
        let pngFile = FileManager.default.temporaryDirectory.appendingPathComponent("OverAI-screenshot-fixture.png")
        let png = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 8, pixelsHigh: 8, bitsPerSample: 8,
                                  samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        try? png.representation(using: .png, properties: [:])!.write(to: pngFile)
        let promise = FixtureDragButton(file: pngFile, promised: true)
        promise.title = "Drag screenshot →"
        promise.frame = NSRect(x: 20, y: 280, width: 170, height: 50)
        root.addSubview(promise)
        session.webView.frame = NSRect(x: 210, y: 0, width: 550, height: 480)
        root.addSubview(session.webView)
        window.contentView = root
        session.webView.loadHTMLString("""
        <style>body{font:18px -apple-system;padding:24px}#zone{border:2px dashed #888;padding:50px 20px}pre{white-space:pre-wrap}</style>
        <h2>Local upload check</h2><div id="zone">Drop the synthetic file here</div>
        <p>Or use the native file picker:</p><input type="file" multiple><pre id="result">No file received</pre>
        <script>
        const zone=document.querySelector('#zone'), result=document.querySelector('#result');
        document.addEventListener('dragover',e=>{e.preventDefault();e.dataTransfer.dropEffect='copy';});
        document.addEventListener('drop',async e=>{e.preventDefault();const files=[...e.dataTransfer.files];result.textContent='DROP: '+files.map(f=>f.name+' ('+f.size+' bytes)').join(', ');});
        document.querySelector('input').addEventListener('change',e=>{result.textContent='PICKER: '+[...e.target.files].map(f=>f.name).join(', ');});
        </script>
        """, baseURL: Provider.chatgpt.home)
        session.windowProvider = { [weak window] in window }
        window.center()
        window.makeKeyAndOrderFront(nil)
    }
}

@MainActor private final class FixtureDragButton: NSButton, NSDraggingSource, NSFilePromiseProviderDelegate {
    let file: URL
    let promised: Bool
    init(file: URL, promised: Bool = false) {
        self.file = file
        self.promised = promised
        super.init(frame: .zero)
        title = "Drag test file →"
        bezelStyle = .rounded
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }
    override func mouseDown(with event: NSEvent) {
        let writer: NSPasteboardWriting = promised ? NSFilePromiseProvider(fileType: "public.png", delegate: self) : file as NSURL
        let item = NSDraggingItem(pasteboardWriter: writer)
        item.setDraggingFrame(bounds, contents: NSImage(systemSymbolName: "doc", accessibilityDescription: nil))
        beginDraggingSession(with: [item], event: event, source: self)
    }
    func draggingSession(_ session: NSDraggingSession, sourceOperationMaskFor context: NSDraggingContext) -> NSDragOperation { .copy }
    func filePromiseProvider(_ filePromiseProvider: NSFilePromiseProvider, fileNameForType fileType: String) -> String { file.lastPathComponent }
    func filePromiseProvider(_ filePromiseProvider: NSFilePromiseProvider, writePromiseTo url: URL, completionHandler: @escaping (Error?) -> Void) {
        do { try FileManager.default.copyItem(at: file, to: url); completionHandler(nil) }
        catch { completionHandler(error) }
    }
}

#endif
