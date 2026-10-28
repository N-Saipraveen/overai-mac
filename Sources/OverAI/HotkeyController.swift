import AppKit
import KeyboardShortcuts

extension KeyboardShortcuts.Name {
    static let toggleOverlay = Self("toggleOverlay", initial: .init(.g, modifiers: [.command]))
}

@MainActor final class HotkeyController {
    private var wakeObservers: [NSObjectProtocol] = []
    private let settings: AppSettings
    private var wakeRecovery: DispatchWorkItem?

    init(settings: AppSettings, toggle: @escaping () -> Void) {
        self.settings = settings
        KeyboardShortcuts.onKeyUp(for: .toggleOverlay) { toggle() }
        refreshLabel()
        let center = NSWorkspace.shared.notificationCenter
        for name in [NSWorkspace.didWakeNotification, NSWorkspace.screensDidWakeNotification,
                     NSWorkspace.sessionDidBecomeActiveNotification] {
            wakeObservers.append(center.addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { self?.recoverAfterWake() }
            })
        }
    }

    func refreshLabel() {
        settings.hotkeySummary = KeyboardShortcuts.getShortcut(for: .toggleOverlay)?.description ?? "No shortcut set"
    }

    func recoverAfterWake() {
        wakeRecovery?.cancel()
        let work = DispatchWorkItem { [weak self] in
            MainActor.assumeIsolated {
                KeyboardShortcuts.disable(.toggleOverlay)
                KeyboardShortcuts.enable(.toggleOverlay)
                self?.refreshLabel()
            }
        }
        wakeRecovery = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6, execute: work)
    }

    func stop() {
        wakeRecovery?.cancel()
        wakeObservers.forEach { NSWorkspace.shared.notificationCenter.removeObserver($0) }
        wakeObservers.removeAll()
        KeyboardShortcuts.removeAllHandlers()
        KeyboardShortcuts.disable(.toggleOverlay)
    }
}
