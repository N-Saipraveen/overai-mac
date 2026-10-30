import AppKit

let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let output = root.appendingPathComponent("assets/installer")
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
let logo = NSImage(contentsOf: root.appendingPathComponent("Sources/OverAI/Resources/logo.png"))!
let ink = NSColor(srgbRed: 0.15, green: 0.18, blue: 0.14, alpha: 1)
let sage = NSColor(srgbRed: 0.42, green: 0.51, blue: 0.35, alpha: 1)
let muted = NSColor(srgbRed: 0.43, green: 0.48, blue: 0.39, alpha: 1)
let paper = NSColor(srgbRed: 0.97, green: 0.975, blue: 0.95, alpha: 1)
func text(_ value: String, _ rect: NSRect, size: CGFloat, weight: NSFont.Weight = .regular, color: NSColor = ink, centered: Bool = false) {
    let style = NSMutableParagraphStyle(); style.alignment = centered ? .center : .left
    (value as NSString).draw(in: rect, withAttributes: [.font: NSFont.systemFont(ofSize: size, weight: weight), .foregroundColor: color, .paragraphStyle: style])
}
func rounded(_ rect: NSRect, radius: CGFloat, fill: NSColor, stroke: NSColor? = nil) {
    let path = NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius)
    fill.setFill(); path.fill()
    if let stroke { stroke.setStroke(); path.lineWidth = 1; path.stroke() }
}
func symbol(_ name: String, _ rect: NSRect, color: NSColor = sage) {
    guard let image = NSImage(systemSymbolName: name, accessibilityDescription: nil) else { return }
    image.withSymbolConfiguration(.init(paletteColors: [color]))?.draw(in: rect, from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
}
func render(_ name: String, size: NSSize, scale: Int = 2, draw: @escaping () -> Void) throws {
    let image = NSImage(size: size, flipped: true) { _ in draw(); return true }
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(size.width)*scale, pixelsHigh: Int(size.height)*scale, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    image.draw(in: NSRect(x: 0, y: 0, width: size.width*CGFloat(scale), height: size.height*CGFloat(scale)))
    NSGraphicsContext.restoreGraphicsState()
    try rep.representation(using: .png, properties: [:])!.write(to: root.appendingPathComponent(name))
}
func dmg() {
    paper.setFill(); NSRect(x: 0, y: 0, width: 720, height: 480).fill()
    logo.draw(in: NSRect(x: 38, y: 27, width: 33, height: 33), from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
    text("OverAI", NSRect(x: 82, y: 32, width: 140, height: 28), size: 20, weight: .semibold)
    text("FREE · MADE FOR MAC", NSRect(x: 495, y: 39, width: 185, height: 20), size: 9, weight: .medium, color: muted, centered: true)
    text("One small drag.", NSRect(x: 50, y: 98, width: 620, height: 46), size: 35, weight: .medium, centered: true)
    text("A home for all your AI websites.", NSRect(x: 50, y: 148, width: 620, height: 24), size: 14, color: muted, centered: true)
    for x: CGFloat in [205, 515] {
        rounded(NSRect(x: x-74, y: 199, width: 148, height: 148), radius: 28, fill: NSColor.white.withAlphaComponent(0.72), stroke: NSColor(srgbRed: 0.86, green: 0.9, blue: 0.81, alpha: 1))
    }
    text("01  DRAG", NSRect(x: 130, y: 178, width: 150, height: 20), size: 9, weight: .medium, color: muted, centered: true)
    text("02  DROP", NSRect(x: 440, y: 178, width: 150, height: 20), size: 9, weight: .medium, color: muted, centered: true)
    symbol("arrow.right", NSRect(x: 340, y: 245, width: 40, height: 25))
    text("Drag OverAI into Applications.", NSRect(x: 50, y: 370, width: 620, height: 26), size: 16, weight: .medium, centered: true)
    text("Then open it from Applications. Press ⌘G whenever you need it.", NSRect(x: 50, y: 401, width: 620, height: 22), size: 11, color: muted, centered: true)
    text("Built by Sai Praveen", NSRect(x: 35, y: 452, width: 250, height: 16), size: 8, color: muted)
    text("Apple Silicon · macOS 14+", NSRect(x: 440, y: 452, width: 245, height: 16), size: 8, color: muted)
}
try render("assets/installer/dmg-background.png", size: NSSize(width: 720, height: 480), scale: 1, draw: dmg)
try render("assets/installer/dmg-background@2x.png", size: NSSize(width: 720, height: 480), draw: dmg)
try render("website/assets/install-guide.png", size: NSSize(width: 1000, height: 330)) {
    paper.setFill(); NSRect(x: 0, y: 0, width: 1000, height: 330).fill()
    text("From download to your first conversation.", NSRect(x: 36, y: 25, width: 920, height: 40), size: 27, weight: .medium)
    let titles = ["Download", "Drag to install", "Open OverAI", "Make it yours"]
    let subtitles = ["Get the Apple Silicon DMG\nfrom GitHub Releases.", "Move OverAI.app into\nyour Applications folder.", "Allow this preview in\nPrivacy & Security if asked.", "Press ⌘G. Pick a website.\nSign in and start talking."]
    let symbols = ["arrow.down.circle", "folder", "checkmark.shield", "command"]
    for i in 0..<4 {
        let x = CGFloat(36+i*242)
        rounded(NSRect(x: x, y: 91, width: 224, height: 195), radius: 18, fill: .white, stroke: NSColor(srgbRed: 0.88, green: 0.91, blue: 0.84, alpha: 1))
        text(String(format: "%02d", i+1), NSRect(x: x+19, y: 107, width: 35, height: 20), size: 10, weight: .medium, color: muted)
        symbol(symbols[i], NSRect(x: x+20, y: 144, width: 33, height: 33))
        text(titles[i], NSRect(x: x+19, y: 196, width: 200, height: 24), size: 17, weight: .medium)
        text(subtitles[i], NSRect(x: x+19, y: 230, width: 200, height: 43), size: 11, color: muted)
    }
    text("Free · No license key · No AI API keys", NSRect(x: 36, y: 306, width: 900, height: 18), size: 10, color: muted)
}
try render("website/assets/social-card.png", size: NSSize(width: 1200, height: 630), scale: 1) {
    paper.setFill(); NSRect(x: 0, y: 0, width: 1200, height: 630).fill()
    logo.draw(in: NSRect(x: 850, y: 180, width: 240, height: 240), from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil)
    text("OverAI / FOR MAC", NSRect(x: 65, y: 60, width: 700, height: 30), size: 19, color: muted)
    text("All your AI.", NSRect(x: 60, y: 150, width: 800, height: 115), size: 80, weight: .semibold)
    text("One button.", NSRect(x: 60, y: 245, width: 800, height: 115), size: 80, weight: .semibold, color: sage)
    text("Free. Privacy first. No AI API keys.", NSRect(x: 66, y: 380, width: 800, height: 45), size: 25, color: muted)
    text("Built by Sai Praveen", NSRect(x: 66, y: 550, width: 700, height: 30), size: 17, color: muted)
}
print("Rendered installer, install guide and social card.")
