import AppKit

MainActor.assumeIsolated {
    if CommandLine.arguments.contains("--version") {
        let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "development"
        let build = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "unknown"
        print("OverAI \(version) (\(build)) · Built by Sai Praveen · Apple Silicon")
    } else {
        #if !OVERAI_VALIDATION
        if CommandLine.arguments.dropFirst().contains(where: { $0.hasPrefix("--") }) {
            print("Unsupported launch option. Use --version for build information.")
            exit(2)
        }
        #endif
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.run()
        withExtendedLifetime(delegate) {}
    }
}
