import AppKit
import Combine
import OverAICore

@MainActor final class AppSettings: ObservableObject {
    let defaults: UserDefaults
    @Published private(set) var websites: [Provider]
    @Published var selectedProvider: Provider { didSet { defaults.set(selectedProvider.rawValue, forKey: "provider") } }
    @Published var opacity: Double { didSet { defaults.set(opacity, forKey: "opacity") } }
    @Published var escapeHides: Bool { didSet { defaults.set(escapeHides, forKey: "escapeHides") } }
    @Published var showOnLaunch: Bool { didSet { defaults.set(showOnLaunch, forKey: "showOnLaunch") } }
    @Published var followPointer: Bool { didSet { defaults.set(followPointer, forKey: "followPointer") } }
    @Published var throttleBackground: Bool { didSet { defaults.set(throttleBackground, forKey: "throttleBackground") } }
    @Published var captureSummary = "Capture exclusion has not been checked"
    @Published var captureReady = false
    @Published var hotkeySummary = ""
    @Published var sessionCount = 0
    @Published var isClearingData = false

    var hasChosenStartup: Bool { defaults.bool(forKey: "startupChoiceMade") }
    func chooseStartup(showWindow: Bool) {
        showOnLaunch = showWindow
        defaults.set(true, forKey: "startupChoiceMade")
    }

    func addWebsite(_ website: Provider) -> Bool {
        guard website.isValidSavedWebsite, !websites.contains(where: { $0.home == website.home }) else { return false }
        websites.append(website)
        persistWebsites()
        return true
    }
    func removeWebsite(_ website: Provider) {
        guard websites.count > 1, let existing = websites.first(where: { $0.id == website.id }) else { return }
        if selectedProvider.id == existing.id { selectedProvider = websites.first { $0.id != existing.id }! }
        websites.removeAll { $0.id == website.id }
        persistWebsites()
    }
    func moveWebsite(_ website: Provider, by offset: Int) {
        guard let from = websites.firstIndex(of: website), websites.indices.contains(from + offset) else { return }
        websites.swapAt(from, from + offset)
        persistWebsites()
    }
    func restoreBuiltIns() {
        websites.append(contentsOf: Provider.allCases.filter { preset in !websites.contains { $0.id == preset.id } })
        persistWebsites()
    }
    private func persistWebsites() { defaults.set(try? JSONEncoder().encode(websites), forKey: "websites") }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        defaults.register(defaults: ["opacity": 1.0, "escapeHides": true, "showOnLaunch": true,
                                     "followPointer": true, "throttleBackground": true])
        let saved = defaults.data(forKey: "websites").flatMap { try? JSONDecoder().decode([Provider].self, from: $0) }
        var ids = Set<String>()
        let valid = saved?.filter { $0.isValidSavedWebsite && ids.insert($0.id).inserted } ?? Provider.allCases
        let initial = valid.isEmpty ? Provider.allCases : valid
        websites = initial
        selectedProvider = initial.first { $0.id == defaults.string(forKey: "provider") } ?? initial.first!
        let savedOpacity = defaults.double(forKey: "opacity")
        opacity = savedOpacity.isFinite ? min(1, max(0.25, savedOpacity)) : 1
        escapeHides = defaults.bool(forKey: "escapeHides")
        showOnLaunch = defaults.bool(forKey: "showOnLaunch")
        followPointer = defaults.bool(forKey: "followPointer")
        throttleBackground = defaults.bool(forKey: "throttleBackground")
    }
}
