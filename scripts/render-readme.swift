import AppKit
import CoreText

// Rebuild the README's own artwork without changing app or installer assets.
let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let folder = root.appendingPathComponent("assets/readme")
try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
CTFontManagerRegisterFontsForURL(root.appendingPathComponent("website/assets/fonts/BebasNeue-Regular.ttf") as CFURL, .process, nil)
let ink = NSColor(white: 0.067, alpha: 1)
let gray = NSColor(white: 0.45, alpha: 1)
let cloud = NSColor(white: 0.96, alpha: 1)
let line = NSColor(white: 0.86, alpha: 1)
let logo = NSImage(contentsOf: root.appendingPathComponent("Sources/OverAI/Resources/logo.png"))!
func text(_ value: String, _ rect: NSRect, size: CGFloat, color: NSColor = ink, bold: Bool = false, display: Bool = false, centered: Bool = false) {
    let paragraph = NSMutableParagraphStyle(); paragraph.alignment = centered ? .center : .left
    let font = display ? NSFont(name: "BebasNeue-Regular", size: size)! : NSFont.systemFont(ofSize: size, weight: bold ? .semibold : .regular)
    (value as NSString).draw(in: rect, withAttributes: [.font:font, .foregroundColor:color, .paragraphStyle:paragraph])
}
func box(_ rect: NSRect, fill: NSColor = .white, radius: CGFloat = 0, border: NSColor? = nil) {
    let p = NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius)
    fill.setFill(); p.fill()
    if let border { border.setStroke(); p.lineWidth = 1; p.stroke() }
}
func icon(_ image: NSImage, _ rect: NSRect) { image.draw(in: rect, from: .zero, operation: .sourceOver, fraction: 1, respectFlipped: true, hints: nil) }
func provider(_ name: String, _ rect: NSRect) { icon(NSImage(contentsOf: root.appendingPathComponent("website/assets/\(name).png"))!, rect) }
func render(_ name: String, size: NSSize, draw: @escaping () -> Void) throws {
    let image = NSImage(size: size, flipped: true) { _ in draw(); return true }
    let rep = NSBitmapImageRep(bitmapDataPlanes:nil, pixelsWide:Int(size.width)*2, pixelsHigh:Int(size.height)*2, bitsPerSample:8, samplesPerPixel:4, hasAlpha:true, isPlanar:false, colorSpaceName:.deviceRGB, bytesPerRow:0, bitsPerPixel:0)!
    NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep:rep)
    image.draw(in:NSRect(x:0,y:0,width:size.width*2,height:size.height*2)); NSGraphicsContext.restoreGraphicsState()
    try rep.representation(using:.png,properties:[:])!.write(to:folder.appendingPathComponent(name))
}
try render("banner.png", size:NSSize(width:1120,height:420)) {
    box(NSRect(x:0,y:0,width:1120,height:420),fill:ink)
    text("OVERAI / FOR MAC",NSRect(x:44,y:30,width:700,height:24),size:13,color:.lightGray,bold:true)
    text("ALL YOUR AI.",NSRect(x:40,y:84,width:800,height:122),size:116,color:.white,display:true)
    text("ONE BUTTON.",NSRect(x:40,y:191,width:800,height:122),size:116,color:.white,display:true)
    icon(logo,NSRect(x:880,y:104,width:160,height:160))
    text("Privacy first. Your accounts. No AI API keys.",NSRect(x:44,y:340,width:800,height:30),size:20,color:.lightGray)
    text("Built by Sai Praveen",NSRect(x:850,y:370,width:230,height:22),size:12,color:.lightGray)
}
try render("workflow.png",size:NSSize(width:1120,height:260)) {
    box(NSRect(x:0,y:0,width:1120,height:260),fill:cloud)
    let titles=["Your shortcut","Your floating window","Your chosen website","Your existing account"]
    let captions=["⌘G, or make it your own","Show. Ask. Hide.","The original website","No AI API key needed"]
    for i in 0..<4 {
        let x=CGFloat(24+i*275)
        box(NSRect(x:x,y:30,width:247,height:164),border:line)
        text(String(format:"%02d",i+1),NSRect(x:x+18,y:45,width:40,height:20),size:11,color:gray)
        text(titles[i],NSRect(x:x+18,y:94,width:220,height:28),size:18,bold:true)
        text(captions[i],NSRect(x:x+18,y:139,width:220,height:25),size:13,color:gray)
        if i<3 { text("→",NSRect(x:x+250,y:93,width:24,height:30),size:20,centered:true) }
    }
    text("Your Mac connects directly to the website. OverAI adds no prompt relay.",NSRect(x:24,y:218,width:1072,height:24),size:13,color:gray,centered:true)
}
try render("window.png",size:NSSize(width:640,height:460)) {
    box(NSRect(x:0,y:0,width:640,height:460),fill:cloud)
    text("ONE WINDOW. ALL YOUR WEBSITES.",NSRect(x:30,y:24,width:580,height:25),size:12,bold:true)
    box(NSRect(x:68,y:79,width:504,height:316),radius:14,border:ink)
    box(NSRect(x:86,y:94,width:156,height:32),fill:cloud,radius:16)
    provider("chatgpt",NSRect(x:98,y:101,width:18,height:18))
    text("ChatGPT  ⌄",NSRect(x:126,y:102,width:110,height:22),size:13,bold:true)
    text("−    +",NSRect(x:494,y:101,width:70,height:24),size:16,color:gray)
    text("A fresh perspective?",NSRect(x:98,y:169,width:444,height:35),size:26,bold:true,centered:true)
    text("Your familiar AI website, close at hand.",NSRect(x:98,y:213,width:444,height:24),size:14,color:gray,centered:true)
    let services=["chatgpt","claude","gemini","grok","arena","muse"]
    for (i,service) in services.enumerated() { provider(service,NSRect(x:157+CGFloat(i)*51,y:268,width:25,height:25)) }
    box(NSRect(x:100,y:327,width:440,height:40),fill:cloud,radius:20)
    text("⌘ G  ·  Show / hide",NSRect(x:100,y:337,width:440,height:25),size:13,centered:true)
    text("Interface illustration · provider features vary",NSRect(x:30,y:422,width:580,height:20),size:10,color:gray,centered:true)
}
try render("websites.png",size:NSSize(width:640,height:460)) {
    box(NSRect(x:0,y:0,width:640,height:460),fill:cloud)
    text("YOUR LINEUP. YOUR ORDER.",NSRect(x:30,y:24,width:580,height:25),size:12,bold:true)
    let names=["Claude","ChatGPT","Your website"]
    for i in 0..<3 {
        let y=CGFloat(86+i*82)
        box(NSRect(x:68,y:y,width:504,height:64),border:line)
        text("⠿",NSRect(x:85,y:y+22,width:24,height:28),size:19,color:gray)
        if i<2 {provider(i==0 ? "claude":"chatgpt",NSRect(x:122,y:y+19,width:26,height:26))}
        else {text("↗",NSRect(x:122,y:y+17,width:26,height:30),size:24)}
        text(names[i],NSRect(x:166,y:y+22,width:240,height:28),size:17,bold:true)
        text("↑  ↓   −",NSRect(x:470,y:y+22,width:90,height:26),size:17,color:gray)
    }
    box(NSRect(x:215,y:353,width:210,height:40),fill:ink,radius:20)
    text("+ Add a website",NSRect(x:215,y:364,width:210,height:24),size:13,color:.white,centered:true)
    text("Settings illustration · add, remove, reorder",NSRect(x:30,y:422,width:580,height:20),size:10,color:gray,centered:true)
}
print("Rendered README banner, workflow and interface illustrations.")
