import asyncio
from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless

def main():
    solver = recaptchaV2Proxyless()
    solver.set_key("61169a7d23d8abc808c935f4ebc4baf8")
    balance = solver.get_balance()
    print(f"Anti-Captcha Balance for key 61169a7d23d8abc808c935f4ebc4baf8: {balance}")

if __name__ == "__main__":
    main()
