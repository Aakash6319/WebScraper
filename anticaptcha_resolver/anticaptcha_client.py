"""
Anti-Captcha API Client
Supports: reCAPTCHA v2, v3, invisible, hCaptcha, image captcha
"""

import requests
import time
from typing import Optional, Dict, Any


class AntiCaptchaClient:
    BASE_URL = "https://api.anti-captcha.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    # ==================== BALANCE ====================
    def get_balance(self) -> Dict[str, Any]:
        """Account balance check"""
        payload = {"clientKey": self.api_key}
        resp = self.session.post(f"{self.BASE_URL}/getBalance", json=payload)
        return resp.json()
    
    # ==================== reCAPTCHA v2 ====================
    def solve_recaptcha_v2(self, website_url: str, website_key: str,
                           is_invisible: bool = False,
                           max_wait: int = 120) -> Optional[str]:
        """
        reCAPTCHA v2 solve karo
        Returns: g-recaptcha-response token
        """
        # Task create
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "RecaptchaV2TaskProxyless",
                "websiteURL": website_url,
                "websiteKey": website_key,
                "isInvisible": is_invisible
            }
        }
        
        create_resp = self.session.post(f"{self.BASE_URL}/createTask", json=payload).json()
        
        if create_resp.get("errorId", 0) != 0:
            print(f"[AntiCaptcha] Error: {create_resp.get('errorDescription')}")
            return None
        
        task_id = create_resp["taskId"]
        print(f"[AntiCaptcha] Task created: {task_id}")
        
        # Poll for result
        return self._poll_result(task_id, max_wait)
    
    # ==================== reCAPTCHA v3 ====================
    def solve_recaptcha_v3(self, website_url: str, website_key: str,
                          min_score: float = 0.3,
                          page_action: str = "login",
                          max_wait: int = 120) -> Optional[str]:
        """reCAPTCHA v3 solve karo"""
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "RecaptchaV3TaskProxyless",
                "websiteURL": website_url,
                "websiteKey": website_key,
                "minScore": min_score,
                "pageAction": page_action
            }
        }
        
        create_resp = self.session.post(f"{self.BASE_URL}/createTask", json=payload).json()
        
        if create_resp.get("errorId", 0) != 0:
            return None
        
        return self._poll_result(create_resp["taskId"], max_wait)
    
    # ==================== Image CAPTCHA ====================
    def solve_image_captcha(self, image_base64: str,
                            phrase: bool = False,
                            case_sensitive: bool = False,
                            max_wait: int = 60) -> Optional[str]:
        """Image captcha solve karo"""
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "ImageToTextTask",
                "body": image_base64,
                "phrase": phrase,
                "case": case_sensitive
            }
        }
        
        create_resp = self.session.post(f"{self.BASE_URL}/createTask", json=payload).json()
        
        if create_resp.get("errorId", 0) != 0:
            return None
        
        result = self._poll_result(create_resp["taskId"], max_wait)
        return result.get("text") if isinstance(result, dict) else result
    
    # ==================== hCaptcha ====================
    def solve_hcaptcha(self, website_url: str, website_key: str,
                       max_wait: int = 120) -> Optional[str]:
        """hCaptcha solve karo"""
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "HCaptchaTaskProxyless",
                "websiteURL": website_url,
                "websiteKey": website_key
            }
        }
        
        create_resp = self.session.post(f"{self.BASE_URL}/createTask", json=payload).json()
        
        if create_resp.get("errorId", 0) != 0:
            return None
        
        return self._poll_result(create_resp["taskId"], max_wait)
    
    # ==================== POLL RESULT ====================
    def _poll_result(self, task_id: int, max_wait: int) -> Optional[str]:
        """Task result ka wait karo"""
        payload = {
            "clientKey": self.api_key,
            "taskId": task_id
        }
        
        start = time.time()
        while time.time() - start < max_wait:
            time.sleep(5)
            
            result = self.session.post(f"{self.BASE_URL}/getTaskResult", json=payload).json()
            
            if result.get("errorId", 0) != 0:
                print(f"[AntiCaptcha] Error: {result.get('errorDescription')}")
                return None
            
            status = result.get("status")
            print(f"[AntiCaptcha] Status: {status}")
            
            if status == "ready":
                solution = result.get("solution", {})
                token = solution.get("gRecaptchaResponse") or solution.get("token")
                print(f"[AntiCaptcha] ✅ Solved!")
                return token
        
        print("[AntiCaptcha] ⏰ Timeout!")
        return None
