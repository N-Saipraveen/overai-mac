#if OVERAI_VALIDATION
import AppKit
import WebKit
import KeyboardShortcuts
import Carbon.HIToolbox
import ScreenCaptureKit
import OverAICore

final class CaptureSentinelView: NSView {
    override func draw(_ dirtyRect: NSRect) {
        NSColor(calibratedRed: 1, green: 0, blue: 0.5, alpha: 1).setFill()
        dirtyRect.fill()
    }
}

/// Exercises the actual overlay/session ownership using synthetic data and nonpersistent storage.
@MainActor final class SelfTestRunner {
    private var overlay: OverlayController?
    private var results: [[String: Any]] = []
    private let captureProbe: Bool
    private let storageProbe: Bool
    init(captureProbe: Bool = false, storageProbe: Bool = false) {
        self.captureProbe = captureProbe
        self.storageProbe = storageProbe
    }

    func start() {
        Task { @MainActor in
            if storageProbe { await runStorageProbe() }
            else if captureProbe { await runCaptureProbe() } else { await run() }
        }
    }
    private func check(_ name: String, _ passed: Bool, detail: String = "") {
        results.append(["name": name, "passed": passed, "detail": detail])
        print("\(passed ? "PASS" : "FAIL") \(name)\(detail.isEmpty ? "" : ": " + detail)")
    }
    private func waitForPage(_ view: WKWebView) async throws {
        for _ in 0..<100 {
            if (try? await view.evaluateJavaScript("window.fixtureReady === true")) as? Bool == true { return }
            try await Task.sleep(for: .milliseconds(100))
        }
        throw NSError(domain: "OverAISelfTest", code: 1, userInfo: [NSLocalizedDescriptionKey: "Synthetic page did not load"])
    }
    private func run() async {
        let suite = "com.overai.selftest." + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let settings = AppSettings(defaults: defaults)
        check("First launch requires a startup choice", !settings.hasChosenStartup)
        settings.chooseStartup(showWindow: false)
        let hiddenSettings = AppSettings(defaults: defaults)
        check("Start Hidden survives relaunch", hiddenSettings.hasChosenStartup && !hiddenSettings.showOnLaunch)
        settings.chooseStartup(showWindow: true)
        let visibleSettings = AppSettings(defaults: defaults)
        check("Show OverAI survives relaunch", visibleSettings.hasChosenStartup && visibleSettings.showOnLaunch)
        defaults.set(Double.nan, forKey: "opacity")
        check("Corrupt nonfinite opacity falls back safely", AppSettings(defaults: defaults).opacity == 1)
        defaults.set(1, forKey: "opacity")
        let deferred = BrowserSession(provider: .chatgpt, configuration: BrowserSession.configuration(persistent: false), loadImmediately: false)
        check("An unopened website makes no page request", deferred.webView.url == nil && !deferred.webView.isLoading)
        deferred.close()
        let permissions = PermissionsController(defaults: defaults)
        check("Fresh installs show permission setup", !permissions.hasShownSetup)
        permissions.markSetupShown()
        check("Permission setup is remembered across launches", PermissionsController(defaults: defaults).hasShownSetup)
        do {
            let folder = FileManager.default.temporaryDirectory.appendingPathComponent("OverAI-folder-check-" + UUID().uuidString)
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false)
            defer { try? FileManager.default.removeItem(at: folder) }
            try permissions.rememberFolder(folder)
            let restored = PermissionsController(defaults: defaults)
            check("Selected upload folder bookmark survives relaunch", restored.uploadFolder?.standardizedFileURL.path == folder.standardizedFileURL.path)
            restored.forgetUploadFolder()
            permissions.stopAccessingFolder()
            check("Forgetting upload folder preserves the folder and clears its bookmark", defaults.data(forKey: "uploadFolderBookmark") == nil && FileManager.default.fileExists(atPath: folder.path))
        } catch { check("Upload folder bookmark", false, detail: error.localizedDescription) }
        let custom = Provider.custom(name: "Local fixture", address: "https://example.com/chat")!
        check("Custom website can be added", settings.addWebsite(custom))
        settings.moveWebsite(custom, by: -1)
        let savedOrder = settings.websites
        settings.selectedProvider = custom
        let reloaded = AppSettings(defaults: defaults)
        check("Custom websites, selection and order survive relaunch", reloaded.websites == savedOrder && reloaded.selectedProvider == custom)
        check("Duplicate website URLs are rejected", !settings.addWebsite(custom))
        for website in settings.websites where website != custom { settings.removeWebsite(website) }
        settings.removeWebsite(custom)
        check("A single custom website works and cannot be accidentally removed", settings.websites == [custom])
        settings.restoreBuiltIns()
        check("Restoring built-ins preserves custom websites", settings.websites.count == 7 && settings.websites.first == custom)
        settings.removeWebsite(custom)
        let removalNavigation = SettingsNavigation()
        let removable = Provider.custom(name: "Removal fixture", address: "https://removal.example")!
        _ = settings.addWebsite(removable)
        removalNavigation.pendingRemoval = removable
        removalNavigation.pendingRemoval = nil
        check("Cancelling removal keeps the custom website", settings.websites.contains(removable))
        removalNavigation.pendingRemoval = removable
        removalNavigation.confirmRemoval(settings: settings)
        check("Settings confirmation removes a custom website and clears confirmation", !settings.websites.contains(removable) && removalNavigation.pendingRemoval == nil)
        removalNavigation.pendingRemoval = .muse
        removalNavigation.confirmRemoval(settings: settings)
        check("Settings confirmation removes a built-in website", !settings.websites.contains(.muse))
        settings.restoreBuiltIns()
        settings.selectedProvider = .chatgpt
        settings.followPointer = false
        check("All six official provider icons are bundled", Provider.allCases.allSatisfy { ProviderArtwork.icon(for: $0) != nil })
        let controller = OverlayController(settings: settings, loadWebsites: false)
        overlay = controller
        check("Free app has no license page", !SettingsPage.allCases.contains { $0.rawValue == "License" })
        let session = controller.current!
        let identity = ObjectIdentifier(session.webView)
        check("Only the selected website is constructed", controller.store.count == 1)
        check("Test website storage is nonpersistent", !session.webView.configuration.websiteDataStore.isPersistent)
        let captured = controller.updateCapture()
        check("Capture exclusion API accepted the window region", captured, detail: settings.captureSummary)
        session.webView.loadHTMLString("""
        <!doctype html><meta charset="utf-8"><title>OverAI synthetic test</title>
        <style>body{font:16px -apple-system;padding:32px;background:#17191e;color:#f5f5f7}textarea{display:block;width:90%;height:80px}button{margin-top:20px}</style>
        <h1>OverAI native lifecycle test</h1><p>Synthetic data only. No account or network connection.</p>
        <textarea id="draft"></textarea><div id="editor" contenteditable="true"></div><button id="send">Test event listener</button>
        <script>window.fixtureReady=true;window.clicks=0;document.querySelector('#send').addEventListener('click',()=>window.clicks++);</script>
        """, baseURL: nil)
        do {
            try await waitForPage(session.webView)
            _ = try await session.webView.evaluateJavaScript("""
            window.runtimeToken='synthetic-runtime';
            document.querySelector('#draft').value='synthetic draft';
            document.querySelector('#editor').textContent='synthetic rich text';
            window.streamTicks=0;window.streamTimer=setInterval(()=>window.streamTicks++,100);
            """)
            if captured { _ = controller.show() }
            controller.hide()
            controller.select(.claude)
            controller.select(.chatgpt)
            settings.opacity = 0.8
            try await Task.sleep(for: .seconds(2))
            _ = try await session.webView.evaluateJavaScript("document.querySelector('#send').click()")
            let state = try await session.webView.evaluateJavaScript("""
            ({token:window.runtimeToken,draft:document.querySelector('#draft').value,
              rich:document.querySelector('#editor').textContent,clicks:window.clicks,ticks:window.streamTicks})
            """) as? [String: Any] ?? [:]
            check("Hide and provider switching retain the same WKWebView", ObjectIdentifier(controller.current.webView) == identity)
            check("Plain draft survives hide and switching", state["draft"] as? String == "synthetic draft")
            check("Rich text draft survives hide and switching", state["rich"] as? String == "synthetic rich text")
            check("JavaScript runtime survives hide and switching", state["token"] as? String == "synthetic-runtime")
            check("Event listeners remain connected", state["clicks"] as? Int == 1)
            check("Synthetic background activity continues", (state["ticks"] as? Int ?? 0) > 0)
            check("Opacity changes do not reload the website", abs(controller.panel.alphaValue - 0.8) < 0.01 && state["token"] as? String == "synthetic-runtime")
            check("Only visited providers are loaded", controller.store.count == 2)
            _ = try await session.webView.evaluateJavaScript("clearInterval(window.streamTimer)")
            controller.panel.contentView?.layoutSubtreeIfNeeded()
            check("Web content receives a nonzero layout", session.webView.bounds.width > 400 && session.webView.bounds.height > 300,
                  detail: NSStringFromRect(session.webView.frame))
            if let index = CommandLine.arguments.firstIndex(of: "--preview"), CommandLine.arguments.count > index + 1 {
                try await renderSyntheticPreview(controller, to: URL(fileURLWithPath: CommandLine.arguments[index + 1]))
            }
            controller.toggleProviderPicker()
            check("Expanded AI picker stays inside the protected panel", controller.toolbarTrayIsVisible && controller.toolbarTraySharesProtectedWindow)
            if let index = CommandLine.arguments.firstIndex(of: "--preview"), CommandLine.arguments.count > index + 1 {
                controller.panel.contentView?.layoutSubtreeIfNeeded()
                let url = URL(fileURLWithPath: CommandLine.arguments[index + 1]).deletingLastPathComponent().appendingPathComponent("picker-preview.png")
                try await renderSyntheticPreview(controller, to: url)
            }
            check("Picker arrow navigation is handled locally", controller.handleTrayKey(125))
            check("Picker Return selects and dismisses", controller.handleTrayKey(36) && !controller.toolbarTrayIsVisible)
            controller.toggleProviderPicker()
            controller.dismissToolbarTray()
            controller.toggleProviderPicker()
            check("Rapid picker reopening remains visible", controller.toolbarTrayIsVisible)
            controller.select(.claude)
            check("Selecting a provider dismisses the picker", !controller.toolbarTrayIsVisible && controller.current.provider == .claude)
            controller.showMore(NSButton())
            check("More options stay inside the protected panel", controller.toolbarTrayIsVisible && controller.toolbarTraySharesProtectedWindow)
            controller.hide()
            check("Hiding dismisses toolbar choices", !controller.toolbarTrayIsVisible)
            controller.select(.chatgpt)
            let folder = FileManager.default.temporaryDirectory.appendingPathComponent("OverAI-attachment-check-" + UUID().uuidString)
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: false)
            defer { try? FileManager.default.removeItem(at: folder) }
            let text = folder.appendingPathComponent("synthetic.txt")
            try Data("synthetic attachment only".utf8).write(to: text)
            let image = folder.appendingPathComponent("Screenshot.png")
            let png = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 8, pixelsHigh: 8, bitsPerSample: 8,
                                       samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
            try png.representation(using: .png, properties: [:])!.write(to: image)
            _ = try await session.webView.evaluateJavaScript("window.fixtureReady=false")
            session.webView.loadHTMLString("""
            <input type="file" multiple><script>
            window.fixtureReady=true; window.uploaded=[];
            document.querySelector('input').onchange=async e=>{
              window.uploaded=await Promise.all([...e.target.files].map(async f=>({name:f.name,size:f.size,text:f.type==='image/png'?'image':await f.text()})));
            };
            </script>
            """, baseURL: Provider.chatgpt.home)
            try await waitForPage(session.webView)
            _ = controller.show()
            session.requestAttachments([text, image])
            for _ in 0..<40 {
                if (try? await session.webView.evaluateJavaScript("window.uploaded.length")) as? Int == 2 { break }
                try await Task.sleep(for: .milliseconds(100))
            }
            let uploaded = try await session.webView.evaluateJavaScript("window.uploaded") as? [[String: Any]] ?? []
            check("Native dropped files reach the website's real file input", uploaded.count == 2,
                  detail: "url=\(session.webView.url?.absoluteString ?? "nil"), status=\(session.message ?? "none"), files=\(uploaded.count)")
            check("WebKit can read the dropped file without a JavaScript file bridge", uploaded.first?["text"] as? String == "synthetic attachment only")
            check("Screenshot PNG reaches the file input", uploaded.last?["name"] as? String == "Screenshot.png" && (uploaded.last?["size"] as? Int ?? 0) > 0)
        } catch {
            check("Native lifecycle experiment", false, detail: error.localizedDescription)
        }
        // Reserve an otherwise unused chord, release it, then reacquire it as wake recovery does.
        var ref: EventHotKeyRef?
        let chord = UInt32(cmdKey | optionKey | controlKey)
        let first = RegisterEventHotKey(UInt32(kVK_F18), chord, EventHotKeyID(signature: 0x4F414954, id: 1), GetEventDispatcherTarget(), 0, &ref)
        if let ref { UnregisterEventHotKey(ref) }
        ref = nil
        let second = RegisterEventHotKey(UInt32(kVK_F18), chord, EventHotKeyID(signature: 0x4F414954, id: 2), GetEventDispatcherTarget(), 0, &ref)
        if let ref { UnregisterEventHotKey(ref) }
        check("OS hotkey can be registered and reacquired", first == noErr && second == noErr)
        check("Privacy is still enabled after lifecycle changes", controller.updateCapture())
        let retained = ObjectIdentifier(controller.current.webView)
        settings.moveWebsite(controller.current.provider, by: 1)
        check("Reordering keeps the current website runtime", ObjectIdentifier(controller.current.webView) == retained)
        let customSessionSite = Provider.custom(name: "Synthetic custom", address: "https://example.com/chat")!
        let countBeforeAdd = controller.store.count
        _ = settings.addWebsite(customSessionSite)
        check("Adding a website does not construct a web view", controller.store.count == countBeforeAdd)
        controller.select(customSessionSite)
        settings.removeWebsite(customSessionSite)
        check("Removing the active website selects a remaining site and releases its session", controller.current.provider != customSessionSite && controller.store.count == countBeforeAdd)
        controller.close()
        check("Closing releases the session registry", controller.store.count == 0)
        if let index = CommandLine.arguments.firstIndex(of: "--preview"), CommandLine.arguments.count > index + 1 {
            let folder = URL(fileURLWithPath: CommandLine.arguments[index + 1]).deletingLastPathComponent()
            let preferences = SettingsController(settings: settings, onShortcutChange: {}, clearData: {})
            for page in SettingsPage.allCases {
                preferences.show(page: page)
                for (name, appearance) in [("light", NSAppearance.Name.aqua), ("dark", NSAppearance.Name.darkAqua)] {
                    preferences.window?.appearance = NSAppearance(named: appearance)
                    try? await Task.sleep(for: .milliseconds(200))
                    guard let view = preferences.window?.contentView,
                          let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds) else {
                        check("Settings \(page.rawValue) \(name) renders", false); continue
                    }
                    view.layoutSubtreeIfNeeded()
                    view.cacheDisplay(in: view.bounds, to: bitmap)
                    let url = folder.appendingPathComponent("settings-\(page.id.replacingOccurrences(of: " ", with: "-").lowercased())-\(name).png")
                    let png = bitmap.representation(using: .png, properties: [:])
                    do {
                        try png?.write(to: url)
                        check("Settings \(page.rawValue) \(name) renders", png != nil && view.bounds.width == 760 && view.bounds.height == 620)
                    } catch { check("Settings preview writes", false, detail: error.localizedDescription) }
                }
            }
            preferences.show(page: .websites)
            preferences.navigation.pendingRemoval = .claude
            try? await Task.sleep(for: .milliseconds(200))
            if let view = preferences.window?.contentView,
               let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds) {
                view.layoutSubtreeIfNeeded()
                view.cacheDisplay(in: view.bounds, to: bitmap)
                try? bitmap.representation(using: .png, properties: [:])?.write(to: folder.appendingPathComponent("settings-removal-confirmation.png"))
                check("Removal confirmation stays inside Settings without a separate sheet", preferences.navigation.pendingRemoval == .claude && preferences.window?.attachedSheet == nil)
            }
            preferences.navigation.pendingRemoval = nil
            preferences.navigation.confirmClearData = true
            preferences.show(page: .privacy)
            try? await Task.sleep(for: .milliseconds(150))
            if let view = preferences.window?.contentView, let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds) {
                view.cacheDisplay(in: view.bounds, to: bitmap)
                try? bitmap.representation(using: .png, properties: [:])?.write(to: folder.appendingPathComponent("settings-clear-data-confirmation.png"))
                check("Data clearing confirmation stays inside Settings", preferences.window?.attachedSheet == nil && preferences.navigation.confirmClearData)
            }
            preferences.navigation.confirmClearData = false
            preferences.close()
            let welcome = StartupController(settings: settings, onFinish: {})
            for (name, appearance) in [("light", NSAppearance.Name.aqua), ("dark", NSAppearance.Name.darkAqua)] {
                welcome.window?.appearance = NSAppearance(named: appearance)
                _ = welcome.show()
                try? await Task.sleep(for: .milliseconds(150))
                if let view = welcome.window?.contentView, let bitmap = view.bitmapImageRepForCachingDisplay(in: view.bounds) {
                    view.cacheDisplay(in: view.bounds, to: bitmap)
                    try? bitmap.representation(using: .png, properties: [:])?.write(to: folder.appendingPathComponent("startup-\(name).png"))
                    check("Startup choice \(name) renders without requesting permissions", view.bounds.size == NSSize(width: 500, height: 380))
                } else { check("Startup choice renders", false) }
            }
            welcome.close()
        }
        finish(extra: ["appProcessFootprintMiB": ProcessMetrics.footprintMiB ?? -1,
                       "scope": "Synthetic state, layout, native registration, API return values; no production AI login, long-idle or capture guarantee."])
    }

    private func runStorageProbe() async {
        let arguments = CommandLine.arguments
        guard let index = arguments.firstIndex(of: "--storage-probe"), arguments.count > index + 2,
              let identifier = UUID(uuidString: arguments[index + 2]) else {
            check("Storage probe arguments", false)
            finish()
        }
        let phase = arguments[index + 1]
        // A fresh UUID supplied by the build script isolates this probe from user accounts.
        let store = WKWebsiteDataStore(forIdentifier: identifier)
        let configuration = BrowserSession.configuration()
        configuration.websiteDataStore = store
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.loadHTMLString("<script>window.fixtureReady=true</script>", baseURL: nil)
        do { try await waitForPage(view) }
        catch { check("Persistent storage fixture initializes", false); finish() }
        let cookie = HTTPCookie(properties: [.domain: "overai-storage-test.invalid", .path: "/",
                                            .name: "overai-persistence-probe", .value: "synthetic-only",
                                            .secure: "TRUE", .expires: Date().addingTimeInterval(3600)])!
        if phase == "write" {
            await withCheckedContinuation { continuation in
                store.httpCookieStore.setCookie(cookie) { continuation.resume() }
            }
        }
        let cookies: [HTTPCookie] = await withCheckedContinuation { continuation in
            store.httpCookieStore.getAllCookies { continuation.resume(returning: $0) }
        }
        check(phase == "write" ? "Persistent cookie written to isolated profile" : "Persistent cookie survives a new app process",
              store.isPersistent && cookies.contains { $0.name == cookie.name && $0.value == cookie.value })
        if phase == "read" {
            await withCheckedContinuation { continuation in
                store.removeData(ofTypes: WKWebsiteDataStore.allWebsiteDataTypes(), modifiedSince: .distantPast) { continuation.resume() }
            }
        }
        finish(extra: ["scope": "Synthetic expiring cookie in an isolated persistent WebKit profile; no user cookies accessed. Site session expiry remains controlled by each provider."])
    }

    private func renderSyntheticPreview(_ controller: OverlayController, to url: URL) async throws {
        // Called only by --self-test, whose sessions never load the network or user storage.
        guard let root = controller.panel.contentView,
              let bitmap = root.bitmapImageRepForCachingDisplay(in: root.bounds) else { return }
        root.cacheDisplay(in: root.bounds, to: bitmap)
        let chrome = NSImage(size: root.bounds.size)
        chrome.addRepresentation(bitmap)
        let snapshot = try await controller.current.webView.takeSnapshot(configuration: nil)
        let webFrame = controller.current.webView.convert(controller.current.webView.bounds, to: root)
        let trayFrame = controller.toolbarTrayContentView.convert(controller.toolbarTrayContentView.bounds, to: root)
        let trayVisible = controller.toolbarTrayIsVisible
        let composed = NSImage(size: root.bounds.size, flipped: false) { rect in
            NSColor.windowBackgroundColor.setFill()
            rect.fill()
            chrome.draw(in: rect)
            snapshot.draw(in: webFrame)
            if trayVisible {
                NSGraphicsContext.saveGraphicsState()
                NSBezierPath(rect: trayFrame).addClip()
                chrome.draw(in: rect)
                NSGraphicsContext.restoreGraphicsState()
            }
            return true
        }
        if let tiff = composed.tiffRepresentation,
           let image = NSBitmapImageRep(data: tiff), let data = image.representation(using: .png, properties: [:]) {
            try data.write(to: url)
        }
    }

    private func runCaptureProbe() async {
        guard CGPreflightScreenCaptureAccess() else {
            results.append(["name": "ScreenCaptureKit pixel test", "skipped": true,
                            "detail": "Screen Recording permission is absent. No permission was requested. Run this probe after granting it to OverAI in System Settings."])
            finish(extra: ["captureValidation": "not run: permission unavailable"])
        }
        let window = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 400, height: 300),
                              styleMask: [.borderless], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.title = "OverAI synthetic capture sentinel"
        let view = CaptureSentinelView(frame: NSRect(x: 0, y: 0, width: 400, height: 300))
        window.contentView = view
        window.backgroundColor = NSColor(calibratedRed: 1, green: 0, blue: 0.5, alpha: 1)
        window.isOpaque = true
        window.level = .floating
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        window.sharingType = .readOnly
        window.makeKeyAndOrderFront(nil)
        window.display()
        defer { window.orderOut(nil) }
        do {
            try await Task.sleep(for: .milliseconds(500))
            let baseline = try await sentinelFraction(window, phase: "baseline")
            check("Capture baseline contains synthetic sentinel", baseline > 0.5, detail: String(format: "sentinel fraction %.3f", baseline))
            guard baseline > 0.5 else {
                finish(extra: ["scope": "The unprotected control was not visible in the captured pixels; exclusion cannot be assessed."])
            }
            check("Region exclusion enabled", CaptureProtection.shared.track(window))
            try await Task.sleep(for: .milliseconds(500))
            let protected = try await sentinelFraction(window, phase: "protected")
            check("ScreenCaptureKit excludes protected sentinel", baseline > 0.5 && protected < 0.05 && window.isVisible,
                  detail: String(format: "sentinel fraction %.3f", protected))
            window.setContentSize(NSSize(width: 520, height: 340))
            try await Task.sleep(for: .milliseconds(500))
            let resized = try await sentinelFraction(window, phase: "resized")
            check("Exclusion survives resize", resized < 0.05 && window.isVisible,
                  detail: String(format: "sentinel fraction %.3f", resized))
            let suite = "com.overai.capturetray." + UUID().uuidString
            let defaults = UserDefaults(suiteName: suite)!
            defer { defaults.removePersistentDomain(forName: suite) }
            let settings = AppSettings(defaults: defaults)
            settings.followPointer = false
            let controller = OverlayController(settings: settings, loadWebsites: false)
            defer { controller.close() }
            guard controller.show() else { throw NSError(domain: "OverAICaptureProbe", code: 3) }
            for (name, open) in [("picker", { controller.toggleProviderPicker() }),
                                 ("more", { controller.showMore(NSButton()) })] {
                // Tray dismissal on focus loss is intentional. Settle activation
                // before asserting that a deliberately opened tray remains visible.
                NSApp.activate(ignoringOtherApps: true)
                controller.panel.makeKeyAndOrderFront(nil)
                try await Task.sleep(for: .milliseconds(400))
                open()
                controller.panel.contentView?.layoutSubtreeIfNeeded()
                let card = controller.toolbarTrayContentView
                let sentinel = CaptureSentinelView(frame: card.bounds)
                sentinel.autoresizingMask = [.width, .height]
                card.addSubview(sentinel)
                controller.panel.display()
                try await Task.sleep(for: .milliseconds(300))
                let fraction = try await sentinelFraction(controller.panel, phase: name)
                check("ScreenCaptureKit excludes expanded \(name)", fraction < 0.01 && controller.panel.isVisible && controller.toolbarTrayIsVisible && controller.toolbarTraySharesProtectedWindow,
                      detail: String(format: "sentinel fraction %.3f; panelVisible=%@ trayVisible=%@ sameWindow=%@ key=%@", fraction, String(controller.panel.isVisible), String(controller.toolbarTrayIsVisible), String(controller.toolbarTraySharesProtectedWindow), String(controller.panel.isKeyWindow)))
                sentinel.removeFromSuperview()
                controller.dismissToolbarTray()
            }
        } catch {
            check("ScreenCaptureKit pixel validation", false, detail: error.localizedDescription)
        }
        finish(extra: ["scope": "Own synthetic window only; other capture tools and displays need separate validation."])
    }
    private func sentinelFraction(_ window: NSWindow, phase: String) async throws -> Double {
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
        guard let ownWindow = content.windows.first(where: { $0.windowID == CGWindowID(window.windowNumber) }) else {
            if phase != "baseline" { return 0 }
            throw NSError(domain: "OverAICaptureProbe", code: 2,
                          userInfo: [NSLocalizedDescriptionKey: "The unprotected control window was absent from the capture catalog; unlock the display and retry."])
        }
        let config = SCStreamConfiguration()
        config.width = 400
        config.height = 300
        config.showsCursor = false
        let image = try await captureWithTransientRetry(ownWindow, configuration: config)
        let pixels = NSBitmapImageRep(cgImage: image)
        if let index = CommandLine.arguments.firstIndex(of: "--output"), CommandLine.arguments.count > index + 1,
           let data = pixels.representation(using: .png, properties: [:]) {
            let folder = URL(fileURLWithPath: CommandLine.arguments[index + 1]).deletingLastPathComponent()
            try data.write(to: folder.appendingPathComponent("capture-\(phase).png"))
        }
        var matches = 0
        var count = 0
        for y in stride(from: 10, to: pixels.pixelsHigh - 10, by: 15) {
            for x in stride(from: 10, to: pixels.pixelsWide - 10, by: 15) {
                guard let color = pixels.colorAt(x: x, y: y)?.usingColorSpace(.sRGB) else { continue }
                count += 1
                // Allow display/profile conversion of the calibrated magenta sentinel.
                if color.redComponent > 0.75 && color.greenComponent < 0.45 && color.blueComponent > 0.2 && color.blueComponent < 0.9 { matches += 1 }
            }
        }
        return count > 0 ? Double(matches) / Double(count) : 0
    }
    // ScreenCaptureKit can transiently fail when successive capture sessions start.
    // Retry only the SDK's failed-to-start/internal-error codes; never retry assertions,
    // permission denial, invalid configuration, or an absent baseline window.
    private func captureWithTransientRetry(_ window: SCWindow, configuration: SCStreamConfiguration) async throws -> CGImage {
        for attempt in 0..<3 {
            do {
                return try await SCScreenshotManager.captureImage(contentFilter: SCContentFilter(desktopIndependentWindow: window), configuration: configuration)
            } catch {
                let failure = error as NSError
                guard failure.domain == SCStreamErrorDomain, [-3802, -3811].contains(failure.code), attempt < 2 else { throw error }
                print("Capture API transient startup error \(failure.code); retry \(attempt + 1)/2")
                try await Task.sleep(for: .milliseconds(300 * (attempt + 1)))
            }
        }
        preconditionFailure("Capture attempts must return or throw")
    }
    private func finish(extra: [String: Any] = [:]) -> Never {
        let failures = results.filter { ($0["passed"] as? Bool) == false }.count
        var output: [String: Any] = ["os": ProcessInfo.processInfo.operatingSystemVersionString,
                                    "architecture": "arm64", "checks": results, "failures": failures]
        extra.forEach { output[$0.key] = $0.value }
        if let index = CommandLine.arguments.firstIndex(of: "--output"), CommandLine.arguments.count > index + 1 {
            let url = URL(fileURLWithPath: CommandLine.arguments[index + 1])
            if let data = try? JSONSerialization.data(withJSONObject: output, options: [.prettyPrinted, .sortedKeys]) { try? data.write(to: url) }
        }
        let skipped = results.filter { $0["skipped"] as? Bool == true }.count
        let executed = results.count - skipped
        print("\(failures > 0 ? "FAIL" : executed == 0 ? "SKIP" : "PASS"): \(executed) checks, \(skipped) skipped, \(failures) failures")
        fflush(stdout)
        // Follow the same graceful shutdown path as a user quitting the app. A raw
        // exit skips AppKit/WebKit termination and is not a normal relaunch test.
        if failures == 0 { NSApp.terminate(nil) }
        exit(failures == 0 ? 0 : 1)
    }
}

#endif
