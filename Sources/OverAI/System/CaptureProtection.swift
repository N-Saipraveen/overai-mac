import AppKit
import Darwin

/// Small compatibility boundary for Chromium's region-based exclusion approach.
/// No private symbols are hard-linked. A successful call is not proof that every recorder excludes it.
@MainActor final class CaptureProtection {
    static let shared = CaptureProtection()
    private typealias Connection = @convention(c) () -> UInt32
    private typealias CreateRegion = @convention(c) (CGRect) -> UnsafeRawPointer?
    private typealias Exclude = @convention(c) (UInt32, Int, UnsafeRawPointer?) -> Int32
    private let connection: Connection?
    private let createRegion: CreateRegion?
    private let exclude: Exclude?
    private var observations: [ObjectIdentifier: [NSObjectProtocol]] = [:]
    private(set) var lastResult = "Not checked"

    private init() {
        let library = dlopen("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight", RTLD_LAZY)
        func symbol<T>(_ name: String, as: T.Type) -> T? {
            guard let address = dlsym(library, name) else { return nil }
            return unsafeBitCast(address, to: T.self)
        }
        connection = symbol("CGSMainConnectionID", as: Connection.self)
        createRegion = symbol("CGRegionCreateWithRect", as: CreateRegion.self)
        exclude = symbol("CGSSetWindowCaptureExcludeShape", as: Exclude.self)
        // The library stays loaded for the lifetime of these function pointers.
    }

    @discardableResult func protect(_ window: NSWindow) -> Bool {
        window.sharingType = .none
        guard let connection, let createRegion, let exclude else {
            lastResult = "This macOS build does not expose region-based capture exclusion."
            return false
        }
        guard window.windowNumber > 0,
              let region = createRegion(CGRect(origin: .zero, size: window.frame.size)) else {
            lastResult = "The window's capture region could not be created."
            return false
        }
        defer { Unmanaged<AnyObject>.fromOpaque(region).release() }
        let result = exclude(connection(), window.windowNumber, region)
        lastResult = result == 0 ? "Capture exclusion enabled; verify your recorder." : "Capture exclusion failed (\(result))."
        return result == 0
    }

    @discardableResult func track(_ window: NSWindow) -> Bool {
        let key = ObjectIdentifier(window)
        if observations[key] == nil {
            let center = NotificationCenter.default
            let resize = center.addObserver(forName: NSWindow.didResizeNotification, object: window, queue: .main) { [weak self, weak window] _ in
                MainActor.assumeIsolated {
                    guard let self, let window else { return }
                    if !self.protect(window) { window.orderOut(nil) }
                }
            }
            let close = center.addObserver(forName: NSWindow.willCloseNotification, object: window, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { self?.untrack(key) }
            }
            observations[key] = [resize, close]
        }
        return protect(window)
    }

    private func untrack(_ key: ObjectIdentifier) {
        observations.removeValue(forKey: key)?.forEach { NotificationCenter.default.removeObserver($0) }
    }
}
