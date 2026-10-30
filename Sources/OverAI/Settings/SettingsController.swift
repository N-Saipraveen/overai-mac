import AppKit
import SwiftUI
import KeyboardShortcuts
import ServiceManagement
import OverAICore

enum SettingsPage: String, CaseIterable, Identifiable {
    case websites = "Websites", general = "General", appearance = "Appearance", privacy = "Privacy", status = "App Status", about = "About"
    var id: String { rawValue }
    var symbol: String {
        switch self {
        case .websites: "square.grid.2x2"
        case .general: "gearshape"
        case .appearance: "macwindow"
        case .privacy: "hand.raised.fill"
        case .status: "waveform.path.ecg"
        case .about: "info.circle"
        }
    }
    var subtitle: String {
        switch self {
        case .websites: "Choose your websites and put them in your order."
        case .general: "Your shortcut and everyday defaults."
        case .appearance: "Make the floating window feel right for you."
        case .privacy: "Control access and manage website data."
        case .status: "A quick look at how OverAI is running."
        case .about: "Your AI websites, one shortcut away."
        }
    }
}

@MainActor final class SettingsNavigation: ObservableObject {
    @Published var page: SettingsPage = .general
    @Published var pendingRemoval: Provider?
    @Published var confirmClearData = false
    func confirmRemoval(settings: AppSettings) {
        if let pendingRemoval { settings.removeWebsite(pendingRemoval) }
        pendingRemoval = nil
    }
}

@MainActor final class SettingsController: NSWindowController {
    let navigation = SettingsNavigation()
    init(settings: AppSettings, onShortcutChange: @escaping () -> Void, clearData: @escaping () -> Void) {
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 760, height: 620),
                              styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "OverAI Settings"
        window.titlebarSeparatorStyle = .none
        window.isReleasedWhenClosed = false
        window.contentView = NSHostingView(rootView: SettingsView(settings: settings, navigation: navigation,
                                                                  onShortcutChange: onShortcutChange, clearData: clearData))
        super.init(window: window)
        window.center()
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }
    func show(page: SettingsPage? = nil) {
        if let page { navigation.page = page }
        PermissionsController.shared.refreshMicrophoneStatus()
        guard let window else { return }
        guard CaptureProtection.shared.track(window) else { NSSound.beep(); return }
        NSApp.activate(ignoringOtherApps: true)
        window.makeKeyAndOrderFront(nil)
    }
}

private struct SettingsView: View {
    @ObservedObject private var permissions = PermissionsController.shared
    @ObservedObject var settings: AppSettings
    @ObservedObject var navigation: SettingsNavigation
    let onShortcutChange: () -> Void
    let clearData: () -> Void
    @State private var launchAtLogin = SMAppService.mainApp.status == .enabled
    @State private var loginError: String?
    @State private var footprint: Double?
    @State private var refreshedAt = Date()
    @State private var websiteName = ""
    @State private var websiteAddress = ""
    @State private var websiteError: String?

    var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 0) {
                HStack(spacing: 10) {
                    Image(nsImage: NSApp.applicationIconImage).resizable().frame(width: 38, height: 38)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("OverAI").font(.headline)
                        Text("Settings").font(.caption).foregroundStyle(.secondary)
                    }
                }.padding(.horizontal, 18).padding(.top, 22).padding(.bottom, 18)
                List(selection: $navigation.page) {
                    ForEach(SettingsPage.allCases) { page in
                        Label(page.rawValue, systemImage: page.symbol)
                            .font(.system(size: 13)).padding(.vertical, 5).tag(page)
                    }
                }.listStyle(.sidebar)
                Text("Native Swift · Apple Silicon").font(.caption2).foregroundStyle(.secondary)
                    .padding(18)
            }.frame(width: 190).background(.regularMaterial)
            Divider()
            VStack(alignment: .leading, spacing: 0) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(navigation.page.rawValue).font(.system(size: 25, weight: .bold))
                    Text(navigation.page.subtitle).font(.callout).foregroundStyle(.secondary)
                }.padding(.horizontal, 28).padding(.top, 28).padding(.bottom, 8)
                Form {
                    switch navigation.page {
                    case .websites: websites
                    case .general: general
                    case .appearance: appearance
                    case .privacy: privacy
                    case .status: status
                                case .about: about
                    }
                }.formStyle(.grouped)
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color(nsColor: .windowBackgroundColor))
        }.disabled(navigation.pendingRemoval != nil || navigation.confirmClearData || settings.isClearingData).frame(width: 760, height: 620)
            .overlay {
                if let website = navigation.pendingRemoval {
                    ZStack {
                        Color.black.opacity(0.22).contentShape(Rectangle())
                            .onTapGesture { navigation.pendingRemoval = nil }
                        VStack(alignment: .leading, spacing: 16) {
                            Label("Remove \(website.name)?", systemImage: "minus.circle")
                                .font(.title3.weight(.semibold)).lineLimit(2)
                            Text("Its open page will close and unsent drafts may be lost. Saved sign-ins and website data stay on this Mac.")
                                .font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                            HStack {
                                Spacer()
                                Button("Cancel") { navigation.pendingRemoval = nil }.keyboardShortcut(.cancelAction)
                                Button("Remove", role: .destructive) { navigation.confirmRemoval(settings: settings) }
                                    .accessibilityLabel("Confirm removal of \(website.name)")
                            }
                        }.padding(24).frame(width: 350)
                            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
                            .overlay(RoundedRectangle(cornerRadius: 16).stroke(.separator, lineWidth: 0.5))
                            .shadow(color: .black.opacity(0.18), radius: 20, y: 8)
                            .accessibilityElement(children: .contain)
                    }
                } else if navigation.confirmClearData {
                    ZStack {
                        Color.black.opacity(0.22).contentShape(Rectangle())
                            .onTapGesture { navigation.confirmClearData = false }
                        VStack(alignment: .leading, spacing: 16) {
                            Label("Clear Website Data?", systemImage: "trash").font(.title3.weight(.semibold))
                            Text("This signs you out of every website and removes cookies, local website storage, and unsent drafts. Chats saved in provider accounts stay there.")
                                .font(.callout).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                            HStack {
                                Spacer()
                                Button("Cancel") { navigation.confirmClearData = false }.keyboardShortcut(.cancelAction)
                                Button("Clear Data", role: .destructive) {
                                    navigation.confirmClearData = false
                                    clearData()
                                }
                            }
                        }.padding(24).frame(width: 350)
                            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
                            .overlay(RoundedRectangle(cornerRadius: 16).stroke(.separator, lineWidth: 0.5))
                            .shadow(color: .black.opacity(0.18), radius: 20, y: 8)
                    }
                }
            }
            .onAppear { refreshStatus() }
            .onChange(of: navigation.page) { _, page in
                if page == .status { refreshStatus() }
            }
            .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in
                permissions.refreshMicrophoneStatus()
                launchAtLogin = SMAppService.mainApp.status == .enabled
            }
    }

    private var websites: some View {
        Group {
            Section {
                ForEach(Array(settings.websites.enumerated()), id: \.element.id) { index, website in
                    HStack(spacing: 10) {
                        if let icon = ProviderArtwork.icon(for: website) {
                            Image(nsImage: icon).resizable().scaledToFit().frame(width: 18, height: 18)
                        }
                        VStack(alignment: .leading, spacing: 2) {
                            Text(website.name).lineLimit(1)
                            Text(website.home.host ?? "").font(.caption).foregroundStyle(.secondary).lineLimit(1)
                        }
                        Spacer(minLength: 4)
                        Button { settings.moveWebsite(website, by: -1) } label: { Image(systemName: "chevron.up") }
                            .disabled(index == 0).help("Move up").accessibilityLabel("Move \(website.name) up")
                        Button { settings.moveWebsite(website, by: 1) } label: { Image(systemName: "chevron.down") }
                            .disabled(index == settings.websites.count - 1).help("Move down").accessibilityLabel("Move \(website.name) down")
                        Button { navigation.pendingRemoval = website } label: { Image(systemName: "minus.circle") }
                            .disabled(settings.websites.count == 1).help(settings.websites.count == 1 ? "Add another website before removing the last one" : "Remove website").accessibilityLabel("Remove \(website.name)")
                    }
                }
            } header: { Text("Your websites") } footer: {
                Text("Use the arrows to reorder. Keep as few as one website. The picker and menu bar follow this order.")
            }
            Section {
                TextField("Name", text: $websiteName).textFieldStyle(.roundedBorder)
                TextField("Website URL", text: $websiteAddress, prompt: Text("https://example.com"))
                    .textFieldStyle(.roundedBorder)
                HStack {
                    if let websiteError { Text(websiteError).font(.caption).foregroundStyle(.red) }
                    Spacer()
                    Button("Add Website", systemImage: "plus") {
                        guard let website = Provider.custom(name: websiteName, address: websiteAddress) else {
                            websiteError = "Enter a name (up to 40 characters) and a secure HTTPS address."; return
                        }
                        guard settings.addWebsite(website) else { websiteError = "This website is already in your list."; return }
                        websiteName = ""; websiteAddress = ""; websiteError = nil
                    }.disabled(websiteName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || websiteAddress.isEmpty)
                }
            } header: { Text("Add your own") } footer: {
                Text("Websites open directly in OverAI. Some services restrict embedded sign-in or browser features.")
            }
            Button("Restore Missing Built-in Websites") { settings.restoreBuiltIns() }
                .disabled(Provider.allCases.allSatisfy { settings.websites.contains($0) })
        }
    }

    private var general: some View {
        Group {
            Section {
                KeyboardShortcuts.Recorder("Show or hide OverAI", name: .toggleOverlay) { _ in onShortcutChange() }
            } header: { Text("Keyboard shortcut") } footer: {
                Text("Click the recorder, then press your preferred key combination. macOS may reserve some shortcuts.")
            }
            Section("Startup") {
                Toggle("Show window at launch", isOn: $settings.showOnLaunch)
                Toggle("Launch at login", isOn: $launchAtLogin).onChange(of: launchAtLogin) { _, value in
                    guard value != (SMAppService.mainApp.status == .enabled) else { return }
                    do {
                        if value { try SMAppService.mainApp.register() } else { try SMAppService.mainApp.unregister() }
                        loginError = nil
                    } catch {
                        loginError = "macOS couldn’t update the login item. Move OverAI to Applications and try again."
                        launchAtLogin = SMAppService.mainApp.status == .enabled
                    }
                }
                if let loginError { Label(loginError, systemImage: "exclamationmark.circle").font(.caption).foregroundStyle(.orange) }
            }
            Section("Window behavior") {
                Toggle("Press Escape to hide", isOn: $settings.escapeHides)
                Toggle("Open on the pointer’s display", isOn: $settings.followPointer)
            }
        }
    }

    private var appearance: some View {
        Group {
            Section {
                HStack {
                    Label("Window opacity", systemImage: "circle.lefthalf.filled")
                    Spacer()
                    Text("\(Int((settings.opacity * 100).rounded()))%")
                        .foregroundStyle(.secondary).monospacedDigit()
                }
                Slider(value: $settings.opacity, in: 0.25...1)
                    .accessibilityLabel("Window opacity")
                HStack {
                    Text("Transparent")
                    Spacer()
                    Button("Reset to 100%") { settings.opacity = 1 }.buttonStyle(.link)
                }.font(.caption).foregroundStyle(.secondary)
            } header: { Text("Transparency") } footer: {
                Text("You can also adjust opacity with the − and + controls in the floating window.")
            }
            Section("System appearance") {
                Label("Follows your Mac’s light or dark appearance", systemImage: "circle.lefthalf.filled")
                Label("Respects Reduce Motion", systemImage: "accessibility")
            }
        }
    }

    private var privacy: some View {
        Group {
            Section {
                HStack {
                    Label("Microphone", systemImage: "mic")
                    Spacer()
                    Text(permissions.microphoneStatus).foregroundStyle(.secondary)
                    Button("Manage…") { permissions.requestMicrophoneFromSettings() }
                }.disabled(permissions.isBusy)
                HStack {
                    Label("Upload folder", systemImage: "folder")
                    Spacer()
                    Text(permissions.uploadFolder?.lastPathComponent ?? "Not selected")
                        .lineLimit(1).truncationMode(.middle).foregroundStyle(.secondary)
                        .help(permissions.uploadFolder?.path ?? "Choose a default folder for attachments")
                    Button("Choose…") { permissions.chooseUploadFolder(parent: NSApp.keyWindow) }
                }.disabled(permissions.isBusy)
                if permissions.uploadFolder != nil {
                    Button("Forget Upload Folder") { permissions.forgetUploadFolder() }.disabled(permissions.isBusy)
                }
            } header: { Text("Permissions") } footer: {
                Text("Only files you attach are sent to a website. Camera access is requested when you use it.")
            }
            Section {
                Label(settings.captureReady ? "Capture exclusion enabled" : "Capture exclusion needs attention",
                      systemImage: settings.captureReady ? "eye.slash" : "exclamationmark.shield")
                    .foregroundStyle(settings.captureReady ? Color.primary : .orange)
            } header: { Text("Screen privacy · always on") } footer: {
                Text("Test your meeting and screenshot tools before relying on capture exclusion. System permission dialogs are managed by macOS.")
            }
            Section {
                Button(settings.isClearingData ? "Clearing Website Data…" : "Clear Website Data…", role: .destructive) { navigation.confirmClearData = true }
                    .disabled(settings.isClearingData)
            } header: { Text("Website data") } footer: {
                Text("Sign-ins stay in OverAI’s website storage until a provider expires them. Clearing data signs you out and removes unsent drafts. Safari uses separate sessions.")
            }
        }
    }

    private var status: some View {
        Group {
            Section {
                LabeledContent("Websites loaded", value: "\(settings.sessionCount)")
                LabeledContent("App memory", value: footprint.map { String(format: "%.1f MiB", $0) } ?? "Unavailable")
                LabeledContent("Global shortcut", value: settings.hotkeySummary.isEmpty ? "Not registered" : settings.hotkeySummary)
            } header: { Text("Current session") } footer: {
                Text("App memory excludes WebKit helper processes. Activity Monitor shows their additional usage.")
            }
            Section {
                Toggle("Throttle background websites", isOn: $settings.throttleBackground)
            } header: { Text("Resources") } footer: {
                Text("Websites load when first opened. Visited pages stay in memory to preserve drafts and responses. Throttling reduces background CPU use.")
            }
            Section("Capture protection") {
                Label(settings.captureSummary, systemImage: settings.captureReady ? "checkmark.shield" : "exclamationmark.shield")
                    .font(.callout).textSelection(.enabled)
            }
            HStack {
                Text("Updated \(refreshedAt.formatted(date: .omitted, time: .shortened))")
                    .font(.caption).foregroundStyle(.secondary)
                Spacer()
                Button("Refresh", systemImage: "arrow.clockwise") { refreshStatus() }
            }
        }
    }

    private var about: some View {
        Group {
            Section {
                HStack(spacing: 16) {
                    Image(nsImage: NSApp.applicationIconImage).resizable().frame(width: 64, height: 64)
                    VStack(alignment: .leading, spacing: 5) {
                        Text("OverAI").font(.title2.weight(.semibold))
                        Text("Version \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "3.0")")
                            .font(.callout).foregroundStyle(.secondary)
                        Text("Built by Sai Praveen").font(.callout)
                        Text("Built for Apple Silicon").font(.caption).foregroundStyle(.secondary)
                    }
                }.padding(.vertical, 8)
            }
            Section("Your connection") {
                Text("OverAI connects directly to the AI websites you choose. It adds no analytics or prompt logging. It is free to use, with no license key or subscription.")
                    .font(.callout).foregroundStyle(.secondary)
            }

        }
    }

    private func refreshStatus() {
        footprint = ProcessMetrics.footprintMiB
        refreshedAt = Date()
    }
}
