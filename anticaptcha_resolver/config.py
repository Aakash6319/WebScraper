"""
Synetal CRM Bot Configuration
"""

# ==================== ANTI-CAPTCHA ====================
ANTI_CAPTCHA_API_KEY = "61169a7d23d8abc808c935f4ebc4baf8"

# ==================== SYNETAL CRM ====================
# Target URL
SYNETAL_LOGIN_URL = "https://shop.aarcorp.com/customer/account/login"

# ==================== CHROME SETTINGS ====================
CHROMEDRIVER_PATH = None  # None = auto-detect via webdriver-manager
HEADLESS = False          # False = browser dikhega (testing ke liye)
WINDOW_SIZE = "1920,1080"

# ==================== TIMEOUTS ====================
PAGE_LOAD_TIMEOUT = 30
IMPLICIT_WAIT = 10
EXPLICIT_WAIT = 20
CAPTCHA_SOLVE_TIMEOUT = 120

# ==================== CREDENTIALS ====================
LOGIN_URL = "https://shop.aarcorp.com/customer/account/login"
LOGIN_USERNAME = "batuhan.pekesen@seattleav.com"
LOGIN_PASSWORD = "Batuhan00."
