"""
    Universal Login Handler with Anti-Captcha
    Supports: Magento, WordPress, Custom CRMs, reCAPTCHA v2/v3, hCaptcha
"""

from anticaptcha_client import AntiCaptchaClient
from browser import ChromeBrowser
from selenium.webdriver.common.by import By
from typing import Optional
import time


class SynetalCRMLogin:
    def __init__(self, api_key: str, url: str, headless: bool = False):
        self.captcha = AntiCaptchaClient(api_key)
        self.browser = ChromeBrowser(headless=headless)
        self.url = url
    
    def login(self, username: str, password: str) -> bool:
        """
        Complete login flow with captcha bypass
        
        Returns: True if login successful, False otherwise
        """
        try:
            # Step 1: Browser start
            self.browser.start()
            
            # Step 2: Navigate to login page
            print(f"\n[1] 🌐 Opening: {self.url}")
            self.browser.navigate(self.url)
            
            # Wait for reCAPTCHA iframe to load (Magento loads it async via RequireJS)
            print("    ⏳ Waiting for reCAPTCHA to load...")
            self.browser.sleep(3)
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                wait = WebDriverWait(self.browser.driver, 15)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha']")))
                print("    ✅ reCAPTCHA iframe detected!")
            except Exception:
                print("    ⚠️ reCAPTCHA iframe not detected, proceeding anyway...")
            self.browser.sleep(2)
            
            # Debug: save page source for manual inspection
            try:
                with open("page_source.html", "w") as f:
                    f.write(self.browser.get_source())
                print("    💾 Page source saved to page_source.html")
            except:
                pass
            
            # Step 3: Check balance
            print("\n[2] 💰 Checking Anti-Captcha balance...")
            balance = self.captcha.get_balance()
            if balance.get("errorId", 0) == 0:
                bal = balance.get("balance", 0)
                print(f"    Balance: ${bal}")
                if bal < 0.01:
                    print("    ⚠️ Low balance! Recharge karo.")
                    return False
            else:
                print(f"    ❌ Error: {balance.get('errorDescription')}")
                return False
            
            # Step 4: Detect captcha type
            print("\n[3] 🔍 Detecting captcha type...")
            captcha_type = self.browser.detect_captcha_type()
            print(f"    Captcha detected: {captcha_type or 'None'}")
            
            # Step 5: Get site key if reCAPTCHA
            site_key = None
            token = None
            
            if captcha_type in ["recaptcha_v2", "recaptcha_v3"]:
                print("\n[4] 🔑 Extracting reCAPTCHA site key...")
                site_key = self.browser.get_recaptcha_site_key()
                
                if site_key:
                    print(f"    ✅ Site Key: {site_key}")
                else:
                    print("    ❌ Site key nahi mila! page_source.html check karo.")
                    self.browser.screenshot("error_no_sitekey.png")
                    return False
            
            elif captcha_type == "hcaptcha":
                print("\n[4] 🔑 Extracting hCaptcha site key...")
                site_key = self.browser.get_hcaptcha_site_key()
                print(f"    Site Key: {site_key}")
            
            # Step 6: Fill login form FIRST
            print("\n[5] 📝 Filling login form...")
            self._fill_login_form(username, password)
            
            # Step 7: Solve captcha
            if site_key:
                if captcha_type == "recaptcha_v2":
                    is_invisible = self.browser.is_recaptcha_invisible()
                    print(f"\n[6] 🤖 Solving reCAPTCHA v2 (invisible={is_invisible})...")
                    token = self.captcha.solve_recaptcha_v2(
                        website_url=self.url,
                        website_key=site_key,
                        is_invisible=is_invisible
                    )
                elif captcha_type == "recaptcha_v3":
                    print("\n[6] 🤖 Solving reCAPTCHA v3 via Anti-Captcha...")
                    token = self.captcha.solve_recaptcha_v3(
                        website_url=self.url,
                        website_key=site_key,
                        page_action="login"
                    )
                elif captcha_type == "hcaptcha":
                    print("\n[6] 🤖 Solving hCaptcha...")
                    token = self.captcha.solve_hcaptcha(
                        website_url=self.url,
                        website_key=site_key
                    )
                
                if not token:
                    print("    ❌ Captcha solve failed!")
                    return False
                
                print("\n[7] 💉 Injecting token (CDP level)...")
                self.browser.inject_bot_token(token)
                
                # Extra wait for Magento to process the callback
                self.browser.sleep(2)
            else:
                print("\n[6] ℹ️ No captcha to solve, proceeding...")
            
            # Step 8: Submit form - try both click and JS
            self.browser.sleep(1)
            print("\n[8] 🚀 Submitting login form...")
            self._submit_login()
            
            # Step 9: Wait for response
            print("\n[9] ⏳ Waiting for login response...")
            self.browser.sleep(6)
            
            # Step 10: Check login success
            print("\n[10] ✅ Checking login status...")
            return self._check_login_success()
            
        except Exception as e:
            print(f"\n❌ Error during login: {str(e)}")
            import traceback
            traceback.print_exc()
            self.browser.screenshot("error.png")
            return False
    
    def _inject_token_and_intercept(self, token: str, captcha_type: str):
        """
        Token inject karo + grecaptcha intercept karo.
        Magento 2 ke liye proper callback trigger karo.
        """
        escaped_token = token.replace("\\", "\\\\").replace("'", "\\'")
        
        script = f"""
        (function() {{
            var TOKEN = '{escaped_token}';
            console.log('[Bot] Starting token injection...');
            
            // 1. Sabhi g-recaptcha-response textareas me token daalo
            var allTextareas = document.querySelectorAll('[name="g-recaptcha-response"], #g-recaptcha-response, .g-recaptcha-response');
            allTextareas.forEach(function(ta) {{
                ta.value = TOKEN;
                ta.style.display = 'block';
                ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                ta.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }});
            
            // Agar koi textarea nahi mila, create karo
            if (allTextareas.length === 0) {{
                var textarea = document.createElement('textarea');
                textarea.id = 'g-recaptcha-response';
                textarea.name = 'g-recaptcha-response';
                textarea.style.display = 'none';
                document.body.appendChild(textarea);
                textarea.value = TOKEN;
            }}
            console.log('[Bot] Token injected into ' + Math.max(allTextareas.length, 1) + ' textarea(s)');
            
            // 2. hCaptcha textarea
            var hcTa = document.querySelector('[name="h-captcha-response"]');
            if (hcTa) hcTa.value = TOKEN;
            
            // 3. Magento 2 specific: find and call the registered callback
            if (typeof ___grecaptcha_cfg !== 'undefined') {{
                var clients = ___grecaptcha_cfg.clients || {{}};
                var fns = ___grecaptcha_cfg.fns || [];
                
                Object.keys(clients).forEach(function(widgetId) {{
                    var client = clients[widgetId];
                    console.log('[Bot] Widget ' + widgetId + ':', JSON.stringify({{
                        sitekey: client.sitekey,
                        callback: !!client.callback,
                        hasCallback: !!client['callback'],
                        isolated: client.isolated
                    }}));
                    
                    // Get the callback function
                    var cb = client.callback || client['callback'];
                    
                    // Magento stores callback as string name in some cases
                    if (typeof cb === 'string' && typeof window[cb] === 'function') {{
                        console.log('[Bot] Calling string callback: ' + cb);
                        try {{ window[cb](TOKEN); }} catch(e) {{ console.log('Error:', e); }}
                    }}
                    
                    // Direct function
                    if (typeof cb === 'function') {{
                        console.log('[Bot] Calling direct callback');
                        try {{ cb(TOKEN); }} catch(e) {{ console.log('Error:', e); }}
                    }}
                    
                    // Magento 2: callback is stored in the iframe's __gf object
                    try {{
                        var iframes = document.querySelectorAll('iframe[src*="recaptcha"]');
                        iframes.forEach(function(iframe) {{
                            if (iframe.contentWindow && iframe.contentWindow.___grecaptcha_cfg) {{
                                // Token already set, try calling callbacks
                            }}
                        }});
                    }} catch(e) {{}}
                }});
            }} else {{
                console.log('[Bot] ___grecaptcha_cfg not found');
            }}
            
            // 4. Intercept grecaptcha.execute
            if (typeof grecaptcha !== 'undefined') {{
                // Store original
                if (!window.__bot_original_execute) {{
                    window.__bot_original_execute = grecaptcha.execute;
                    window.__bot_original_getResponse = grecaptcha.getResponse;
                    window.__bot_original_render = grecaptcha.render;
                }}
                
                grecaptcha.execute = function(widgetId) {{
                    console.log('[Bot] grecaptcha.execute(' + widgetId + ') intercepted');
                    // Find and call the callback for this widget
                    if (typeof ___grecaptcha_cfg !== 'undefined') {{
                        var client = (___grecaptcha_cfg.clients || {{}})[widgetId || 0];
                        if (client) {{
                            var cb = client.callback || client['callback'];
                            if (typeof cb === 'function') {{
                                setTimeout(function() {{ cb(TOKEN); }}, 100);
                            }} else if (typeof cb === 'string' && typeof window[cb] === 'function') {{
                                setTimeout(function() {{ window[cb](TOKEN); }}, 100);
                            }}
                        }}
                    }}
                    // Also call ALL callbacks for safety
                    if (typeof ___grecaptcha_cfg !== 'undefined') {{
                        var allClients = ___grecaptcha_cfg.clients || {{}};
                        Object.keys(allClients).forEach(function(wid) {{
                            var c = allClients[wid];
                            var cb = c.callback || c['callback'];
                            if (typeof cb === 'function') setTimeout(function() {{ cb(TOKEN); }}, 100);
                            else if (typeof cb === 'string' && window[cb]) setTimeout(function() {{ window[cb](TOKEN); }}, 100);
                        }});
                    }}
                    return {{ then: function(cb) {{ setTimeout(function() {{ cb(TOKEN); }}, 50); }} }};
                }};
                
                grecaptcha.getResponse = function(widgetId) {{
                    console.log('[Bot] grecaptcha.getResponse(' + widgetId + ') = TOKEN');
                    return TOKEN;
                }};
                
                console.log('[Bot] grecaptcha functions intercepted');
            }}
            
            // 5. Magento: trigger form reCAPTCHA validation bypass
            var form = document.querySelector('form[action*="login"], form[action*="account"], form#login-form');
            if (form) {{
                // Add hidden input with token
                var hiddenInput = form.querySelector('input[name="g-recaptcha-response"]');
                if (!hiddenInput) {{
                    hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = 'g-recaptcha-response';
                    form.appendChild(hiddenInput);
                }}
                hiddenInput.value = TOKEN;
                console.log('[Bot] Hidden input added to form');
            }}
            
            // 6. Wait for Magento's ko/bindings to update, then trigger any pending submits
            setTimeout(function() {{
                // Re-check all textareas have the token
                document.querySelectorAll('[name="g-recaptcha-response"]').forEach(function(ta) {{
                    ta.value = TOKEN;
                }});
                console.log('[Bot] Token re-verified after timeout');
            }}, 1000);
            
            console.log('[Bot] All injection complete');
        }})();
        """
        self.browser.driver.execute_script(script)
        print("    ✅ Token injected + grecaptcha intercepted!")
    
    def _fill_login_form(self, username: str, password: str):
        """Login form fields fill karo"""
        username_selectors = [
            "input[name='login[username]']",
            "input[name='username']",
            "input[name='email']",
            "input[type='email']",
            "input[id='username']",
            "input[id='email']",
            "#username",
            "#email",
            "#login-email",
            "input[name='login[email]']",
            "#inputEmail",
            "input[placeholder*='username' i]",
            "input[placeholder*='email' i]",
            "input[placeholder*='Email' i]"
        ]
        
        password_selectors = [
            "input[name='login[password]']",
            "input[name='password']",
            "input[type='password']",
            "input[id='password']",
            "input[id='pass']",
            "#password",
            "#pass",
            "#login-password",
            "#inputPassword",
            "input[placeholder*='password' i]",
            "input[placeholder*='Password' i]"
        ]
        
        # Fill username
        filled = False
        for sel in username_selectors:
            try:
                self.browser.type_text(sel, username)
                print(f"    ✅ Username filled: {sel}")
                filled = True
                break
            except Exception:
                continue
        
        if not filled:
            print("    ⚠️ Username field nahi mila! Trying JS fallback...")
            self.browser.driver.execute_script("""
                var inputs = document.querySelectorAll('input[type="email"], input[name*="email"], input[name*="user"], input[name*="login"]');
                if (inputs.length > 0) {
                    inputs[0].value = arguments[0];
                    inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                    inputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                }
            """, username)
        
        # Fill password
        filled = False
        for sel in password_selectors:
            try:
                self.browser.type_text(sel, password)
                print(f"    ✅ Password filled: {sel}")
                filled = True
                break
            except Exception:
                continue
        
        if not filled:
            print("    ⚠️ Password field nahi mila! Trying JS fallback...")
            self.browser.driver.execute_script("""
                var inputs = document.querySelectorAll('input[type="password"]');
                if (inputs.length > 0) {
                    inputs[0].value = arguments[0];
                    inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                    inputs[0].dispatchEvent(new Event('change', { bubbles: true }));
                }
            """, password)
    
    def _submit_login(self):
        """Login form submit karo - click + JS fallback"""
        submit_selectors = [
            "button#send2",
            "button.action.login",
            "button.login",
            ".actions-toolbar button.primary",
            "button[type='submit']",
            "input[type='submit']",
            "button.btn-login",
            "button.btn-primary",
            "#login-btn",
            ".login-button",
            "button.action-login",
            ".login-form button.primary",
            "#btnLogin",
            "button.submit"
        ]
        
        submitted = False
        for sel in submit_selectors:
            try:
                elem = self.browser.driver.find_element(By.CSS_SELECTOR, sel)
                # Try JS click first (bypasses event handlers sometimes)
                self.browser.driver.execute_script("arguments[0].click();", elem)
                print(f"    ✅ Submitted via JS click: {sel}")
                submitted = True
                break
            except:
                continue
        
        if not submitted:
            # Try native click
            for sel in submit_selectors:
                try:
                    self.browser.click(sel)
                    print(f"    ✅ Submitted via native click: {sel}")
                    submitted = True
                    break
                except:
                    continue
        
        if not submitted:
            # JS form submit - bypass all handlers
            self.browser.driver.execute_script("""
                var forms = document.getElementsByTagName('form');
                for (var i = 0; i < forms.length; i++) {
                    var action = (forms[i].action || '').toLowerCase();
                    if (action.indexOf('login') > -1 || action.indexOf('account') > -1 || forms.length === 1) {
                        // Ensure token is in the form before submitting
                        var ta = forms[i].querySelector('[name="g-recaptcha-response"]');
                        if (!ta) {
                            ta = document.createElement('input');
                            ta.type = 'hidden';
                            ta.name = 'g-recaptcha-response';
                            ta.value = document.getElementById('g-recaptcha-response') ? document.getElementById('g-recaptcha-response').value : '';
                            forms[i].appendChild(ta);
                        }
                        forms[i].submit();
                        return;
                    }
                }
                if (forms.length > 0) forms[0].submit();
            """)
            print("    ✅ Submitted via JavaScript")
    
    def _check_login_success(self) -> bool:
        """Check karo login successful hua ya nahi"""
        current_url = self.browser.get_url()
        source = self.browser.get_source().lower()
        
        print(f"    Current URL: {current_url}")
        
        # URL still on login page = strong failure indicator
        url_still_login = 'login' in current_url or 'authentication' in current_url
        
        # Check for error messages on page
        error_patterns = [
            'invalid login', 'incorrect password', 'wrong password',
            'invalid email', 'account not found', 'these credentials',
            'captcha failed', 'reCAPTCHA validation failed',
            'please verify', 'login failed', 'sign in failed',
            'message-error', 'alert-danger', 'login-error',
            "we can't find", 'no match', 'does not match',
            'incorrect captcha', 'please complete the recaptcha'
        ]
        has_error = any(pattern in source for pattern in error_patterns)
        
        # Check via JS for Magento error messages
        try:
            has_error_js = self.browser.driver.execute_script("""
                var errors = document.querySelectorAll(
                    '.message-error, .messages .error, .login.error, ' +
                    '[data-ui-id="checkout-cart-validationmessages-message-error"], ' +
                    '.mage-error, .field-error, [role="alert"]'
                );
                return errors.length > 0;
            """)
            if has_error_js:
                has_error = True
        except:
            pass
        
        # URL changed away from login → very likely success
        if not url_still_login:
            print("    ✅ URL changed - logged in!")
            self.browser.screenshot("login_success.png")
            return True
        
        # Still on login page with error → definite failure
        if url_still_login and has_error:
            print("    ❌ Login page + error message!")
            self.browser.screenshot("login_failed.png")
            return False
        
        # Still on login page, no error, but check JS for logged-in state
        try:
            logged_in_js = self.browser.driver.execute_script("""
                // Check for Magento customer data in localStorage
                var customerData = localStorage.getItem('mage-cache-storage');
                if (customerData) {
                    try {
                        var data = JSON.parse(customerData);
                        if (data.customer && data.customer.firstname) {
                            return true;
                        }
                    } catch(e) {}
                }
                // Check for welcome message
                var welcome = document.querySelector('.logged-in, .customer-welcome, .customer-name');
                if (welcome) return true;
                // Check if customer menu has sign out
                var signOut = document.querySelector('a[href*="logout"], .customer-menu, .authorization-link[href*="logout"]');
                // Only if NOT on login page (we already checked URL)
                return false;
            """)
            if logged_in_js:
                print("    ✅ Logged in (JS check)!")
                self.browser.screenshot("login_success.png")
                return True
        except:
            pass
        
        # Still on login page, no error → likely failure (captcha/session issue)
        print("    ❌ Still on login page (no redirect)")
        self.browser.screenshot("login_failed.png")
        return False
    
    def close(self):
        self.browser.close()
