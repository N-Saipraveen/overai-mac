import AppKit
import SwiftUI

@MainActor final class StartupController: NSWindowController {
    private let settings: AppSettings
    private var isFinishing = false
    private let onFinish: () -> Void

    init(settings: AppSettings, onFinish: @escaping () -> Void) {
        self.settings = settings
        self.onFinish = onFinish
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 500, height: 380),
                              styleMask: [.titled], backing: .buffered, defer: false)
        window.title = "Welcome to OverAI"
        window.titlebarSeparatorStyle = .none
        window.isReleasedWhenClosed = false
        super.init(window: window)
        window.contentView = NSHostingView(rootView: StartupView { [weak self] show in self?.choose(showWindow: show) })
        window.center()
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }
    @discardableResult func show() -> Bool {
        guard let window, CaptureProtection.shared.track(window) else { NSSound.beep(); return false }
        NSApp.activate(ignoringOtherApps: true)
        window.makeKeyAndOrderFront(nil)
        return true
    }
    private func choose(showWindow: Bool) {
        guard !isFinishing, let window else { return }
        isFinishing = true
        settings.chooseStartup(showWindow: showWindow)
        let finish = { [weak self] in
            guard let self else { return }
            self.close()
            self.onFinish()
        }
        if !PermissionsController.shared.hasShownSetup {
            PermissionsController.shared.presentSetup(parent: window, completion: finish)
        } else { finish() }
    }
}

private struct StartupView: View {
    let choose: (Bool) -> Void
    @State private var hasChosen = false
    var body: some View {
        VStack(spacing: 18) {
            Image(nsImage: NSApp.applicationIconImage).resizable().frame(width: 72, height: 72)
            VStack(spacing: 8) {
                Text("Welcome to OverAI").font(.system(size: 26, weight: .bold))
                Text("How should OverAI start?").font(.title3)
                Text("Show the floating window, or start quietly in the menu bar. You can change this anytime in Settings → General.")
                    .font(.callout).foregroundStyle(.secondary).multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
            }
            HStack(spacing: 12) {
                Button("Start Hidden") { finish(false) }.controlSize(.large)
                Button("Show OverAI") { finish(true) }.controlSize(.large).buttonStyle(.borderedProminent).keyboardShortcut(.defaultAction)
            }.disabled(hasChosen)
            Text("Built by Sai Praveen").font(.caption).foregroundStyle(.secondary)
        }.padding(32).frame(width: 500, height: 380)
            .background(Color(nsColor: .windowBackgroundColor))
    }
    private func finish(_ show: Bool) { guard !hasChosen else { return }; hasChosen = true; choose(show) }
}
