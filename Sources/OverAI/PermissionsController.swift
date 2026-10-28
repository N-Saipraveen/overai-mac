import AppKit
import AVFoundation
import Combine

@MainActor final class PermissionsController: ObservableObject {
    static let shared = PermissionsController()
    private let defaults: UserDefaults
    private var scopedFolder: URL?
    private var hasScope = false
    @Published private(set) var microphoneStatus = ""
    @Published private(set) var uploadFolder: URL?
    @Published private(set) var isBusy = false
    var hasShownSetup: Bool { defaults.bool(forKey: "permissionsSetupShown") }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        refreshMicrophoneStatus()
        if let data = defaults.data(forKey: "uploadFolderBookmark") {
            var stale = false
            if let url = try? URL(resolvingBookmarkData: data, options: [.withSecurityScope, .withoutUI],
                                  relativeTo: nil, bookmarkDataIsStale: &stale) {
                useFolder(url)
                if stale { try? rememberFolder(url) }
            }
        }
    }

    func refreshMicrophoneStatus() {
        microphoneStatus = switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized: "Allowed"
        case .denied: "Not allowed — change in System Settings"
        case .restricted: "Restricted by this Mac"
        case .notDetermined: "Not requested yet"
        @unknown default: "Unavailable"
        }
    }

    private func authorizeMicrophone() async {
        if AVCaptureDevice.authorizationStatus(for: .audio) == .notDetermined {
            _ = await AVCaptureDevice.requestAccess(for: .audio)
        }
        refreshMicrophoneStatus()
    }

    func requestMicrophoneFromSettings() {
        guard !isBusy else { return }
        if AVCaptureDevice.authorizationStatus(for: .audio) == .denied {
            NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone")!)
            return
        }
        isBusy = true
        Task { @MainActor in await authorizeMicrophone(); isBusy = false }
    }

    func markSetupShown() { defaults.set(true, forKey: "permissionsSetupShown") }

    func presentSetup(parent: NSWindow, completion: @escaping () -> Void = {}) {
        guard !isBusy, parent.attachedSheet == nil else { completion(); return }
        let alert = NSAlert()
        alert.messageText = "Welcome to OverAI"
        alert.informativeText = "Set up your microphone for voice chats and choose a folder for uploads. macOS will ask for microphone access, then show a folder picker. Choosing a folder does not upload anything. You can skip this and return in Settings."
        alert.addButton(withTitle: "Set Up Microphone & Files")
        alert.addButton(withTitle: "Not Now")
        guard CaptureProtection.shared.track(alert.window) else { completion(); return }
        isBusy = true
        markSetupShown()
        NSApp.activate(ignoringOtherApps: true)
        alert.beginSheetModal(for: parent) { [weak self, weak parent] response in
            guard let self else { return }
            guard response == .alertFirstButtonReturn else { self.isBusy = false; completion(); return }
            Task { @MainActor in
                await self.authorizeMicrophone()
                // The welcome sheet has to finish detaching before the folder sheet begins.
                await Task.yield()
                if let parent { await self.pickUploadFolder(parent: parent) }
                self.isBusy = false
                completion()
            }
        }
    }

    func chooseUploadFolder(parent: NSWindow?) {
        guard !isBusy, let parent, parent.attachedSheet == nil else { return }
        isBusy = true
        Task { @MainActor in await pickUploadFolder(parent: parent); isBusy = false }
    }

    private func pickUploadFolder(parent: NSWindow) async {
        guard parent.attachedSheet == nil else { return }
        let picker = NSOpenPanel()
        picker.title = "Choose Your Upload Folder"
        picker.message = "Choose a folder you use for screenshots and attachments. Files are sent only when you attach them to a website. Other files can still be selected individually."
        picker.prompt = "Choose Folder"
        picker.canChooseDirectories = true
        picker.canChooseFiles = false
        picker.allowsMultipleSelection = false
        picker.canCreateDirectories = false
        picker.directoryURL = uploadFolder
        guard CaptureProtection.shared.track(picker) else { return }
        let response: NSApplication.ModalResponse = await withCheckedContinuation { continuation in
            picker.beginSheetModal(for: parent) { continuation.resume(returning: $0) }
        }
        guard response == .OK, let url = picker.url else { return }
        do { try rememberFolder(url) }
        catch {
            let alert = NSAlert()
            alert.messageText = "This folder couldn't be remembered"
            alert.informativeText = "You can still select individual files when uploading. Try choosing the folder again in Settings."
            if CaptureProtection.shared.track(alert.window) { _ = await alert.beginSheetModal(for: parent) }
        }
    }

    func rememberFolder(_ url: URL) throws {
        let bookmark = try url.bookmarkData(options: [.withSecurityScope, .securityScopeAllowOnlyReadAccess],
                                            includingResourceValuesForKeys: nil, relativeTo: nil)
        defaults.set(bookmark, forKey: "uploadFolderBookmark")
        useFolder(url)
    }

    private func useFolder(_ url: URL) {
        if hasScope { scopedFolder?.stopAccessingSecurityScopedResource() }
        scopedFolder = url
        hasScope = url.startAccessingSecurityScopedResource()
        uploadFolder = url
    }

    func forgetUploadFolder() {
        if hasScope { scopedFolder?.stopAccessingSecurityScopedResource() }
        hasScope = false
        scopedFolder = nil
        uploadFolder = nil
        defaults.removeObject(forKey: "uploadFolderBookmark")
    }

    func stopAccessingFolder() {
        if hasScope { scopedFolder?.stopAccessingSecurityScopedResource() }
        hasScope = false
    }
}
