"""
AutoWebAgent - CAPTCHA Solver Service
=======================================
Detects and solves CAPTCHAs using Anti-Captcha API.
Supports reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile, DataDome.
"""

import asyncio
import time
from typing import Optional, Dict, Any
from loguru import logger
from playwright.async_api import Page


class CaptchaSolver:
    """
    CAPTCHA detection and solving using Anti-Captcha API.

    Detection patterns for all major CAPTCHA providers.
    Automatic solving with retry and fallback strategies.
    """

    # ── CAPTCHA Detection Patterns ────────────────────────────

    CAPTCHA_PATTERNS = {
        "recaptcha_v2": [
            'iframe[src*="recaptcha/api2"]',
            'iframe[src*="google.com/recaptcha"]',
            '.g-recaptcha',
            '[data-sitekey]',
            '#recaptcha',
        ],
        "hcaptcha": [
            'iframe[src*="hcaptcha.com"]',
            '.h-captcha',
            '[data-hcaptcha-widget-id]',
        ],
        "cloudflare_turnstile": [
            'iframe[src*="challenges.cloudflare.com/turnstile"]',
            '#turnstile-wrapper',
            '.cf-turnstile',
        ],
        "cloudflare_challenge": [
            '#challenge-form',
            '#cf-challenge-running',
            'iframe[src*="challenges.cloudflare.com/cdn-cgi/challenge-platform"]',
        ],
        "datadome": [
            'iframe[src*="datadome.co"]',
            '#datadome-captcha',
        ],
        "perimeterx": [
            '#px-captcha',
        ],
        "generic_captcha": [
            'img[src*="captcha"]',
            'input[name*="captcha"]',
            '#captcha',
            '.captcha',
        ],
    }

    @classmethod
    async def _is_captcha_solved(cls, page: Page) -> bool:
        """Check if CAPTCHA on page has already been solved/token-filled."""
        try:
            # 1. First check if any active challenge modal (bframe) is visible in the main page.
            # If a challenge modal is visible, the CAPTCHA is definitely NOT solved yet.
            bframe_visible = await page.evaluate("""
                () => {
                    const bframe = document.querySelector('iframe[src*="recaptcha/api2/bframe"], iframe[src*="google.com/recaptcha/api2/bframe"]');
                    if (bframe) {
                        const rect = bframe.getBoundingClientRect();
                        const style = window.getComputedStyle(bframe);
                        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
                    }
                    return false;
                }
            """)
            if bframe_visible:
                logger.info("ℹ️ CAPTCHA challenge modal (bframe) is visible on screen. It is NOT solved yet.")
                return False

            # 2. Check each frame's anchor state or token inputs
            for frame in page.frames:
                try:
                    if frame.is_detached():
                        continue
                    
                    # If this is the anchor frame, check if the checkbox is checked
                    has_anchor = await frame.evaluate("""
                        () => {
                            const anchor = document.querySelector('#recaptcha-anchor');
                            if (anchor) {
                                return {
                                    found: true,
                                    checked: anchor.getAttribute('aria-checked') === 'true'
                                };
                            }
                            return { found: false, checked: false };
                        }
                    """)
                    if has_anchor["found"]:
                        if not has_anchor["checked"]:
                            logger.info("ℹ️ reCAPTCHA checkbox is NOT checked yet.")
                            return False
                        else:
                            logger.info("⏳ reCAPTCHA checkbox is already checked.")
                            return True
                    
                    has_val = await frame.evaluate("""
                        () => {
                            const tokenSelectors = [
                                'textarea[name="g-recaptcha-response"]',
                                'textarea[id*="g-recaptcha-response"]',
                                'input[name="captchaUserResponseToken"]',
                                'textarea[name="h-captcha-response"]',
                                'input[name="cf-turnstile-response"]',
                                '.g-recaptcha-response'
                            ];
                            for (const selector of tokenSelectors) {
                                const el = document.querySelector(selector);
                                if (el && el.value && el.value.length > 25) {
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    if has_val:
                        return True
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Error checking if CAPTCHA is already solved: {e}")
        return False

    @classmethod
    async def detect_captcha(cls, page: Page) -> Optional[Dict[str, Any]]:
        """
        Scan the page and all its frames for known CAPTCHA types.

        Returns:
            None if no CAPTCHA detected, or dict with 'type', 'sitekey', 'url', etc.
        """
        # Check if the page is currently asking for Security Verification OTP instead of CAPTCHA
        try:
            page_text = await page.evaluate("() => document.body.innerText.toLowerCase()")
            if any(kw in page_text for kw in ["verification code", "verification-code", "security code", "enter the code", "enter the 6-digit", "sent to your email"]):
                logger.info("ℹ️ Page text indicates an OTP / Verification page. Skipping CAPTCHA detection.")
                return None
        except Exception:
            pass

        try:
            # ── Check if CAPTCHA has already been solved/token-filled ──
            if await cls._is_captcha_solved(page):
                logger.info("⏳ CAPTCHA token is already populated. Skipping re-detection/re-solve.")
                return None
        except Exception:
            pass

        sitekey_from_input = None
        try:
            sitekey_from_input = await page.evaluate("""
                () => {
                    const input = document.querySelector('input[name="captchaSiteKey"], input[id*="captchaSiteKey"]');
                    if (input && input.value && input.value.trim().length > 10) {
                        return input.value.trim();
                    }
                    return null;
                }
            """)
        except Exception:
            pass

        try:
            # 1. First, check frame URLs for direct detection (very fast and reliable)
            for frame in page.frames:
                try:
                    if frame.is_detached():
                        continue
                    url = frame.url
                    if not url:
                        continue
                    
                    # reCAPTCHA
                    if "google.com/recaptcha" in url or "recaptcha/api2" in url:
                        import urllib.parse
                        import re
                        parsed = urllib.parse.urlparse(url)
                        params = urllib.parse.parse_qs(parsed.query or parsed.fragment)
                        sitekey = params.get("k", [None])[0]
                        if not sitekey:
                            match = re.search(r"[?&#]k=([^&#]+)", url)
                            if match:
                                sitekey = match.group(1)
                                
                        if sitekey:
                            target_frame = frame.parent_frame or page.main_frame
                            invisible = "size=invisible" in url
                            enterprise = "enterprise" in url
                            
                            if sitekey_from_input and sitekey != sitekey_from_input:
                                logger.info(f"Overriding frame URL sitekey {sitekey} with input sitekey: {sitekey_from_input}")
                                sitekey = sitekey_from_input
                                enterprise = False
                                
                            logger.info(f"Detected reCAPTCHA via frame URL: sitekey={sitekey}, invisible={invisible}, enterprise={enterprise}")
                            return {
                                "type": "recaptcha_v2",
                                "sitekey": sitekey,
                                "url": page.url,
                                "selector": "iframe URL",
                                "invisible": invisible,
                                "enterprise": enterprise,
                                "target_frame": target_frame
                            }
                    
                    # hCaptcha
                    if "hcaptcha.com" in url and "captcha.html" in url:
                        import urllib.parse
                        import re
                        parsed = urllib.parse.urlparse(url)
                        params = urllib.parse.parse_qs(parsed.fragment or parsed.query)
                        sitekey = params.get("sitekey", [None])[0]
                        if not sitekey:
                            match = re.search(r"[?&#]sitekey=([^&#]+)", url)
                            if match:
                                sitekey = match.group(1)
                                
                        if sitekey:
                            target_frame = frame.parent_frame or page.main_frame
                            logger.info(f"Detected hCaptcha via frame URL: sitekey={sitekey}")
                            return {
                                "type": "hcaptcha",
                                "sitekey": sitekey,
                                "url": page.url,
                                "selector": "iframe URL",
                                "target_frame": target_frame
                            }

                    # Cloudflare Turnstile
                    if "challenges.cloudflare.com/turnstile" in url or "/turnstile/v0/" in url:
                        import urllib.parse
                        import re
                        parsed = urllib.parse.urlparse(url)
                        params = urllib.parse.parse_qs(parsed.query or parsed.fragment)
                        sitekey = params.get("sitekey", [None])[0]
                        if not sitekey:
                            match = re.search(r"[?&#]sitekey=([^&#]+)", url)
                            if match:
                                sitekey = match.group(1)
                                
                        if sitekey:
                            target_frame = frame.parent_frame or page.main_frame
                            logger.info(f"Detected Cloudflare Turnstile via frame URL: sitekey={sitekey}")
                            return {
                                "type": "cloudflare_turnstile",
                                "sitekey": sitekey,
                                "url": page.url,
                                "selector": "iframe URL",
                                "target_frame": target_frame
                            }
                except Exception as ex:
                    logger.debug(f"Error checking frame URL: {ex}")

            # 2. Second, scan all frames using selector-based queries inside their documents
            for frame in page.frames:
                try:
                    if frame.is_detached():
                        continue
                    
                    result = await asyncio.wait_for(
                        frame.evaluate("""
                            (patterns) => {
                                const isVisible = (el) => {
                                    if (!el) return false;
                                    const rect = el.getBoundingClientRect();
                                    return !!(rect.width || rect.height || el.getClientRects().length);
                                };
                                for (const [captchaType, selectors] of Object.entries(patterns)) {
                                    for (const selector of selectors) {
                                        try {
                                            const el = document.querySelector(selector);
                                            if (el) {
                                                if (selector.startsWith('iframe')) {
                                                    if (!el.src) continue;
                                                } else if (selector === '#recaptcha' || selector === '.g-recaptcha') {
                                                    const hasSitekey = el.hasAttribute('data-sitekey');
                                                    const hasIframe = el.querySelector('iframe') !== null;
                                                    if (!hasSitekey && !hasIframe) {
                                                        continue;
                                                    }
                                                    if (!isVisible(el)) {
                                                        continue;
                                                    }
                                                } else {
                                                    if (!isVisible(el)) continue;
                                                }
                                                
                                                return {
                                                    type: captchaType,
                                                    selector: selector
                                                };
                                            }
                                        } catch (e) {
                                            // Ignore invalid selectors
                                        }
                                    }
                                }
                                return null;
                            }
                        """, cls.CAPTCHA_PATTERNS),
                        timeout=5.0
                    )
                    
                    if result:
                        captcha_type = result["type"]
                        selector = result["selector"]
                        
                        try:
                            if captcha_type in ("recaptcha_v2", "recaptcha_v3"):
                                sitekey = await asyncio.wait_for(cls._extract_sitekey(frame, captcha_type), timeout=5.0)
                                if sitekey_from_input and sitekey != sitekey_from_input:
                                    logger.info(f"Overriding selector sitekey {sitekey} with input sitekey: {sitekey_from_input}")
                                    sitekey = sitekey_from_input
                            elif captcha_type == "hcaptcha":
                                sitekey = await asyncio.wait_for(cls._extract_hcaptcha_sitekey(frame), timeout=5.0)
                            elif captcha_type == "cloudflare_turnstile":
                                sitekey = await asyncio.wait_for(cls._extract_turnstile_sitekey(frame), timeout=5.0)
                        except Exception as ex:
                            logger.warning(f"Timeout or error extracting sitekey in frame for {captcha_type}: {ex}")
                            
                        invisible = False
                        enterprise = False
                        if captcha_type == "recaptcha_v2":
                            try:
                                invisible = await asyncio.wait_for(cls._check_recaptcha_invisible(frame), timeout=3.0)
                                enterprise = await asyncio.wait_for(cls._check_recaptcha_enterprise(frame), timeout=3.0)
                            except Exception as ex:
                                logger.debug(f"Failed to check invisible/enterprise recaptcha in frame: {ex}")
                                
                        if sitekey_from_input and sitekey == sitekey_from_input:
                            enterprise = False
                                
                        logger.info(
                            f"🔐 CAPTCHA detected via selectors in frame: {captcha_type} "
                            f"(sitekey={'present' if sitekey else 'none'}, invisible={invisible}, enterprise={enterprise})"
                        )
                        return {
                            "type": captcha_type,
                            "sitekey": sitekey,
                            "url": page.url,
                            "selector": selector,
                            "invisible": invisible,
                            "enterprise": enterprise,
                            "target_frame": frame
                        }
                except Exception as ex:
                    logger.debug(f"Error evaluating selectors in frame: {ex}")

        except Exception as e:
            logger.error(f"Error during CAPTCHA detection: {e}")
            
        return None

    @classmethod
    async def _extract_sitekey(cls, page: Page, captcha_type: str) -> Optional[str]:
        """Extract reCAPTCHA sitekey from page."""
        try:
            # Try from data-sitekey attribute
            sitekey = await page.evaluate("""
                () => {
                    const el = document.querySelector('[data-sitekey]');
                    if (el) return el.getAttribute('data-sitekey');

                    // Try from grecaptcha.render calls
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        const match = script.textContent?.match(/['\"]sitekey['\"]\s*:\s*['\"]([^'\"]+)['\"]/);
                        if (match) return match[1];

                        const match2 = script.src?.match(/[?&]k=([^&]+)/);
                        if (match2) return match2[1];
                    }

                    // Try from iframe src
                    const iframe = document.querySelector('iframe[src*="recaptcha"]');
                    if (iframe) {
                        const match = iframe.src.match(/[?&]k=([^&]+)/);
                        if (match) return match[1];
                    }

                    return null;
                }
            """)
            return sitekey
        except Exception as e:
            logger.debug(f"Failed to extract reCAPTCHA sitekey: {e}")
            return None

    @classmethod
    async def _check_recaptcha_invisible(cls, page: Page) -> bool:
        """Check if reCAPTCHA v2 is invisible."""
        try:
            return await page.evaluate("""
                () => {
                    const el = document.querySelector('[data-size="invisible"]');
                    if (el) return true;
                    
                    const iframe = document.querySelector('iframe[src*="recaptcha"][src*="size=invisible"]');
                    if (iframe) return true;
                    
                    const anchor = document.querySelector('iframe[src*="recaptcha/api2/anchor"]');
                    if (anchor && anchor.src.includes('size=invisible')) return true;
                    
                    return false;
                }
            """)
        except Exception:
            return False

    @classmethod
    async def _check_recaptcha_enterprise(cls, page: Page) -> bool:
        """Check if reCAPTCHA is Enterprise version."""
        try:
            return await page.evaluate("""
                () => {
                    const isEnterprise = !!(
                        document.querySelector('script[src*="recaptcha/enterprise"]') ||
                        document.querySelector('iframe[src*="recaptcha/enterprise"]')
                    );
                    return isEnterprise;
                }
            """)
        except Exception:
            return False

    @classmethod
    async def _extract_hcaptcha_sitekey(cls, page: Page) -> Optional[str]:
        """Extract hCaptcha sitekey from page."""
        try:
            return await page.evaluate("""
                () => {
                    const el = document.querySelector('[data-sitekey]');
                    if (el) return el.getAttribute('data-sitekey');
                    const iframe = document.querySelector('iframe[src*="hcaptcha"]');
                    if (iframe) {
                        const match = iframe.src.match(/[?&]sitekey=([^&]+)/);
                        if (match) return match[1];
                    }
                    return null;
                }
            """)
        except Exception:
            return None

    @classmethod
    async def _extract_turnstile_sitekey(cls, page: Page) -> Optional[str]:
        """Extract Cloudflare Turnstile sitekey from page."""
        try:
            return await page.evaluate("""
                () => {
                    const el = document.querySelector('[data-sitekey], .cf-turnstile');
                    if (el) return el.getAttribute('data-sitekey');
                    return null;
                }
            """)
        except Exception:
            return None

    @classmethod
    async def solve(
        cls,
        page: Page,
        captcha_info: Dict[str, Any],
        anticaptcha_key: Optional[str] = None,
        capsolver_key: Optional[str] = None,
    ) -> Optional[str]:
        """
        Solve a detected CAPTCHA using CapSolver or Anti-Captcha API.

        Args:
            page: Playwright page containing the CAPTCHA.
            captcha_info: Detection result from detect_captcha().
            anticaptcha_key: Anti-Captcha API key.
            capsolver_key: CapSolver API key (prioritized).

        Returns:
            Solution token string, or None if solving failed.
        """
        captcha_type = captcha_info["type"]
        target_frame = captcha_info.get("target_frame") or page

        logger.info(f"🔐 Solving {captcha_type} CAPTCHA...")

        try:
            if capsolver_key:
                logger.info("Using CapSolver solver...")
                if captcha_type == "cloudflare_challenge":
                    return await cls._solve_cloudflare_challenge(page, capsolver_key)
                return await cls._solve_with_capsolver_route(target_frame, captcha_info, capsolver_key)
            elif anticaptcha_key:
                logger.info("Using Anti-Captcha solver...")
                if captcha_type in ("recaptcha_v2", "recaptcha_v3"):
                    return await cls._solve_recaptcha(target_frame, captcha_info, anticaptcha_key)
                elif captcha_type == "hcaptcha":
                    return await cls._solve_hcaptcha(target_frame, captcha_info, anticaptcha_key)
                elif captcha_type == "cloudflare_turnstile":
                    return await cls._solve_turnstile(target_frame, captcha_info, anticaptcha_key)
                elif captcha_type == "cloudflare_challenge":
                    return await cls._solve_cloudflare_challenge(page, anticaptcha_key)
                else:
                    return await cls._solve_generic_captcha(target_frame, captcha_info, anticaptcha_key)
            else:
                logger.warning("No CAPTCHA solver keys configured")
                return None
        except Exception as e:
            logger.error(f"❌ CAPTCHA solving failed: {e}")
            return None

    @classmethod
    async def _solve_recaptcha(
        cls, page: Any, captcha_info: Dict[str, Any], api_key: str
    ) -> Optional[str]:
        """Solve reCAPTCHA v2/v3 using Anti-Captcha."""
        from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless

        sitekey = captcha_info.get("sitekey")
        if not sitekey:
            logger.warning("No reCAPTCHA sitekey found")
            return None

        actual_page = page.page if hasattr(page, "page") else page
        top_url = actual_page.url

        solver = recaptchaV2Proxyless()
        solver.set_verbose(1)
        solver.set_key(api_key)
        solver.set_website_url(top_url)
        solver.set_website_key(sitekey)

        # For invisible recaptcha
        if captcha_info["type"] == "recaptcha_v3":
            solver.set_is_invisible(True)

        start_time = time.time()
        token = solver.solve_and_return_solution()

        if token:
            elapsed = (time.time() - start_time) * 1000
            logger.success(f"✅ reCAPTCHA solved in {elapsed:.0f}ms")

            # Inject the token
            await page.evaluate(f"""
                () => {{
                    const textarea = document.querySelector('#g-recaptcha-response');
                    if (textarea) {{
                        textarea.value = '{token}';
                        textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}

                    // Try calling the callback if defined
                    if (typeof ___grecaptcha_cfg !== 'undefined') {{
                        const clients = ___grecaptcha_cfg.clients || {{}};
                        for (const [id, client] of Object.entries(clients)) {{
                            if (client.callback) {{
                                try {{ client.callback('{token}'); }} catch(e) {{}}
                            }}
                        }}
                    }}

                    // Also try window callback
                    if (typeof recaptchaCallback === 'function') {{
                        recaptchaCallback('{token}');
                    }}
                }}
            """)

            return token

        logger.error("reCAPTCHA solving returned no token")
        return None

    @classmethod
    async def _solve_hcaptcha(
        cls, page: Any, captcha_info: Dict[str, Any], api_key: str
    ) -> Optional[str]:
        """Solve hCaptcha using Anti-Captcha."""
        from anticaptchaofficial.hcaptchaproxyless import hCaptchaProxyless

        sitekey = captcha_info.get("sitekey")
        if not sitekey:
            return None

        actual_page = page.page if hasattr(page, "page") else page
        top_url = actual_page.url

        solver = hCaptchaProxyless()
        solver.set_verbose(1)
        solver.set_key(api_key)
        solver.set_website_url(top_url)
        solver.set_website_key(sitekey)

        start_time = time.time()
        token = solver.solve_and_return_solution()

        if token:
            elapsed = (time.time() - start_time) * 1000
            logger.success(f"✅ hCaptcha solved in {elapsed:.0f}ms")

            await page.evaluate(f"""
                () => {{
                    const textarea = document.querySelector('[name="h-captcha-response"]');
                    if (textarea) {{
                        textarea.value = '{token}';
                        textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}

                    // Call hcaptcha callback
                    if (typeof hcaptcha !== 'undefined') {{
                        try {{ hcaptcha.getResponse(); }} catch(e) {{}}
                    }}
                }}
            """)

            return token

        return None

    @classmethod
    async def _solve_turnstile(
        cls, page: Any, captcha_info: Dict[str, Any], api_key: str
    ) -> Optional[str]:
        """Solve Cloudflare Turnstile using Anti-Captcha."""
        from anticaptchaofficial.turnstileproxyless import turnstileProxyless

        sitekey = captcha_info.get("sitekey")
        if not sitekey:
            # Try to extract sitekey from turnstile widget
            try:
                sitekey = await page.evaluate("""
                    () => {
                        const els = document.querySelectorAll('[data-sitekey]');
                        for (const el of els) {
                            const key = el.getAttribute('data-sitekey');
                            if (key) return key;
                        }
                        return null;
                    }
                """)
            except Exception:
                pass

        if not sitekey:
            logger.warning("No Turnstile sitekey found")
            return None

        actual_page = page.page if hasattr(page, "page") else page
        top_url = actual_page.url

        solver = turnstileProxyless()
        solver.set_verbose(1)
        solver.set_key(api_key)
        solver.set_website_url(top_url)
        solver.set_website_key(sitekey)

        start_time = time.time()
        token = solver.solve_and_return_solution()

        if token:
            elapsed = (time.time() - start_time) * 1000
            logger.success(f"✅ Turnstile solved in {elapsed:.0f}ms")

            await page.evaluate(f"""
                () => {{
                    const input = document.querySelector('[name="cf-turnstile-response"]');
                    if (input) {{
                        input.value = '{token}';
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}

                    // Call turnstile callback
                    if (typeof turnstile !== 'undefined') {{
                        turnstile.render = function(){{}};
                    }}
                    if (typeof window.__cfBeacon !== 'undefined') {{
                        window.__cfBeacon('{token}');
                    }}
                }}
            """)

            return token

        return None

    @classmethod
    async def _solve_cloudflare_challenge(
        cls, page: Page, api_key: str
    ) -> Optional[str]:
        """
        Handle Cloudflare JS Challenge / "Checking your browser" page.

        Strategy: Wait for the challenge to auto-complete. If it doesn't,
        we rely on our stealth patches to pass the JS challenge.
        """
        logger.info("⏳ Waiting for Cloudflare challenge to resolve...")

        try:
            # Wait for the challenge page to redirect (normally 5 seconds)
            await page.wait_for_url(
                lambda url: "challenges.cloudflare.com" not in url,
                timeout=30000,
            )
            logger.success("✅ Cloudflare challenge passed automatically")
            return "cf_challenge_passed"
        except Exception:
            logger.warning("Cloudflare challenge did not resolve automatically")
            # Try clicking the "Verify you are human" checkbox if present
            try:
                checkbox = await page.query_selector(
                    'input[type="checkbox"], .h-captcha-box, #challenge-stage'
                )
                if checkbox:
                    await checkbox.click()
                    await asyncio.sleep(5)
                    return "cf_challenge_clicked"
            except Exception:
                pass
            return None

    @classmethod
    async def _solve_generic_captcha(
        cls, page: Page, captcha_info: Dict[str, Any], api_key: str
    ) -> Optional[str]:
        """Solve generic image CAPTCHAs using Anti-Captcha."""
        from anticaptchaofficial.imagecaptcha import imagecaptcha

        # Find and screenshot the CAPTCHA image
        img_selectors = [
            'img[src*="captcha"]',
            '#captcha img',
            '.captcha img',
            '#captchaImg',
            'img[alt*="captcha" i]',
        ]

        captcha_img = None
        for selector in img_selectors:
            captcha_img = await page.query_selector(selector)
            if captcha_img:
                break

        if not captcha_img:
            logger.warning("Could not find generic CAPTCHA image")
            return None

        # Get the image as base64
        import base64
        img_bytes = await captcha_img.screenshot(type="png")
        img_base64 = base64.b64encode(img_bytes).decode()

        solver = imagecaptcha()
        solver.set_verbose(1)
        solver.set_key(api_key)
        solver.set_body(img_base64)

        start_time = time.time()
        solution = solver.solve_and_return_solution()

        if solution:
            elapsed = (time.time() - start_time) * 1000
            logger.success(f"✅ Generic CAPTCHA solved in {elapsed:.0f}ms: '{solution}'")

            # Find and fill the input field
            input_selectors = [
                'input[name*="captcha" i]',
                '#captchaInput',
                '.captcha-input',
                'input[placeholder*="captcha" i]',
            ]
            for selector in input_selectors:
                input_field = await page.query_selector(selector)
                if input_field:
                    await input_field.fill(solution)
                    break

            return solution

        return None

    @classmethod
    async def _solve_via_capsolver(
        cls,
        capsolver_key: str,
        task_payload: Dict[str, Any],
        poll_interval: int = 3,
        timeout: int = 120,
    ) -> Optional[str]:
        import httpx
        import asyncio
        url_create = "https://api.capsolver.com/createTask"
        url_result = "https://api.capsolver.com/getTaskResult"

        async def _execute():
            async with httpx.AsyncClient(timeout=15.0) as client:
                logger.debug("🔍 CapSolver: sending createTask request...")
                res = await client.post(
                    url_create,
                    json={
                        "clientKey": capsolver_key,
                        "task": task_payload,
                    }
                )
                logger.debug(f"🔍 CapSolver: createTask response code {res.status_code}")
                if res.status_code != 200:
                    logger.error(f"CapSolver createTask HTTP error: {res.status_code}, response: {res.text}")
                    return None

                data = res.json()
                if data.get("errorId", 0) != 0:
                    logger.error(f"CapSolver createTask API error: {data.get('errorDescription')}")
                    return None

                task_id = data.get("taskId")
                if not task_id:
                    logger.error("CapSolver createTask response missing taskId")
                    return None

                logger.debug(f"🔍 CapSolver: created taskId {task_id}. Starting polling loop...")
                start_time = time.time()
                while time.time() - start_time < timeout:
                    await asyncio.sleep(poll_interval)
                    try:
                        logger.debug(f"🔍 CapSolver: polling taskId {task_id}...")
                        res_poll = await client.post(
                            url_result,
                            json={
                                "clientKey": capsolver_key,
                                "taskId": task_id,
                            }
                        )
                        logger.debug(f"🔍 CapSolver: poll response code {res_poll.status_code}")
                        if res_poll.status_code != 200:
                            logger.warning(f"CapSolver getTaskResult HTTP error: {res_poll.status_code}")
                            continue

                        data_poll = res_poll.json()
                        if data_poll.get("errorId", 0) != 0:
                            logger.error(f"CapSolver getTaskResult API error: {data_poll.get('errorDescription')}")
                            return None

                        status = data_poll.get("status")
                        logger.debug(f"🔍 CapSolver: taskId {task_id} status is '{status}'")
                        if status == "ready":
                            solution = data_poll.get("solution", {})
                            token = solution.get("gRecaptchaResponse") or solution.get("token") or solution.get("text")
                            return token
                        elif status == "failed":
                            logger.error("CapSolver task failed status received")
                            return None
                    except Exception as poll_ex:
                        logger.warning(f"Error during CapSolver poll request: {poll_ex}")
                        continue

                logger.error("CapSolver polling timed out in loop")
                return None

        try:
            logger.debug(f"🔍 CapSolver: entering asyncio.wait_for wrapper with timeout={timeout}s")
            return await asyncio.wait_for(_execute(), timeout=float(timeout))
        except asyncio.TimeoutError:
            logger.error("❌ CapSolver solve timed out (asyncio.wait_for)")
            return None
        except Exception as e:
            logger.error(f"CapSolver connection/parsing error: {e}")
            return None

    @classmethod
    async def _solve_with_capsolver_route(
        cls,
        page: Any,
        captcha_info: Dict[str, Any],
        capsolver_key: str,
    ) -> Optional[str]:
        captcha_type = captcha_info["type"]
        sitekey = captcha_info.get("sitekey")
        actual_page = page.page if hasattr(page, "page") else page
        page_url = actual_page.url

        # Look for legacy hidden captchaSiteKey input field in form (since backend might verify using it)
        input_sitekey = None
        try:
            input_sitekey_el = await page.query_selector('input[name="captchaSiteKey"]')
            if input_sitekey_el:
                input_sitekey = await input_sitekey_el.get_attribute("value")
                if input_sitekey:
                    logger.info(f"Found legacy captchaSiteKey input in form: {input_sitekey}")
        except Exception as ex:
            logger.debug(f"Failed to query captchaSiteKey input: {ex}")
            
        use_sitekey = input_sitekey or sitekey
        # Determine enterprise flag:
        # - If we are using the legacy input sitekey (LinkedIn-style), we DON'T know if it's enterprise
        #   so we try enterprise first.
        # - If the frame URL says enterprise, use enterprise.
        is_enterprise = captcha_info.get("enterprise", False)
        using_legacy_sitekey = bool(input_sitekey and input_sitekey != sitekey)
        if using_legacy_sitekey:
            # Legacy captchaSiteKey inputs on LinkedIn are typically enterprise reCAPTCHA
            is_enterprise = True

        proxy_config = getattr(actual_page.context, "_proxy_config", None)

        if captcha_type in ("recaptcha_v2", "recaptcha_v3"):
            if captcha_type == "recaptcha_v3":
                task_type = "ReCaptchaV3TaskProxyLess"
                payload = {
                    "type": task_type,
                    "websiteURL": page_url,
                    "websiteKey": use_sitekey,
                }
            else:
                if proxy_config and proxy_config.get("host") and proxy_config.get("port"):
                    task_type = "ReCaptchaV2EnterpriseTask" if is_enterprise else "ReCaptchaV2Task"
                    payload = {
                        "type": task_type,
                        "websiteURL": page_url,
                        "websiteKey": use_sitekey,
                        "proxyType": "http",
                        "proxyAddress": proxy_config["host"],
                        "proxyPort": int(proxy_config["port"]),
                    }
                    if proxy_config.get("username"):
                        payload["proxyLogin"] = proxy_config["username"]
                    if proxy_config.get("password"):
                        payload["proxyPassword"] = proxy_config["password"]
                else:
                    task_type = "ReCaptchaV2EnterpriseTaskProxyLess" if is_enterprise else "ReCaptchaV2TaskProxyLess"
                    payload = {
                        "type": task_type,
                        "websiteURL": page_url,
                        "websiteKey": use_sitekey,
                    }
            if captcha_type == "recaptcha_v2" and captcha_info.get("invisible") and not using_legacy_sitekey:
                # Only set isInvisible for true invisible reCAPTCHAs, NOT for LinkedIn legacy sitekey overrides
                # (LinkedIn checkpoint uses a visible challenge with a legacy sitekey — isInvisible causes API errors)
                payload["isInvisible"] = True
            if captcha_type == "recaptcha_v3":
                payload["pageAction"] = "verify"

            token = None
            if payload["type"] in ("ReCaptchaV2EnterpriseTask", "ReCaptchaV2Task"):
                logger.info(f"Attempting proxy-based solve with CapSolver ({payload['type']})...")
                token = await cls._solve_via_capsolver(capsolver_key, payload)
                if not token and is_enterprise:
                    # Try non-enterprise variant as fallback
                    logger.warning("Enterprise proxy-based solve failed, trying non-enterprise fallback...")
                    fallback_payload = {**payload, "type": "ReCaptchaV2Task"}
                    token = await cls._solve_via_capsolver(capsolver_key, fallback_payload)
                if not token:
                    logger.warning("Proxy-based solve failed, falling back to ProxyLess...")
            
            if not token:
                proxyless_payload = {
                    "type": "ReCaptchaV2EnterpriseTaskProxyLess" if is_enterprise else "ReCaptchaV2TaskProxyLess",
                    "websiteURL": page_url,
                    "websiteKey": use_sitekey,
                }
                if captcha_type == "recaptcha_v2" and captcha_info.get("invisible") and not using_legacy_sitekey:
                    proxyless_payload["isInvisible"] = True
                logger.info(f"Attempting ProxyLess solve with CapSolver ({proxyless_payload['type']})...")
                token = await cls._solve_via_capsolver(capsolver_key, proxyless_payload)
                if not token and is_enterprise:
                    # Try non-enterprise proxyless as final fallback
                    logger.warning("Enterprise proxyless solve failed, trying non-enterprise proxyless fallback...")
                    fallback_proxyless = {**proxyless_payload, "type": "ReCaptchaV2TaskProxyLess"}
                    token = await cls._solve_via_capsolver(capsolver_key, fallback_proxyless)
            if token:
                injection_js = f"""
                    () => {{
                        // 1. Set the token value in any g-recaptcha-response textareas
                        const textareas = document.querySelectorAll('textarea[name="g-recaptcha-response"], textarea[id*="g-recaptcha-response"], .g-recaptcha-response');
                        for (const textarea of textareas) {{
                            textarea.value = '{token}';
                            textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}

                        // 2. Set the token value in hidden response inputs (like LinkedIn's captchaUserResponseToken)
                        const responseInputs = document.querySelectorAll('input[name="captchaUserResponseToken"]');
                        for (const input of responseInputs) {{
                            input.value = '{token}';
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}

                        // 3. Update legacy/hidden captchaSiteKey input to match the actual sitekey used to solve it
                        const sitekeyInput = document.querySelector('input[name="captchaSiteKey"]');
                        if (sitekeyInput) {{
                            sitekeyInput.value = '{sitekey}';
                            sitekeyInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}

                        // 4. Recursively find and invoke callback functions in ___grecaptcha_cfg
                        if (typeof ___grecaptcha_cfg !== 'undefined') {{
                            const visited = new Set();
                            const findAndTriggerCallbacks = (obj, depth = 0) => {{
                                if (depth > 12 || !obj || typeof obj !== 'object' || visited.has(obj)) return;
                                visited.add(obj);
                                
                                for (const key in obj) {{
                                    try {{
                                        if (key === 'callback' && typeof obj[key] === 'function') {{
                                            obj[key]('{token}');
                                        }} else if (obj[key] && typeof obj[key] === 'object') {{
                                            findAndTriggerCallbacks(obj[key], depth + 1);
                                        }}
                                    }} catch(e) {{}}
                                }}
                            }};
                            
                            if (___grecaptcha_cfg.clients) {{
                                for (const [id, client] of Object.entries(___grecaptcha_cfg.clients)) {{
                                    findAndTriggerCallbacks(client);
                                }}
                            }}
                        }}

                        // 5. Fallback to standard global callback functions
                        const globalCallbacks = [
                            'recaptchaOnSubmit',
                            'onSubmit',
                            'onCaptchaSubmit',
                            'onCaptchaSuccess',
                            'captchaCallback',
                            'submitForm'
                        ];
                        let callbackTriggered = false;
                        for (const cbName of globalCallbacks) {{
                            if (typeof window[cbName] === 'function' && cbName !== 'recaptchaCallback') {{
                                try {{
                                    window[cbName]('{token}');
                                    callbackTriggered = true;
                                    break;
                                }} catch(e) {{}}
                            }}
                        }}

                        if (!callbackTriggered && typeof recaptchaCallback === 'function') {{
                            try {{
                                recaptchaCallback('{token}');
                            }} catch(e) {{
                                try {{
                                    recaptchaCallback({{ preventDefault: () => {{}} }});
                                }} catch(e2) {{}}
                            }}
                        }}

                        // 6. Auto-submit form if it's a dedicated captcha challenge form
                        const challengeForm = document.querySelector('form#captcha-challenge');
                        if (challengeForm) {{
                            let extraInput = challengeForm.querySelector('input[name="g-recaptcha-response"]');
                            if (!extraInput) {{
                                extraInput = document.createElement('input');
                                extraInput.type = 'hidden';
                                extraInput.name = 'g-recaptcha-response';
                                challengeForm.appendChild(extraInput);
                            }}
                            extraInput.value = '{token}';
                            challengeForm.submit();
                        }}
                    }}
                """
                
                # Evaluate in main page with timeout
                logger.debug("Evaluating injection_js on main page...")
                await asyncio.wait_for(actual_page.evaluate(injection_js), timeout=10.0)
                
                # Evaluate in all child frames as well with timeout
                for frame in actual_page.frames:
                    try:
                        if not frame.is_detached() and frame != actual_page.main_frame:
                            logger.debug(f"Evaluating injection_js on child frame: {frame.url[:50]}")
                            await asyncio.wait_for(frame.evaluate(injection_js), timeout=5.0)
                    except Exception as frame_ex:
                        logger.debug(f"Frame evaluation skipped or failed: {frame_ex}")
                        
                return token

        elif captcha_type == "hcaptcha":
            payload = {
                "type": "HCaptchaTaskProxyLess",
                "websiteURL": page_url,
                "websiteKey": sitekey,
            }
            token = await cls._solve_via_capsolver(capsolver_key, payload)
            if token:
                await page.evaluate(f"""
                    () => {{
                        const textarea = document.querySelector('[name="h-captcha-response"]');
                        if (textarea) {{
                            textarea.value = '{token}';
                            textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}

                        if (typeof hcaptcha !== 'undefined') {{
                            try {{ hcaptcha.getResponse(); }} catch(e) {{}}
                        }}
                    }}
                """)
                return token

        elif captcha_type == "cloudflare_turnstile":
            if not sitekey:
                try:
                    sitekey = await page.evaluate("""
                        () => {
                            const els = document.querySelectorAll('[data-sitekey]');
                            for (const el of els) {
                                const key = el.getAttribute('data-sitekey');
                                if (key) return key;
                            }
                            return null;
                        }
                    """)
                except Exception:
                    pass

            if not sitekey:
                logger.warning("No Turnstile sitekey found for CapSolver")
                return None

            payload = {
                "type": "AntiTurnstileTaskProxyLess",
                "websiteURL": page_url,
                "websiteKey": sitekey,
            }
            token = await cls._solve_via_capsolver(capsolver_key, payload)
            if token:
                await page.evaluate(f"""
                    () => {{
                        const input = document.querySelector('[name="cf-turnstile-response"]');
                        if (input) {{
                            input.value = '{token}';
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}

                        if (typeof turnstile !== 'undefined') {{
                            turnstile.render = function(){{}};
                        }}
                        if (typeof window.__cfBeacon !== 'undefined') {{
                            window.__cfBeacon('{token}');
                        }}
                    }}
                """)
                return token

        elif captcha_type == "cloudflare_challenge":
            return await cls._solve_cloudflare_challenge(page, capsolver_key)

        else:
            img_selectors = [
                'img[src*="captcha"]',
                '#captcha img',
                '.captcha img',
                '#captchaImg',
                'img[alt*="captcha" i]',
            ]

            captcha_img = None
            for selector in img_selectors:
                captcha_img = await page.query_selector(selector)
                if captcha_img:
                    break

            if not captcha_img:
                logger.warning("Could not find generic CAPTCHA image for CapSolver")
                return None

            import base64
            img_bytes = await captcha_img.screenshot(type="png")
            img_base64 = base64.b64encode(img_bytes).decode()

            payload = {
                "type": "ImageToTextTask",
                "body": img_base64,
            }
            solution = await cls._solve_via_capsolver(capsolver_key, payload)
            if solution:
                logger.success(f"✅ Generic CAPTCHA solved by CapSolver: '{solution}'")
                input_selectors = [
                    'input[name*="captcha" i]',
                    '#captchaInput',
                    '.captcha-input',
                    'input[placeholder*="captcha" i]',
                ]
                for selector in input_selectors:
                    input_field = await page.query_selector(selector)
                    if input_field:
                        await input_field.fill(solution)
                        break
                return solution

        return None

    # LinkedIn's known reCAPTCHA v2 sitekey used on checkpoint/challenge pages
    LINKEDIN_RECAPTCHA_SITEKEY = "6LdpuiQTAAAAALDtAuMQ3MD-GHHHKqONaqK2_xM3"

    @classmethod
    async def force_detect_linkedin_recaptcha(cls, page: Page) -> Optional[Dict[str, Any]]:
        """
        Force-detect reCAPTCHA on LinkedIn's checkpoint/challenge page.
        
        LinkedIn uses reCAPTCHA v2 with a specific sitekey. This method tries multiple
        extraction strategies and falls back to LinkedIn's known sitekey.
        
        Returns a captcha_info dict (like detect_captcha) or None.
        """
        # Check if the page is currently asking for Security Verification OTP instead of CAPTCHA
        try:
            page_text = await page.evaluate("() => document.body.innerText.toLowerCase()")
            if any(kw in page_text for kw in ["verification code", "verification-code", "security code", "enter the code", "enter the 6-digit", "sent to your email"]):
                logger.info("ℹ️ Page text indicates an OTP / Verification page. Skipping force-detection.")
                return None
        except Exception:
            pass

        try:
            # ── Check if CAPTCHA has already been solved/token-filled ──
            if await cls._is_captcha_solved(page):
                logger.info("⏳ CAPTCHA token is already populated. Skipping force-detection.")
                return None
        except Exception:
            pass

        sitekey_from_input = None
        try:
            sitekey_from_input = await page.evaluate("""
                () => {
                    const input = document.querySelector('input[name="captchaSiteKey"], input[id*="captchaSiteKey"]');
                    if (input && input.value && input.value.trim().length > 10) {
                        return input.value.trim();
                    }
                    return null;
                }
            """)
        except Exception:
            pass

        try:
            page_url = page.url
            logger.info(f"🔍 Force-detecting LinkedIn reCAPTCHA on: {page_url}")

            # Strategy 1: Scan all frames for reCAPTCHA iframes
            for frame in page.frames:
                try:
                    if frame.is_detached():
                        continue
                    frame_url = frame.url or ""
                    if "google.com/recaptcha" in frame_url or "recaptcha/api2" in frame_url:
                        import urllib.parse, re
                        parsed = urllib.parse.urlparse(frame_url)
                        params = urllib.parse.parse_qs(parsed.query or parsed.fragment)
                        sitekey = params.get("k", [None])[0]
                        if not sitekey:
                            match = re.search(r"[?&#]k=([^&#]+)", frame_url)
                            if match:
                                sitekey = match.group(1)
                        
                        if not sitekey:
                            sitekey = cls.LINKEDIN_RECAPTCHA_SITEKEY
                        
                        if sitekey_from_input and sitekey != sitekey_from_input:
                            logger.info(f"Overriding force-detect sitekey {sitekey} with input sitekey: {sitekey_from_input}")
                            sitekey = sitekey_from_input
                        
                        logger.info(f"✅ Force-detected reCAPTCHA via frame scan: sitekey={sitekey}")
                        return {
                            "type": "recaptcha_v2",
                            "sitekey": sitekey,
                            "url": page_url,
                            "selector": "iframe (force-detected)",
                            "invisible": False,
                            "enterprise": False,
                            "target_frame": page.main_frame,
                        }
                except Exception:
                    continue

            # Strategy 2: Look for reCAPTCHA in DOM (even if not yet interactive)
            try:
                sitekey = await asyncio.wait_for(
                    page.evaluate("""
                        () => {
                            // Check data-sitekey attribute
                            const el = document.querySelector('[data-sitekey]');
                            if (el) return el.getAttribute('data-sitekey');
                            // Check iframe src
                            const iframes = document.querySelectorAll('iframe');
                            for (const f of iframes) {
                                const src = f.src || f.getAttribute('src') || '';
                                if (src.includes('recaptcha')) {
                                    const m = src.match(/[?&]k=([^&]+)/);
                                    if (m) return m[1];
                                }
                            }
                            // Check scripts for sitekey
                            for (const s of document.querySelectorAll('script')) {
                                const text = s.textContent || '';
                                const m = text.match(/sitekey['"\\s]*:['"\\s]*([A-Za-z0-9_-]{30,})/);
                                if (m) return m[1];
                            }
                            return null;
                        }
                    """),
                    timeout=5.0,
                )
                if sitekey:
                    logger.info(f"✅ Force-detected reCAPTCHA via DOM: sitekey={sitekey}")
                    return {
                        "type": "recaptcha_v2",
                        "sitekey": sitekey,
                        "url": page_url,
                        "selector": "DOM (force-detected)",
                        "invisible": False,
                        "enterprise": False,
                        "target_frame": page.main_frame,
                    }
            except Exception as ex:
                logger.debug(f"DOM sitekey extraction failed: {ex}")

            # Strategy 3: LinkedIn checkpoint page — use known sitekey as fallback
            if "checkpoint" in page_url.lower() or "challenge" in page_url.lower():
                # Check if the page has any reCAPTCHA-related text or elements
                try:
                    has_recaptcha = await asyncio.wait_for(
                        page.evaluate("""
                            () => {
                                const text = document.body.innerText.toLowerCase();
                                const hasRecaptchaText = text.includes('not a robot') || 
                                    text.includes('security check') || text.includes('verify');
                                const hasRecaptchaEl = !!(
                                    document.querySelector('.g-recaptcha') ||
                                    document.querySelector('[id*="recaptcha"]') ||
                                    document.querySelector('[class*="recaptcha"]') ||
                                    document.querySelector('iframe')
                                );
                                return hasRecaptchaText || hasRecaptchaEl;
                            }
                        """),
                        timeout=5.0,
                    )
                    if has_recaptcha:
                        logger.info(f"✅ Force-detected LinkedIn reCAPTCHA using fallback sitekey: {cls.LINKEDIN_RECAPTCHA_SITEKEY}")
                        return {
                            "type": "recaptcha_v2",
                            "sitekey": cls.LINKEDIN_RECAPTCHA_SITEKEY,
                            "url": page_url,
                            "selector": "force-detect fallback",
                            "invisible": False,
                            "enterprise": False,
                            "target_frame": page.main_frame,
                        }
                except Exception as ex:
                    logger.debug(f"reCAPTCHA presence check failed: {ex}")

        except Exception as e:
            logger.error(f"force_detect_linkedin_recaptcha error: {e}")

        return None

    @classmethod
    async def handle_captcha_flow(
        cls,
        page,
        anticaptcha_key: Optional[str] = None,
        capsolver_key: Optional[str] = None,
        max_attempts: int = 3,
    ) -> bool:
        """
        Full CAPTCHA handling flow: detect → solve → verify.

        Returns True if CAPTCHA was solved or none was detected.
        Returns False if CAPTCHA could not be solved after max_attempts.
        """
        for attempt in range(max_attempts):
            captcha_info = await cls.detect_captcha(page)

            if not captcha_info:
                logger.debug("No CAPTCHA detected on page")
                return True

            logger.info(
                f"🔐 CAPTCHA attempt {attempt + 1}/{max_attempts}: "
                f"{captcha_info['type']}"
            )

            token = await cls.solve(
                page,
                captcha_info,
                anticaptcha_key=anticaptcha_key,
                capsolver_key=capsolver_key,
            )

            if token:
                logger.success("✅ CAPTCHA solved successfully!")
                return True
            else:
                logger.warning(f"CAPTCHA solve attempt {attempt + 1} failed")

            await asyncio.sleep(2 ** attempt)

        logger.error(f"❌ Failed to solve CAPTCHA after {max_attempts} attempts")
        return False
