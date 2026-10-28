// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "OverAI",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "OverAI", targets: ["OverAI"]), .library(name: "OverAICore", targets: ["OverAICore"])],
    dependencies: [
        .package(url: "https://github.com/sindresorhus/KeyboardShortcuts", exact: "3.1.0")
    ],
    targets: [
        .target(name: "OverAICore"),
        .executableTarget(name: "OverAI", dependencies: ["OverAICore", "KeyboardShortcuts"],
                          resources: [.copy("Resources/ThirdPartyNotices.txt"), .copy("Resources/ProviderIcons"),
                                      .copy("Resources/icon.icns"), .copy("Resources/logo.png")]),
        .testTarget(name: "OverAICoreTests", dependencies: ["OverAICore"])
    ],
    swiftLanguageModes: [.v5]
)
