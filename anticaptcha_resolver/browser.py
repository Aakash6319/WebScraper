"""
Chrome Browser Automation with Anti-Detection
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional, List
import time
import re


class ChromeBrowser:
    def __init__(self, headless: bool = False, chromedriver_path: Optional[str] = None):
        self.headless = headless
        self.chromedriver_path = chromedriver_path
        self.driver = None
        self.wait = None
    
    def start(self):
        """Chrome start karo with anti-detection"""
        options = Options()
        
        # Anti-detection options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        
        # Real user agent
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
        
        # Experimental options
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Preferences
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        options.add_experimental_option("prefs", prefs)
        
        if self.headless:
            options.add_argument("--headless=new")
        
        # Driver initialize
        if self.chromedriver_path:
            service = Service(self.chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
        else:
            self.driver = webdriver.Chrome(options=options)
        
        # Remove webdriver property
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                window.chrome = { runtime: {} };
            '''
        })
        
        # Intercept grecaptcha BEFORE any page JS runs (Magento 2 fix)
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                (function() {
                    // Bot state - Python code will set __bot_token
                    window.__bot_token = null;
                    window.__bot_callbacks = [];
                    window.__bot_widget_ids = {};
                    
                    // Wait for grecaptcha to be defined, then intercept
                    var _interval = setInterval(function() {
                        if (typeof grecaptcha === 'undefined') return;
                        
                        // Intercept grecaptcha.render
                        if (!grecaptcha.__bot_hooked) {
                            var _render = grecaptcha.render;
                            grecaptcha.render = function() {
                                var widgetId = _render.apply(this, arguments);
                                var container = arguments[0];
                                var params = arguments[1] || {};
                                
                                window.__bot_widget_ids[widgetId] = {
                                    container: container,
                                    params: params,
                                    callback: params.callback
                                };
                                
                                console.log('[Bot CDP] grecaptcha.render hooked: widgetId=' + widgetId + ', sitekey=' + params.sitekey);
                                
                                // If we already have a token, call the callback immediately
                                if (window.__bot_token && typeof params.callback === 'function') {
                                    setTimeout(function() { params.callback(window.__bot_token); }, 200);
                                }
                                
                                return widgetId;
                            };
                            
                            // Intercept grecaptcha.execute
                            var _execute = grecaptcha.execute;
                            grecaptcha.execute = function(widgetId) {
                                console.log('[Bot CDP] grecaptcha.execute(' + widgetId + ')');
                                
                                // If we have a token, call the callback directly
                                if (window.__bot_token) {
                                    var w = window.__bot_widget_ids[widgetId || 0];
                                    if (w && typeof w.callback === 'function') {
                                        setTimeout(function() { w.callback(window.__bot_token); }, 100);
                                        return;
                                    }
                                    // Also try ___grecaptcha_cfg
                                    if (typeof ___grecaptcha_cfg !== 'undefined') {
                                        var c = (___grecaptcha_cfg.clients || {})[widgetId || 0];
                                        if (c) {
                                            var cb = c.callback || c['callback'];
                                            if (typeof cb === 'function') {
                                                setTimeout(function() { cb(window.__bot_token); }, 100);
                                                return;
                                            }
                                        }
                                    }
                                }
                                
                                // Fall through to original
                                return _execute.apply(this, arguments);
                            };
                            
                            // Intercept grecaptcha.getResponse
                            var _getResponse = grecaptcha.getResponse;
                            grecaptcha.getResponse = function(widgetId) {
                                if (window.__bot_token) return window.__bot_token;
                                return _getResponse.apply(this, arguments);
                            };
                            
                            // Intercept grecaptcha.reset
                            var _reset = grecaptcha.reset;
                            grecaptcha.reset = function(widgetId) {
                                // Don't actually reset - we want to keep our token
                                console.log('[Bot CDP] grecaptcha.reset blocked');
                            };
                            
                            grecaptcha.__bot_hooked = true;
                            console.log('[Bot CDP] grecaptcha fully intercepted');
                        }
                    }, 50);
                })();
            '''
        })
        
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 20)
        print("[Browser] ✅ Chrome started!")
    
    def inject_bot_token(self, token: str):
        """
        CDP-level token injection - yeh grecaptcha ke internal state me token daalega.
        Magento 2 ke liye zaroori hai kyunki wo grecaptcha.getResponse() check karta hai.
        """
        self.driver.execute_script(f"""
            window.__bot_token = '{token}';
            
            // Fill ALL g-recaptcha-response textareas
            document.querySelectorAll('[name="g-recaptcha-response"], #g-recaptcha-response, .g-recaptcha-response').forEach(function(ta) {{
                ta.value = '{token}';
                ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                ta.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }});
            
            // Trigger all stored callbacks
            Object.values(window.__bot_widget_ids).forEach(function(w) {{
                if (typeof w.callback === 'function') {{
                    try {{ w.callback('{token}'); console.log('[Bot] Called stored callback'); }} catch(e) {{}}
                }}
            }});
            
            // Also trigger ___grecaptcha_cfg callbacks
            if (typeof ___grecaptcha_cfg !== 'undefined') {{
                var clients = ___grecaptcha_cfg.clients || {{}};
                Object.keys(clients).forEach(function(wid) {{
                    var c = clients[wid];
                    var cb = c.callback || c['callback'];
                    if (typeof cb === 'function') {{
                        try {{ cb('{token}'); console.log('[Bot] Called cfg callback for ' + wid); }} catch(e) {{}}
                    }}
                }});
            }}
            
            console.log('[Bot] Token injected at CDP level: ' + '{token}'.substring(0, 20) + '...');
        """)
        print("[Browser] ✅ Bot token injected at CDP level!")
    
    def navigate(self, url: str):
        self.driver.get(url)
        print(f"[Browser] Navigated: {url}")
    
    def find(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = 10):
        """Element find karo"""
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located((by, selector)))
    
    def find_all(self, selector: str, by: By = By.CSS_SELECTOR):
        return self.driver.find_elements(by, selector)
    
    def click(self, selector: str, by: By = By.CSS_SELECTOR):
        elem = self.find(selector, by)
        elem.click()
    
    def type_text(self, selector: str, text: str, by: By = By.CSS_SELECTOR, clear: bool = True):
        """Text field me type karo"""
        elem = self.find(selector, by)
        if clear:
            elem.clear()
        elem.send_keys(text)
    
    # ==================== CAPTCHA DETECTION ====================
    def detect_captcha_type(self) -> Optional[str]:
        """Page par kaunsa captcha hai detect karo"""
        page_source = self.driver.page_source.lower()
        
        has_recaptcha = "recaptcha" in page_source or "g-recaptcha" in page_source
        has_api_v3 = "recaptcha/api.js?render=" in page_source
        has_grecaptcha_execute = "grecaptcha.execute" in page_source
        has_grecaptcha_render = "grecaptcha.render" in page_source
        has_g_recaptcha_div = ".g-recaptcha" in page_source or 'class="g-recaptcha"' in page_source
        has_recaptcha_net = "recaptcha.net" in page_source
        
        # reCAPTCHA v3 detection (first, because it's more specific)
        if has_api_v3 or has_grecaptcha_execute:
            return "recaptcha_v3"
        
        # reCAPTCHA v2 (invisible ya normal)
        if has_recaptcha:
            if has_g_recaptcha_div:
                return "recaptcha_v2"
            else:
                # Could be invisible v2 or v3 without explicit render param
                return "recaptcha_v2"
        
        # hCaptcha
        if "hcaptcha" in page_source or "data-hcaptcha-widget-id" in page_source:
            return "hcaptcha"
        
        # Image captcha
        if self.find_all("img[src*='captcha']") or self.find_all(".captcha-img"):
            return "image_captcha"
        
        # Cloudflare Turnstile
        if "turnstile" in page_source or "cf-challenge" in page_source:
            return "turnstile"
        
        # Generic math/text captcha
        if self.find_all("input[name*='captcha']") or self.find_all("#captcha"):
            return "generic"
        
        return None
    
    def get_recaptcha_site_key(self) -> Optional[str]:
        """reCAPTCHA site key nikalo - multiple strategies"""
        source = self.driver.page_source
        
        # Method 0: JavaScript se directly DOM check (most reliable)
        try:
            key = self.driver.execute_script("""
                // Check all iframes with recaptcha in src
                var iframes = document.querySelectorAll('iframe[src*="recaptcha"]');
                for (var i = 0; i < iframes.length; i++) {
                    var src = iframes[i].src;
                    var match = src.match(/[?&]k=([a-zA-Z0-9_-]{30,50})/);
                    if (match) return match[1];
                }
                // Check data-sitekey attributes
                var elems = document.querySelectorAll('[data-sitekey]');
                for (var i = 0; i < elems.length; i++) {
                    var key = elems[i].getAttribute('data-sitekey');
                    if (key && key.length > 30) return key;
                }
                // Check ___grecaptcha_cfg
                if (typeof ___grecaptcha_cfg !== 'undefined') {
                    var clients = ___grecaptcha_cfg.clients || {};
                    for (var c in clients) {
                        if (clients[c].sitekey) return clients[c].sitekey;
                    }
                }
                return null;
            """)
            if key:
                print(f"    Found via JS DOM inspection")
                return key
        except Exception as e:
            print(f"    JS DOM check failed: {e}")
        
        # Method 1: Already-rendered iframe src (Magento render=explicit pattern)
        # Google iframe URL contains: k=SITE_KEY (handle &amp; HTML encoding)
        match = re.search(r'recaptcha/(?:api2/anchor|api/fallback)\?[^"\'<>\s]*(?:&|&amp;)k=([a-zA-Z0-9_-]{30,50})', source)
        if match:
            key = match.group(1)
            print(f"    Found via reCAPTCHA iframe k= parameter")
            return key
        
        # Also try simpler k= pattern (broader search)
        match = re.search(r'[?&](?:amp;)?k=([a-zA-Z0-9_-]{30,50})', source)
        if match:
            key = match.group(1)
            # Verify it's in a recaptcha context
            if 'recaptcha' in source[max(0, match.start()-200):match.end()].lower():
                print(f"    Found via recaptcha k= parameter (broad)")
                return key
        
        
        # Method 1: data-sitekey attribute on .g-recaptcha div
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, ".g-recaptcha")
            key = elem.get_attribute("data-sitekey")
            if key:
                print(f"    Found via .g-recaptcha data-sitekey")
                return key
        except:
            pass
        
        # Method 2: api.js?render=SITE_KEY (v3 ka common pattern)
        match = re.search(r'recaptcha/api\.js\?render=([^"&\s\']+)', source)
        if match:
            key = match.group(1)
            print(f"    Found via api.js?render=")
            return key
        
        # Method 3: api.js?onload=...&render=SITE_KEY
        match = re.search(r'[?&]render=([^"&\s\']+)', source)
        if match:
            candidate = match.group(1)
            # Filter out non-key values
            if candidate not in ('explicit', 'onload', 'v2'):
                print(f"    Found via &render=")
                return candidate
        
        # Method 4: grecaptcha.execute('SITE_KEY', ...)
        match = re.search(r"grecaptcha\.execute\s*\(\s*['\"]([^'\"]+)['\"]", source)
        if match:
            key = match.group(1)
            print(f"    Found via grecaptcha.execute()")
            return key
        
        # Method 5: grecaptcha.render('el', { sitekey: 'SITE_KEY' })
        match = re.search(r"grecaptcha\.render\s*\([^,]+,\s*\{[^}]*sitekey\s*:\s*['\"]([^'\"]+)['\"]", source)
        if match:
            key = match.group(1)
            print(f"    Found via grecaptcha.render()")
            return key
        
        # Method 6: Generic patterns in script/config
        generic_patterns = [
            (r'data-sitekey="([^"]+)"', 'data-sitekey attribute'),
            (r"'sitekey'\s*:\s*'([^']+)'", 'JS sitekey config'),
            (r'"sitekey"\s*:\s*"([^"]+)"', 'JS sitekey config (double)'),
            (r"sitekey\s*:\s*'([^']+)'", 'JS sitekey shorthand'),
            (r'sitekey\s*:\s*"([^"]+)"', 'JS sitekey shorthand (double)'),
            ('recaptcha_site_key\\\\s*=\\\\s*[\\\'"]([^\\\'"]+)[\\\'"]', 'recaptcha_site_key var'),
            (r'"RECAPTCHA_SITE_KEY"\s*:\s*"([^"]+)"', 'RECAPTCHA_SITE_KEY const'),
            ('window\\\\._recaptchaSiteKey\\\\s*=\\\\s*[\\\'"]([^\\\'"]+)[\\\'"]', '_recaptchaSiteKey'),
        ]
        
        for pattern, label in generic_patterns:
            match = re.search(pattern, source)
            if match:
                key = match.group(1)
                # Validate: site keys are typically 40 chars, alphanumeric with dashes/underscores
                if re.match(r'^[a-zA-Z0-9_-]{30,50}$', key):
                    print(f"    Found via {label}")
                    return key
        
        # Method 7: Check all script tags directly via JS
        try:
            scripts = self.driver.execute_script("""
                var scripts = document.querySelectorAll('script');
                var results = [];
                for (var i = 0; i < scripts.length; i++) {
                    var src = scripts[i].src || '';
                    var text = scripts[i].textContent || '';
                    results.push({src: src, text: text.substring(0, 5000)});
                }
                return results;
            """)
            for script in scripts:
                combined = script['src'] + ' ' + script['text']
                match = re.search(r'recaptcha/api\.js\?render=([^"&\s\']+)', combined)
                if match:
                    print(f"    Found via JS script inspection")
                    return match.group(1)
                match = re.search(r"sitekey['\"]?\s*[:=]\s*['\"]([^'\"]{30,50})['\"]", combined)
                if match:
                    print(f"    Found via JS deep inspection")
                    return match.group(1)
        except Exception as e:
            print(f"    JS inspection error: {e}")
        
        return None
    
    def get_hcaptcha_site_key(self) -> Optional[str]:
        """hCaptcha site key nikalo"""
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, "[data-hcaptcha-widget-id]")
            return elem.get_attribute("data-sitekey")
        except:
            pass
        
        patterns = [
            'data-sitekey="([^"]+)"',
            'hcaptcha_site_key\\s*=\\s*["\']([^"\']+)["\']'
        ]
        
        source = self.driver.page_source
        for pattern in patterns:
            match = re.search(pattern, source)
            if match:
                return match.group(1)
        
        return None
    
    def is_recaptcha_invisible(self) -> bool:
        """Check karo reCAPTCHA invisible hai ya visible"""
        source = self.driver.page_source
        
        # Check iframe for size=invisible
        if 'size=invisible' in source:
            return True
        
        # Check for invisible badge
        if 'grecaptcha-badge' in source and 'data-style="none"' in source:
            return True
        
        # Check .g-recaptcha for data-size="invisible"
        try:
            elem = self.driver.find_element(By.CSS_SELECTOR, ".g-recaptcha")
            size = elem.get_attribute("data-size")
            if size == "invisible":
                return True
        except:
            pass
        
        # If render=explicit without visible .g-recaptcha, likely invisible
        if 'render=explicit' in source:
            try:
                self.driver.find_element(By.CSS_SELECTOR, ".g-recaptcha[data-size='normal'],.g-recaptcha:not([data-size='invisible'])")
                return False
            except:
                return True  # No visible widget found, likely invisible
        
        return False
    
    # ==================== TOKEN INJECTION ====================
    def inject_recaptcha_token(self, token: str):
        """reCAPTCHA token inject karo"""
        script = f"""
            // Method 1: Textarea me daalo
            var textarea = document.getElementById("g-recaptcha-response");
            if (!textarea) {{
                textarea = document.createElement("textarea");
                textarea.id = "g-recaptcha-response";
                textarea.name = "g-recaptcha-response";
                document.body.appendChild(textarea);
            }}
            textarea.style.display = "block";
            textarea.value = "{token}";
            
            // Method 2: Agar callback hai toh call karo
            if (typeof ___grecaptcha_cfg !== 'undefined') {{
                var clients = ___grecaptcha_cfg.clients;
                for (var c in clients) {{
                    var callback = clients[c].callback;
                    if (callback) callback("{token}");
                }}
            }}
            
            // Method 3: grecaptcha.render ke through
            if (typeof grecaptcha !== 'undefined') {{
                try {{
                    var widgets = document.querySelectorAll('.g-recaptcha');
                    for (var i = 0; i < widgets.length; i++) {{
                        var widgetId = widgets[i].getAttribute('data-widgetid');
                        if (widgetId) {{
                            grecaptcha.execute(widgetId);
                        }}
                    }}
                }} catch(e) {{}}
            }}
        """
        self.driver.execute_script(script)
        print("[Browser] ✅ reCAPTCHA token injected!")
    
    def inject_hcaptcha_token(self, token: str):
        """hCaptcha token inject karo"""
        script = f"""
            var textarea = document.querySelector('[name=\"h-captcha-response\"]');
            if (!textarea) {{
                textarea = document.createElement("textarea");
                textarea.name = "h-captcha-response";
                document.body.appendChild(textarea);
            }}
            textarea.value = "{token}";
        """
        self.driver.execute_script(script)
    
    # ==================== FORM HANDLING ====================
    def submit_form(self, submit_selector: Optional[str] = None):
        """Form submit karo"""
        if submit_selector:
            self.click(submit_selector)
            return
        
        # Common submit buttons try karo
        selectors = [
            "button[type='submit']",
            "input[type='submit']",
            ".btn-primary",
            ".submit",
            "#submit",
            "[type='submit']"
        ]
        
        for sel in selectors:
            try:
                self.click(sel)
                print(f"[Browser] ✅ Form submitted via: {sel}")
                return
            except:
                continue
        
        # Last resort: JavaScript se submit
        self.driver.execute_script("document.forms[0].submit();")
        print("[Browser] ✅ Form submitted via JS")
    
    # ==================== SCREENSHOT & DEBUG ====================
    def screenshot(self, filename: str = "screenshot.png"):
        self.driver.save_screenshot(filename)
        print(f"[Browser] 📸 Screenshot: {filename}")
    
    def get_url(self) -> str:
        return self.driver.current_url
    
    def get_source(self) -> str:
        return self.driver.page_source
    
    def sleep(self, seconds: float):
        time.sleep(seconds)
    
    def close(self):
        if self.driver:
            self.driver.quit()
            print("[Browser] ❌ Closed")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.close()
