import XCTest
@testable import OverAICore

final class PolicyTests: XCTestCase {
    func testProviderHostBoundaries() {
        XCTAssertTrue(Provider.chatgpt.owns(URL(string: "https://chatgpt.com/c/123")!))
        XCTAssertTrue(Provider.arena.owns(URL(string: "https://arena.ai/text/direct?model_a=max")!))
        XCTAssertTrue(Provider.muse.owns(URL(string: "https://auth.muse.ai/login")!))
        XCTAssertFalse(Provider.muse.owns(URL(string: "https://muse.ai.attacker.example")!))
        XCTAssertFalse(Provider.chatgpt.owns(URL(string: "https://chatgpt.com.attacker.example")!))
        XCTAssertFalse(Provider.claude.owns(URL(string: "https://notclaude.ai")!))
    }
    func testArenaKeepsDirectModeWithoutBreakingAuthentication() {
        XCTAssertEqual(Provider.arena.home.absoluteString, "https://arena.ai/text/direct?model_a=max")
        for path in ["/", "/text", "/text/battle", "/text/side-by-side", "/battle"] {
            XCTAssertEqual(Provider.arena.directModeRedirect(for: URL(string: "https://arena.ai" + path)!), Provider.arena.home)
        }
        for url in ["https://arena.ai/text/direct?model_a=max", "https://arena.ai/login", "https://accounts.google.com"] {
            XCTAssertNil(Provider.arena.directModeRedirect(for: URL(string: url)!))
        }
    }
    func testUnsafeNavigationCannotLaunchFilesOrCommands() {
        for value in ["file:///etc/passwd", "javascript:alert(1)", "http://example.com", "overai://execute", "https://user:password@example.com"] {
            XCTAssertEqual(NavigationPolicy.decision(for: URL(string: value)!, isUserAction: true), .block, value)
        }
        XCTAssertEqual(NavigationPolicy.decision(for: URL(string: "mailto:hi@example.com")!, isUserAction: false), .block)
        XCTAssertEqual(NavigationPolicy.decision(for: URL(string: "mailto:hi@example.com")!, isUserAction: true), .external)
        XCTAssertEqual(NavigationPolicy.decision(for: URL(string: "https://accounts.google.com")!, isUserAction: false), .web)
    }
    func testDownloadNamesStayInsideTheChosenDirectory() {
        XCTAssertEqual(NavigationPolicy.safeFilename("../../private/report.pdf"), "report.pdf")
        XCTAssertEqual(NavigationPolicy.safeFilename(".."), "Download")
        XCTAssertEqual(NavigationPolicy.safeFilename(""), "Download")
        XCTAssertEqual(NavigationPolicy.safeFilename("bad:name.txt"), "bad-name.txt")
        XCTAssertFalse(NavigationPolicy.safeFilename("line\nname.txt").contains("\n"))
    }
    func testMediaRequiresMatchingSecureProviderDocument() {
        let page = URL(string: "https://chatgpt.com/c/123")!
        XCTAssertTrue(MediaAccessPolicy.allows(provider: .chatgpt, page: page, frame: page, originHost: "chatgpt.com", originPort: 443))
        for value in ["http://chatgpt.com", "https://chatgpt.com:8443", "https://evil.example", "https://auth.chatgpt.com", "https://user:password@chatgpt.com"] {
            XCTAssertFalse(MediaAccessPolicy.allows(provider: .chatgpt, page: page, frame: URL(string: value)!, originHost: "chatgpt.com", originPort: 443), value)
        }
        XCTAssertFalse(MediaAccessPolicy.allows(provider: .chatgpt, page: page, frame: page, originHost: "evil.example", originPort: 443))
        XCTAssertFalse(MediaAccessPolicy.allows(provider: .chatgpt, page: page, frame: page, originHost: "chatgpt.com", originPort: 8443))
    }
    func testCustomWebsiteValidationAndHostIsolation() throws {
        let site = try XCTUnwrap(Provider.custom(name: "My AI", address: "example.com/chat"))
        XCTAssertEqual(site.home.absoluteString, "https://example.com/chat")
        XCTAssertTrue(site.owns(URL(string: "https://example.com/conversation")!))
        for value in ["https://evil.example.com", "https://example.com.attacker.test", "https://example.com:8443"] {
            XCTAssertFalse(site.owns(URL(string: value)!))
        }
        for address in ["http://example.com", "file:///etc/passwd", "javascript:alert(1)", "https://user:secret@example.com", "https://", "https://example.com/a\nb"] {
            XCTAssertNil(Provider.custom(name: "Test", address: address), address)
        }
        XCTAssertNil(Provider.custom(name: "  ", address: "https://example.com"))
        let restored = try JSONDecoder().decode(Provider.self, from: JSONEncoder().encode(site))
        XCTAssertEqual(site, restored)
        XCTAssertTrue(restored.isValidSavedWebsite)
    }
    func testCustomWebsiteRejectsInvalidPortsAndSavedIdentity() throws {
        XCTAssertNil(Provider.custom(name: "Wrong port", address: "https://example.com:99999"))
        XCTAssertNil(Provider.custom(name: "Wrong port", address: "https://example.com:0"))
        let valid = try XCTUnwrap(Provider.custom(name: "Secure site", address: "https://example.com:8443/chat"))
        XCTAssertTrue(valid.isValidSavedWebsite)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(valid)) as? [String: Any])
        object["rawValue"] = "chatgpt"
        let forged = try JSONDecoder().decode(Provider.self, from: JSONSerialization.data(withJSONObject: object))
        XCTAssertFalse(forged.isValidSavedWebsite)
    }
    func testRecoveryStopsCrashLoopsAndCanBeResetByTheUser() {
        var budget = RecoveryBudget()
        XCTAssertTrue(budget.consume())
        XCTAssertTrue(budget.consume())
        XCTAssertFalse(budget.consume())
        budget.reset()
        XCTAssertTrue(budget.consume())
    }
}
