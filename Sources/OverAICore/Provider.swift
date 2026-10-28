import Foundation

public struct Provider: Codable, Identifiable, Hashable, Sendable {
    public let rawValue: String
    public let name: String
    public let home: URL
    public let symbol: String
    public var id: String { rawValue }
    public var isBuiltIn: Bool { Self.allCases.contains { $0.id == id } }
    private init(_ id: String, _ name: String, _ address: String, _ symbol: String) {
        rawValue = id; self.name = name; home = URL(string: address)!; self.symbol = symbol
    }
    public init?(rawValue: String) {
        guard let provider = Self.allCases.first(where: { $0.id == rawValue }) else { return nil }
        self = provider
    }
    public static let chatgpt = Provider("chatgpt", "ChatGPT", "https://chatgpt.com", "bubble.left.and.bubble.right")
    public static let claude = Provider("claude", "Claude", "https://claude.ai", "sun.max")
    public static let gemini = Provider("gemini", "Gemini", "https://gemini.google.com", "sparkles")
    public static let grok = Provider("grok", "Grok", "https://grok.com", "bolt")
    public static let arena = Provider("arena", "Arena", "https://arena.ai/text/direct?model_a=max", "text.bubble")
    public static let muse = Provider("muse", "Muse", "https://muse.ai/", "waveform")
    public static let allCases: [Provider] = [.chatgpt, .claude, .gemini, .grok, .arena, .muse]

    public static func custom(name: String, address: String) -> Provider? {
        let name = name.trimmingCharacters(in: .whitespacesAndNewlines)
        let address = address.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty, name.count <= 40, address.count <= 2048,
              address.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) }),
              name.unicodeScalars.allSatisfy({ !CharacterSet.controlCharacters.contains($0) }),
              let url = URL(string: address.contains("://") ? address : "https://" + address),
              url.scheme?.lowercased() == "https", let host = url.host, !host.isEmpty,
              url.user == nil, url.password == nil, url.port.map({ (1...65535).contains($0) }) ?? true else { return nil }
        return Provider("custom-" + UUID().uuidString, name, url.absoluteString, "globe")
    }
    public var isValidSavedWebsite: Bool {
        if let builtIn = Provider(rawValue: id) { return self == builtIn }
        return id.hasPrefix("custom-") && Self.custom(name: name, address: home.absoluteString) != nil
    }
    public func owns(_ url: URL) -> Bool {
        guard let host = url.host?.lowercased(), let domain = home.host?.lowercased() else { return false }
        if !isBuiltIn { return host == domain && (url.port ?? 443) == (home.port ?? 443) }
        return host == domain || host.hasSuffix("." + domain)
    }
    public func directModeRedirect(for url: URL) -> URL? {
        guard self == .arena, owns(url) else { return nil }
        let path = url.path.lowercased()
        if path == "/" || path.isEmpty || path == "/text" ||
            (path.hasPrefix("/text/") && !path.hasPrefix("/text/direct")) ||
            path.split(separator: "/").contains("battle") || path.contains("side-by-side") { return home }
        return nil
    }
}

public enum NavigationPolicy {
    public enum Decision: Equatable { case web, external, block }
    /// Top-level policy. WebKit continues to enforce origin, TLS and iframe rules.
    public static func decision(for url: URL, isUserAction: Bool) -> Decision {
        guard url.user == nil, url.password == nil else { return .block }
        switch url.scheme?.lowercased() {
        case "https": return url.host == nil ? .block : .web
        case "about": return ["about:blank", "about:srcdoc"].contains(url.absoluteString) ? .web : .block
        case "blob", "data": return .web
        case "mailto", "tel": return isUserAction ? .external : .block
        default: return .block
        }
    }
    public static func safeFilename(_ suggested: String) -> String {
        let leaf = (suggested as NSString).lastPathComponent
            .components(separatedBy: .controlCharacters).joined()
            .replacingOccurrences(of: ":", with: "-")
        return leaf.isEmpty || leaf == "." || leaf == ".." ? "Download" : String(leaf.prefix(180))
    }
}

public struct RecoveryBudget: Sendable {
    public private(set) var failures = 0
    public let limit: Int
    public init(limit: Int = 2) { self.limit = limit }
    public mutating func consume() -> Bool {
        guard failures < limit else { return false }
        failures += 1
        return true
    }
    public mutating func reset() { failures = 0 }
}

/// Media grants are limited to the visible provider document on the default TLS port.
public enum MediaAccessPolicy {
    public static func allows(provider: Provider, page: URL, frame: URL, originHost: String, originPort: Int) -> Bool {
        guard page.scheme == "https", frame.scheme == "https",
              page.user == nil, page.password == nil, frame.user == nil, frame.password == nil,
              provider.owns(page), provider.owns(frame),
              page.host?.lowercased() == frame.host?.lowercased(),
              frame.host?.lowercased() == originHost.lowercased(),
              [nil, 443].contains(page.port), [nil, 443].contains(frame.port),
              originPort == 0 || originPort == 443 else { return false }
        return true
    }
}
