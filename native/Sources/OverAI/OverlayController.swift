import AppKit
import Combine
import QuartzCore
import OverAICore

final class OverlayPanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}

final class TrayDismissView: NSView {
    var onDismiss: (() -> Void)?
    override func mouseDown(with event: NSEvent) { onDismiss?() }
}

final class ToolbarCardView: NSView {
    override var wantsUpdateLayer: Bool { true }
    override func updateLayer() {
        layer?.backgroundColor = NSColor.windowBackgroundColor.cgColor
        layer?.borderColor = NSColor.separatorColor.cgColor
    }
    override func viewDidChangeEffectiveAppearance() {
        super.viewDidChangeEffectiveAppearance()
        needsDisplay = true
    }
}

@MainActor final class OverlayController: NSObject, NSWindowDelegate {
    let panel: OverlayPanel
    let store: SessionStore
    private(set) var current: BrowserSession!
    var onSettings: (() -> Void)?
    var onQuit: (() -> Void)?
    private let settings: AppSettings
    private let root = NSVisualEffectView()
    private let header = FileDropView()
    private let browserContainer = NSView()
    private let providerPicker = NSButton()
    private let trayOverlay = TrayDismissView()
    private let trayCard = ToolbarCardView()
    private let trayItems = NSStackView()
    private let trayScroll = NSScrollView()
    private var trayHeight: NSLayoutConstraint!
    private var trayProviders: [Provider] = []
    private var activeTray: String?
    var toolbarTrayIsVisible: Bool { !trayOverlay.isHidden }
    var toolbarTraySharesProtectedWindow: Bool { trayCard.window === panel && trayItems.window === panel }
    var toolbarTrayContentView: NSView { trayCard }
    private let backButton = NSButton()
    private let forwardButton = NSButton()
    private let reloadButton = NSButton()
    private let statusLabel = NSTextField(labelWithString: "")
    private let opacityControl = NSSegmentedControl()
    private let errorBanner = NSVisualEffectView()
    private let retryButton = NSButton(title: "Retry", target: nil, action: nil)
    private let progress = NSProgressIndicator()
    private var bindings: Set<AnyCancellable> = []
    private var saveFrameWork: DispatchWorkItem?
    private let loadWebsites: Bool

    init(settings: AppSettings, loadWebsites: Bool = true) {
        self.settings = settings
        self.loadWebsites = loadWebsites
        store = SessionStore(persistent: loadWebsites)
        panel = OverlayPanel(contentRect: NSRect(x: 0, y: 0, width: 620, height: 720),
                             styleMask: [.borderless, .resizable, .nonactivatingPanel], backing: .buffered, defer: false)
        super.init()
        panel.title = "OverAI"
        panel.isReleasedWhenClosed = false
        panel.isFloatingPanel = true
        panel.hidesOnDeactivate = false
        panel.becomesKeyOnlyIfNeeded = false
        panel.worksWhenModal = true
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .ignoresCycle]
        panel.minSize = NSSize(width: 460, height: 400)
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.delegate = self
        panel.alphaValue = settings.opacity
        buildInterface()
        header.toolTip = "Drop files or screenshots on this toolbar to attach them to the current website."
        restoreFrame()
        updateCapture()
        select(settings.selectedProvider)
        settings.$websites.dropFirst().sink { [weak self] websites in
            guard let self else { return }
            self.dismissToolbarTray()
            if !websites.contains(self.current.provider) { self.select(websites.first!) }
            self.store.retainOnly(websites)
            self.settings.sessionCount = self.store.count
        }.store(in: &bindings)
        settings.$opacity.sink { [weak self] value in
            self?.panel.alphaValue = value
            self?.updateOpacityControls(value)
        }.store(in: &bindings)
        settings.$throttleBackground.sink { [weak self] in self?.store.setBackgroundThrottling($0) }.store(in: &bindings)
    }

    private func buildInterface() {
        root.material = .titlebar
        root.blendingMode = .behindWindow
        root.state = .active
        root.wantsLayer = true
        root.layer?.cornerRadius = 16
        root.layer?.masksToBounds = true
        root.layer?.borderWidth = 0.5
        root.layer?.borderColor = NSColor.separatorColor.withAlphaComponent(0.45).cgColor
        panel.contentView = root
        [header, browserContainer].forEach { $0.translatesAutoresizingMaskIntoConstraints = false; root.addSubview($0) }

        let hide = iconButton("xmark.circle.fill", label: "Hide OverAI", action: #selector(hideAction))
        hide.contentTintColor = .tertiaryLabelColor
        configure(backButton, symbol: "chevron.left", label: "Back", action: #selector(goBack))
        configure(forwardButton, symbol: "chevron.right", label: "Forward", action: #selector(goForward))
        configure(reloadButton, symbol: "arrow.clockwise", label: "Reload website (⌘R)", action: #selector(reload))
        let more = iconButton("ellipsis", label: "More options", action: #selector(showMore(_:)))
        opacityControl.segmentCount = 2
        opacityControl.trackingMode = .momentary
        opacityControl.segmentStyle = .rounded
        opacityControl.controlSize = .regular
        opacityControl.target = self
        opacityControl.action = #selector(changeOpacity(_:))
        opacityControl.setAccessibilityLabel("Window opacity")
        for (index, symbol) in ["minus", "plus"].enumerated() {
            opacityControl.setImage(NSImage(systemSymbolName: symbol, accessibilityDescription: index == 0 ? "Decrease opacity" : "Increase opacity"), forSegment: index)
            opacityControl.setWidth(27, forSegment: index)
        }
        providerPicker.isBordered = true
        providerPicker.bezelStyle = .rounded
        providerPicker.font = .systemFont(ofSize: 13, weight: .semibold)
        providerPicker.target = self
        providerPicker.action = #selector(toggleProviderPicker)
        providerPicker.image = NSImage(systemSymbolName: "chevron.down", accessibilityDescription: nil)
        providerPicker.imagePosition = .imageTrailing
        providerPicker.setAccessibilityLabel("AI website")
        let leading = NSStackView(views: [hide, backButton, forwardButton, reloadButton])
        leading.spacing = 2
        leading.setCustomSpacing(8, after: hide)
        let navigation = NSStackView(views: [opacityControl, more])
        navigation.spacing = 10
        [leading, providerPicker, navigation].forEach { $0.translatesAutoresizingMaskIntoConstraints = false; header.addSubview($0) }

        progress.style = .bar
        progress.isIndeterminate = false
        progress.minValue = 0
        progress.maxValue = 1
        progress.isHidden = true
        progress.translatesAutoresizingMaskIntoConstraints = false
        root.addSubview(progress)

        errorBanner.material = .headerView
        errorBanner.blendingMode = .withinWindow
        errorBanner.state = .active
        errorBanner.isHidden = true
        errorBanner.translatesAutoresizingMaskIntoConstraints = false
        root.addSubview(errorBanner)
        statusLabel.font = .systemFont(ofSize: 12)
        statusLabel.textColor = .secondaryLabelColor
        statusLabel.lineBreakMode = .byTruncatingTail
        statusLabel.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        retryButton.target = self
        retryButton.action = #selector(reload)
        retryButton.bezelStyle = .rounded
        retryButton.controlSize = .small
        retryButton.font = .systemFont(ofSize: 12)
        retryButton.translatesAutoresizingMaskIntoConstraints = false
        [statusLabel, retryButton].forEach { errorBanner.addSubview($0) }
        let divider = NSBox()
        divider.boxType = .separator
        divider.translatesAutoresizingMaskIntoConstraints = false
        root.addSubview(divider)
        NSLayoutConstraint.activate([
            header.topAnchor.constraint(equalTo: root.topAnchor), header.leadingAnchor.constraint(equalTo: root.leadingAnchor),
            header.trailingAnchor.constraint(equalTo: root.trailingAnchor), header.heightAnchor.constraint(equalToConstant: 48),
            leading.leadingAnchor.constraint(equalTo: header.leadingAnchor, constant: 10), leading.centerYAnchor.constraint(equalTo: header.centerYAnchor),
            providerPicker.leadingAnchor.constraint(greaterThanOrEqualTo: leading.trailingAnchor, constant: 10),
            providerPicker.centerXAnchor.constraint(equalTo: header.centerXAnchor),
            providerPicker.centerYAnchor.constraint(equalTo: header.centerYAnchor), providerPicker.widthAnchor.constraint(equalToConstant: 140),
            navigation.trailingAnchor.constraint(equalTo: header.trailingAnchor, constant: -12), navigation.centerYAnchor.constraint(equalTo: header.centerYAnchor),
            providerPicker.trailingAnchor.constraint(lessThanOrEqualTo: navigation.leadingAnchor, constant: -10),
            browserContainer.topAnchor.constraint(equalTo: header.bottomAnchor), browserContainer.leadingAnchor.constraint(equalTo: root.leadingAnchor),
            browserContainer.trailingAnchor.constraint(equalTo: root.trailingAnchor), browserContainer.bottomAnchor.constraint(equalTo: root.bottomAnchor),
            errorBanner.topAnchor.constraint(equalTo: header.bottomAnchor), errorBanner.leadingAnchor.constraint(equalTo: root.leadingAnchor),
            errorBanner.trailingAnchor.constraint(equalTo: root.trailingAnchor), errorBanner.heightAnchor.constraint(equalToConstant: 44),
            statusLabel.leadingAnchor.constraint(equalTo: errorBanner.leadingAnchor, constant: 16), statusLabel.centerYAnchor.constraint(equalTo: errorBanner.centerYAnchor),
            retryButton.leadingAnchor.constraint(equalTo: statusLabel.trailingAnchor, constant: 12), retryButton.centerYAnchor.constraint(equalTo: errorBanner.centerYAnchor),
            retryButton.trailingAnchor.constraint(equalTo: errorBanner.trailingAnchor, constant: -12),
            divider.leadingAnchor.constraint(equalTo: root.leadingAnchor), divider.trailingAnchor.constraint(equalTo: root.trailingAnchor),
            divider.topAnchor.constraint(equalTo: header.bottomAnchor), divider.heightAnchor.constraint(equalToConstant: 1),
            progress.leadingAnchor.constraint(equalTo: root.leadingAnchor), progress.trailingAnchor.constraint(equalTo: root.trailingAnchor),
            progress.topAnchor.constraint(equalTo: header.bottomAnchor), progress.heightAnchor.constraint(equalToConstant: 2)
        ])
        // AppKit menus/popovers own separate windows. Keep every toolbar choice in this
        // panel's content hierarchy so its existing capture exclusion covers the choices.
        trayOverlay.isHidden = true
        trayOverlay.onDismiss = { [weak self] in self?.dismissToolbarTray() }
        trayOverlay.translatesAutoresizingMaskIntoConstraints = false
        root.addSubview(trayOverlay)
        trayCard.wantsLayer = true
        trayCard.layer?.cornerRadius = 12
        trayCard.layer?.borderWidth = 0.5
        trayCard.layer?.masksToBounds = true
        trayCard.translatesAutoresizingMaskIntoConstraints = false
        trayOverlay.addSubview(trayCard)
        trayItems.orientation = .vertical
        trayItems.alignment = .leading
        trayItems.spacing = 4
        trayItems.translatesAutoresizingMaskIntoConstraints = false
        trayScroll.drawsBackground = false
        trayScroll.hasVerticalScroller = true
        trayScroll.autohidesScrollers = true
        trayScroll.translatesAutoresizingMaskIntoConstraints = false
        trayCard.addSubview(trayScroll)
        trayScroll.documentView = trayItems
        trayHeight = trayCard.heightAnchor.constraint(equalToConstant: 100)
        trayHeight.priority = .defaultHigh
        NSLayoutConstraint.activate([
            trayOverlay.topAnchor.constraint(equalTo: header.bottomAnchor),
            trayOverlay.bottomAnchor.constraint(equalTo: root.bottomAnchor),
            trayOverlay.leadingAnchor.constraint(equalTo: root.leadingAnchor),
            trayOverlay.trailingAnchor.constraint(equalTo: root.trailingAnchor),
            trayCard.topAnchor.constraint(equalTo: trayOverlay.topAnchor, constant: 8),
            trayCard.centerXAnchor.constraint(equalTo: trayOverlay.centerXAnchor),
            trayCard.widthAnchor.constraint(equalToConstant: 280),
            trayHeight,
            trayCard.bottomAnchor.constraint(lessThanOrEqualTo: trayOverlay.bottomAnchor, constant: -8),
            trayScroll.topAnchor.constraint(equalTo: trayCard.topAnchor, constant: 10),
            trayScroll.bottomAnchor.constraint(equalTo: trayCard.bottomAnchor, constant: -10),
            trayScroll.leadingAnchor.constraint(equalTo: trayCard.leadingAnchor, constant: 10),
            trayScroll.trailingAnchor.constraint(equalTo: trayCard.trailingAnchor, constant: -10),
            trayItems.topAnchor.constraint(equalTo: trayScroll.contentView.topAnchor),
            trayItems.leadingAnchor.constraint(equalTo: trayScroll.contentView.leadingAnchor),
            trayItems.widthAnchor.constraint(equalTo: trayScroll.contentView.widthAnchor)
        ])
    }

    private func iconButton(_ symbol: String, label: String, action: Selector) -> NSButton {
        let button = NSButton()
        configure(button, symbol: symbol, label: label, action: action)
        return button
    }
    private func configure(_ button: NSButton, symbol: String, label: String, action: Selector) {
        button.image = NSImage(systemSymbolName: symbol, accessibilityDescription: label)
        button.symbolConfiguration = NSImage.SymbolConfiguration(pointSize: 13, weight: .medium)
        button.imagePosition = .imageOnly
        button.isBordered = false
        button.bezelStyle = .texturedRounded
        button.contentTintColor = .secondaryLabelColor
        button.target = self
        button.action = action
        button.toolTip = label
        button.setAccessibilityLabel(label)
        button.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([button.widthAnchor.constraint(equalToConstant: 27), button.heightAnchor.constraint(equalToConstant: 28)])
    }

    func select(_ provider: Provider) {
        dismissToolbarTray()
        guard current?.provider != provider else { return }
        current?.onChange = nil
        current?.webView.removeFromSuperview()
        let session = store.session(for: provider, loadImmediately: loadWebsites && panel.isVisible)
        if loadWebsites && panel.isVisible { session.ensureLoaded() }
        current = session
        // Capture the destination when the drop begins, even if a promised file arrives later.
        header.onFiles = { [weak self, weak session] urls in
            guard let self, let session, self.current === session else { return }
            self.dismissToolbarTray()
            session.requestAttachments(urls)
        }
        header.onFailure = { [weak session] message in session?.report(message, error: true) }
        session.windowProvider = { [weak panel] in panel }
        session.onChange = { [weak self] in self?.updateStatus() }
        session.webView.frame = browserContainer.bounds
        browserContainer.addSubview(session.webView)
        session.webView.autoresizingMask = [.width, .height]
        settings.selectedProvider = provider
        settings.sessionCount = store.count
        store.setBackgroundThrottling(settings.throttleBackground)
        providerPicker.title = provider.name
        providerPicker.image = ProviderArtwork.icon(for: provider)
        providerPicker.imagePosition = .imageLeading
        updateStatus()
        fadeIn(session.webView)
        if panel.isKeyWindow { panel.makeFirstResponder(session.webView); session.focusComposer() }
    }

    private func updateStatus() {
        guard let current else { return }
        backButton.isEnabled = current.webView.canGoBack
        forwardButton.isEnabled = current.webView.canGoForward
        progress.doubleValue = current.webView.estimatedProgress
        progress.isHidden = !current.webView.isLoading || current.webView.estimatedProgress >= 1
        statusLabel.stringValue = current.hasError ? (current.message ?? "This website couldn't load.") : ""
        statusLabel.toolTip = current.message
        errorBanner.isHidden = !current.hasError
    }

    @discardableResult func updateCapture() -> Bool {
        let ready = CaptureProtection.shared.track(panel)
        settings.captureReady = ready
        settings.captureSummary = CaptureProtection.shared.lastResult
        return ready
    }

    @discardableResult func show() -> Bool {
        if settings.followPointer, let screen = NSScreen.screens.first(where: { $0.frame.contains(NSEvent.mouseLocation) }),
           screen != panel.screen {
            let rect = screen.visibleFrame
            panel.setFrameOrigin(NSPoint(x: rect.midX - panel.frame.width / 2, y: rect.midY - panel.frame.height / 2))
        }
        guard updateCapture() else {
            let alert = NSAlert()
            alert.messageText = "OverAI couldn't enable capture exclusion"
            alert.informativeText = "The chat window will stay hidden. \(settings.captureSummary)"
            alert.addButton(withTitle: "OK")
            alert.runModal()
            return false
        }
        if loadWebsites { current.ensureLoaded() }
        panel.alphaValue = settings.opacity
        panel.makeKeyAndOrderFront(nil)
        panel.makeFirstResponder(current.webView)
        current.focusComposer()
        return true
    }
    func hide() { dismissToolbarTray(); saveFrame(); panel.orderOut(nil) }
    func toggle() { if panel.isVisible { hide() } else { _ = show() } }

    @objc private func hideAction() { hide() }
    @objc func reload() { current.reload() }
    @objc func goBack() { if current.webView.canGoBack { current.webView.goBack() } }
    @objc func goForward() { if current.webView.canGoForward { current.webView.goForward() } }
    @objc private func providerChanged(_ sender: NSButton) {
        guard trayProviders.indices.contains(sender.tag) else { return }
        select(trayProviders[sender.tag])
    }
    /// A short compositor animation; no snapshots, timers, or extra web views.
    private func fadeIn(_ view: NSView) {
        view.layer?.removeAnimation(forKey: "overaiReveal")
        guard !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion, panel.isVisible else { return }
        view.wantsLayer = true
        let animation = CABasicAnimation(keyPath: "opacity")
        animation.fromValue = 0
        animation.toValue = 1
        animation.duration = 0.12
        animation.timingFunction = CAMediaTimingFunction(name: .easeOut)
        view.layer?.add(animation, forKey: "overaiReveal")
    }

    func handleTrayKey(_ code: UInt16) -> Bool {
        guard toolbarTrayIsVisible else { return false }
        let buttons = trayItems.arrangedSubviews.compactMap { $0 as? NSButton }
        guard !buttons.isEmpty else { return false }
        let index = buttons.firstIndex { $0 === panel.firstResponder } ?? -1
        switch code {
        case 125, 126, 48:
            let delta = code == 126 ? -1 : 1
            let next = (index + delta + buttons.count) % buttons.count
            panel.makeFirstResponder(buttons[next])
            trayItems.scrollToVisible(buttons[next].frame)
        case 36, 76, 49:
            guard index >= 0 else { return false }
            buttons[index].performClick(nil)
        default: return false
        }
        return true
    }

    func dismissToolbarTray() {
        if toolbarTrayIsVisible { panel.makeFirstResponder(current?.webView) }
        trayCard.layer?.removeAnimation(forKey: "overaiReveal")
        trayOverlay.isHidden = true
        activeTray = nil
    }
    private func prepareTray(_ name: String) -> Bool {
        if activeTray == name { dismissToolbarTray(); return false }
        guard updateCapture() else { hide(); return false }
        trayItems.arrangedSubviews.forEach { trayItems.removeArrangedSubview($0); $0.removeFromSuperview() }
        activeTray = name
        trayOverlay.isHidden = false
        fadeIn(trayCard)
        return true
    }
    private func addTrayButton(_ title: String, symbol: String, action: Selector, tag: Int = 0) {
        let button = NSButton(title: title, target: self, action: action)
        button.image = NSImage(systemSymbolName: symbol, accessibilityDescription: nil)
        button.imagePosition = .imageLeading
        button.alignment = .left
        button.bezelStyle = .recessed
        button.showsBorderOnlyWhileMouseInside = true
        button.font = .systemFont(ofSize: 13)
        button.tag = tag
        button.focusRingType = .exterior
        button.translatesAutoresizingMaskIntoConstraints = false
        trayItems.addArrangedSubview(button)
        trayHeight.constant = CGFloat(trayItems.arrangedSubviews.count * 36 + 16)
        NSLayoutConstraint.activate([
            button.widthAnchor.constraint(equalTo: trayItems.widthAnchor),
            button.heightAnchor.constraint(equalToConstant: 32)
        ])
    }
    @objc func toggleProviderPicker() {
        guard prepareTray("providers") else { return }
        trayProviders = settings.websites
        for (index, provider) in trayProviders.enumerated() {
            let selected = provider == current.provider
            addTrayButton(provider.name + (selected ? "  ✓" : ""), symbol: provider.symbol,
                          action: #selector(providerChanged(_:)), tag: index)
            (trayItems.arrangedSubviews.last as? NSButton)?.image = ProviderArtwork.icon(for: provider)
            if let button = trayItems.arrangedSubviews.last as? NSButton, selected {
                button.state = .on
                button.showsBorderOnlyWhileMouseInside = false
                panel.makeFirstResponder(button)
            }
            trayItems.arrangedSubviews.last?.setAccessibilityLabel(provider.name + (selected ? ", selected" : ""))
        }
    }
    private func updateOpacityControls(_ value: Double) {
        opacityControl.setEnabled(value > 0.25, forSegment: 0)
        opacityControl.setEnabled(value < 1, forSegment: 1)
        let percent = Int((value * 100).rounded())
        opacityControl.setToolTip("Decrease opacity · \(percent)%", forSegment: 0)
        opacityControl.setToolTip("Increase opacity · \(percent)%", forSegment: 1)
    }
    @objc private func changeOpacity(_ sender: NSSegmentedControl) {
        let delta = sender.selectedSegment == 0 ? -0.1 : 0.1
        settings.opacity = min(1, max(0.25, ((settings.opacity + delta) * 100).rounded() / 100))
    }
    @objc func showMore(_ sender: NSButton) {
        guard prepareTray("more") else { return }
        for (title, symbol, action) in [("Settings…", "gearshape", #selector(settingsAction)),
                                       ("Open page in browser", "safari", #selector(openInBrowser)),
                                       ("Provider home", "house", #selector(goHome)),
                                       ("Quit OverAI", "power", #selector(quitAction))] {
            addTrayButton(title, symbol: symbol, action: action)
        }
        panel.makeFirstResponder(trayItems.arrangedSubviews.first)
    }
    @objc private func settingsAction() { dismissToolbarTray(); onSettings?() }
    @objc private func quitAction() { dismissToolbarTray(); onQuit?() }
    @objc func openInBrowser() {
        dismissToolbarTray()
        let url = current.webView.url ?? current.provider.home
        if url.scheme == "https" { NSWorkspace.shared.open(url) }
    }
    @objc func goHome() {
        dismissToolbarTray()
        let alert = NSAlert()
        alert.messageText = "Open \(current.provider.name)'s home page?"
        alert.informativeText = "This navigates away from your current page. Unsent text may be lost."
        alert.addButton(withTitle: "Open Home")
        alert.addButton(withTitle: "Cancel")
        guard CaptureProtection.shared.track(alert.window), panel.attachedSheet == nil else { return }
        alert.beginSheetModal(for: panel) { [weak self] response in
            guard let self, response == .alertFirstButtonReturn else { return }
            self.current.load(self.current.provider.home)
        }
    }

    private func restoreFrame() {
        if let saved = settings.defaults.string(forKey: "windowFrame") {
            let frame = NSRectFromString(saved)
            if frame.width.isFinite && frame.height.isFinite && frame.minX.isFinite && frame.minY.isFinite &&
                frame.width >= 460 && frame.height >= 400 && NSScreen.screens.contains(where: { $0.visibleFrame.intersects(frame) }) {
                let screen = NSScreen.screens.first(where: { $0.visibleFrame.intersects(frame) })!
                var fitted = frame
                fitted.size.width = min(frame.width, screen.visibleFrame.width)
                fitted.size.height = min(frame.height, screen.visibleFrame.height)
                fitted.origin.x = min(max(fitted.minX, screen.visibleFrame.minX), screen.visibleFrame.maxX - fitted.width)
                fitted.origin.y = min(max(fitted.minY, screen.visibleFrame.minY), screen.visibleFrame.maxY - fitted.height)
                panel.setFrame(fitted, display: false)
                return
            }
        }
        panel.center()
    }
    private func saveFrame() { settings.defaults.set(NSStringFromRect(panel.frame), forKey: "windowFrame") }
    private func scheduleFrameSave() {
        saveFrameWork?.cancel()
        let work = DispatchWorkItem { [weak self] in self?.saveFrame() }
        saveFrameWork = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3, execute: work)
    }
    func windowDidMove(_ notification: Notification) { scheduleFrameSave() }
    func windowDidResignKey(_ notification: Notification) { dismissToolbarTray() }
    // CaptureProtection already observes resizing and reapplies the exclusion.
    func windowDidResize(_ notification: Notification) { scheduleFrameSave() }
    func windowShouldClose(_ sender: NSWindow) -> Bool { hide(); return false }
    func close() {
        header.cleanUp()
        saveFrameWork?.cancel()
        saveFrame()
        store.close()
        panel.delegate = nil
        panel.close()
    }
}
