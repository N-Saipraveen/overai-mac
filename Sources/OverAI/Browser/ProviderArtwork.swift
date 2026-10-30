import AppKit
import OverAICore

/// Official website artwork, bundled once and decoded lazily. No icon network requests.
@MainActor enum ProviderArtwork {
    private static var cache: [Provider: NSImage] = [:]

    static func icon(for provider: Provider) -> NSImage? {
        guard provider.isBuiltIn else { return NSImage(systemSymbolName: "globe", accessibilityDescription: provider.name) }
        if let image = cache[provider] { return image }
        #if SWIFT_PACKAGE
        let bundle = Bundle.module
        #else
        let bundle = Bundle.main
        #endif
        guard let url = bundle.url(forResource: provider.rawValue, withExtension: "png", subdirectory: "ProviderIcons"),
              let image = NSImage(contentsOf: url) else { return nil }
        image.size = NSSize(width: 18, height: 18)
        // Preserve brand colours, while adapting monochrome marks to light/dark mode.
        image.isTemplate = provider == .chatgpt
        cache[provider] = image
        return image
    }
}
