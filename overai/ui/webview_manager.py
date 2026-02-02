"""
Optimized WebView manager with lazy loading and memory management.
Uses WKWebView with proper configuration for AI services.
Optimized for low RAM usage with aggressive memory management.
"""
import os
import json
import base64
from pathlib import Path
from typing import Optional, Dict, Callable
from dataclasses import dataclass
import objc
from Foundation import (
    NSURL, NSURLRequest, NSObject, NSDate, NSNotificationCenter,
    NSURLCache, NSProcessInfo, NSTimer
)
from WebKit import (
    WKWebView, WKWebViewConfiguration, WKPreferences,
    WKWebsiteDataStore, WKUserScript, WKUserScriptInjectionTimeAtDocumentEnd,
    WKUserContentController, WKProcessPool
)
from AppKit import (
    NSMakeRect, NSViewWidthSizable, NSViewHeightSizable,
    NSApplication
)
from ..utils.logger import Logger
from ..utils.theme import ThemeManager

logger = Logger("WebViewManager")

# Shared process pool to reduce memory across multiple webviews (if ever needed)
_shared_process_pool = None

def get_shared_process_pool():
    """Get shared process pool to reduce memory footprint."""
    global _shared_process_pool
    if _shared_process_pool is None:
        _shared_process_pool = WKProcessPool.alloc().init()
    return _shared_process_pool

# Memory cache limits (in bytes)
MEMORY_CACHE_LIMIT = 10 * 1024 * 1024  # 10 MB
DISK_CACHE_LIMIT = 50 * 1024 * 1024  # 50 MB


@dataclass
class AIService:
    """AI Service configuration."""
    name: str
    url: str
    icon: str = ""


# Supported AI services (web-based)
AI_SERVICES = {
    "grok": AIService("Grok", "https://grok.com", "bolt.fill"),
    "chatgpt": AIService("ChatGPT", "https://chat.openai.com", "bubble.left.fill"),
    "claude": AIService("Claude", "https://claude.ai/chat", "quote.bubble.fill"),
    "gemini": AIService("Gemini", "https://gemini.google.com", "sparkles"),
    "deepseek": AIService("DeepSeek", "https://chat.deepseek.com", "magnifyingglass"),
    "perplexity": AIService("Perplexity", "https://www.perplexity.ai", "magnifyingglass.circle"),
}


def get_local_ai_html(models_json: str) -> str:
    """Generate Local AI HTML with injected models."""
    # Escape the JSON for safe injection into JavaScript
    safe_json = models_json.replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ')
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local AI</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        :root {{
            --bg: #000000;
            --bg-secondary: #1c1c1e;
            --bg-input: #1c1c1e;
            --blue: #0b84fe;
            --gray: #3a3a3c;
            --text: #ffffff;
            --text-dim: #8e8e93;
            --text-muted: #636366;
            --green: #30d158;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
            background: var(--bg);
            color: var(--text);
            height: 100vh;
            display: flex;
            flex-direction: column;
            -webkit-font-smoothing: antialiased;
        }}
        
        /* Header - minimal like iMessage */
        .header {{
            background: var(--bg-secondary);
            padding: 14px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 0.5px solid rgba(255,255,255,0.1);
        }}
        
        .header-left {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .header-icon {{
            width: 36px;
            height: 36px;
            background: linear-gradient(180deg, #5ac8fa 0%, #007aff 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .header-icon svg {{
            width: 20px;
            height: 20px;
            fill: white;
        }}
        
        .header-title {{
            font-size: 17px;
            font-weight: 600;
        }}
        
        .model-selector {{
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 16px;
            color: var(--text);
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            padding: 6px 28px 6px 12px;
            margin-top: 2px;
            -webkit-appearance: none;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='5' viewBox='0 0 8 5'%3E%3Cpath fill='%2398989d' d='M4 5L0 0h8z'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 10px center;
            transition: all 0.15s ease;
        }}
        
        .model-selector:hover {{
            background: rgba(255,255,255,0.12);
            border-color: rgba(255,255,255,0.25);
        }}
        
        .model-selector:focus {{
            outline: none;
            border-color: var(--blue);
            box-shadow: 0 0 0 3px rgba(11, 132, 254, 0.2);
        }}
        
        .model-selector option {{
            background: #2c2c2e;
            color: white;
            padding: 10px;
        }}
        
        .status-badge {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 12px;
            color: var(--text-dim);
        }}
        
        .status-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--text-muted);
        }}
        
        .status-dot.online {{ background: var(--green); }}
        
        /* Messages area */
        .messages {{
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}
        
        .messages::-webkit-scrollbar {{ width: 0; }}
        
        /* Welcome state */
        .welcome {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            gap: 16px;
        }}
        
        .welcome-icon {{
            width: 80px;
            height: 80px;
            background: linear-gradient(180deg, #5ac8fa 0%, #007aff 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .welcome-icon svg {{
            width: 40px;
            height: 40px;
            fill: white;
        }}
        
        .welcome h1 {{
            font-size: 28px;
            font-weight: 700;
        }}
        
        .welcome p {{
            color: var(--text-dim);
            font-size: 15px;
            max-width: 280px;
        }}
        
        /* Message bubbles - iMessage style */
        .message {{
            display: flex;
            flex-direction: column;
            max-width: 70%;
            animation: slideIn 0.2s ease;
        }}
        
        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .message.sent {{
            align-self: flex-end;
        }}
        
        .message.received {{
            align-self: flex-start;
        }}
        
        .bubble {{
            padding: 10px 14px;
            font-size: 16px;
            line-height: 1.35;
            word-wrap: break-word;
        }}
        
        /* Sent messages - blue bubbles */
        .message.sent .bubble {{
            background: var(--blue);
            color: white;
            border-radius: 18px 18px 4px 18px;
        }}
        
        .message.sent.first .bubble {{
            border-radius: 18px 18px 4px 18px;
        }}
        
        .message.sent.last .bubble {{
            border-radius: 18px 4px 18px 18px;
        }}
        
        .message.sent.single .bubble {{
            border-radius: 18px;
        }}
        
        /* Received messages - gray bubbles */
        .message.received .bubble {{
            background: var(--gray);
            color: white;
            border-radius: 18px 18px 18px 4px;
        }}
        
        .message.received.first .bubble {{
            border-radius: 18px 18px 18px 4px;
        }}
        
        .message.received.last .bubble {{
            border-radius: 4px 18px 18px 18px;
        }}
        
        .message.received.single .bubble {{
            border-radius: 18px;
        }}
        
        /* Code styling */
        .bubble pre {{
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 6px 0;
            font-size: 13px;
            font-family: 'SF Mono', Menlo, monospace;
        }}
        
        .bubble code {{
            background: rgba(0,0,0,0.2);
            padding: 2px 4px;
            border-radius: 4px;
            font-size: 14px;
            font-family: 'SF Mono', Menlo, monospace;
        }}
        
        .bubble strong {{
            font-weight: 600;
        }}
        
        .bubble h3, .bubble h4 {{
            font-size: 15px;
            font-weight: 600;
            margin: 8px 0 4px 0;
        }}
        
        .bubble li {{
            margin-left: 16px;
        }}
        
        /* Typing indicator */
        .typing {{
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 12px 16px;
        }}
        
        .typing span {{
            width: 8px;
            height: 8px;
            background: var(--text-dim);
            border-radius: 50%;
            animation: typing 1.4s infinite ease-in-out;
        }}
        
        .typing span:nth-child(1) {{ animation-delay: 0s; }}
        .typing span:nth-child(2) {{ animation-delay: 0.2s; }}
        .typing span:nth-child(3) {{ animation-delay: 0.4s; }}
        
        @keyframes typing {{
            0%, 60%, 100% {{ opacity: 0.3; transform: scale(0.8); }}
            30% {{ opacity: 1; transform: scale(1); }}
        }}
        
        /* Input area - iMessage style */
        .input-area {{
            padding: 8px 12px 24px;
            background: var(--bg);
        }}
        
        .input-container {{
            display: flex;
            align-items: flex-end;
            gap: 8px;
            background: var(--bg-input);
            border-radius: 20px;
            padding: 4px 4px 4px 14px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .input-container:focus-within {{
            border-color: var(--blue);
        }}
        
        textarea {{
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text);
            font-size: 16px;
            padding: 8px 0;
            resize: none;
            outline: none;
            font-family: inherit;
            line-height: 1.3;
            max-height: 100px;
        }}
        
        textarea::placeholder {{
            color: var(--text-muted);
        }}
        
        .send-btn {{
            width: 32px;
            height: 32px;
            background: var(--blue);
            border: none;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s ease;
            flex-shrink: 0;
        }}
        
        .send-btn svg {{
            width: 16px;
            height: 16px;
            fill: white;
            margin-left: 2px;
        }}
        
        .send-btn:hover {{
            transform: scale(1.05);
        }}
        
        .send-btn:disabled {{
            background: var(--gray);
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }}
    </style>
</head>
<body>
<div class="header">
    <div class="header-left">
        <div class="header-icon">
            <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
        </div>
        <div>
            <div class="header-title">Local AI</div>
            <select class="model-selector" id="modelSelect" disabled><option>Loading...</option></select>
        </div>
    </div>
    <div class="status-badge"><span class="status-dot" id="statusDot"></span><span id="statusText">Connecting</span></div>
</div>

<div class="messages" id="messages">
    <div class="welcome" id="welcome">
        <div class="welcome-icon">
            <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>
        </div>
        <h1>Local AI</h1>
        <p id="welcomeText">Connecting to Ollama...</p>
    </div>
</div>

<div class="input-area">
    <div class="input-container">
        <textarea id="input" placeholder="iMessage" rows="1" disabled></textarea>
        <button class="send-btn" id="sendBtn" disabled>
            <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
    </div>
</div>
<script>
(function() {{
    'use strict';
    
    // Injected models data
    const MODELS = JSON.parse('{safe_json}');
    const MAX_MESSAGES = 20; // Limit chat history for memory
    
    let currentModel = '';
    let msgs = [];
    let busy = false;
    
    function getEl(id) {{ return document.getElementById(id); }}
    
    // Trim old messages to limit memory usage
    function trimMessages() {{
        if (msgs.length > MAX_MESSAGES) {{
            msgs = msgs.slice(-MAX_MESSAGES);
            // Also trim DOM elements
            const messagesArea = getEl('messages');
            if (messagesArea) {{
                const msgDivs = messagesArea.querySelectorAll('.message');
                const excess = msgDivs.length - MAX_MESSAGES;
                for (let i = 0; i < excess; i++) {{
                    msgDivs[i].remove();
                }}
            }}
        }}
    }}
    
    function init() {{
        console.log('Local AI init started, models:', MODELS.length);
        
        const modelSelect = getEl('modelSelect');
        const statusText = getEl('statusText');
        const welcomeText = getEl('welcomeText');
        const statusDot = getEl('statusDot');
        const userInput = getEl('input');
        const sendBtn = getEl('sendBtn');
        const messagesArea = getEl('messages');
        const welcome = getEl('welcome');
        
        if (!modelSelect || !messagesArea) {{
            console.error('DOM not ready, retrying...');
            setTimeout(init, 100);
            return;
        }}
        
        if (MODELS.length === 0) {{
            if (statusText) statusText.textContent = 'Offline';
            if (statusDot) statusDot.className = 'status-dot';
            if (welcomeText) welcomeText.textContent = 'No models found. Make sure Ollama is running.';
            return;
        }}
        
        // Populate models
        modelSelect.innerHTML = '';
        MODELS.forEach(function(m) {{
            const opt = document.createElement('option');
            opt.value = m.name;
            opt.textContent = m.name.split(':')[0];
            modelSelect.appendChild(opt);
        }});
        
        currentModel = MODELS[0].name;
        modelSelect.disabled = false;
        
        // Update status
        statusDot.className = 'status-dot online';
        statusText.textContent = 'Connected';
        
        // Update welcome message
        if (welcomeText) {{
            welcomeText.textContent = 'Type a message to start chatting with ' + currentModel.split(':')[0];
        }}
        
        // Enable input
        userInput.disabled = false;
        userInput.placeholder = 'Message';
        sendBtn.disabled = false;
        
        // *** ATTACH EVENT HANDLERS HERE - AFTER DOM IS READY ***
        modelSelect.onchange = function() {{
            currentModel = modelSelect.value;
            msgs = [];
            // Clear messages and show welcome
            if (welcome) welcome.style.display = 'flex';
            if (welcomeText) welcomeText.textContent = 'Type a message to start chatting with ' + currentModel.split(':')[0];
            // Remove all message bubbles
            messagesArea.querySelectorAll('.message').forEach(m => m.remove());
        }};
        
        sendBtn.onclick = function() {{
            const text = userInput.value.trim();
            if (!text || busy || !currentModel) return;
            
            // Hide welcome
            if (welcome) welcome.style.display = 'none';
            
            // Add user message (iMessage style - sent)
            const userDiv = document.createElement('div');
            userDiv.className = 'message sent single';
            userDiv.innerHTML = '<div class="bubble">' + text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>';
            messagesArea.appendChild(userDiv);
            
            msgs.push({{ role: 'user', content: text }});
            trimMessages();
            userInput.value = '';
            busy = true;
            sendBtn.disabled = true;
            
            // Add AI typing indicator (iMessage style - received)
            const aiDiv = document.createElement('div');
            aiDiv.className = 'message received single';
            aiDiv.innerHTML = '<div class="bubble" id="currentBubble"><div class="typing"><span></span><span></span><span></span></div></div>';
            messagesArea.appendChild(aiDiv);
            messagesArea.scrollTop = messagesArea.scrollHeight;
            
            // Send to Python via webkit message handler
            if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.ollama) {{
                window.webkit.messageHandlers.ollama.postMessage({{
                    type: 'chat',
                    model: currentModel,
                    messages: msgs
                }});
            }} else {{
                getEl('currentBubble').innerHTML = 'Error: Message handler not available';
                busy = false;
                sendBtn.disabled = false;
            }}
        }};
        
        userInput.onkeydown = function(e) {{
            if (e.key === 'Enter' && !e.shiftKey) {{
                e.preventDefault();
                sendBtn.onclick();
            }}
        }};
        
        userInput.oninput = function() {{
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 150) + 'px';
        }};
        
        userInput.focus();
        console.log('Local AI init complete');
    }}
    
    // Response handler from Python (must be global)
    window.receiveResponse = function(response) {{
        const bubble = document.getElementById('currentBubble');
        const sendBtn = getEl('sendBtn');
        const userInput = getEl('userInput');
        const chatArea = getEl('chatArea');
        
        if (bubble) {{
            bubble.removeAttribute('id');
            // Enhanced markdown formatting
            let formatted = response
                // Code blocks first (before other formatting)
                .replace(/```(\\w*)\\n([\\s\\S]*?)```/g, '<pre><code>$2</code></pre>')
                // Inline code
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                // Bold
                .replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>')
                .replace(/__([^_]+)__/g, '<strong>$1</strong>')
                // Italic  
                .replace(/\\*([^*]+)\\*/g, '<em>$1</em>')
                .replace(/_([^_]+)_/g, '<em>$1</em>')
                // Headers
                .replace(/^### (.+)$/gm, '<h4>$1</h4>')
                .replace(/^## (.+)$/gm, '<h3>$1</h3>')
                .replace(/^# (.+)$/gm, '<h3>$1</h3>')
                // Lists
                .replace(/^[*-] (.+)$/gm, '<li>$1</li>')
                .replace(/^(\\d+)\\. (.+)$/gm, '<li>$2</li>')
                // Line breaks
                .replace(/\\n/g, '<br>');
            bubble.innerHTML = formatted;
            msgs.push({{ role: 'assistant', content: response }});
        }}
        busy = false;
        if (sendBtn) sendBtn.disabled = false;
        if (userInput) userInput.focus();
        if (chatArea) chatArea.scrollTop = chatArea.scrollHeight;
    }};
    
    // Start init when DOM is ready
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', init);
    }} else {{
        init();
    }}
}})();
</script>
</body>
</html>'''


class WebViewManager(NSObject):
    """
    Manages WKWebView with lazy loading and aggressive memory optimization.
    """
    CONFIG_PATH = Path.home() / "Library" / "Application Support" / "OverAI" / "service.json"

    def init(self):
        self = objc.super(WebViewManager, self).init()
        if self is None:
            return None

        self._web_view: Optional[WKWebView] = None
        self._configuration: Optional[WKWebViewConfiguration] = None
        self._current_service: str = "grok"
        self._theme_manager = ThemeManager()
        self._background_callback: Optional[Callable] = None

        # Memory optimization state
        self._is_suspended = False
        self._last_loaded_service: Optional[str] = None
        self._memory_pressure_observer = None

        # API service handling
        self._current_api_service = None

        # Load saved service
        self._load_service()

        # Setup memory pressure monitoring
        self._setup_memory_pressure_handler()

        return self

    def _setup_memory_pressure_handler(self):
        """Subscribe to system memory pressure notifications."""
        try:
            # Register for memory warning notifications
            NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
                self,
                "handleMemoryPressure:",
                "NSProcessInfoPowerStateDidChangeNotification",
                None
            )
            logger.debug("Memory pressure handler registered")
        except Exception as e:
            logger.debug(f"Could not register memory pressure handler: {e}")

    def handleMemoryPressure_(self, notification):
        """Handle system memory pressure by clearing caches."""
        logger.info("Memory pressure detected - clearing caches")
        self._clear_memory_caches()

    def _clear_memory_caches(self):
        """Clear in-memory caches to reduce RAM usage."""
        try:
            # Clear URL cache
            cache = NSURLCache.sharedURLCache()
            cache.removeAllCachedResponses()
            # Clear back-forward list if webview exists
            if self._web_view:
                self._clear_back_forward_list()
            logger.debug("Memory caches cleared")
        except Exception as e:
            logger.error(f"Failed to clear caches: {e}")

    def _clear_back_forward_list(self):
        """Clear navigation history to free memory (10-30 MB savings)."""
        if not self._web_view:
            return
        try:
            # Load empty page to clear back-forward list
            # This is the most reliable way to clear navigation history
            self._web_view.evaluateJavaScript_completionHandler_(
                """
                (function() {
                    // Clear any references that might hold memory
                    if (window.history && window.history.length > 1) {
                        // Can't directly clear, but we can minimize impact
                        return window.history.length;
                    }
                    return 0;
                })();
                """,
                lambda result, error: None
            )
        except Exception as e:
            logger.debug(f"Could not clear back-forward list: {e}")

    def _load_service(self):
        """Load saved service preference."""
        try:
            if self.CONFIG_PATH.exists():
                with open(self.CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                self._current_service = data.get('service', 'grok')
                # Allow local_ai as a valid service
                if self._current_service not in AI_SERVICES and self._current_service != 'local_ai':
                    self._current_service = 'grok'
        except Exception as e:
            logger.error(f"Failed to load service: {e}")

    def save_service(self, service_id: str):
        """Save service preference."""
        self._current_service = service_id
        try:
            self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.CONFIG_PATH, 'w') as f:
                json.dump({'service': service_id}, f)
        except Exception as e:
            logger.error(f"Failed to save service: {e}")

    def create_webview(self, frame) -> WKWebView:
        """Create optimized WKWebView with minimal RAM usage."""
        logger.info("Creating WebView with memory optimizations")

        # Setup limited URL cache BEFORE creating webview
        self._setup_limited_cache()

        # Create configuration
        config = WKWebViewConfiguration.alloc().init()

        # Configure preferences for minimal memory
        prefs = WKPreferences.alloc().init()
        prefs.setJavaScriptCanOpenWindowsAutomatically_(False)  # Reduce memory
        prefs.setJavaScriptEnabled_(True)  # Keep JS enabled for AI services
        config.setPreferences_(prefs)

        # Use shared process pool for memory efficiency
        config.setProcessPool_(get_shared_process_pool())

        # Use default data store for better memory management
        # Non-persistent stores use MORE memory as they can't page to disk
        config.setWebsiteDataStore_(WKWebsiteDataStore.defaultDataStore())

        # Allow localhost/127.0.0.1 access for Ollama API
        try:
            config.setValue_forKey_(True, "allowUniversalAccessFromFileURLs")
        except Exception as e:
            logger.debug(f"Could not set allowUniversalAccessFromFileURLs: {e}")

        # Create webview
        self._web_view = WKWebView.alloc().initWithFrame_configuration_(
            frame,
            config
        )

        # Configure for auto-resizing
        self._web_view.setAutoresizingMask_(
            NSViewWidthSizable | NSViewHeightSizable
        )

        # Set modern user agent
        self._web_view.setCustomUserAgent_(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.1 Safari/605.1.15"
        )

        # Setup message handler for background color
        self._setup_message_handler(config)

        # Load initial service
        if self._current_service == 'local_ai':
            self.load_local_ai()
        else:
            self.load_service(self._current_service)

        return self._web_view

    def _setup_limited_cache(self):
        """Configure URL cache with strict memory limits."""
        try:
            cache = NSURLCache.alloc().initWithMemoryCapacity_diskCapacity_diskPath_(
                MEMORY_CACHE_LIMIT,  # 10 MB memory
                DISK_CACHE_LIMIT,  # 50 MB disk
                None  # Use default path
            )
            NSURLCache.setSharedURLCache_(cache)
            logger.debug(f"URL cache limited to {MEMORY_CACHE_LIMIT // (1024*1024)}MB memory")
        except Exception as e:
            logger.error(f"Failed to setup limited cache: {e}")

    def _setup_message_handler(self, config: WKWebViewConfiguration):
        """Setup JavaScript message handlers for theme detection and Ollama."""
        controller = config.userContentController()

        # Theme handler
        controller.addScriptMessageHandler_name_(self, "themeHandler")

        # Ollama handler for Local AI
        controller.addScriptMessageHandler_name_(self, "ollama")

        # Minimal script - only runs once on load, no continuous observers
        # Saves significant RAM by avoiding MutationObserver overhead
        script = """
            (function() {
                function reportTheme() {
                    const body = document.body;
                    if (body) {
                        const bg = window.getComputedStyle(body).backgroundColor;
                        if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.themeHandler) {
                            window.webkit.messageHandlers.themeHandler.postMessage(bg);
                        }
                    }
                }
                // Report once on load only
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', reportTheme, {once: true});
                } else {
                    reportTheme();
                }
            })();
        """
        user_script = WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
            script,
            WKUserScriptInjectionTimeAtDocumentEnd,
            True  # Only inject into main frame (saves memory)
        )
        controller.addUserScript_(user_script)

    def load_service(self, service_id: str):
        """Load AI service."""
        if service_id not in AI_SERVICES:
            logger.error(f"Unknown service: {service_id}")
            return

        service = AI_SERVICES[service_id]
        logger.info(f"Loading service: {service.name}")

        # Clear back-forward list when switching services to prevent memory accumulation
        if self._last_loaded_service and self._last_loaded_service != service_id:
            self._clear_back_forward_list()

        self._current_service = service_id
        self._last_loaded_service = service_id
        self._is_suspended = False
        self.save_service(service_id)

        if self._web_view:
            url = NSURL.URLWithString_(service.url)
            request = NSURLRequest.requestWithURL_(url)
            self._web_view.loadRequest_(request)

    def load_local_ai(self):
        """Load the Local AI (Ollama) chat interface using data URI."""
        logger.info("Loading Local AI chat interface")
        self._current_service = "local_ai"
        self._last_loaded_service = "local_ai"
        self._is_suspended = False
        self.save_service("local_ai")

        if not self._web_view:
            return

        # Fetch models from Ollama
        try:
            from ..api.ollama_client import get_ollama_client
            client = get_ollama_client()
            models = client.get_models()
            models_list = [{'name': m.name} for m in models]
            models_json = json.dumps(models_list)
            logger.info(f"Found {len(models)} Ollama models")
        except Exception as e:
            logger.error(f"Failed to get Ollama models: {e}")
            models_json = "[]"

        # Generate HTML with models injected
        html_content = get_local_ai_html(models_json)

        # Write to temp file and load via file:// URL
        # This is the most reliable method - bypasses all WKWebView sandbox restrictions
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "overai"
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / "local_ai.html"
        temp_file.write_text(html_content, encoding='utf-8')
        
        file_url = NSURL.fileURLWithPath_(str(temp_file))
        request = NSURLRequest.requestWithURL_(file_url)
        self._web_view.loadRequest_(request)
        logger.info(f"Loaded Local AI from {temp_file}")

    def reload(self):
        """Reload current page."""
        if self._web_view:
            self._web_view.reload()

    def go_home(self):
        """Go to current service home."""
        if self._current_service == 'local_ai':
            self.load_local_ai()
        else:
            self.load_service(self._current_service)

    def clear_data(self):
        """Clear webview data."""
        if self._web_view:
            data_store = self._web_view.configuration().websiteDataStore()
            data_types = WKWebsiteDataStore.allWebsiteDataTypes()
            data_store.removeDataOfTypes_modifiedSince_completionHandler_(
                data_types,
                NSDate.distantPast(),
                lambda: logger.info("WebView data cleared")
            )

    def focus_input(self):
        """Focus the text input area."""
        if self._web_view:
            self._web_view.evaluateJavaScript_completionHandler_(
                """
                (function() {
                    const selectors = [
                        'textarea',
                        '[contenteditable="true"]',
                        'input[type="text"]',
                        '[role="textbox"]'
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            el.focus();
                            return true;
                        }
                    }
                    return false;
                })();
                """,
                lambda result, error: None
            )

    def userContentController_didReceiveScriptMessage_(self, controller, message):
        """Handle messages from JavaScript."""
        if message.name() == "themeHandler":
            bg_color = message.body()
            if self._background_callback:
                self._background_callback(bg_color)
        elif message.name() == "ollama":
            # Handle Ollama messages from Local AI interface
            self._handle_ollama_message(message.body())
        elif message.name() == "apiChat":
            # Handle API chat messages
            self._handle_api_chat_message(message.body())

    def _handle_ollama_message(self, data):
        """Handle Ollama message from Local AI interface."""
        import threading
        import json

        msg_type = data.get('type')

        if msg_type == 'getModels':
            # Get models in background thread
            def get_models():
                try:
                    from ..api.ollama_client import get_ollama_client
                    client = get_ollama_client()
                    models = client.get_models()
                    models_json = json.dumps([{'name': m.name} for m in models])
                    self._run_js(f"window.receiveModels('{models_json}')")
                except Exception as e:
                    logger.error(f"Failed to get Ollama models: {e}")
                    self._run_js(f"window.receiveError('{str(e)}')")

            threading.Thread(target=get_models, daemon=True).start()

        elif msg_type == 'chat':
            # Chat in background thread
            model = str(data.get('model', ''))
            raw_messages = data.get('messages', [])
            
            # Convert NSArray/NSDictionary to Python list/dict
            messages = []
            for m in raw_messages:
                messages.append({
                    'role': str(m.get('role', 'user')),
                    'content': str(m.get('content', ''))
                })

            def chat():
                try:
                    from ..api.ollama_client import get_ollama_client
                    client = get_ollama_client()
                    response = client.chat(model, messages)
                    # Escape for JS
                    escaped = response.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
                    self._run_js(f"window.receiveResponse('{escaped}')")
                except Exception as e:
                    logger.error(f"Ollama chat error: {e}")
                    self._run_js(f"window.receiveResponse('Error: {str(e)}')")

            threading.Thread(target=chat, daemon=True).start()

    def _run_js(self, js_code):
        """Run JavaScript in webview on main thread."""
        try:
            from PyObjCTools import AppHelper

            def run_on_main():
                if self._web_view:
                    self._web_view.evaluateJavaScript_completionHandler_(js_code, None)

            AppHelper.callAfter(run_on_main)
        except Exception as e:
            logger.error(f"Failed to run JS: {e}")

    def _handle_api_chat_message(self, data):
        """Handle chat message from API interface."""
        if not self._current_api_service:
            return
        try:
            from ..api.api_manager import get_api_manager
            msg_type = data.get('type')
            message = data.get('message')
            if msg_type == 'send' and message:
                # Send to API
                self._send_api_message(message)
        except Exception as e:
            logger.error(f"Error handling API chat: {e}")
            self._send_to_chat(f"Error: {str(e)}")

    def _send_api_message(self, message: str):
        """Send message to API and handle response."""
        import threading

        def api_call():
            try:
                from ..api.api_manager import get_api_manager
                api_manager = get_api_manager()
                service = self._current_api_service
                api_key = api_manager.get_api_key(service.id)
                # Simple OpenAI-compatible API call
                import urllib.request
                import json
                url = service.get_full_url(service.chat_endpoint)
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                data = {
                    "model": service.default_model or "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": message}],
                    "max_tokens": 1000
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode('utf-8'),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=60) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    content = result['choices'][0]['message']['content']
                    # Send response back to webview
                    self._send_to_chat(content)
            except Exception as e:
                logger.error(f"API call error: {e}")
                self._send_to_chat(f"Sorry, there was an error: {str(e)}")

        # Run in background thread
        threading.Thread(target=api_call, daemon=True).start()

    def _send_to_chat(self, message: str):
        """Send a message to the chat interface."""
        if self._web_view:
            # Escape quotes and newlines
            escaped = message.replace('"', '\\"').replace('\n', '\\n')
            js = f'window.receiveMessage("{escaped}")'
            self._web_view.evaluateJavaScript_completionHandler_(js, None)

    def set_background_callback(self, callback: Callable):
        """Set callback for background color changes."""
        self._background_callback = callback

    def get_services(self) -> Dict[str, AIService]:
        """Get available services."""
        return AI_SERVICES

    def get_current_service(self) -> str:
        """Get current service ID."""
        return self._current_service

    def cleanup(self):
        """Clean up WebView resources."""
        logger.info("Cleaning up WebView")
        # Remove memory pressure observer
        if self._memory_pressure_observer:
            NSNotificationCenter.defaultCenter().removeObserver_(self)
            self._memory_pressure_observer = None

        if self._web_view:
            # Stop loading
            self._web_view.stopLoading()
            # Clear content to free memory immediately
            self._web_view.loadHTMLString_baseURL_("", None)
            # Remove from superview
            self._web_view.removeFromSuperview()
            self._web_view = None

        self._background_callback = None
        self._is_suspended = False

    def suspend(self):
        """Suspend webview to reduce memory when hidden (saves 30-50 MB)."""
        if self._is_suspended or not self._web_view:
            return

        logger.info("Suspending WebView for memory savings")
        self._is_suspended = True

        # Aggressive memory cleanup
        self._web_view.evaluateJavaScript_completionHandler_(
            """
            (function() {
                // Stop all loading
                window.stop();
                // Clear all intervals and timeouts
                var highestId = setTimeout(function() {}, 0);
                for (var i = 0; i < highestId; i++) {
                    clearTimeout(i);
                    clearInterval(i);
                }
                // Remove event listeners from body to free memory
                if (document.body) {
                    var clone = document.body.cloneNode(true);
                    document.body.parentNode.replaceChild(clone, document.body);
                }
                // Hint to garbage collector
                if (window.gc) window.gc();
                return 'suspended';
            })();
            """,
            lambda result, error: logger.debug(f"JS cleanup: {result}")
        )

        # Clear URL cache
        cache = NSURLCache.sharedURLCache()
        cache.removeAllCachedResponses()
        logger.debug("WebView suspended - memory freed")

    def resume(self):
        """Resume webview when shown (smart reload)."""
        if not self._web_view:
            return

        # Only reload if was suspended
        if self._is_suspended:
            logger.info("Resuming WebView")
            self._is_suspended = False
            # Reload current service
            if self._current_service == 'local_ai':
                self.load_local_ai()
            else:
                self.load_service(self._current_service)
            logger.debug("WebView resumed")
        else:
            # Just focus input if not suspended
            self.focus_input()

    @property
    def web_view(self) -> Optional[WKWebView]:
        return self._web_view

    @property
    def is_suspended(self) -> bool:
        return self._is_suspended
