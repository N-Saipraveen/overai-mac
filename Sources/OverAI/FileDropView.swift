import AppKit
import UniformTypeIdentifiers

/// Native drop target for the toolbar. WebKit continues to own drops on the website.
final class FileDropView: NSView {
    var onFiles: (([URL]) -> Void)?
    var onFailure: ((String) -> Void)?
    private var generation = 0
    private var temporaryFolders: [URL] = []
    override init(frame: NSRect) {
        super.init(frame: frame)
        registerForDraggedTypes([.fileURL, .png, .tiff] + NSFilePromiseReceiver.readableDraggedTypes.map { NSPasteboard.PasteboardType($0) })
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }
    override func mouseDown(with event: NSEvent) { window?.performDrag(with: event) }
    override func draggingEntered(_ sender: NSDraggingInfo) -> NSDragOperation { .copy }
    override func draggingUpdated(_ sender: NSDraggingInfo) -> NSDragOperation { .copy }
    override func prepareForDragOperation(_ sender: NSDraggingInfo) -> Bool { true }
    override func performDragOperation(_ sender: NSDraggingInfo) -> Bool {
        let delivery = onFiles
        let failure = onFailure
        let dropGeneration = generation
        let board = sender.draggingPasteboard
        let urls = (board.readObjects(forClasses: [NSURL.self], options: [.urlReadingFileURLsOnly: true]) as? [URL]) ?? []
        if !urls.isEmpty { delivery?(urls); return true }
        do {
            let folder = FileManager.default.temporaryDirectory.appendingPathComponent("OverAI-drop-" + UUID().uuidString, isDirectory: true)
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
            temporaryFolders.append(folder)
            if let promises = board.readObjects(forClasses: [NSFilePromiseReceiver.self]) as? [NSFilePromiseReceiver], !promises.isEmpty {
                var remaining = promises.reduce(0) { $0 + max(1, $1.fileNames.count) }
                var received: [URL] = []
                var failed = false
                for receiver in promises {
                    receiver.receivePromisedFiles(atDestination: folder, options: [:], operationQueue: .main) { [weak self] url, error in
                        guard let self, self.generation == dropGeneration else { return }
                        if error != nil { failed = true } else { received.append(url) }
                        remaining -= 1
                        if remaining == 0 {
                            if !received.isEmpty { delivery?(received) }
                            if failed { failure?("Some screenshots couldn't be received. Save them first, then drop the saved files.") }
                        }
                    }
                }
                return true
            }
            if let png = board.data(forType: .png) ?? board.data(forType: .tiff).flatMap({ NSBitmapImageRep(data: $0)?.representation(using: .png, properties: [:]) }) {
                let file = folder.appendingPathComponent("Screenshot.png")
                try png.write(to: file, options: .atomic)
                delivery?([file])
                return true
            }
        } catch { onFailure?("The dropped file couldn't be read. Try the website's upload button.") }
        return false
    }
    func cleanUp() {
        generation += 1
        onFiles = nil
        onFailure = nil
        temporaryFolders.forEach { try? FileManager.default.removeItem(at: $0) }
        temporaryFolders.removeAll()
    }
}
