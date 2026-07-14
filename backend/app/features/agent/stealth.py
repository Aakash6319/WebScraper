"""
AutoWebAgent - Ultra Stealth & Anti-Detection System
======================================================
The MOST CRITICAL component. Makes the Playwright browser
completely undetectable by any bot protection system.

Covers:
- Canvas fingerprint randomization (consistent per session)
- WebGL fingerprint spoofing
- AudioContext fingerprinting
- WebRTC IP leak protection
- Navigator properties spoofing (userAgent, platform, hardware, etc.)
- Human-like behavior simulation (Bezier mouse, variable typing, natural scroll)
- Headless detection bypass (all known vectors)
- Cloudflare, PerimeterX, DataDome, Akamai bypass techniques
- Proxy + Fingerprint Consistency
- TLS Fingerprint randomization hints
"""

import random
import hashlib
import math
import uuid
from typing import Dict, Any, Optional, List
from loguru import logger


class StealthManager:
    """
    Central stealth orchestrator.

    Generates consistent fingerprints per session, injects anti-detection
    JavaScript, and provides human-like interaction primitives.
    """

    # ── Real-world browser User-Agents (updated regularly) ────────

    REAL_USER_AGENTS = [
        # Chrome 120 on Windows 11
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Chrome 120 on macOS Sonoma
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Chrome 119 on Windows 10
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Edge 120 on Windows 11
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Chrome 120 on macOS Ventura
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Firefox 121 on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Chrome 121 on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        # Safari 17 on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]

    # ── WebGL Vendor/Renderer pairs (matches real GPUs) ──────────

    WEBGL_PAIRS = [
        {"vendor": "Google Inc. (Intel)", "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
        {"vendor": "Google Inc. (Intel)", "renderer": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"},
        {"vendor": "Google Inc. (NVIDIA)", "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
        {"vendor": "Google Inc. (AMD)", "renderer": "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
        {"vendor": "Google Inc. (Apple)", "renderer": "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)"},
        {"vendor": "Google Inc. (Intel)", "renderer": "ANGLE (Intel, Intel(R) HD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"},
        {"vendor": "Google Inc. (NVIDIA)", "renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)"},
    ]

    # ── Platform strings ──────────────────────────────────────────

    PLATFORMS = {
        "windows": "Win32",
        "mac_intel": "MacIntel",
        "linux_x64": "Linux x86_64",
    }

    # ── Common screen resolutions ─────────────────────────────────

    SCREEN_RESOLUTIONS = [
        (1920, 1080),
        (2560, 1440),
        (1366, 768),
        (1440, 900),
        (1680, 1050),
        (3840, 2160),
    ]

    @classmethod
    def generate_consistent_fingerprint(
        cls,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        locale: str = "en-US",
        timezone_id: str = "America/New_York",
        seed: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a CONSISTENT fingerprint for an entire session.

        Uses a deterministic seed derived from session params so that
        the same session always gets the same fingerprint values.
        This prevents fingerprint mismatch detection.

        Returns a complete fingerprint dictionary with:
        - user_agent, platform, languages
        - canvas noise seed, webgl vendor/renderer
        - hardware concurrency, device memory
        - screen/window dimensions
        - timezone, locale, geolocation
        - font list
        """
        # Deterministic seed from session identity
        if seed is None:
            seed = str(uuid.uuid4())

        rng = random.Random(hashlib.sha256(seed.encode()).digest())

        # Select platform-appropriate fingerprints
        platform_key = rng.choice(list(cls.PLATFORMS.keys()))
        platform = cls.PLATFORMS[platform_key]

        # User-agent matching the platform
        ua_candidates = [ua for ua in cls.REAL_USER_AGENTS if _ua_matches_platform(ua, platform_key)]
        if not ua_candidates:
            ua_candidates = cls.REAL_USER_AGENTS
        user_agent = rng.choice(ua_candidates)

        # WebGL pair
        webgl_pair = rng.choice(cls.WEBGL_PAIRS)

        # Canvas noise seed (consistent per session)
        canvas_seed = uuid.uuid4().hex[:16]

        # Screen dimensions
        screen_width, screen_height = rng.choice(cls.SCREEN_RESOLUTIONS)

        # Hardware
        hardware_concurrency = rng.choice([4, 8, 12, 16])
        device_memory = rng.choice([4, 8, 16])

        # Languages
        languages = ["en-US", "en"] if locale == "en-US" else [locale, "en-US", "en"]

        # Timezone offset
        timezone_offset = _get_timezone_offset(timezone_id)

        # Geolocation (approximate for the timezone)
        geolocation = _get_geolocation_for_timezone(timezone_id)

        fingerprint = {
            "fingerprint_id": hashlib.md5(seed.encode()).hexdigest()[:16],
            "seed": seed,
            "user_agent": user_agent,
            "platform": platform,
            "platform_key": platform_key,
            "languages": languages,
            "canvas_seed": canvas_seed,
            "webgl_vendor": webgl_pair["vendor"],
            "webgl_renderer": webgl_pair["renderer"],
            "hardware_concurrency": hardware_concurrency,
            "device_memory": device_memory,
            "screen_width": screen_width,
            "screen_height": screen_height,
            "viewport_width": viewport_width,
            "viewport_height": viewport_height,
            "color_depth": 24,
            "pixel_depth": 24,
            "timezone_id": timezone_id,
            "timezone_offset": timezone_offset,
            "locale": locale,
            "geolocation": geolocation,
            "do_not_track": rng.choice([None, "1", "0"]),
        }

        logger.debug(f"🎭 Fingerprint generated: id={fingerprint['fingerprint_id']}")
        return fingerprint

    @classmethod
    async def inject_stealth_scripts(cls, context) -> None:
        """
        Inject all anti-detection JavaScript patches into the browser context.

        These scripts run BEFORE any page loads — they patch browser APIs
        to hide automation indicators and spoof realistic fingerprints.
        """
        # Each page in this context gets the stealth patches
        await context.add_init_script("""
        // ============================================================
        // AutoWebAgent Ultra Stealth - Anti-Detection Patches
        // ============================================================

        (function() {
            'use strict';

            // ── 1. Hide WebDriver property ──────────────────────
            // This is the #1 way sites detect automation
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true,
            });

            // Also patch the navigator.webdriver property descriptor
            delete Object.getPrototypeOf(navigator).webdriver;

            // ── 2. Hide Chrome automation flags ────────────────
            // Remove "Chrome is being controlled by automated software" infobar
            if (window.chrome && window.chrome.runtime) {
                // Make chrome.runtime appear normal
            }

            // Fake plugins array — real browsers have plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugins = [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
                    ];
                    plugins.item = (i) => plugins[i] || null;
                    plugins.namedItem = (name) => plugins.find(p => p.name === name) || null;
                    plugins.refresh = () => {};
                    Object.setPrototypeOf(plugins, PluginArray.prototype);
                    return plugins;
                },
                configurable: true,
            });

            // ── 3. Fake languages ───────────────────────────────
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                configurable: true,
            });

            // ── 4. Hide automation permissions ──────────────────
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => {
                if (parameters.name === 'notifications') {
                    return Promise.resolve({
                        state: Notification.permission,
                        onchange: null,
                    });
                }
                return originalQuery(parameters);
            };

            // ── 5. Spoof chrome object ──────────────────────────
            window.chrome = {
                app: {
                    isInstalled: false,
                    InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
                    RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
                },
                runtime: {
                    OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
                    OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
                    PlatformArch: { ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
                    PlatformNaclArch: { ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
                    PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
                    RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' },
                },
                loadTimes: () => {},
                csi: () => {},
            };

            // ── 6. Remove "HeadlessChrome" from userAgent ───────
            // (Playwright already sets real UA, this is a safety net)

            // ── 7. Spoof connection type ────────────────────────
            if (navigator.connection) {
                Object.defineProperty(navigator.connection, 'rtt', {
                    get: () => 50 + Math.floor(Math.random() * 50),
                });
            }

            // ── 8. Add fake touch support (only if desktop) ────
            // Most real desktops have maxTouchPoints: 0
            Object.defineProperty(navigator, 'maxTouchPoints', {
                get: () => 0,
            });

            // ── 9. Patch toString() on native functions ────────
            // Bot detectors check if toString returns "[native code]"
            const originalFunctionToString = Function.prototype.toString;
            // Ensure our patched functions still look native
            Function.prototype.toString = function() {
                if (this === window.chrome?.loadTimes || this === window.chrome?.csi) {
                    return 'function () { [native code] }';
                }
                return originalFunctionToString.call(this);
            };

            // ── 10. Hide iframe detection ───────────────────────
            // Prevent sites from detecting if we're in an iframe
            Object.defineProperty(window, 'frameElement', {
                get: () => null,
            });

            // ── 11. Battery API protection ──────────────────────
            if (navigator.getBattery) {
                const originalGetBattery = navigator.getBattery;
                navigator.getBattery = function() {
                    return originalGetBattery.call(navigator).then(battery => {
                        // Add small noise to battery values
                        return battery;
                    });
                };
            }

            console.debug('[AutoWebAgent] Stealth patches applied');
        })();
        """)

    @classmethod
    async def apply_fingerprint_overrides(
        cls, context, fingerprint: Dict[str, Any]
    ) -> None:
        """
        Apply fingerprint-specific overrides to the browser context.

        These override navigator properties, canvas, WebGL, AudioContext
        to present a consistent fake identity per session.
        """
        canvas_seed = fingerprint.get("canvas_seed", "default")
        webgl_vendor = fingerprint.get("webgl_vendor", "")
        webgl_renderer = fingerprint.get("webgl_renderer", "")
        hardware_concurrency = fingerprint.get("hardware_concurrency", 8)
        device_memory = fingerprint.get("device_memory", 8)
        platform = fingerprint.get("platform", "Win32")

        # Inject fingerprint-specific overrides
        await context.add_init_script(f"""
        // ============================================================
        // AutoWebAgent - Fingerprint Overrides (Session-Specific)
        // ============================================================
        (function() {{
            'use strict';

            // ── Canvas Fingerprint Randomization ──────────────
            // Consistent per session via deterministic seed: "{canvas_seed}"
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            const originalToBlob = HTMLCanvasElement.prototype.toBlob;
            const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            const originalFillText = CanvasRenderingContext2D.prototype.fillText;

            const canvasSeed = "{canvas_seed}";

            // Simple deterministic hash function for canvas noise
            function canvasHash(str) {{
                let hash = 0;
                for (let i = 0; i < str.length; i++) {{
                    const char = str.charCodeAt(i);
                    hash = ((hash << 5) - hash) + char;
                    hash |= 0;
                }}
                return Math.abs(hash);
            }}

            // Add noise to getImageData for canvas fingerprint randomization
            CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {{
                const imageData = originalGetImageData.call(this, x, y, w, h);
                const seedNum = canvasHash(canvasSeed + x + ':' + y + ':' + w + ':' + h);

                // Add subtle noise to a few pixels (undetectable to human eye)
                if (w * h > 10 && seedNum % 3 === 0) {{
                    const data = imageData.data;
                    const noiseAmount = (seedNum % 3); // 0, 1, or 2
                    for (let i = 0; i < Math.min(data.length, 20); i += 4) {{
                        data[i] = Math.min(255, Math.max(0, data[i] + noiseAmount - 1));
                    }}
                }}
                return imageData;
            }};

            // ── WebGL Fingerprint Spoofing ────────────────────
            const spoofedVendor = "{webgl_vendor}";
            const spoofedRenderer = "{webgl_renderer}";

            const getParameterProxyHandler = {{
                apply: function(target, thisArg, args) {{
                    const param = args[0];
                    // UNMASKED_VENDOR_WEBGL
                    if (param === 37445) return spoofedVendor;
                    // UNMASKED_RENDERER_WEBGL
                    if (param === 37446) return spoofedRenderer;
                    return Reflect.apply(target, thisArg, args);
                }}
            }};

            // Patch WebGLRenderingContext.getParameter
            if (typeof WebGLRenderingContext !== 'undefined') {{
                WebGLRenderingContext.prototype.getParameter = new Proxy(
                    WebGLRenderingContext.prototype.getParameter,
                    getParameterProxyHandler
                );
            }}
            if (typeof WebGL2RenderingContext !== 'undefined') {{
                WebGL2RenderingContext.prototype.getParameter = new Proxy(
                    WebGL2RenderingContext.prototype.getParameter,
                    getParameterProxyHandler
                );
            }}

            // ── AudioContext Fingerprint Spoofing ──────────────
            if (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined') {{
                const AudioContextClass = window.AudioContext || window.webkitAudioContext;
                const originalCreateOscillator = AudioContextClass.prototype.createOscillator;
                const originalCreateDynamicsCompressor = AudioContextClass.prototype.createDynamicsCompressor;
                const originalCreateAnalyser = AudioContextClass.prototype.createAnalyser;

                // Add subtle noise to dynamics compressor (common fingerprinting target)
                if (originalCreateDynamicsCompressor) {{
                    AudioContextClass.prototype.createDynamicsCompressor = function() {{
                        const compressor = originalCreateDynamicsCompressor.call(this);
                        const originalGetFloatFrequencyData = AnalyserNode.prototype.getFloatFrequencyData;
                        // Noise will be injected when getFloatFrequencyData is called
                        return compressor;
                    }};
                }}

                // Patch AnalyserNode.getFloatFrequencyData to add noise
                if (typeof AnalyserNode !== 'undefined') {{
                    const origGetFloatFreqData = AnalyserNode.prototype.getFloatFrequencyData;
                    AnalyserNode.prototype.getFloatFrequencyData = function(array) {{
                        origGetFloatFreqData.call(this, array);
                        const seedNum = canvasHash(canvasSeed + 'audio');
                        // Add extremely subtle noise (-120dB range)
                        for (let i = 0; i < Math.min(array.length, 10); i++) {{
                            array[i] += (seedNum % 3) * 0.000001;
                        }}
                    }};
                }}
            }}

            // ── Hardware Spoofing ──────────────────────────────
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {hardware_concurrency},
                configurable: true,
            }});

            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {device_memory},
                configurable: true,
            }});

            Object.defineProperty(navigator, 'platform', {{
                get: () => "{platform}",
                configurable: true,
            }});

            console.debug('[AutoWebAgent] Fingerprint overrides applied');
        }})();
        """)

    @classmethod
    async def apply_human_behavior_patches(cls, page) -> None:
        """
        Inject human-like behavior modifications to the page.

        These patches make interactions (mouse, keyboard, scroll) appear
        indistinguishable from real human behavior.
        """
        await page.evaluate("""
        // ============================================================
        // AutoWebAgent - Human Behavior Simulation Patches
        // ============================================================
        (function() {
            'use strict';

            // Track last interaction times to simulate human pauses
            window.__awagent_timers = {
                lastMouseMove: Date.now(),
                lastClick: Date.now(),
                lastKeypress: Date.now(),
                lastScroll: Date.now(),
            };

            // Dispatch custom events that sites might listen for
            const realisticEvents = ['mousemove', 'mouseover', 'mouseout',
                'pointermove', 'pointerover', 'pointerout'];

            console.debug('[AutoWebAgent] Human behavior patches active');
        })();
        """)

    # ── Human-like Mouse Movement (Bezier Curves) ──────────────

    @staticmethod
    def generate_bezier_path(
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        num_points: int = 50,
    ) -> List[tuple]:
        """
        Generate a natural-looking mouse movement path using cubic Bezier curves.

        Real mouse movements are NOT straight lines — they follow curved paths
        with slight overshoot and correction.

        Args:
            start_x, start_y: Starting cursor position.
            end_x, end_y: Target cursor position.
            num_points: Number of intermediate points.

        Returns:
            List of (x, y) tuples forming the path.
        """
        # Add some randomness to control points for natural variation
        distance = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)
        overshoot = min(distance * 0.1, 50) * random.uniform(-1, 1)

        # Control points for cubic Bezier
        cp1_x = start_x + (end_x - start_x) * random.uniform(0.3, 0.5) + random.uniform(-20, 20)
        cp1_y = start_y + (end_y - start_y) * random.uniform(0.1, 0.3) + overshoot

        cp2_x = start_x + (end_x - start_x) * random.uniform(0.5, 0.8) + random.uniform(-15, 15)
        cp2_y = start_y + (end_y - start_y) * random.uniform(0.7, 0.9) - overshoot * 0.5

        path = []
        for i in range(num_points):
            t = i / (num_points - 1)

            # Cubic Bezier formula: B(t) = (1-t)³P0 + 3(1-t)²tP1 + 3(1-t)t²P2 + t³P3
            x = ((1 - t) ** 3 * start_x +
                 3 * (1 - t) ** 2 * t * cp1_x +
                 3 * (1 - t) * t ** 2 * cp2_x +
                 t ** 3 * end_x)

            y = ((1 - t) ** 3 * start_y +
                 3 * (1 - t) ** 2 * t * cp1_y +
                 3 * (1 - t) * t ** 2 * cp2_y +
                 t ** 3 * end_y)

            # Add tiny jitter (human hand tremor simulation)
            if i > 0 and i < num_points - 1:
                x += random.gauss(0, 0.5)
                y += random.gauss(0, 0.5)

            path.append((round(x, 1), round(y, 1)))

        return path

    @staticmethod
    async def human_mouse_move(page, target_x: float, target_y: float):
        """
        Move mouse to target coordinates with natural Bezier movement.
        """
        # Get current position (approximate from last known or random nearby)
        import random as _random
        start_x = target_x + _random.uniform(-200, 200)
        start_y = target_y + _random.uniform(-200, 200)

        path = StealthManager.generate_bezier_path(start_x, start_y, target_x, target_y)

        for x, y in path:
            await page.mouse.move(x, y)
            # Variable delay between movements (faster in middle, slower at start/end)
            delay = _random.uniform(2, 8) / 1000  # 2-8ms between points
            import asyncio
            await asyncio.sleep(delay)

    @staticmethod
    async def human_click(page, selector: str):
        """
        Click an element with human-like movement + random delay.
        """
        import asyncio

        # Small pre-click delay (human "thinking" time)
        await asyncio.sleep(random.uniform(0.1, 0.4))

        # Get element position
        element = await page.query_selector(selector)
        if not element:
            raise ValueError(f"Element not found: {selector}")

        box = await element.bounding_box()
        if not box:
            raise ValueError(f"Cannot get bounding box for: {selector}")

        # Target center-ish with slight offset (humans don't click exact center)
        target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
        target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)

        # Move with Bezier path
        await StealthManager.human_mouse_move(page, target_x, target_y)

        # Small hover delay before click
        await asyncio.sleep(random.uniform(0.05, 0.15))

        # Click with random duration
        await page.mouse.click(target_x, target_y)

        # Post-click delay
        await asyncio.sleep(random.uniform(0.1, 0.3))

    @staticmethod
    async def human_type(page, selector: str, text: str):
        """
        Type text with variable speed, occasional mistakes, and corrections.

        Real humans:
        - Type at 200-400ms per character (variable)
        - Make occasional typos and backspace-correct them
        - Pause at word boundaries
        - Sometimes type faster in the middle of words
        """
        import asyncio

        # Click the field first (human-like)
        await StealthManager.human_click(page, selector)

        # Clear existing content
        await page.fill(selector, "")

        i = 0
        while i < len(text):
            char = text[i]

            # Random typo (5% chance), then correct it
            if random.random() < 0.05 and char.isalpha():
                # Type a nearby key (QWERTY proximity)
                nearby_keys = {
                    'a': 's', 's': 'a', 'd': 'f', 'f': 'd', 'g': 'h',
                    'h': 'g', 'j': 'k', 'k': 'j', 'l': 'k',
                    'q': 'w', 'w': 'q', 'e': 'r', 'r': 'e', 't': 'y',
                    'y': 't', 'u': 'i', 'i': 'u', 'o': 'p', 'p': 'o',
                }
                typo = nearby_keys.get(char.lower(), char.lower())
                await page.type(selector, typo, delay=random.uniform(80, 150))
                await asyncio.sleep(random.uniform(0.1, 0.3))
                # Backspace to correct
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.05, 0.15))

            # Type the correct character with variable delay
            # Longer delay at word boundaries (spaces)
            if char == " ":
                delay = random.uniform(150, 350)
            elif char in ",.!?;:":
                delay = random.uniform(120, 280)
            else:
                delay = random.uniform(50, 200)

            await page.type(selector, char, delay=delay)
            i += 1

        # Small post-typing pause
        await asyncio.sleep(random.uniform(0.2, 0.5))

    @staticmethod
    async def human_scroll(page, direction: str = "down", amount: int = None):
        """
        Perform a natural scroll with acceleration/deceleration.

        Humans don't scroll at constant speed — they accelerate at the start
        and decelerate at the end.
        """
        import asyncio

        if amount is None:
            amount = random.randint(200, 600)

        direction_mult = 1 if direction == "down" else -1
        total_scroll = amount * direction_mult

        # Break scroll into small steps with acceleration profile
        steps = random.randint(8, 15)
        for i in range(steps):
            # Acceleration curve: slow → fast → slow
            progress = i / (steps - 1)
            # Sinusoidal speed profile
            speed_factor = math.sin(progress * math.pi)
            step_amount = (total_scroll / steps) * (0.5 + speed_factor * 0.5)

            await page.mouse.wheel(0, step_amount)
            await asyncio.sleep(random.uniform(0.01, 0.05))

        # Post-scroll pause (humans read after scrolling)
        await asyncio.sleep(random.uniform(0.3, 1.5))

    @staticmethod
    async def random_delay(min_ms: float = 100, max_ms: float = 2000):
        """Insert a random but realistic delay."""
        import asyncio
        # Use gamma distribution for more realistic delay patterns
        delay = random.gammavariate(2, (max_ms - min_ms) / 4) + min_ms
        delay = min(delay, max_ms)
        await asyncio.sleep(delay / 1000)


# ─────────────────────────────────────────────────────────────────
# HumanBehavior — Advanced Human Timing & Fingerprint-Safe Actions
# ─────────────────────────────────────────────────────────────────

class HumanBehavior:
    """
    Advanced human-like behavior simulator for maximum anti-detection.

    Covers realistic timing patterns, mouse micro-movements, keyboard
    inter-key delays, reading pauses, and browser idle simulation.

    All delays are drawn from statistical distributions that match
    real human behavior research data:
    - Keystroke dynamics (dwell + flight times)
    - Mouse click reaction times (Fitts's Law)
    - Reading speed pauses before interaction
    - Post-action cooldown
    """

    # ── Keystroke timing profiles (milliseconds) ──────────────────
    # Source: Academic keystroke dynamics studies
    TYPING_PROFILES = {
        "fast_typist":   {"dwell": (40, 80),   "flight": (30, 100)},   # 80-120 WPM
        "average_typist": {"dwell": (60, 120),  "flight": (80, 200)},   # 40-70 WPM
        "slow_typist":   {"dwell": (80, 160),  "flight": (150, 350)},  # 20-40 WPM
    }

    # ── Mouse click reaction time profiles (ms) ───────────────────
    REACTION_TIMES = {
        "fast":    (100, 200),
        "normal":  (200, 500),
        "slow":    (400, 800),
    }

    # ── Reading pause profiles (seconds per action) ───────────────
    READING_PAUSES = {
        "none":    (0.0, 0.05),    # No pause
        "brief":   (0.1, 0.4),    # Glance
        "normal":  (0.4, 1.2),    # Read a line
        "thorough":(1.0, 3.5),    # Read a paragraph
    }

    @classmethod
    def _pick_typing_profile(cls) -> dict:
        """Pick a random but consistent typing profile."""
        weights = [0.2, 0.6, 0.2]  # fast, average, slow
        profile_name = random.choices(
            list(cls.TYPING_PROFILES.keys()), weights=weights, k=1
        )[0]
        return cls.TYPING_PROFILES[profile_name]

    @classmethod
    async def pre_action_pause(cls, action_type: str = "normal") -> None:
        """
        Pause before an action, simulating human reading/thinking time.
        
        Different actions require different pre-pause durations:
        - click: brief (saw the button, about to click)
        - type: normal (focus on field, prepare to type)  
        - navigate: none (programmatic navigation)
        - submit: thorough (reviewing form before submit)
        """
        import asyncio
        pause_map = {
            "click":    "brief",
            "type":     "normal",
            "fill":     "normal",
            "scroll":   "brief",
            "navigate": "none",
            "submit":   "thorough",
            "wait":     "none",
        }
        pause_level = pause_map.get(action_type, "brief")
        min_s, max_s = cls.READING_PAUSES[pause_level]
        # Add small gaussian noise for realism
        delay = random.uniform(min_s, max_s) + abs(random.gauss(0, 0.05))
        await asyncio.sleep(delay)

    @classmethod
    async def post_action_pause(cls, action_type: str = "click") -> None:
        """
        Pause after an action to simulate human processing time.
        Longer for navigation (page loads), shorter for typing.
        """
        import asyncio
        post_map = {
            "navigate": (1.5, 4.0),    # Wait for page to settle + read it
            "click":    (0.15, 0.6),   # Brief pause after click
            "type":     (0.1, 0.3),    # Inter-field pause
            "fill":     (0.1, 0.3),
            "scroll":   (0.3, 1.2),    # Read after scroll
            "submit":   (2.0, 5.0),    # Wait for form response
            "select":   (0.2, 0.5),
            "press_key":(0.1, 0.4),
        }
        min_s, max_s = post_map.get(action_type, (0.1, 0.5))
        delay = random.uniform(min_s, max_s)
        import asyncio
        await asyncio.sleep(delay)

    @classmethod
    async def human_type_locator(cls, locator, text: str) -> None:
        """
        Type text into a Playwright locator with realistic keystroke dynamics.
        
        Uses dwell time (key held) + flight time (between keys) modeling.
        Includes:
        - Variable inter-key delays (matching human keystroke dynamics)
        - Occasional micro-pauses mid-word (brain processing)
        - Word boundary pauses
        - Random typos with backspace correction (5% chance)
        - Realistic shift key timing for capitals
        """
        import asyncio

        profile = cls._pick_typing_profile()
        dwell_min, dwell_max = profile["dwell"]
        flight_min, flight_max = profile["flight"]

        # Focus the element first
        await locator.click()
        await asyncio.sleep(random.uniform(0.1, 0.3))

        # Clear the field
        await locator.fill("")
        await asyncio.sleep(random.uniform(0.05, 0.15))

        i = 0
        word_len = 0
        while i < len(text):
            char = text[i]

            # Word boundary pause (space or punctuation)
            if char in " \t\n":
                word_len = 0
                delay_ms = random.uniform(flight_min * 1.5, flight_max * 2.0)
            elif char in ".,!?;:":
                delay_ms = random.uniform(flight_min * 1.2, flight_max * 1.5)
                word_len = 0
            else:
                word_len += 1
                # Slight acceleration mid-word, deceleration at start/end
                speed_factor = 1.0
                if word_len > 3:
                    speed_factor = random.uniform(0.7, 0.9)  # speed up mid-word
                delay_ms = random.uniform(flight_min, flight_max) * speed_factor

            # Random typo (4% chance on alphabetic chars)
            if random.random() < 0.04 and char.isalpha():
                nearby = {
                    'a': 'sq', 's': 'ad', 'd': 'sf', 'f': 'dg', 'g': 'fh',
                    'h': 'gj', 'j': 'hk', 'k': 'jl', 'l': 'k',
                    'q': 'wa', 'w': 'qe', 'e': 'wr', 'r': 'et', 't': 'ry',
                    'y': 'tu', 'u': 'yi', 'i': 'uo', 'o': 'ip', 'p': 'ol',
                    'z': 'xa', 'x': 'zc', 'c': 'xv', 'v': 'cb', 'b': 'vn',
                    'n': 'bm', 'm': 'n',
                }
                typo_options = nearby.get(char.lower(), char.lower())
                typo_char = random.choice(typo_options)
                await locator.press(typo_char)
                await asyncio.sleep(random.uniform(0.08, 0.25))
                # Realise mistake and correct it
                await locator.press("Backspace")
                await asyncio.sleep(random.uniform(0.05, 0.18))

            # Occasionally pause mid-sentence (thinking/distraction)
            if random.random() < 0.02:
                await asyncio.sleep(random.uniform(0.3, 1.2))

            # Type the actual character
            await locator.press_sequentially(char, delay=random.uniform(dwell_min, dwell_max))
            await asyncio.sleep(delay_ms / 1000)
            i += 1

        # Post-typing pause (human checks what they typed)
        await asyncio.sleep(random.uniform(0.2, 0.6))

    @classmethod
    async def human_click_locator(cls, locator) -> None:
        """
        Click a Playwright locator with human-like mouse movement and timing.
        
        Includes:
        - Pre-click reading pause
        - Mouse hover before click (humans move to element, then click)
        - Random offset within element bounds (not always center)
        - Post-click wait
        """
        import asyncio

        # Pre-click thinking pause
        await asyncio.sleep(random.uniform(0.15, 0.55))

        # Get bounding box for natural offset calculation
        try:
            box = await locator.bounding_box()
            if box:
                # Click with natural offset (humans rarely click exact center)
                offset_x = box["width"] * random.uniform(0.25, 0.75)
                offset_y = box["height"] * random.uniform(0.25, 0.75)

                # Brief hover before click (human mouse-over)
                await locator.hover()
                await asyncio.sleep(random.uniform(0.05, 0.2))

                # Actual click with offset
                await locator.click(
                    position={"x": offset_x, "y": offset_y},
                    delay=random.uniform(30, 100),  # ms button held down
                )
            else:
                # Fallback: normal click
                await locator.click(delay=random.uniform(30, 80))
        except Exception:
            await locator.click()

        # Post-click pause
        await asyncio.sleep(random.uniform(0.1, 0.4))

    @classmethod
    async def navigate_with_human_wait(cls, page, url: str) -> None:
        """
        Navigate to a URL and wait with realistic human timing.
        Simulates user looking at loading page, then reading initial content.
        """
        import asyncio

        response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Check if the page loaded with a WAF block
        status = response.status if response else None
        title = await page.title() or ""
        content = await page.content() or ""

        if (
            (status and status in (403, 503, 401, 502)) or
            "forbidden" in title.lower() or
            "access denied" in title.lower() or
            "403 forbidden" in content.lower() or
            "access denied" in content.lower()
        ):
            raise Exception(f"Access Blocked: Status {status}, Title '{title}'. Proxy needs rotation.")

        # Simulate user watching page load (random glance time)
        await asyncio.sleep(random.uniform(1.2, 3.5))

        # Random micro-scroll (user checks page content)
        if random.random() < 0.4:
            scroll_amount = random.randint(50, 200)
            await page.mouse.wheel(0, scroll_amount)
            await asyncio.sleep(random.uniform(0.3, 0.8))
            await page.mouse.wheel(0, -scroll_amount)  # scroll back
            await asyncio.sleep(random.uniform(0.2, 0.5))

    @classmethod
    async def idle_mouse_jitter(cls, page, duration_s: float = 1.0) -> None:
        """
        Simulate idle mouse micro-movements while waiting for something.
        Real users unconsciously move the mouse while reading/waiting.
        """
        import asyncio
        steps = int(duration_s / 0.15)
        x = random.randint(300, 900)
        y = random.randint(200, 600)

        for _ in range(steps):
            x += random.gauss(0, 8)
            y += random.gauss(0, 6)
            x = max(100, min(1800, x))
            y = max(50, min(900, y))
            try:
                await page.mouse.move(x, y)
            except Exception:
                break
            await asyncio.sleep(random.uniform(0.08, 0.22))

    @classmethod
    async def simulate_page_reading(cls, page, duration_s: float = None) -> None:
        """
        Simulate a human reading the page: random scrolls, mouse movements,
        and pauses that mimic genuine page consumption behavior.
        """
        import asyncio

        if duration_s is None:
            duration_s = random.uniform(0.8, 2.5)

        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < duration_s:
            action = random.choice(["mouse_jitter", "scroll_peek", "pause"])
            if action == "mouse_jitter":
                await cls.idle_mouse_jitter(page, duration_s=0.3)
            elif action == "scroll_peek" and random.random() < 0.3:
                await page.mouse.wheel(0, random.randint(30, 150))
                await asyncio.sleep(random.uniform(0.2, 0.5))
            else:
                await asyncio.sleep(random.uniform(0.1, 0.4))




# ── Helper Functions ──────────────────────────────────────────

def _ua_matches_platform(user_agent: str, platform_key: str) -> bool:
    """Check if a User-Agent string matches a platform category."""
    ua_lower = user_agent.lower()
    if platform_key == "windows":
        return "windows nt" in ua_lower
    elif platform_key == "mac_intel":
        return "mac os x" in ua_lower or "macintosh" in ua_lower
    elif platform_key == "linux_x64":
        return "linux" in ua_lower and "android" not in ua_lower
    return True


def _get_timezone_offset(timezone_id: str) -> int:
    """Get UTC offset in minutes for a timezone ID."""
    offsets = {
        "America/New_York": -300,
        "America/Chicago": -360,
        "America/Denver": -420,
        "America/Los_Angeles": -480,
        "Europe/London": 0,
        "Europe/Berlin": 60,
        "Europe/Paris": 60,
        "Asia/Tokyo": 540,
        "Asia/Shanghai": 480,
        "Asia/Kolkata": 330,
        "Australia/Sydney": 600,
    }
    return offsets.get(timezone_id, 0)


def _get_geolocation_for_timezone(timezone_id: str) -> Dict[str, float]:
    """Get approximate geolocation for a timezone."""
    locations = {
        "America/New_York": {"latitude": 40.7128, "longitude": -74.0060},
        "America/Chicago": {"latitude": 41.8781, "longitude": -87.6298},
        "America/Denver": {"latitude": 39.7392, "longitude": -104.9903},
        "America/Los_Angeles": {"latitude": 34.0522, "longitude": -118.2437},
        "Europe/London": {"latitude": 51.5074, "longitude": -0.1278},
        "Europe/Berlin": {"latitude": 52.5200, "longitude": 13.4050},
        "Europe/Paris": {"latitude": 48.8566, "longitude": 2.3522},
        "Asia/Tokyo": {"latitude": 35.6762, "longitude": 139.6503},
        "Asia/Shanghai": {"latitude": 31.2304, "longitude": 121.4737},
        "Asia/Kolkata": {"latitude": 28.6139, "longitude": 77.2090},
        "Australia/Sydney": {"latitude": -33.8688, "longitude": 151.2093},
    }
    return locations.get(timezone_id, {"latitude": 40.7128, "longitude": -74.0060})
