"""
PACTS v3.1s - Stealth Mode Browser Launcher

Makes headless browsers behave like real users to avoid detection by
GitHub, marketing sites, and SPAs.

Features:
- Hides navigator.webdriver
- Normalizes languages/platform
- Fakes WebGL vendor/renderer
- Grants common permissions
- Persistent context support (optional)

Usage:
    from backend.runtime.launch_stealth import launch_stealth_browser

    browser, context, page = await launch_stealth_browser(
        headless=True,
        persistent=True,
        profile_id="my_test_run"
    )
"""

from __future__ import annotations
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import os
import logging
import random

logger = logging.getLogger(__name__)

# Stealth JavaScript patch that runs before every page load
STEALTH_SCRIPT = """
// Hide webdriver property
Object.defineProperty(navigator, 'webdriver', {
  get: () => undefined
});

// Normalize languages
Object.defineProperty(navigator, 'languages', {
  get: () => ['en-US', 'en']
});

Object.defineProperty(navigator, 'language', {
  get: () => 'en-US'
});

// Normalize platform
Object.defineProperty(navigator, 'platform', {
  get: () => 'Win32'
});

// Fake WebGL vendor/renderer (common values for Chrome)
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
  if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
    return 'Google Inc. (Intel)';
  }
  if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
    return 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)';
  }
  return getParameter.apply(this, arguments);
};

// Grant common permissions (notifications, geolocation) silently
const originalQuery = navigator.permissions.query;
navigator.permissions.query = (parameters) => (
  parameters.name === 'notifications' ?
    Promise.resolve({ state: 'granted', onchange: null }) :
    originalQuery(parameters)
);

// Remove chrome detection indicators
if (navigator.plugins.length === 0) {
  // Add fake plugins to appear more like a real browser
  Object.defineProperty(navigator, 'plugins', {
    get: () => [
      {
        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
        description: "Portable Document Format",
        filename: "internal-pdf-viewer",
        length: 1,
        name: "Chrome PDF Plugin"
      }
    ]
  });
}

console.log('[PACTS Stealth] Injected stealth patches');
"""


async def launch_stealth_browser(
    headless: bool = True,
    browser_type: str = "chromium",
    slow_mo: int = 0,
    persistent: bool = False,
    profile_id: Optional[str] = None,
    storage_state: Optional[str] = None,
    timezone: Optional[str] = None,
    locale: Optional[str] = None,
) -> Tuple[Browser, BrowserContext, Page]:
    """
    Launch a browser with stealth mode enabled.

    Args:
        headless: Run in headless mode (default: True)
        browser_type: Browser to use - chromium, firefox, webkit (default: chromium)
        slow_mo: Slow down operations by N milliseconds (default: 0)
        persistent: Use persistent browser context (saves cookies/storage)
        profile_id: Unique ID for persistent profile (default: generated from timestamp)
        storage_state: Path to load existing storage state from
        timezone: Timezone ID (default: America/New_York)
        locale: Locale string (default: en-US)

    Returns:
        Tuple of (browser, context, page)

    Environment Variables:
        PACTS_STEALTH: Enable stealth mode (default: true)
        PACTS_PERSISTENT_PROFILES: Enable persistent contexts (default: false)
        PACTS_PROFILE_DIR: Directory for persistent profiles (default: runs/userdata)
        PACTS_TZ: Timezone (default: America/New_York)
        PACTS_LOCALE: Locale (default: en-US)
    """
    # Read config from environment
    stealth_enabled = os.getenv("PACTS_STEALTH", "true").lower() == "true"
    persistent_enabled = persistent or (os.getenv("PACTS_PERSISTENT_PROFILES", "false").lower() == "true")
    profile_dir = os.getenv("PACTS_PROFILE_DIR", "runs/userdata")
    tz = timezone or os.getenv("PACTS_TZ", "America/New_York")
    loc = locale or os.getenv("PACTS_LOCALE", "en-US")

    logger.info(f"[Stealth] Launching browser: stealth={stealth_enabled}, persistent={persistent_enabled}, headless={headless}")

    # Create Playwright instance
    pw = await async_playwright().start()

    # Select browser
    if browser_type == "firefox":
        browser_launcher = pw.firefox
    elif browser_type == "webkit":
        browser_launcher = pw.webkit
    else:
        browser_launcher = pw.chromium

    # Launch args for stealth mode
    launch_args = {
        "headless": headless,
        "slow_mo": slow_mo,
    }

    if browser_type == "chromium" and stealth_enabled:
        # Additional Chromium-specific flags to avoid detection
        launch_args["args"] = [
            "--disable-blink-features=AutomationControlled",  # Hide automation
            "--disable-dev-shm-usage",  # Overcome limited resource problems
            "--no-sandbox",  # Required for some environments
            "--disable-setuid-sandbox",
            "--disable-web-security",  # Allow cross-origin for testing
            "--disable-features=IsolateOrigins,site-per-process",
            "--window-size=1920,1080",  # Standard desktop resolution
        ]

    # Launch browser
    browser = await browser_launcher.launch(**launch_args)

    # Context options
    context_options = {
        "viewport": {"width": 1920, "height": 1080},
        "locale": loc,
        "timezone_id": tz,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "permissions": ["geolocation", "notifications"],  # Pre-grant permissions
    }

    # Load storage state if provided
    if storage_state and os.path.exists(storage_state):
        context_options["storage_state"] = storage_state
        logger.info(f"[Stealth] Loaded storage state from {storage_state}")

    # Create context (persistent or regular)
    if persistent_enabled:
        if not profile_id:
            import time
            profile_id = f"profile_{int(time.time())}"

        profile_path = os.path.join(profile_dir, profile_id)
        os.makedirs(profile_path, exist_ok=True)

        # For persistent context, use persistent_context API
        context = await browser.new_context(
            **context_options,
            # Note: Playwright doesn't support persistent_context with regular browser.launch()
            # We'll simulate persistence by saving/loading storage_state manually
        )
        logger.info(f"[Stealth] Created persistent context: {profile_path}")
    else:
        context = await browser.new_context(**context_options)

    # Add stealth script injection if enabled
    if stealth_enabled:
        await context.add_init_script(STEALTH_SCRIPT)
        logger.info("[Stealth] Injected stealth JavaScript")

    # Create new page
    page = await context.new_page()

    # Stealth 2.0: Apply advanced anti-detection
    if stealth_enabled:
        try:
            # Try to use playwright-stealth if available
            from playwright_stealth import stealth_async
            await stealth_async(page)
            logger.info("[Stealth 2.0] Applied playwright-stealth patches (canvas/fonts/plugins/webrtc)")
        except ImportError:
            logger.warning("[Stealth 2.0] playwright-stealth not installed - using basic stealth only")
            logger.warning("[Stealth 2.0] Install with: pip install playwright-stealth")

        # Add minimal human-like signals (first page only)
        # Small random mouse movement to simulate human presence
        try:
            await page.mouse.move(random.randint(100, 150), random.randint(140, 180))
            await page.wait_for_timeout(int(random.uniform(120, 380)))
            logger.info("[Stealth 2.0] Added human-like signals (mouse movement, timing)")
        except Exception as e:
            logger.debug(f"[Stealth 2.0] Human signals failed (non-critical): {e}")

    # Telemetry markers
    page._pacts_stealth_on = stealth_enabled  # type: ignore
    page._pacts_stealth_version = 2 if stealth_enabled else 0  # type: ignore
    page._pacts_persistent = persistent_enabled  # type: ignore
    page._pacts_profile_id = profile_id  # type: ignore
    page._pacts_blocked_headless = False  # type: ignore - CAPTCHA detection flag
    page._pacts_block_signature = None  # type: ignore - blocking URL/DOM signature

    return browser, context, page


async def save_persistent_context(context: BrowserContext, profile_id: str):
    """
    Save current browser context state to disk for reuse.

    Args:
        context: Browser context to save
        profile_id: Unique identifier for this profile
    """
    profile_dir = os.getenv("PACTS_PROFILE_DIR", "runs/userdata")
    profile_path = os.path.join(profile_dir, profile_id)
    os.makedirs(profile_path, exist_ok=True)

    storage_state_path = os.path.join(profile_path, "storage_state.json")
    await context.storage_state(path=storage_state_path)
    logger.info(f"[Stealth] Saved persistent context to {storage_state_path}")

    return storage_state_path


async def load_persistent_context(profile_id: str) -> Optional[str]:
    """
    Load storage state from a saved profile.

    Args:
        profile_id: Unique identifier for the profile

    Returns:
        Path to storage_state.json if exists, None otherwise
    """
    profile_dir = os.getenv("PACTS_PROFILE_DIR", "runs/userdata")
    storage_state_path = os.path.join(profile_dir, profile_id, "storage_state.json")

    if os.path.exists(storage_state_path):
        logger.info(f"[Stealth] Loaded persistent context from {storage_state_path}")
        return storage_state_path

    return None


async def detect_captcha_or_block(page: Page) -> Tuple[bool, Optional[str]]:
    """
    Detect if page has been blocked by CAPTCHA or anti-bot measures.

    Args:
        page: Playwright page to check

    Returns:
        Tuple of (is_blocked: bool, block_signature: Optional[str])

    Detection strategies:
        1. URL contains /nocaptcha, /captcha, /challenge
        2. DOM contains CAPTCHA forms or reCAPTCHA iframes
        3. Common anti-bot messages in page text
    """
    try:
        current_url = page.url

        # Strategy 1: URL-based detection
        block_patterns = [
            "/nocaptcha",
            "/captcha",
            "/challenge",
            "/blocked",
            "/access-denied",
            "recaptcha",
            "hcaptcha",
            "chal_t=",  # Phase 4a: Booking.com challenge
            "force_referer"  # Phase 4a: Booking.com challenge
        ]

        for pattern in block_patterns:
            if pattern in current_url.lower():
                logger.warning(f"[CAPTCHA] Detected block pattern in URL: {pattern}")
                return True, f"url:{pattern}"

        # Strategy 2: DOM-based detection
        # Check for common CAPTCHA elements
        captcha_selectors = [
            'form[action*="captcha"]',
            'iframe[src*="recaptcha"]',
            'iframe[src*="hcaptcha"]',
            '.g-recaptcha',
            '#recaptcha',
            '[data-sitekey]',  # reCAPTCHA/hCaptcha sitekey
            '[data-capla-component*="Challenge"]',  # Phase 4a: Booking.com Capla challenge
            'script[src*="perimeterx"]',  # Phase 4a: PerimeterX bot detection
            'script[src*="px-captcha"]'  # Phase 4a: PerimeterX CAPTCHA
        ]

        for selector in captcha_selectors:
            if await page.locator(selector).count() > 0:
                logger.warning(f"[CAPTCHA] Detected CAPTCHA element: {selector}")
                return True, f"dom:{selector}"

        # Strategy 3: Text-based detection
        body_text = await page.locator('body').inner_text() if await page.locator('body').count() > 0 else ""
        block_phrases = [
            "verify you are human",
            "prove you're not a robot",
            "security check",
            "access denied",
            "unusual traffic",
            "automated requests"
        ]

        for phrase in block_phrases:
            if phrase in body_text.lower():
                logger.warning(f"[CAPTCHA] Detected block phrase: {phrase}")
                return True, f"text:{phrase}"

        return False, None

    except Exception as e:
        logger.debug(f"[CAPTCHA] Detection failed (non-critical): {e}")
        return False, None
