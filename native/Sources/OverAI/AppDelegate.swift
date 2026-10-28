import AppKit
import WebKit
import OverAICore
import KeyboardShortcuts

@MainActor final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    let settings = AppSettings()
    private(set) var overlay: OverlayController!
    private var preferences: SettingsController?
    private var hotkeys: HotkeyController?
    private var statusItem: NSStatusItem?
    private var keyMonitor: Any?
    private var memoryMonitor: MemoryPressureMonitor?
    private var startup: StartupController?
    #if OVERAI_VALIDATION
    private var selfTest: SelfTestRunner?
    private var uploadLab: UploadLab?
    #endif
    private var isTerminating = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        #if OVERAI_VALIDATION
        if CommandLine.arguments.contains("--upload-lab") {
            uploadLab = UploadLab()
            return
        }
        if CommandLine.arguments.contains("--self-test") {
            selfTest = SelfTestRunner()
            selfTest?.start()
            return
        }
        if CommandLine.arguments.contains("--capture-probe") {
            selfTest = SelfTestRunner(captureProbe: true)
            selfTest?.start()
            return
        }
        if CommandLine.arguments.contains("--storage-probe") {
            selfTest = SelfTestRunner(storageProbe: true)
            selfTest?.start()
            return
        }
        #endif
        installMainMenu()
        createOverlay()
        installStatusItem()
        hotkeys = HotkeyController(settings: settings) { [weak self] in self?.toggleOverlay() }
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            if let self, event.window === self.overlay.panel,
               self.overlay.panel.attachedSheet == nil,
               event.modifierFlags.intersection([.command, .option, .control, .shift]).isEmpty,
               self.overlay.handleTrayKey(event.keyCode) { return nil }
            guard let self, event.keyCode == 53,
                  event.modifierFlags.intersection([.command, .option, .control, .shift]).isEmpty,
                  event.window === self.overlay.panel, !event.isARepeat else { return event }
            if let input = self.overlay.panel.firstResponder as? NSTextInputClient, input.hasMarkedText() { return event }
            if self.overlay.panel.attachedSheet != nil { return event }
            if self.overlay.toolbarTrayIsVisible { self.overlay.dismissToolbarTray(); return nil }
            guard self.settings.escapeHides else { return event }
            self.overlay.hide()
            return nil
        }
        memoryMonitor = MemoryPressureMonitor { [weak self] in
            // Never destroy an unknown website state in response to pressure.
            self?.overlay.store.setBackgroundThrottling(true)
        }
        if !settings.hasChosenStartup {
            startup = StartupController(settings: settings) { [weak self] in
                guard let self else { return }
                self.startup = nil
                if self.settings.showOnLaunch { self.showOverlay() }
            }
            _ = startup?.show()
        } else if settings.showOnLaunch { showOverlay() }
    }

    private func createOverlay() {
        overlay = OverlayController(settings: settings)
        overlay.onSettings = { [weak self] in self?.showSettings() }
        overlay.onQuit = { [weak self] in self?.quit() }
    }

    private func installMainMenu() {
        let menu = NSMenu()
        let appItem = NSMenuItem()
        let appMenu = NSMenu(title: "OverAI")
        add("Show / Hide OverAI", action: #selector(toggleOverlay), key: "", to: appMenu).setShortcut(for: .toggleOverlay)
        appMenu.delegate = self
        appMenu.addItem(.separator())
        add("Settings…", action: #selector(showSettings), key: ",", to: appMenu)
        appMenu.addItem(.separator())
        add("Hide Overlay", action: #selector(hideOverlay), key: "h", to: appMenu)
        add("Quit OverAI", action: #selector(quit), key: "q", to: appMenu)
        appItem.submenu = appMenu
        menu.addItem(appItem)
        let editItem = NSMenuItem()
        let edit = NSMenu(title: "Edit")
        for (title, action, key) in [("Undo", "undo:", "z"), ("Redo", "redo:", "Z"),
                                     ("Cut", "cut:", "x"), ("Copy", "copy:", "c"),
                                     ("Paste", "paste:", "v"), ("Select All", "selectAll:", "a")] {
            edit.addItem(NSMenuItem(title: title, action: Selector(action), keyEquivalent: key))
        }
        editItem.submenu = edit
        menu.addItem(editItem)
        let websiteItem = NSMenuItem()
        let website = NSMenu(title: "Website")
        add("Reload", action: #selector(reload), key: "r", to: website)
        add("Hide Overlay", action: #selector(hideOverlay), key: "w", to: website)
        websiteItem.submenu = website
        menu.addItem(websiteItem)
        NSApp.mainMenu = menu
    }

    private func installStatusItem() {
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        item.button?.image = NSImage(systemSymbolName: "sparkles", accessibilityDescription: "OverAI")
        item.button?.image?.size = NSSize(width: 17, height: 17)
        item.button?.setAccessibilityLabel("OverAI menu")
        item.button?.image?.isTemplate = true
        item.button?.toolTip = "OverAI — your AI websites"
        let menu = NSMenu()
        menu.delegate = self
        add("Show / Hide OverAI", action: #selector(toggleOverlay), key: "", to: menu).setShortcut(for: .toggleOverlay)
        menu.addItem(.separator())
        for provider in settings.websites {
            let entry = add(provider.name, action: #selector(selectProvider(_:)), key: "", to: menu)
            entry.representedObject = provider.rawValue
            entry.image = ProviderArtwork.icon(for: provider)
        }
        menu.addItem(.separator())
        add("Settings…", action: #selector(showSettings), key: ",", to: menu)
        add("App Status…", action: #selector(showAppStatus), key: "", to: menu)
        menu.addItem(.separator())
        add("Quit OverAI", action: #selector(quit), key: "q", to: menu)
        item.menu = menu
        statusItem = item
    }

    @discardableResult private func add(_ title: String, action: Selector, key: String, to menu: NSMenu) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
        item.target = self
        menu.addItem(item)
        return item
    }
    private func showOverlay() {
        guard !settings.isClearingData else { return }
        _ = overlay.show()
    }
    @objc func toggleOverlay() {
        if startup != nil { _ = startup?.show(); return }
        if overlay.panel.isVisible { overlay.hide() } else { showOverlay() }
    }
    @objc func hideOverlay() { overlay.hide() }
    @objc func reload() {
        guard !settings.isClearingData else { return }
        overlay.current.reload()
    }
    @objc private func selectProvider(_ sender: NSMenuItem) {
        guard !settings.isClearingData else { return }
        guard let id = sender.representedObject as? String, let provider = settings.websites.first(where: { $0.id == id }) else { return }
        overlay.select(provider)
        showOverlay()
    }
    @objc func showSettings() { openSettings() }
    private func openSettings(page: SettingsPage? = nil) {
        if preferences == nil {
            preferences = SettingsController(settings: settings, onShortcutChange: { [weak self] in self?.hotkeys?.refreshLabel() },
                                             clearData: { [weak self] in self?.clearData() })
        }
        preferences?.show(page: page)
    }
    @objc private func showAppStatus() { openSettings(page: .status) }
    // Called only after the protected Settings confirmation is accepted.
    private func clearData() {
        guard !settings.isClearingData else { return }
        settings.isClearingData = true
        let wasVisible = overlay.panel.isVisible
        overlay.close()
        settings.sessionCount = 0
        WKWebsiteDataStore.default().removeData(ofTypes: WKWebsiteDataStore.allWebsiteDataTypes(), modifiedSince: .distantPast) { [weak self] in
            Task { @MainActor in
                guard let self else { return }
                self.createOverlay()
                self.settings.isClearingData = false
                if wasVisible { self.showOverlay() }
            }
        }
    }
    @objc func quit() { NSApp.terminate(nil) }
    func menuWillOpen(_ menu: NSMenu) {
        if menu === statusItem?.menu {
            for entry in menu.items where entry.representedObject is String { menu.removeItem(entry) }
            let insertion = 2
            for (offset, provider) in settings.websites.enumerated() {
                let entry = NSMenuItem(title: provider.name, action: #selector(selectProvider(_:)), keyEquivalent: "")
                entry.target = self
                entry.representedObject = provider.id
                entry.image = ProviderArtwork.icon(for: provider)
                menu.insertItem(entry, at: insertion + offset)
            }
        }
        if menu.items.first?.action == #selector(toggleOverlay) {
            menu.items.first?.title = overlay?.panel.isVisible == true ? "Hide OverAI" : "Show OverAI"
        }
        for entry in menu.items {
            if let id = entry.representedObject as? String {
                entry.state = id == settings.selectedProvider.rawValue ? .on : .off
            }
        }
        KeyboardShortcuts.disable(.toggleOverlay)
    }
    func menuDidClose(_ menu: NSMenu) { KeyboardShortcuts.enable(.toggleOverlay) }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if let startup { _ = startup.show() }
        else if overlay != nil && !settings.isClearingData { showOverlay() }
        return true
    }
    func applicationWillTerminate(_ notification: Notification) {
        PermissionsController.shared.stopAccessingFolder()
        guard !isTerminating else { return }
        isTerminating = true
        hotkeys?.stop()
        if let keyMonitor { NSEvent.removeMonitor(keyMonitor) }
        memoryMonitor = nil
        overlay?.close()
        if let statusItem { NSStatusBar.system.removeStatusItem(statusItem) }
    }
}
