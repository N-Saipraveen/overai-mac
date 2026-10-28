import AppKit
import AVFoundation
import WebKit
import OverAICore

@MainActor final class BrowserSession: NSObject, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    let provider: Provider
    let webView: WKWebView
    var onChange: (() -> Void)?
    var windowProvider: (() -> NSWindow?)?
    private(set) var message: String?
    private(set) var hasError = false
    private(set) var lastURL: URL
    private var observations: [NSKeyValueObservation] = []
    private var popups: [PopupWindowController] = []
    private var downloads: [ObjectIdentifier: WKDownload] = [:]
    private var didRequestLoad = false
    private var isClosed = false
    private var recovery = RecoveryBudget()
    private var stablePage: DispatchWorkItem?
    private var navigationGeneration = 0
    private var pendingAttachments: [URL]?
    private var attachmentTimeout: DispatchWorkItem?

    func requestAttachments(_ urls: [URL]) {
        guard let page = webView.url, provider.owns(page), page.scheme == "https", pendingAttachments == nil else {
            report("Open the provider's chat page before dropping files. Finish any current file selection first.", error: true)
            return
        }
        let files = urls.filter { $0.isFileURL && (try? $0.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) == true }
        guard !files.isEmpty else { report("Drop files rather than folders.", error: true); return }
        pendingAttachments = files
        let timeout = DispatchWorkItem { [weak self] in
            guard let self, self.pendingAttachments != nil else { return }
            self.pendingAttachments = nil
            self.report("Open the website's attachment menu, then drop the files on the toolbar again. This page hasn't exposed a file upload field yet.", error: true)
        }
        attachmentTimeout = timeout
        DispatchQueue.main.asyncAfter(deadline: .now() + 3, execute: timeout)
        // Ask the website's real file input to use WebKit's native file chooser.
        // No file bytes, credentials or native filesystem bridge enter JavaScript.
        webView.evaluateJavaScript("""
        (() => {
          const input = [...document.querySelectorAll('input[type="file"]')].find(e => !e.disabled);
          if (!input) return false;
          input.click(); return true;
        })()
        """) { [weak self] result, error in
            guard let self, self.pendingAttachments != nil else { return }
            if error != nil || result as? Bool != true {
                self.attachmentTimeout?.cancel()
                self.pendingAttachments = nil
                self.report("Open the website's attachment menu, then drop the files on the toolbar again.", error: true)
            }
        }
    }

    init(provider: Provider, configuration: WKWebViewConfiguration? = nil, loadImmediately: Bool = true) {
        self.provider = provider
        self.lastURL = provider.home
        let config = configuration ?? Self.configuration()
        if provider == .arena {
            // Arena is a SPA: changing modes may use history.pushState without a
            // WebKit navigation callback. Enforce the user's Direct-only choice there too.
            config.userContentController.addUserScript(WKUserScript(source: """
            (() => {
              const direct = 'https://arena.ai/text/direct?model_a=max';
              const blocked = value => {
                try { const u = new URL(value, location.href); const p = u.pathname.toLowerCase();
                  return (u.hostname === 'arena.ai' || u.hostname.endsWith('.arena.ai')) &&
                    (p === '/' || p === '/text' || (p.startsWith('/text/') && !p.startsWith('/text/direct')) || p.split('/').includes('battle') || p.includes('side-by-side'));
                } catch { return false; }
              };
              for (const method of ['pushState', 'replaceState']) {
                const original = history[method];
                history[method] = function(state, title, url) {
                  if (url != null && blocked(url)) { location.replace(direct); return; }
                  return original.apply(this, arguments);
                };
              }
              const enforce = () => { if (blocked(location.href)) location.replace(direct); };
              addEventListener('popstate', enforce); enforce();
            })();
            """, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        }
        webView = WKWebView(frame: .zero, configuration: config)
        super.init()
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = true
        webView.allowsMagnification = true
        webView.autoresizingMask = [.width, .height]
        observations = [
            webView.observe(\.estimatedProgress, options: [.new]) { [weak self] _, _ in MainActor.assumeIsolated { self?.changed() } },
            webView.observe(\.isLoading, options: [.new]) { [weak self] _, _ in MainActor.assumeIsolated { self?.changed() } },
            webView.observe(\.canGoBack, options: [.new]) { [weak self] _, _ in MainActor.assumeIsolated { self?.changed() } },
            webView.observe(\.canGoForward, options: [.new]) { [weak self] _, _ in MainActor.assumeIsolated { self?.changed() } },
            webView.observe(\.url, options: [.new]) { [weak self] view, _ in
                MainActor.assumeIsolated {
                    if let url = view.url, url.scheme == "https" { self?.lastURL = url }
                    self?.changed()
                }
            }
        ]
        if loadImmediately { load(provider.home) }
    }

    static func configuration(persistent: Bool = true) -> WKWebViewConfiguration {
        let config = WKWebViewConfiguration()
        config.websiteDataStore = persistent ? .default() : .nonPersistent()
        config.preferences.javaScriptCanOpenWindowsAutomatically = false
        config.preferences.isFraudulentWebsiteWarningEnabled = true
        config.preferences.inactiveSchedulingPolicy = .throttle
        config.mediaTypesRequiringUserActionForPlayback = .all
        config.defaultWebpagePreferences.allowsContentJavaScript = true
        let os = ProcessInfo.processInfo.operatingSystemVersion.majorVersion
        let safari = Bundle(url: URL(fileURLWithPath: "/Applications/Safari.app"))?
            .object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String
        config.applicationNameForUserAgent = "Version/\(safari ?? String(os >= 26 ? os : os + 3) + ".0") Safari/605.1.15"
        return config
    }

    private func changed() { onChange?() }
    func report(_ text: String?, error: Bool = false) {
        message = text
        hasError = error
        changed()
    }
    func ensureLoaded() {
        guard !isClosed, !didRequestLoad else { return }
        load(provider.home)
    }
    func load(_ url: URL) {
        guard !isClosed, url.scheme == "https" else { return }
        didRequestLoad = true
        let url = provider.directModeRedirect(for: url) ?? url
        lastURL = url
        report(nil)
        webView.load(URLRequest(url: url))
    }
    func reload() {
        recovery.reset()
        report(nil)
        if webView.url == nil { load(lastURL) } else { webView.reload() }
    }
    func focusComposer() {
        // Focus only a visible composer. Do not change text or dispatch synthetic input.
        webView.evaluateJavaScript("""
        (() => {
          const selectors = ['#prompt-textarea', 'textarea:not([disabled])', '[contenteditable="true"][role="textbox"]', '[contenteditable="true"]'];
          for (const s of selectors) {
            const el = [...document.querySelectorAll(s)].find(e => e.getClientRects().length && e.getAttribute('aria-hidden') !== 'true');
            if (el) { el.focus({preventScroll:true}); return true; }
          }
          return false;
        })()
        """, completionHandler: nil)
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        if action.targetFrame?.isMainFrame == true, let direct = provider.directModeRedirect(for: url) {
            decisionHandler(.cancel)
            load(direct)
            return
        }
        let isUser = action.navigationType == .linkActivated
        switch NavigationPolicy.decision(for: url, isUserAction: isUser) {
        case .block:
            if action.targetFrame?.isMainFrame == true { report("This link cannot open inside OverAI.", error: true) }
            decisionHandler(.cancel)
        case .external:
            NSWorkspace.shared.open(url)
            decisionHandler(.cancel)
        case .web:
            if action.shouldPerformDownload { decisionHandler(.download); return }
            if isUser && action.targetFrame?.isMainFrame == true && url.scheme == "https"
                && !provider.owns(url) && !Self.isAuthenticationHost(url.host) {
                NSWorkspace.shared.open(url)
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }
    }

    private static func isAuthenticationHost(_ host: String?) -> Bool {
        guard let host = host?.lowercased() else { return false }
        return ["accounts.google.com", "appleid.apple.com", "login.microsoftonline.com", "auth.openai.com",
                "auth0.com", "clerk.accounts.dev", "accounts.x.ai", "x.com", "twitter.com"].contains {
            host == $0 || host.hasSuffix("." + $0)
        }
    }

    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse,
                 decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        decisionHandler(response.canShowMIMEType ? .allow : .download)
    }
    func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
        didRequestLoad = true
        navigationGeneration += 1
        stablePage?.cancel()
        attachmentTimeout?.cancel()
        pendingAttachments = nil
        report(nil)
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        report(nil)
        stablePage?.cancel()
        let stable = DispatchWorkItem { [weak self] in self?.recovery.reset() }
        stablePage = stable
        DispatchQueue.main.asyncAfter(deadline: .now() + 30, execute: stable)
        if windowProvider?()?.isKeyWindow == true { focusComposer() }
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        handle(error)
    }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { handle(error) }
    private func handle(_ error: Error) {
        let ns = error as NSError
        guard ns.code != NSURLErrorCancelled, ns.code != 102 else { return }
        report("Couldn't load \(provider.name). Check your connection, then reload.", error: true)
    }
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        stablePage?.cancel()
        guard recovery.consume() else {
            report("This website stopped repeatedly. Reload when you're ready.", error: true)
            return
        }
        report("Website restarted. Unsent text may need to be entered again.", error: true)
        let target = lastURL
        webView.load(URLRequest(url: target))
    }

    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        guard popups.count < 4,
              let url = action.request.url,
              NavigationPolicy.decision(for: url, isUserAction: action.navigationType == .linkActivated) == .web else { return nil }
        let popup = PopupWindowController(provider: provider, configuration: configuration)
        popup.onClose = { [weak self] id in self?.popups.removeAll { $0.id == id } }
        guard popup.show(parent: windowProvider?()) else {
            report("The login window couldn't enable capture exclusion.", error: true)
            return nil
        }
        popups.append(popup)
        return popup.session.webView
    }
    func webViewDidClose(_ webView: WKWebView) { windowProvider?()?.close() }

    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        if let files = pendingAttachments {
            pendingAttachments = nil
            attachmentTimeout?.cancel()
            guard frame.isMainFrame, let url = frame.request.url, provider.owns(url),
                  url.scheme == "https", !parameters.allowsDirectories else { completionHandler(nil); return }
            completionHandler(parameters.allowsMultipleSelection ? files : Array(files.prefix(1)))
            report(nil)
            return
        }
        guard let parent = windowProvider?(), parent.attachedSheet == nil else { completionHandler(nil); return }
        let panel = NSOpenPanel()
        panel.directoryURL = PermissionsController.shared.uploadFolder
        panel.allowsMultipleSelection = parameters.allowsMultipleSelection
        panel.canChooseDirectories = parameters.allowsDirectories
        panel.canChooseFiles = true
        guard CaptureProtection.shared.track(panel) else { completionHandler(nil); return }
        panel.beginSheetModal(for: parent) { result in completionHandler(result == .OK ? panel.urls : nil) }
    }

    func webView(_ webView: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin,
                 initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType,
                 decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        guard frame.isMainFrame, origin.protocol == "https",
              let url = frame.request.url, let page = webView.url,
              MediaAccessPolicy.allows(provider: provider, page: page, frame: url, originHost: origin.host, originPort: origin.port),
              let parent = windowProvider?(), parent.attachedSheet == nil else { decisionHandler(.deny); return }
        let requestGeneration = navigationGeneration
        let alert = NSAlert()
        let description: String = switch type {
        case .camera: "your camera"
        case .microphone: "your microphone"
        case .cameraAndMicrophone: "your camera and microphone"
        @unknown default: "media capture"
        }
        alert.messageText = "Allow \(provider.name) to use \(description)?"
        alert.informativeText = "Only this website receives the media. macOS also controls the app's camera and microphone access."
        alert.addButton(withTitle: "Allow Once")
        alert.addButton(withTitle: "Don't Allow")
        guard CaptureProtection.shared.track(alert.window) else { decisionHandler(.deny); return }
        alert.beginSheetModal(for: parent) { response in
            guard response == .alertFirstButtonReturn else { decisionHandler(.deny); return }
            let media: [AVMediaType] = switch type {
            case .camera: [.video]
            case .microphone: [.audio]
            case .cameraAndMicrophone: [.video, .audio]
            @unknown default: []
            }
            Task { @MainActor in
                guard !media.isEmpty else { decisionHandler(.deny); return }
                var allowed = true
                for item in media {
                    let granted = await AVCaptureDevice.requestAccess(for: item)
                    allowed = allowed && granted
                }
                // A permission prompt may outlive the document that requested it.
                decisionHandler(allowed && self.navigationGeneration == requestGeneration && webView.url == page ? .grant : .deny)
            }
        }
    }

    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        dialog(message: message, confirm: false) { _ in completionHandler() }
    }
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        dialog(message: message, confirm: true, completion: completionHandler)
    }
    func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String,
                 defaultText: String?, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (String?) -> Void) {
        guard let parent = windowProvider?(), parent.attachedSheet == nil else { completionHandler(nil); return }
        let alert = NSAlert()
        alert.messageText = provider.name
        alert.informativeText = String(prompt.prefix(1500))
        let field = NSTextField(string: defaultText ?? "")
        field.frame = NSRect(x: 0, y: 0, width: 300, height: 24)
        alert.accessoryView = field
        alert.addButton(withTitle: "OK")
        alert.addButton(withTitle: "Cancel")
        guard CaptureProtection.shared.track(alert.window) else { completionHandler(nil); return }
        alert.beginSheetModal(for: parent) { result in completionHandler(result == .alertFirstButtonReturn ? field.stringValue : nil) }
    }
    private func dialog(message: String, confirm: Bool, completion: @escaping (Bool) -> Void) {
        guard let parent = windowProvider?(), parent.attachedSheet == nil else { completion(false); return }
        let alert = NSAlert()
        alert.messageText = provider.name
        alert.informativeText = String(message.prefix(1500))
        alert.addButton(withTitle: "OK")
        if confirm { alert.addButton(withTitle: "Cancel") }
        guard CaptureProtection.shared.track(alert.window) else { completion(false); return }
        alert.beginSheetModal(for: parent) { result in completion(result == .alertFirstButtonReturn) }
    }

    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { track(download) }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { track(download) }
    private func track(_ download: WKDownload) {
        downloads[ObjectIdentifier(download)] = download
        download.delegate = self
        report("Choose where to save your download.")
    }
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse,
                  suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        guard let parent = windowProvider?(), parent.attachedSheet == nil else { completionHandler(nil); return }
        let panel = NSSavePanel()
        panel.nameFieldStringValue = NavigationPolicy.safeFilename(suggestedFilename)
        panel.canCreateDirectories = true
        guard CaptureProtection.shared.track(panel) else { completionHandler(nil); return }
        panel.beginSheetModal(for: parent) { [weak self] result in
            completionHandler(result == .OK ? panel.url : nil)
            self?.report(result == .OK ? "Downloading…" : nil)
        }
    }
    func downloadDidFinish(_ download: WKDownload) {
        downloads.removeValue(forKey: ObjectIdentifier(download))
        report("Download saved.")
    }
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        downloads.removeValue(forKey: ObjectIdentifier(download))
        if (error as NSError).code == NSURLErrorCancelled { report(nil) }
        else { report("Download failed. Try downloading again.", error: true) }
    }

    func close() {
        guard !isClosed else { return }
        isClosed = true
        navigationGeneration += 1
        attachmentTimeout?.cancel()
        pendingAttachments = nil
        stablePage?.cancel()
        observations.removeAll()
        let closingPopups = popups
        popups.removeAll()
        closingPopups.forEach { $0.onClose = nil; $0.close() }
        let closingDownloads = Array(downloads.values)
        downloads.removeAll()
        closingDownloads.forEach { $0.cancel { _ in } }
        webView.navigationDelegate = nil
        webView.uiDelegate = nil
        webView.stopLoading()
        onChange = nil
        windowProvider = nil
    }
}

@MainActor final class PopupWindowController: NSWindowController, NSWindowDelegate {
    let id = UUID()
    let session: BrowserSession
    var onClose: ((UUID) -> Void)?

    init(provider: Provider, configuration: WKWebViewConfiguration) {
        session = BrowserSession(provider: provider, configuration: configuration, loadImmediately: false)
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 560, height: 680),
                              styleMask: [.titled, .closable, .resizable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "\(provider.name) — OverAI"
        window.minSize = NSSize(width: 400, height: 400)
        window.isReleasedWhenClosed = false
        window.contentView = session.webView
        super.init(window: window)
        window.delegate = self
        session.windowProvider = { [weak window] in window }
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }
    func show(parent: NSWindow?) -> Bool {
        guard let window, CaptureProtection.shared.track(window) else { return false }
        window.center()
        if let parent { parent.addChildWindow(window, ordered: .above) }
        window.makeKeyAndOrderFront(nil)
        return true
    }
    func windowWillClose(_ notification: Notification) {
        session.close()
        onClose?(id)
    }
}

@MainActor final class SessionStore {
    private var sessions: [Provider: BrowserSession] = [:]
    private let persistent: Bool
    init(persistent: Bool = true) { self.persistent = persistent }
    var count: Int { sessions.count }
    func session(for provider: Provider, loadImmediately: Bool = true) -> BrowserSession {
        if let existing = sessions[provider] { return existing }
        let session = BrowserSession(provider: provider, configuration: BrowserSession.configuration(persistent: persistent), loadImmediately: loadImmediately)
        sessions[provider] = session
        return session
    }
    func setBackgroundThrottling(_ enabled: Bool) {
        for session in sessions.values {
            session.webView.configuration.preferences.inactiveSchedulingPolicy = enabled ? .throttle : .none
        }
    }
    func retainOnly(_ websites: [Provider]) {
        let removed = sessions.keys.filter { !websites.contains($0) }
        for key in removed { sessions.removeValue(forKey: key)?.close() }
    }
    func close() { sessions.values.forEach { $0.close() }; sessions.removeAll() }
}
