"""
AutoWebAgent - Agent Service (Core Execution Engine)
======================================================
The main agent that executes natural language tasks on websites.
Orchestrates: LLM planning → Stealth browsing → CAPTCHA solving → Execution.
"""

import asyncio
import json
import time
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from beanie import PydanticObjectId
from loguru import logger

from app.core.config import settings
from app.core.llm import get_llm_client
from app.core.exceptions import (
    AgentExecutionError,
    CaptchaSolveError,
    SessionNotFoundError,
    TaskNotFoundError,
)
from app.features.tasks.models import TaskDocument, TaskStatus
from app.features.sessions.models import SessionDocument
from app.features.sessions.service import SessionService
from app.features.auth.models import UserDocument
from app.features.auth.service import AuthService
from app.features.agent.stealth import StealthManager, HumanBehavior
from app.features.agent.captcha_solver import CaptchaSolver
from app.features.agent.dom_parser import PageAgentDOMParser


class AgentService:
    """
    Core agent that executes web automation tasks.

    Flow:
    1. Get task + session → Load browser context
    2. LLM generates action plan from task prompt
    3. Execute each action step with stealth + human-like behavior
    4. Detect & solve CAPTCHAs as encountered
    5. Retry failed steps with alternative strategies
    6. Extract results and persist
    """

    @staticmethod
    async def _accept_cookies(page) -> bool:
        """
        Accept cookie consent popups (OneTrust + generic).
        Returns True if a cookie dialog was found and accepted/closed.
        Call this multiple times — cookie popups often appear with a delay.
        """
        try:
            # Quick check: is any cookie dialog visible?
            has_dialog = await page.evaluate("""
                () => {
                    const ot = document.querySelector('#onetrust-consent-sdk');
                    if (ot && ot.offsetParent !== null) return true;
                    const banners = document.querySelectorAll(
                        '[id*="cookie" i], [class*="cookie" i], [id*="consent" i], [class*="consent" i], [aria-label*="cookie" i]'
                    );
                    for (const b of banners) {
                        if (b.offsetParent !== null) return true;
                    }
                    return false;
                }
            """)
            if not has_dialog:
                return False

            await asyncio.sleep(0.3)  # let dialog fully render

            # ── Pass 1: ACCEPT buttons ──
            accept_selectors = [
                "#accept-recommended-btn-handler",
                "#onetrust-accept-btn-handler",
                "button:has-text('Allow All')",
                "button:has-text('Accept All Cookies')",
                "button:has-text('Accept All')",
                "button:has-text('Accept Cookies')",
                "button:has-text('I Accept')",
                "button:has-text('I Agree')",
                "button:has-text('Accept')",
                "a:has-text('Accept')",
                "button:has-text('Agree')",
                "button:has-text('Allow')",
                "button:has-text('Got it')",
                "button:has-text('OK')",
                ".cc-btn.cc-allow",
                "button[aria-label*='accept' i]",
                "button[aria-label*='allow' i]",
                ".save-preference-btn-handler",
                "button:has-text('Confirm My Choices')",
                "button:has-text('Save')",
            ]
            for css in accept_selectors:
                try:
                    btn = page.locator(css).first
                    if await btn.is_visible(timeout=300):
                        label = (await btn.inner_text()).strip()[:40]
                        logger.info(f"🍪 ACCEPTING cookie popup: '{label}' via {css}")
                        await btn.click(force=True, timeout=3000)
                        await asyncio.sleep(0.8)
                        return True
                except Exception:
                    continue

            # ── Pass 2: CLOSE buttons (last resort) ──
            close_selectors = [
                "#close-pc-btn-handler",
                "button[aria-label*='close' i]",
                "button:has-text('Close')",
                "button:has-text('Reject All')",
                "button:has-text('Decline')",
                "button:has-text('No Thanks')",
                "button:has-text('Necessary Only')",
            ]
            for css in close_selectors:
                try:
                    btn = page.locator(css).first
                    if await btn.is_visible(timeout=300):
                        label = (await btn.inner_text()).strip()[:40]
                        logger.info(f"🍪 Closing cookie popup (no accept found): '{label}' via {css}")
                        await btn.click(force=True, timeout=3000)
                        await asyncio.sleep(0.8)
                        return True
                except Exception:
                    continue

            return False
        except Exception as e:
            logger.debug(f"Cookie accept check error: {e}")
            return False

    @classmethod
    async def execute_task(cls, task_id: str, user_id: str) -> None:
        """
        Main execution entry point. Runs the full agent pipeline.

        Called asynchronously when a task is created.
        Updates task status throughout execution.
        """
        task = await TaskDocument.get(PydanticObjectId(task_id))
        if not task:
            logger.error(f"Task not found: {task_id}")
            return

        try:
            # Mark as running
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            await task.save()

            logger.info(f"🤖 Agent starting task {task_id}: '{task.prompt[:100]}...'")

            # Get user and API keys
            user = await UserDocument.get(PydanticObjectId(user_id))
            if not user:
                raise AgentExecutionError(task_id, "User not found")

            api_keys = AuthService.get_decrypted_api_keys(user)

            # Validate required keys
            deepseek_key = api_keys.get("deepseek_api_key")
            if not deepseek_key:
                raise AgentExecutionError(
                    task_id,
                    "No DeepSeek API key configured. Add your key in Settings.",
                )

            anticaptcha_key = api_keys.get("anticaptcha_api_key")
            capsolver_key = api_keys.get("capsolver_api_key")

            # Get or create session
            session_id = task.session_id
            if not session_id:
                # Auto-create a session if none provided
                from app.features.sessions.schemas import SessionCreateRequest
                session_data = SessionCreateRequest(
                    name=f"Task-{task_id[:8]}",
                    stealth_mode=settings.STEALTH_MODE,
                )
                session = await SessionService.create_session(
                    user_id, session_data, api_keys
                )
                session_id = str(session.id)
                task.session_id = session_id
                await task.save()

            # Get browser context
            context = SessionService.get_context(session_id)
            page = await context.new_page()

            # Intercept grecaptcha functions on page creation (New Document load)
            await page.add_init_script("""
                window.__bot_widget_ids = {};
                window.__bot_token = '';
                
                let rawGrecaptcha = window.grecaptcha;
                
                function wrapGrecaptcha(val) {
                    if (!val || typeof val !== 'object' || val.__is_bot_proxy) return val;
                    
                    return new Proxy(val, {
                        get: function(target, prop, receiver) {
                            if (prop === '__is_bot_proxy') return true;
                            
                            if (prop === 'render') {
                                const origRender = target[prop];
                                if (typeof origRender === 'function') {
                                    return function(container, config) {
                                        console.log('[Bot] grecaptcha.render called with config:', config);
                                        const widgetId = origRender.apply(this, arguments);
                                        window.__bot_widget_ids[widgetId] = config;
                                        
                                        // If we already have the token, trigger callback immediately
                                        if (window.__bot_token && typeof config.callback === 'function') {
                                            setTimeout(function() { config.callback(window.__bot_token); }, 200);
                                        }
                                        return widgetId;
                                    };
                                }
                            }
                            
                            if (prop === 'execute') {
                                const origExecute = target[prop];
                                return function(widgetId) {
                                    console.log('[Bot] grecaptcha.execute(' + widgetId + ') called');
                                    if (window.__bot_token) {
                                        var w = window.__bot_widget_ids[widgetId || 0];
                                        if (w && typeof w.callback === 'function') {
                                            setTimeout(function() { w.callback(window.__bot_token); }, 100);
                                            return Promise.resolve(window.__bot_token);
                                        }
                                        // Also try ___grecaptcha_cfg
                                        if (typeof ___grecaptcha_cfg !== 'undefined') {
                                            var c = (___grecaptcha_cfg.clients || {})[widgetId || 0];
                                            if (c) {
                                                var cb = c.callback || c['callback'];
                                                if (typeof cb === 'function') {
                                                    setTimeout(function() { cb(window.__bot_token); }, 100);
                                                    return Promise.resolve(window.__bot_token);
                                                }
                                            }
                                        }
                                    }
                                    if (typeof origExecute === 'function') {
                                        return origExecute.apply(this, arguments);
                                    }
                                    return Promise.resolve(window.__bot_token || '');
                                };
                            }
                            
                            if (prop === 'getResponse') {
                                const origGetResponse = target[prop];
                                return function(widgetId) {
                                    if (window.__bot_token) return window.__bot_token;
                                    if (typeof origGetResponse === 'function') {
                                        return origGetResponse.apply(this, arguments);
                                    }
                                    return '';
                                };
                            }
                            
                            if (prop === 'reset') {
                                return function(widgetId) {
                                    console.log('[Bot] grecaptcha.reset blocked');
                                };
                            }
                            
                            return Reflect.get(target, prop, receiver);
                        }
                    });
                }
                
                if (rawGrecaptcha) {
                    rawGrecaptcha = wrapGrecaptcha(rawGrecaptcha);
                }
                
                Object.defineProperty(window, 'grecaptcha', {
                    configurable: true,
                    enumerable: true,
                    get: function() { return rawGrecaptcha; },
                    set: function(val) { rawGrecaptcha = wrapGrecaptcha(val); }
                });
            """)

            # ── Dynamic Step Planning & Execution Loop ───────
            logger.info(f"🧠 Initiating dynamic step-by-step agent loop for task {task_id}...")

            llm = get_llm_client(
                user_api_key=deepseek_key,
                user_id=user_id,
            )

            # Get initial page loaded if specified
            if task.website_id:
                from app.features.websites.service import WebsiteService
                try:
                    website = await WebsiteService.get_website(
                        task.website_id, user_id
                    )
                    logger.info(f"Navigating to initial website: {website.url}")
                    await page.goto(website.url, wait_until="networkidle")
                except Exception as e:
                    logger.warning(f"Failed to load initial website: {e}")

            task.plan = []
            task.total_steps = 0
            await task.save()

            extracted_data = {}
            screenshots = []
            screenshot_worker_state = {"active": True}

            async def screenshot_worker():
                while screenshot_worker_state["active"]:
                    try:
                        screenshot = await asyncio.wait_for(
                            page.screenshot(type="png", full_page=False),
                            timeout=3.0
                        )
                        screenshot_b64 = base64.b64encode(screenshot).decode()
                        
                        fresh_task = await TaskDocument.get(task.id)
                        if fresh_task:
                            current_ss = fresh_task.screenshots or []
                            current_ss.append(screenshot_b64)
                            fresh_task.screenshots = current_ss[-50:]
                            await fresh_task.save()
                            
                            nonlocal screenshots
                            screenshots = fresh_task.screenshots
                    except Exception:
                        pass
                    await asyncio.sleep(3.0)

            screenshot_bg_task = asyncio.create_task(screenshot_worker())

            max_steps = 50
            step_idx = 0
            task_finished_successfully = False
            # ── Anti-loop tracking ─────────────────────────────────────
            _recent_nav_urls: list[str] = []   # track last 5 navigate URLs
            _wait_scroll_streak: int = 0        # consecutive wait/scroll count
            _was_on_oauth: bool = False          # track OAuth domain transitions
            _oauth_return_time: float = 0.0       # timestamp when we returned from OAuth (block navigate for 45s)

            while step_idx < max_steps and not task_finished_successfully:
                # 0a. ── Post-OAuth settle wait ──────────────────────────────
                # When OAuth redirect lands back on the store, the SPA needs
                # 3-8 seconds to initialize the session. If agent clicks "Sign In"
                # during this window, it interrupts the session and discards it.
                _oauth_keywords = [
                    "customerlogin.", "login.microsoft", "login.live",
                    "microsoftonline", "azure.com/oauth", "okta.com",
                    "auth0.com", "onelogin.", "/sso/", "/idp/",
                ]
                _currently_on_oauth = any(kw in page.url.lower() for kw in _oauth_keywords)
                if _was_on_oauth and not _currently_on_oauth:
                    logger.info("🔄 Just returned from OAuth/SSO domain. Waiting 10s for session to initialize (SPA settle)...")
                    _oauth_return_time = time.time()  # start 45s block window
                    await asyncio.sleep(10)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    # ── Re-check: is session actually loaded? ──
                    # If header still shows "Sign In", session hasn't initialized yet — wait more
                    # ALSO accept any cookie popup that appears during this wait
                    for _retry in range(3):
                        try:
                            # ── Accept cookies during settle wait ──
                            await cls._accept_cookies(page)

                            page_text_check2 = await page.evaluate(
                                "() => document.body ? document.body.innerText.toLowerCase() : ''"
                            )
                            still_shows_signin = (
                                "sign in" in page_text_check2
                                or "sign in / register" in page_text_check2
                            ) and not any(
                                kw in page_text_check2 for kw in [
                                    "my account", "welcome", "log out", "sign out",
                                    "my orders", "quick order", "order status"
                                ]
                            )
                            if still_shows_signin:
                                logger.info(f"⏳ Session still initializing (header shows 'Sign In'). Waiting 5s more (retry {_retry + 1}/3)...")
                                await asyncio.sleep(5)
                            else:
                                break
                        except Exception:
                            break
                    # ── Final cookie accept after settle ──
                    await cls._accept_cookies(page)
                    logger.info("✅ Post-OAuth settle complete. Session should be ready now.")
                _was_on_oauth = _currently_on_oauth

                # 0b. ACCEPT cookie consent popups (retry — they often load with delay)
                try:
                    for _cookie_retry in range(2):
                        if await cls._accept_cookies(page):
                            break
                        await asyncio.sleep(1)  # short delay between retries
                except Exception:
                    pass

                # 0b. Check if page shows reCAPTCHA verification failed — reload so agent retries login
                try:
                    page_text_check = await page.evaluate("() => document.body ? document.body.innerText.toLowerCase() : ''")
                    current_url_check = page.url.lower()

                    # Derive the login URL from the current origin (works for any Magento site)
                    _login_url = "https://shop.aarcorp.com/customer/account/login"
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(page.url)
                        origin = f"{parsed.scheme}://{parsed.netloc}"
                        _login_url = f"{origin}/customer/account/login"
                    except Exception:
                        pass

                    if ("recaptcha verification failed" in page_text_check or
                            "something went wrong with recaptcha" in page_text_check):
                        logger.warning("⚠️ reCAPTCHA verification failed on page. Reloading login page to retry...")
                        await page.goto(_login_url, wait_until="networkidle", timeout=30000)
                        await asyncio.sleep(3)

                    # Detect if we landed on homepage after a login attempt (Magento redirect pattern)
                    # Last step was a login click but we're not on an account page
                    # ── BUT skip this check on OAuth/SSO domains (they naturally contain "login") ──
                    _oauth_domains_0 = [
                        "customerlogin.", "login.microsoft", "login.live",
                        "microsoftonline", "azure.com", "oauth", "okta.com",
                        "auth0.com", "onelogin.", "sso.", "idp.",
                    ]
                    _is_oauth_0 = any(d in current_url_check for d in _oauth_domains_0)
                    if task.steps_executed and not _is_oauth_0:
                        last_step = task.steps_executed[-1]
                        last_desc = (last_step.get("description") or "").lower()
                        last_action = last_step.get("action", "")
                        was_login_attempt = (
                            last_action == "click"
                            and any(kw in last_desc for kw in ["sign in", "login", "log in", "submit", "signin"])
                        )
                        if was_login_attempt:
                            # If we're on homepage (not account/dashboard) after login attempt → failed
                            is_on_login_page = any(
                                kw in current_url_check
                                for kw in ["/login", "/signin", "sign_in", "/auth"]
                            )
                            is_on_homepage_root = (
                                current_url_check.rstrip("/").endswith((".com", ".com/"))
                                and not any(
                                    kw in current_url_check
                                    for kw in ["account", "dashboard", "my-account", "profile", "user", "checkout"]
                                )
                            )
                            if is_on_login_page or is_on_homepage_root:
                                logger.warning(
                                    f"🔴 Step-0 detection: Login attempt failed — landed on "
                                    f"{'login page' if is_on_login_page else 'homepage'} instead of account. "
                                    f"Reloading login page to retry..."
                                )
                                await page.goto(_login_url, wait_until="networkidle", timeout=30000)
                                await asyncio.sleep(3)
                except Exception:
                    pass

                # 1. First scan and solve any CAPTCHA before doing any analysis or step decisions!
                try:
                    captcha_detected = await CaptchaSolver.detect_captcha(page)
                    if captcha_detected:
                        logger.info(f"🔐 CAPTCHA detected at step {step_idx + 1} start: {captcha_detected['type']}. Solving...")
                        task.captcha_detected = True
                        task.captcha_type = captcha_detected["type"]
                        await task.save()
                        captcha_start = time.time()

                        if capsolver_key or anticaptcha_key:
                            solved = await CaptchaSolver.handle_captcha_flow(
                                page,
                                anticaptcha_key=anticaptcha_key,
                                capsolver_key=capsolver_key,
                            )
                            if solved:
                                task.captcha_solved = True
                                task.captcha_solve_time_ms = int(
                                    (time.time() - captcha_start) * 1000
                                )
                                session_doc = await SessionDocument.get(
                                    PydanticObjectId(session_id)
                                )
                                if session_doc:
                                    session_doc.captchas_solved += 1
                                    await session_doc.save()
                                await task.save()
                                logger.success("✅ CAPTCHA solved successfully!")
                                # Give the page a moment to load next content after solve
                                await asyncio.sleep(4)
                            else:
                                raise CaptchaSolveError(captcha_detected["type"])
                        else:
                            logger.warning("⚠️ CAPTCHA detected but no solver keys configured")
                            task.status = TaskStatus.WAITING_CAPTCHA
                            await task.save()
                            # We can't proceed without solver keys
                            return
                except Exception as captcha_ex:
                    logger.error(f"Error handling CAPTCHA at step start: {captcha_ex}")
                    task.status = TaskStatus.FAILED
                    task.error_message = f"CAPTCHA solving failed: {captcha_ex}"
                    await task.save()
                    return

                # 2. Check if the page is asking for Security Verification (OTP/Email Code/Checkpoint)
                try:
                    is_verification_page = False
                    for _eval_attempt in range(3):
                        try:
                            # Wait for load state to settle if navigating
                            try:
                                await page.wait_for_load_state("domcontentloaded", timeout=3000)
                            except Exception:
                                pass
                            page_text_lower = await page.evaluate("() => document.body ? document.body.innerText.toLowerCase() : ''")
                            current_url = page.url
                            current_title = await page.title()
                            current_url_lower = current_url.lower()
                            current_title_lower = current_title.lower()

                            # Check URL and title keywords — only trigger on explicit checkpoint URLs
                            if "checkpoint/challenge" in current_url_lower or "checkpoint" in current_url_lower:
                                is_verification_page = True

                            # Only check title for very explicit verification titles
                            if "security verification" in current_title_lower and "linkedin" in current_url_lower:
                                is_verification_page = True

                            # Check text keywords — use only very specific OTP phrases unlikely to appear on commerce sites
                            for kw in ["verification code", "enter the code", "enter the 6-digit", "enter your one-time", "enter the one-time"]:
                                if kw in page_text_lower:
                                    is_verification_page = True
                                    break
                            break
                        except Exception as eval_ex:
                            logger.debug(f"Failed to evaluate page for OTP request (attempt {_eval_attempt + 1}): {eval_ex}")
                            await asyncio.sleep(2)

                    # Check if we recently received user input and are still typing/submitting it
                    recent_input_received = False
                    for step in reversed(task.steps_executed):
                        if step.get("action") == "receive_user_input":
                            recent_input_received = True
                            break
                        if step.get("action") in ("click", "navigate"):
                            break

                    if is_verification_page and not recent_input_received:
                        # ── Retry CAPTCHA detection with longer waits for LinkedIn reCAPTCHA ──
                        # LinkedIn's reCAPTCHA iframe takes several seconds to fully load.
                        # We do multiple detection passes before giving up and going to OTP mode.
                        captcha_solved_on_security_page = False
                        captcha_solve_error = None
                        detection_wait_schedule = [3, 4, 5]  # seconds to wait between attempts

                        for detection_attempt, wait_seconds in enumerate(detection_wait_schedule):
                            logger.info(f"⏳ Security challenge detected. Waiting {wait_seconds}s for CAPTCHA to load (attempt {detection_attempt + 1}/{len(detection_wait_schedule)})...")
                            await asyncio.sleep(wait_seconds)

                            try:
                                captcha_detected = await CaptchaSolver.detect_captcha(page)
                                
                                # If no CAPTCHA detected via normal detection, try force-detecting
                                # reCAPTCHA on LinkedIn's checkpoint/challenge page
                                if not captcha_detected and "checkpoint" in page.url.lower():
                                    captcha_detected = await CaptchaSolver.force_detect_linkedin_recaptcha(page)

                                if captcha_detected:
                                    logger.info(f"🔐 CAPTCHA detected after waiting: {captcha_detected['type']} (sitekey={captcha_detected.get('sitekey', 'unknown')}). Solving...")
                                    task.captcha_detected = True
                                    task.captcha_type = captcha_detected["type"]
                                    await task.save()
                                    captcha_start = time.time()

                                    if capsolver_key or anticaptcha_key:
                                        solved = await CaptchaSolver.handle_captcha_flow(
                                            page,
                                            anticaptcha_key=anticaptcha_key,
                                            capsolver_key=capsolver_key,
                                        )
                                        if solved:
                                            task.captcha_solved = True
                                            task.captcha_solve_time_ms = int(
                                                (time.time() - captcha_start) * 1000
                                            )
                                            session_doc = await SessionDocument.get(
                                                PydanticObjectId(session_id)
                                            )
                                            if session_doc:
                                                session_doc.captchas_solved += 1
                                                await session_doc.save()
                                            await task.save()
                                            logger.success("✅ CAPTCHA on security page solved successfully!")
                                            await asyncio.sleep(4)
                                            captcha_solved_on_security_page = True
                                            break  # exit detection retry loop
                                        else:
                                            captcha_solve_error = captcha_detected["type"]
                                            logger.warning(f"⚠️ CAPTCHA solve attempt {detection_attempt + 1} failed for {captcha_detected['type']}")
                                            break  # exit detection retry loop — solving failed
                                    else:
                                        logger.warning("⚠️ CAPTCHA detected on security page but no solver keys configured")
                                        task.status = TaskStatus.WAITING_CAPTCHA
                                        await task.save()
                                        return
                                else:
                                    logger.info(f"No CAPTCHA detected yet on attempt {detection_attempt + 1}, retrying...")

                            except CaptchaSolveError:
                                raise  # Re-raise solve errors immediately
                            except Exception as inner_ex:
                                logger.error(f"Error checking CAPTCHA on security challenge page (attempt {detection_attempt + 1}): {inner_ex}")

                        if captcha_solved_on_security_page:
                            continue  # go to next main loop iteration

                        if captcha_solve_error:
                            raise CaptchaSolveError(captcha_solve_error)

                        # If no CAPTCHA is detected, check if it's indeed an OTP page
                        # Re-read page text after sleep to check if code inputs are present
                        page_text_lower = await page.evaluate("() => document.body.innerText.toLowerCase()")

                        logger.info("⚠️ Security verification or OTP page detected!")
                        task.status = TaskStatus.WAITING_USER_INPUT
                        task.user_input_required = True
                        task.user_input_prompt = "LinkedIn is requesting security verification. Please enter the verification code sent to your email, or solve the challenge and enter any value to proceed."
                        task.user_input_value = None
                        await task.save()
                        
                        # Wait for user input
                        logger.info(f"⏳ Pausing execution for task {task.id} — waiting for user verification code...")
                        wait_timeout = 300  # 5 minutes
                        poll_interval = 2
                        elapsed = 0
                        
                        while elapsed < wait_timeout:
                            await asyncio.sleep(poll_interval)
                            elapsed += poll_interval
                            
                            # Refresh task document
                            task = await TaskDocument.get(task.id)
                            if task.status == TaskStatus.CANCELLED:
                                logger.info(f"🚫 Task {task.id} cancelled while waiting for user input.")
                                return
                            if task.user_input_value:
                                logger.info(f"📥 Received user input verification code: {task.user_input_value}")
                                
                                # Log input receipt in steps_executed so LLM sees it in history
                                task.steps_executed.append({
                                    "step": len(task.steps_executed) + 1,
                                    "action": "receive_user_input",
                                    "description": f"Received user verification code: {task.user_input_value}",
                                    "success": True,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                })
                                
                                # Mark task status back to running
                                task.status = TaskStatus.RUNNING
                                task.user_input_required = False
                                await task.save()
                                break
                        else:
                            # Timeout
                            task.status = TaskStatus.FAILED
                            task.error_message = "Timed out waiting for verification code from user."
                            await task.save()
                            return
                except Exception as eval_ex:
                    logger.debug(f"Failed to evaluate page for OTP request: {eval_ex}")

                task.current_step = step_idx + 1
                await task.save()

                # Get current page properties
                current_url = page.url
                current_title = await page.title()

                # Extract page text so LLM can see error messages, status text, etc.
                page_text = ""
                try:
                    page_text = await page.evaluate(
                        "() => document.body ? document.body.innerText.substring(0, 3000) : ''"
                    )
                except Exception:
                    pass

                # Get the DOM tree of interactive elements
                logger.info(f"🔍 [Step {step_idx + 1}] Capturing current DOM elements...")
                elements = await PageAgentDOMParser.get_interactive_elements(page)
                dom_tree = PageAgentDOMParser.serialize_to_text(elements)

                logger.info(f"🧠 [Step {step_idx + 1}] Generating next action from page state...")
                next_step_text = await llm.generate_next_step(
                    task_prompt=task.prompt,
                    page_url=current_url,
                    page_title=current_title,
                    dom_tree=dom_tree[:8000],
                    history=task.steps_executed,
                    page_text=page_text,
                )

                # Parse the dynamic action
                try:
                    cleaned_json = next_step_text.strip()
                    if cleaned_json.startswith("```"):
                        cleaned_json = cleaned_json.split("```")[1]
                        if cleaned_json.startswith("json"):
                            cleaned_json = cleaned_json[4:]
                    step = json.loads(cleaned_json)
                except Exception as ex:
                    logger.error(f"Failed to parse LLM next step JSON: {next_step_text} -> {ex}")
                    # Fallback to wait step
                    step = {"action": "wait", "value": "2", "description": "Wait due to step generation parsing error"}

                action = step.get("action", "wait")
                selector = step.get("selector")
                value = step.get("value")
                description = step.get("description", f"Step {step_idx + 1}")

                # ── OAuth Navigate Blocker ────────────────────────────────────
                # Block navigate + Sign In clicks for 45s after OAuth return.
                # The SPA needs time to process the auth token and initialize session.
                _oauth_domains_block = [
                    "customerlogin.", "login.microsoft", "login.live",
                    "microsoftonline", "azure.com/oauth", "okta.com",
                    "auth0.com", "onelogin.", "/sso/", "/idp/", "login.",
                ]
                _oauth_block_active = (
                    _oauth_return_time > 0
                    and (time.time() - _oauth_return_time) < 45.0
                )
                _on_oauth_domain = any(d in page.url.lower() for d in _oauth_domains_block)
                _should_block_navigate = _on_oauth_domain or _oauth_block_active

                if _should_block_navigate and action == "navigate" and value:
                    logger.warning(
                        f"🛑 BLOCKED navigate "
                        f"{'on OAuth domain' if _on_oauth_domain else f'post-OAuth ({(time.time() - _oauth_return_time):.0f}s since return)'}! "
                        f"Agent tried '{value[:80]}' — replacing with wait"
                    )
                    step = {
                        "action": "wait",
                        "value": "6",
                        "description": "WAIT for OAuth redirect/session settle — do NOT manually navigate!",
                    }
                    action = step["action"]
                    selector = None
                    value = step["value"]
                    description = step["description"]

                # ── Post-OAuth: Block "Sign In" clicks too ──────────────────
                if action == "click" and _oauth_block_active:
                    lower_desc_block = description.lower()
                    if any(kw in lower_desc_block for kw in ["sign in", "login", "signin"]):
                        logger.warning(
                            f"🛑 BLOCKED 'Sign In' click post-OAuth "
                            f"({(time.time() - _oauth_return_time):.0f}s since return)! "
                            f"Session is still settling. Replacing with wait."
                        )
                        step = {
                            "action": "wait",
                            "value": "5",
                            "description": "WAIT — session still initializing after OAuth. Do NOT click Sign In!",
                        }
                        action = step["action"]
                        selector = None
                        value = step["value"]
                        description = step["description"]

                # ── Hard Loop Detection ─────────────────────────────────────
                # Strategy 1: URL-fingerprint loop — same navigate URL repeated 3+ times
                if action == "navigate" and value:
                    _recent_nav_urls.append(value)
                    if len(_recent_nav_urls) > 5:
                        _recent_nav_urls.pop(0)
                    if len(_recent_nav_urls) >= 3 and len(set(_recent_nav_urls[-3:])) == 1:
                        logger.warning(f"🔁 Navigate loop detected! Same URL repeated 3+ times: '{value}'. Forcing extract to re-read page.")
                        step = {
                            "action": "extract",
                            "selector": None,
                            "value": None,
                            "description": "Extract full page text to re-evaluate current state and break navigate loop",
                        }
                        action = step["action"]
                        selector = None
                        value = None
                        description = step["description"]
                        _recent_nav_urls.clear()

                # Strategy 2: Fingerprint loop — action+url+description combo repeated 3+ times
                if len(task.steps_executed) >= 3:
                    def _make_fingerprint(s: dict) -> str:
                        return f"{s.get('action','')}|{s.get('description','').lower()[:60]}"
                    current_fp = f"{action}|{description.lower()[:60]}"
                    recent_fps = [_make_fingerprint(s) for s in task.steps_executed[-3:]]
                    if all(fp == current_fp for fp in recent_fps):
                        logger.warning(f"🔁 Fingerprint loop detected! Repeated 3x: '{current_fp}'. Forcing scroll to break loop.")
                        step = {
                            "action": "scroll",
                            "value": "600",
                            "description": "Scroll to break out of repeated action loop and re-evaluate page state",
                        }
                        action = step["action"]
                        selector = None
                        value = step["value"]
                        description = step["description"]

                # Strategy 3: Wait/scroll streak — if 4+ consecutive wait/scroll steps, force a re-read
                if action in ("wait", "scroll"):
                    _wait_scroll_streak += 1
                    if _wait_scroll_streak >= 4:
                        logger.warning(f"🔁 Wait/scroll streak ({_wait_scroll_streak}) detected — forcing extract to break modal/overlay stall.")
                        step = {
                            "action": "extract",
                            "selector": None,
                            "value": None,
                            "description": "Extract full page text to diagnose why agent is stuck waiting",
                        }
                        action = step["action"]
                        selector = None
                        value = None
                        description = step["description"]
                        _wait_scroll_streak = 0
                else:
                    _wait_scroll_streak = 0

                # If action is 'complete', LLM believes task is finished
                if action == "complete":
                    logger.success(f"🏁 Dynamic task completion signal received: {description}")
                    task_finished_successfully = True
                    # Record the final complete step in plan
                    task.plan.append(step)
                    task.total_steps = len(task.plan)
                    await task.save()
                    break

                # Append this generated step to task plan
                task.plan.append(step)
                task.total_steps = len(task.plan)
                await task.save()

                logger.info(f"  ▶️ Step {step_idx + 1}: {action} — {description}")

                step_result = {
                    "step": step_idx + 1,
                    "action": action,
                    "description": description,
                    "success": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                success = False
                attempt = 0
                max_attempts = 1 + task.max_retries

                while attempt < max_attempts and not success:
                    try:
                        if attempt > 0:
                            task.retry_count += 1
                            step_result["retried"] = True
                            logger.info(f"  🔄 Retrying ({task.retry_count}/{task.max_retries}) [Attempt {attempt + 1}/{max_attempts}]...")
                            await asyncio.sleep(2)

                            # Rotate proxy and recreate page if navigation/timeout/proxy/connection/block error occurred
                            err_str = step_result.get("error", "").lower()
                            if any(x in err_str for x in ("timeout", "navigation", "proxy", "connect", "block", "forbidden", "denied", "access")):
                                logger.info("🔄 Navigation/Timeout error detected. Rotating session proxy and recreating page...")
                                # Determine target URL to verify proxy against
                                proxy_target_url = value if (action == "navigate" and value and value.startswith("http")) else page.url
                                context = await SessionService.rotate_session_proxy(
                                    session_id=session_id,
                                    user_id=user_id,
                                    user_api_keys=api_keys,
                                    target_url=proxy_target_url,
                                )
                                page = await context.new_page()
                                if action != "navigate" and proxy_target_url and proxy_target_url != "about:blank":
                                    logger.info(f"Navigating back to {proxy_target_url} after page/proxy recreation...")
                                    try:
                                        await page.goto(proxy_target_url, wait_until="networkidle", timeout=30000)
                                    except Exception as nav_err:
                                        logger.warning(f"Failed navigating back to {proxy_target_url} during retry: {nav_err}")

                        # ── Pre-submit CAPTCHA solve (matching Selenium script order) ──
                        # Working script: fill form FIRST → solve captcha → inject token → submit
                        # Here we detect submit/login clicks and solve captcha right before clicking,
                        # so the fresh token is injected just moments before form submission.
                        lower_desc = (step_result.get("description", "") or "").lower()
                        is_submit_click = action == "click" and any(
                            kw in lower_desc for kw in ["sign in", "login", "log in", "submit", "signin"]
                        )
                        if is_submit_click and (anticaptcha_key or capsolver_key):
                            try:
                                pre_captcha = await CaptchaSolver.detect_captcha(page)
                                if pre_captcha:
                                    logger.info(f"🔐 Pre-submit CAPTCHA detected ({pre_captcha['type']}). Solving fresh token before click...")
                                    pre_solved = await CaptchaSolver.handle_captcha_flow(
                                        page,
                                        anticaptcha_key=anticaptcha_key,
                                        capsolver_key=capsolver_key,
                                    )
                                    if pre_solved:
                                        logger.success("✅ Pre-submit CAPTCHA solved. Waiting 2s before clicking submit...")
                                        await asyncio.sleep(2)
                                    else:
                                        logger.warning("⚠️ Pre-submit CAPTCHA solve failed. Proceeding with click anyway...")
                            except Exception as pre_cap_ex:
                                logger.warning(f"⚠️ Pre-submit CAPTCHA check failed: {pre_cap_ex}")

                        # Execute the action
                        result = await cls._execute_action(
                            page=page,
                            action=action,
                            selector=selector,
                            value=value,
                            task=task,
                            step_result=step_result,
                            is_retry=(attempt > 0),
                            user_id=user_id,
                            deepseek_key=deepseek_key or "",
                        )

                        step_result.update(result)
                        step_result["success"] = True
                        success = True
                        if "error" in step_result:
                            del step_result["error"]

                    except Exception as e:
                        logger.error(f"  ❌ Step {step_idx + 1} attempt {attempt + 1} failed: {e}")
                        step_result["error"] = str(e)
                        step_result["success"] = False
                        attempt += 1

                if not step_result["success"]:
                    task.status = TaskStatus.FAILED
                    task.error_message = f"Step {step_idx + 1} failed: {step_result.get('error')}"
                    task.steps_executed.append(step_result)
                    task.screenshots = screenshots
                    await task.save()
                    return

                # ── Post-submit validation: detect if login/submit actually failed ──
                # After clicking "Sign In"/"Login"/"Submit", check if we landed on the
                # wrong page (homepage or login page instead of account/dashboard).
                # Magento and similar sites redirect away from the reCAPTCHA error page
                # before our main-loop check can catch it, so we detect here instead.
                if action == "click":
                    lower_action_desc = description.lower()
                    is_auth_click = any(
                        kw in lower_action_desc
                        for kw in ["sign in", "login", "log in", "submit", "signin"]
                    )
                    if is_auth_click:
                        try:
                            # Check if _execute_action already detected an immediate post-click error
                            immediate_error = step_result.get("_post_click_error", False)
                            
                            post_url = page.url
                            post_url_lower = post_url.lower()

                            # If we are on a processing URL, wait for the redirect to settle
                            if any(kw in post_url_lower for kw in ["/process", "/check", "/post", "/authenticate", "/submit"]):
                                logger.info(f"⏳ On form processing URL: {post_url}. Waiting up to 10s for redirect to settle...")
                                try:
                                    # Wait for URL to change away from processing URL
                                    await page.wait_for_function(
                                        """
                                        (processing_url) => window.location.href !== processing_url
                                        """,
                                        post_url,
                                        timeout=10000
                                    )
                                    post_url = page.url
                                    post_url_lower = post_url.lower()
                                    logger.info(f"🔄 Page redirected to: {post_url}")
                                except Exception:
                                    logger.warning("Timeout waiting for processing URL to redirect.")
                            
                            # ── SKIP validation for OAuth/SSO external domains ──
                            # These domains handle auth externally — "login" in their URL is NORMAL
                            _oauth_domains = [
                                "customerlogin.", "login.microsoft", "login.live",
                                "microsoftonline", "azure.com", "oauth", "okta.com",
                                "auth0.com", "onelogin.", "sso.", "idp.", "accounts.google",
                                "appleid.apple", "facebook.com/login",
                            ]
                            _is_oauth_domain = any(d in post_url_lower for d in _oauth_domains)
                            if _is_oauth_domain:
                                logger.info(f"🔗 On OAuth/SSO domain ({post_url[:80]}...) — skipping post-submit login-failure check")
                                # Don't run the validation below — proceed normally
                            else:
                                post_text = await page.evaluate(
                                    "() => document.body ? document.body.innerText.substring(0, 2000).toLowerCase() : ''"
                                )

                                # Check 4: Page shows login/sign-in prompts (means NOT logged in)
                                shows_login_prompts = (
                                    "sign in" in post_text
                                    or "create an account" in post_text
                                    or "customer login" in post_text
                                )

                                # Check 1: Still on login/auth page → login failed
                                still_on_login = any(
                                    kw in post_url_lower
                                    for kw in ["/login", "/signin", "sign_in", "/auth"]
                                ) and not any(
                                    kw in post_url_lower
                                    for kw in ["/process", "/check", "/post", "/authenticate", "/submit"]
                                )
                                # Check 2: Redirected to homepage root (not account/dashboard) → login failed
                                on_homepage = (
                                    post_url_lower.rstrip("/").endswith((".com", ".com/"))
                                    and not any(
                                        kw in post_url_lower
                                        for kw in ["account", "dashboard", "my-account", "profile", "user"]
                                    )
                                    and shows_login_prompts
                                )
                                # Check 3: Page text contains reCAPTCHA/error messages → login failed
                                has_recaptcha_error = any(
                                    kw in post_text
                                    for kw in [
                                        "recaptcha verification failed",
                                        "something went wrong with recaptcha",
                                        "recaptcha validation failed",
                                        "invalid login",
                                        "incorrect captcha",
                                        "the captcha verification failed",
                                    ]
                                )

                                if immediate_error or still_on_login or on_homepage or has_recaptcha_error:
                                    logger.warning(
                                        f"🔴 POST-SUBMIT FAILURE DETECTED: "
                                        f"immediate_error={immediate_error}, still_on_login={still_on_login}, on_homepage={on_homepage}, "
                                        f"has_recaptcha_error={has_recaptcha_error}, shows_login_prompts={shows_login_prompts}"
                                    )
                                    # Inject a synthetic failure step so the LLM knows login failed
                                    failure_note = {
                                        "step": step_idx + 2,  # next logical step
                                        "action": "detection",
                                        "description": (
                                            "⚠️ LOGIN FAILED — reCAPTCHA token was rejected or login was unsuccessful. "
                                            "Current page URL is still a login/home page, not an account dashboard. "
                                            "You MUST go back to the login page, re-fill credentials, solve CAPTCHA "
                                            "freshly, and click Sign In again. Do NOT navigate to search for products."
                                        ),
                                        "success": False,
                                        "error": "Login failed: reCAPTCHA token rejected by server or invalid credentials.",
                                        "timestamp": datetime.now(timezone.utc).isoformat(),
                                    }
                                    # Append the original step + the failure note
                                    task.steps_executed.append(step_result)
                                    task.steps_executed.append(failure_note)
                                    task.screenshots = screenshots
                                    await task.save()
                                    step_idx += 2  # skip ahead to account for both steps
                                    await StealthManager.random_delay(1000, 2000)
                                    continue  # go to next loop iteration — LLM will see the failure

                        except Exception as post_check_ex:
                            logger.debug(f"Post-submit validation check failed: {post_check_ex}")

                task.steps_executed.append(step_result)
                task.screenshots = screenshots
                await task.save()

                # Increment step index
                step_idx += 1

                # Random delay between steps (human-like pacing)
                await StealthManager.random_delay(500, 2000)

            # ── Step 3: Extract Results ──────────────────────
            try:
                extracted_data = await cls._extract_results(page, task.prompt)
                task.extracted_data = extracted_data
            except Exception as e:
                logger.warning(f"Result extraction fell back: {e}")
                extracted_data = {"page_url": page.url, "page_title": await page.title()}
                task.extracted_data = extracted_data

            # ── Step 4: Complete ─────────────────────────────
            if task_finished_successfully:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.FAILED
                task.error_message = "Task failed: Max steps limit (50 steps) exceeded without completion."
            task.screenshots = screenshots[-3:]  # Keep last 3 screenshots
            task.completed_at = datetime.now(timezone.utc)
            if task.started_at:
                # Ensure both datetimes are timezone-aware (MongoDB may return naive datetimes)
                started = task.started_at
                completed = task.completed_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                if completed.tzinfo is None:
                    completed = completed.replace(tzinfo=timezone.utc)
                task.duration_ms = int(
                    (completed - started).total_seconds() * 1000
                )
            await task.save()

            # Update session stats
            session_doc = await SessionDocument.get(PydanticObjectId(session_id))
            if session_doc:
                session_doc.tasks_completed += 1
                await session_doc.save()

            # Update user stats
            user.total_tasks_executed += 1
            await user.save()

            logger.success(
                f"✅ Task {task_id} completed in {task.duration_ms}ms "
                f"({step_idx} steps)"
            )

        except Exception as e:
            import traceback
            logger.error(f"❌ Agent execution failed for task {task_id}: {e}\n{traceback.format_exc()}")
            try:
                # ── AUTO-RETRY LOGIC ──────────────────────────────────────
                # If task has retries remaining, reset and re-run instead of failing
                error_str = str(e).lower()
                is_permanent = any(x in error_str for x in (
                    "cancelled", "user cancelled", "max steps", "max_steps"
                ))

                if not is_permanent and task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.RETRYING
                    task.error_message = f"Attempt {task.retry_count} failed: {str(e)[:200]}. Retrying..."
                    task.steps_executed = []    # clear steps for fresh start
                    task.screenshots = []       # clear screenshots
                    task.current_step = 0
                    task.completed_at = None
                    await task.save()

                    logger.warning(
                        f"🔁 Task {task_id} auto-retrying "
                        f"(attempt {task.retry_count}/{task.max_retries}) in 3s..."
                    )
                    await asyncio.sleep(3)
                    # Re-run — this call is async fire-and-forget from within itself,
                    # use create_task to avoid blocking the finally block
                    import asyncio as _asyncio
                    _asyncio.create_task(cls.execute_task(task_id, user_id, api_keys))
                    return  # exit current run; new task created above

                else:
                    # Max retries exhausted or permanent failure
                    task.status = TaskStatus.FAILED
                    task.error_message = (
                        f"Failed after {task.retry_count} retries: {str(e)}"
                        if task.retry_count > 0 else str(e)
                    )
                    if not task.completed_at:
                        task.completed_at = datetime.now(timezone.utc)
                    await task.save()
                    logger.error(
                        f"💀 Task {task_id} permanently failed "
                        f"(retries={task.retry_count}/{task.max_retries})"
                    )
            except Exception:
                pass

        finally:
            try:
                if "screenshot_worker_state" in locals():
                    screenshot_worker_state["active"] = False
                if "screenshot_bg_task" in locals():
                    screenshot_bg_task.cancel()
                    try:
                        await screenshot_bg_task
                    except Exception:
                        pass
            except Exception:
                pass

    @classmethod
    async def _resolve_selector_via_dom(
        cls,
        page,
        action: str,
        selector: Optional[str],
        description: str,
        value: Optional[str],
        user_id: str,
        deepseek_key: str,
    ):
        """
        Page-Agent style dynamic DOM resolution.

        Serializes the current page's interactive elements into an indexed
        text tree, then asks the LLM which element best matches the intended
        action. Returns a Playwright Locator for the resolved element.

        Falls back gracefully to the original CSS selector if resolution fails.
        """
        logger.info("🔍 Page-Agent DOM resolver: serializing interactive elements...")

        elements = await PageAgentDOMParser.get_interactive_elements(page)
        if not elements:
            logger.warning("DOM Parser returned no elements — falling back to CSS selector")
            return None, elements

        dom_tree = PageAgentDOMParser.serialize_to_text(elements)
        logger.debug(f"DOM tree:\n{dom_tree}")

        # Ask the LLM which element to target
        from app.core.llm import get_llm_client
        llm = get_llm_client(user_api_key=deepseek_key, user_id=user_id)
        decision = await llm.analyze_dom_action(
            dom_tree=dom_tree,
            action_description=description,
            action_type=action,
            value=value,
        )

        element_index = decision.get("element_index")
        confidence = decision.get("confidence", 0)
        reason = decision.get("reason", "")

        logger.info(
            f"🎯 Page-Agent picked element [{element_index}] "
            f"(confidence={confidence:.2f}) — {reason}"
        )

        if element_index is None or confidence < 0.3:
            logger.warning(f"Page-Agent confidence too low ({confidence}) — falling back")
            return None, elements

        locator = await PageAgentDOMParser.get_element_by_index(page, element_index, elements)
        return locator, elements

    @classmethod
    async def _execute_action(
        cls,
        page,
        action: str,
        selector: Optional[str],
        value: Optional[str],
        task: TaskDocument,
        step_result: Dict[str, Any],
        is_retry: bool = False,
        # Page-Agent context (injected by execute_task)
        user_id: str = "",
        deepseek_key: str = "",
    ) -> Dict[str, Any]:
        """
        Execute a single action from the plan.

        Uses StealthManager for human-like interactions when appropriate.
        On selector failures, falls back to Page-Agent dynamic DOM resolution.
        """
        result = {}

        # ── Pre-action human pause ──────────────────────────────
        await HumanBehavior.pre_action_pause(action)

        if action == "navigate":
            if value:
                # Human-like navigation with natural post-load reading pause
                await HumanBehavior.navigate_with_human_wait(page, value)
                result["url"] = page.url
                result["title"] = await page.title()

        elif action == "click":
            description = step_result.get("description", "click element")
            locator = None

            # Try the CSS selector first
            if selector:
                try:
                    if is_retry:
                        await page.locator(selector).first.click(force=True, timeout=10000)
                    else:
                        await StealthManager.human_click(page, selector)
                    result["clicked"] = selector
                    result["method"] = "css_selector"
                except Exception as css_err:
                    logger.warning(
                        f"CSS selector '{selector}' failed: {css_err}. "
                        "Falling back to Page-Agent DOM resolver..."
                    )
                    if deepseek_key:
                        locator, _ = await cls._resolve_selector_via_dom(
                            page, action, selector, description, None,
                            user_id, deepseek_key
                        )
            else:
                # No selector provided — go straight to Page-Agent
                if deepseek_key:
                    locator, _ = await cls._resolve_selector_via_dom(
                        page, action, selector, description, None,
                        user_id, deepseek_key
                    )

            if locator is not None and "clicked" not in result:
                # Human-like click with hover, random offset, and timing
                await HumanBehavior.human_click_locator(locator)
                result["clicked"] = f"page-agent:[{description}]"
                result["method"] = "page_agent_dom"

            # ── Post-click settle wait for login/form submits ──
            lower_desc = description.lower()
            if any(kw in lower_desc for kw in ["submit", "sign in", "login", "verify", "continue", "next", "confirm", "send", "yes", "stay", "code"]):
                # ── IMMEDIATE post-click error detection (before Magento redirects away) ──
                # Magento shows "reCAPTCHA verification failed" momentarily then redirects.
                # We must capture it RIGHT NOW, before the page changes.
                try:
                    await asyncio.sleep(0.5)  # tiny delay to let error page start rendering
                    instant_url = page.url
                    instant_text = await page.evaluate(
                        "() => document.body ? document.body.innerText.substring(0, 2000).toLowerCase() : ''"
                    )
                    has_instant_error = any(
                        kw in instant_text for kw in [
                            "recaptcha verification failed",
                            "something went wrong with recaptcha",
                            "recaptcha validation failed",
                            "invalid login or password",
                            "incorrect captcha",
                            "the captcha verification failed",
                        ]
                    )
                    instant_url_lower = instant_url.lower()
                    still_on_login = any(
                        kw in instant_url_lower
                        for kw in ["/login", "/signin", "sign_in", "/auth"]
                    )
                    if has_instant_error or still_on_login:
                        logger.warning(
                            f"🔴 IMMEDIATE POST-CLICK ERROR DETECTED: "
                            f"has_instant_error={has_instant_error}, still_on_login={still_on_login}, "
                            f"url={instant_url[:100]}"
                        )
                        result["_post_click_error"] = True
                        result["_post_click_url"] = instant_url
                        result["_post_click_text_snippet"] = instant_text[:300]
                except Exception as instant_ex:
                    logger.debug(f"Immediate post-click error check failed: {instant_ex}")

                logger.info("⏳ Critical click detected (submit/login/verify). Waiting 5s for page to settle and process session cookies...")
                await asyncio.sleep(5)
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass

        elif action == "type":
            description = step_result.get("description", "type text")
            locator = None

            if selector and value is not None:
                try:
                    await StealthManager.human_type(page, selector, value)
                    result["typed"] = value
                    result["method"] = "css_selector"
                except Exception as css_err:
                    logger.warning(
                        f"CSS selector '{selector}' failed for type: {css_err}. "
                        "Falling back to Page-Agent DOM resolver..."
                    )
                    if deepseek_key:
                        locator, _ = await cls._resolve_selector_via_dom(
                            page, action, selector, description, value,
                            user_id, deepseek_key
                        )
            elif value is not None:
                # No selector — go straight to Page-Agent
                if deepseek_key:
                    locator, _ = await cls._resolve_selector_via_dom(
                        page, action, selector, description, value,
                        user_id, deepseek_key
                    )

            if locator is not None and "typed" not in result and value is not None:
                # Human-like typing with keystroke dynamics
                await HumanBehavior.human_type_locator(locator, value)
                result["typed"] = value
                result["method"] = "page_agent_dom"

        elif action == "fill":
            description = step_result.get("description", "fill field")
            locator = None

            if selector and value is not None:
                try:
                    await page.locator(selector).first.fill(value, timeout=10000)
                    result["filled"] = value
                    result["method"] = "css_selector"
                except Exception as css_err:
                    logger.warning(
                        f"CSS selector '{selector}' failed for fill: {css_err}. "
                        "Falling back to Page-Agent DOM resolver..."
                    )
                    if deepseek_key:
                        locator, _ = await cls._resolve_selector_via_dom(
                            page, action, selector, description, value,
                            user_id, deepseek_key
                        )
            elif value is not None:
                if deepseek_key:
                    locator, _ = await cls._resolve_selector_via_dom(
                        page, action, selector, description, value,
                        user_id, deepseek_key
                    )

            if locator is not None and "filled" not in result and value is not None:
                await locator.fill(value)
                result["filled"] = value
                result["method"] = "page_agent_dom"

        elif action == "scroll":
            direction = "down"
            amount = None
            if value:
                try:
                    amount = int(value)
                except ValueError:
                    if "up" in value.lower():
                        direction = "up"
            await StealthManager.human_scroll(page, direction, amount)
            result["scrolled"] = f"{direction} {amount or 'default'}"

        elif action == "wait":
            wait_time = 2
            if value:
                try:
                    wait_time = float(value)
                    # If LLM generated milliseconds (>= 100), convert to seconds
                    if wait_time >= 100:
                        wait_time = wait_time / 1000.0
                    # Cap maximum wait time to 15 seconds to prevent accidental long sleeps
                    if wait_time > 15.0:
                        wait_time = 15.0
                except ValueError:
                    pass
            await asyncio.sleep(wait_time)
            result["waited"] = f"{wait_time}s"

        elif action == "wait_for_selector":
            if selector:
                await page.wait_for_selector(selector, timeout=30000)
                result["element_found"] = selector

        elif action == "extract":
            if selector:
                text = await page.text_content(selector)
                result["extracted_text"] = text
            else:
                # Extract page text
                text = await page.evaluate("() => document.body.innerText")
                result["extracted_text"] = text[:5000]

        elif action == "screenshot":
            screenshot = await page.screenshot(type="png", full_page=False)
            result["screenshot_base64"] = base64.b64encode(screenshot).decode()

        elif action == "execute_js":
            if value:
                js_result = await page.evaluate(value)
                result["js_result"] = js_result

        elif action == "press_key":
            if value:
                await page.keyboard.press(value)
                result["pressed"] = value

        elif action == "select_option":
            if selector and value:
                await page.select_option(selector, value)
                result["selected"] = value

        elif action == "hover":
            if selector:
                await page.hover(selector)
                result["hovered"] = selector

        elif action == "solve_captcha":
            # Already handled in the main loop
            result["captcha"] = "handled by main loop"

        else:
            logger.warning(f"Unknown action: {action}")
            result["warning"] = f"Unknown action: {action}"

        return result

    @classmethod
    async def _extract_results(cls, page, prompt: str) -> Dict[str, Any]:
        """
        Extract structured results from the page after task completion.

        Uses LLM to identify and extract relevant data from the page.
        """
        try:
            page_text = await page.evaluate("""
                () => {
                    // Get main content text (skip nav, footer, scripts)
                    const main = document.querySelector('main, article, [role="main"]');
                    const target = main || document.body;
                    return target.innerText.substring(0, 8000);
                }
            """)

            result = {
                "page_url": page.url,
                "page_title": await page.title(),
                "extracted_text_preview": page_text[:500],
                "extraction_method": "raw_text",
            }

            return result
        except Exception as e:
            logger.warning(f"Result extraction error: {e}")
            return {
                "page_url": page.url,
                "page_title": await page.title(),
                "extraction_error": str(e),
            }
