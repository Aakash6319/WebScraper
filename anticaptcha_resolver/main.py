"""
Universal Anti-Captcha Login Bot
Run: python main.py
"""

from synetal_login import SynetalCRMLogin
from config import ANTI_CAPTCHA_API_KEY, LOGIN_URL, LOGIN_USERNAME, LOGIN_PASSWORD, HEADLESS
import sys


def main():
    print("=" * 60)
    print("  🚀 Anti-Captcha Login Automation")
    print("=" * 60)
    
    # Check API key
    if ANTI_CAPTCHA_API_KEY == "YOUR_ANTI_CAPTCHA_API_KEY_HERE":
        print("\n❌ ERROR: config.py me apni Anti-Captcha API key daalo!")
        print("   Website: https://anti-captcha.com")
        sys.exit(1)
    
    # Check credentials
    if not LOGIN_URL or not LOGIN_USERNAME or not LOGIN_PASSWORD:
        print("\n❌ ERROR: config.py me LOGIN_URL, LOGIN_USERNAME, LOGIN_PASSWORD daalo!")
        sys.exit(1)
    
    print(f"\n🌐 URL: {LOGIN_URL}")
    print(f"👤 User: {LOGIN_USERNAME}")
    print(f"🔑 Pass: {'*' * len(LOGIN_PASSWORD)}")
    
    # Initialize and login
    bot = SynetalCRMLogin(
        api_key=ANTI_CAPTCHA_API_KEY,
        url=LOGIN_URL,
        headless=HEADLESS
    )
    
    try:
        success = bot.login(LOGIN_USERNAME, LOGIN_PASSWORD)
        
        if success:
            print("\n" + "=" * 60)
            print("  ✅ LOGIN SUCCESSFUL!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("  ❌ LOGIN FAILED!")
            print("=" * 60)
            
    finally:
        input("\n⏹️  Press Enter to close browser...")
        bot.close()


if __name__ == "__main__":
    main()
