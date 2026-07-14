"""
AutoWebAgent - LLM Client (DeepSeek via OpenAI SDK)
====================================================
Unified LLM interface that respects user-level API keys.
Superadmin can override with global keys.
DeepSeek is OpenAI-compatible, so we use the OpenAI SDK directly.
"""

from typing import Optional, AsyncIterator
from openai import AsyncOpenAI
from loguru import logger

from app.core.config import settings


class LLMClient:
    """
    Async LLM client for DeepSeek via OpenAI SDK.
    Supports per-user API keys with superadmin global fallback.
    """

    def __init__(
        self,
        user_api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = settings.DEEPSEEK_API_KEY or user_api_key
        self.model = model or settings.DEEPSEEK_MODEL
        self.base_url = settings.DEEPSEEK_BASE_URL

        if not self.api_key:
            logger.warning(
                "⚠️ No DeepSeek API key configured! "
                "LLM calls will fail until a key is set."
            )

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs,
    ):
        logger.debug(
            f"🤖 LLM call: model={self.model}, "
            f"messages={len(messages)}, stream={stream}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs,
            )
            return response
        except Exception as e:
            logger.error(f"❌ LLM call failed: {e}")
            raise

    async def generate_agent_plan(
        self,
        task_prompt: str,
        page_context: str = "",
        previous_actions: str = "",
    ) -> str:
        """
        Generate a structured action plan for the web automation agent.

        Uses a specialized system prompt that instructs the agent to output
        a step-by-step plan with specific actions.

        Args:
            task_prompt: User's natural language task description.
            page_context: Current page HTML/DOM snapshot.
            previous_actions: History of actions already taken.

        Returns:
            Structured plan text from the LLM.
        """
        system_prompt = """You are AutoWebAgent, an expert web automation agent.
Your job is to break down web tasks into high-level, precise, executable steps.

OUTPUT FORMAT (JSON array of action objects):
[
  {
    "action": "navigate|click|type|scroll|wait|extract|screenshot|solve_captcha|press_key|select_option",
    "selector": "CSS selector (OPTIONAL — only if you are 100% certain it is stable)",
    "value": "Text to type or URL to navigate to (optional)",
    "description": "CLEAR description of what to do (e.g. 'Click the Sign In button', 'Type email in the email/username field')"
  }
]

CRITICAL RULES:
- NEVER generate brittle or dynamic CSS selectors (e.g. ids like `«Refvd3ksopa55j6»`, obfuscated class names).
- If starting on a landing page, check if the login inputs are directly visible; if not, you MUST generate a 'click' step to click the "Sign In" or "Log In" button/link first to navigate to the login form before typing credentials.
- For login/auth forms, DO NOT include `selector` at all — write a clear `description` and let the agent resolve elements dynamically.
- Only include `selector` for stable, semantic attributes like `data-testid`, `aria-label`, `[type='submit']`, or well-known IDs.
- Write extremely clear `description` fields — they are used by AI to identify the element at runtime.
- Include wait steps after navigation and dynamic content changes.
- Handle popups, cookie banners, and CAPTCHAs proactively.
- For typing text into fields, use `action: "type"` with a description like: "Type email into the email/username input field".
- NEVER include sensitive data (passwords, tokens) in the plan; leave value as a placeholder like "user_email_here".
"""

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if page_context:
            messages.append({
                "role": "system",
                "content": f"CURRENT PAGE CONTEXT:\n{page_context[:8000]}"
            })

        if previous_actions:
            messages.append({
                "role": "system",
                "content": f"PREVIOUS ACTIONS TAKEN:\n{previous_actions[:4000]}"
            })

        messages.append({
            "role": "user",
            "content": f"TASK: {task_prompt}\n\nGenerate the action plan."
        })

        response = await self.chat(
            messages=messages,
            temperature=0.3,
            max_tokens=4096,
        )

        return response.choices[0].message.content

    async def generate_next_step(
        self,
        task_prompt: str,
        page_url: str,
        page_title: str,
        dom_tree: str,
        history: list[dict],
    ) -> str:
        """
        Generate the single next best action object for the agent based on current page state and history.
        """
        history_text = ""
        for h in history:
            history_text += f"- Step {h.get('step')}: {h.get('action')} ({h.get('description')}) -> {'Success' if h.get('success') else 'Failed: ' + str(h.get('error'))}\n"
            
        system_prompt = """You are AutoWebAgent, an expert web automation agent.
Given the user's overall goal, the current page state, and the history of actions taken so far, decide the SINGLE next best action to perform.

OUTPUT FORMAT (JSON object only, no markdown):
{
  "action": "navigate|click|type|select_option|press_key|scroll|wait|extract|screenshot|solve_captcha|complete",
  "selector": "CSS selector (Optional — only if you are 100% certain it is stable)",
  "value": "Text to type, URL to navigate to, or key to press (optional)",
  "description": "CLEAR description of what to do (e.g. 'Type email in username field', 'Click next button', 'Upload resume')"
}

CRITICAL RULES:
- If the goal has been fully accomplished (e.g. job application successfully submitted, or confirmation message shown), return action "complete" with description "Goal fully achieved".
- DO NOT repeat the same failed actions unless you change parameters or element targets. If a step failed, try an alternative element or path.
- COOKIES & POPUPS: If you see cookie consent popups (e.g. "LinkedIn respects your privacy", "Accept", "Reject", "Accept Cookies") or active filter overlays blocking your view, you MUST close/accept/dismiss them FIRST (e.g. click "Accept", "Reject", or the close "X" button) before attempting to click other buttons on the page. Cookie banners and overlays often block clicks from executing correctly on the rest of the page.
- LOOP PREVENTION: If a previous click action succeeded (marked as Success) but the page state/screenshot didn't change and you are on the same page, DO NOT repeat the same click. Try dismissing any overlays, closing any modals, clicking a different element, or selecting a different option first.
- When you see a form or modal (like LinkedIn Easy Apply), look at the interactive elements and fill them out one by one (type into inputs, select options, upload files) before clicking "Next" or "Submit".
- For fields where you need to fill information with the help of AI, generate appropriate, professional values tailored to the job description (e.g., Aakash Solanki, Python developer, 3+ years experience, cover letter).
- Never include sensitive credentials (passwords, tokens) in the selector or value; use placeholders like "user_password_here" and let the runner substitute them, or type them directly if they are in the task description.

LINKEDIN-SPECIFIC RULES:
- After login, ALWAYS search for jobs using the logged-in search: navigate to "https://www.linkedin.com/jobs/search/?keywords=python+developer&location=India" (use the authenticated URL, NOT public /jobs/view/ URLs).
- Cookie Consent: If the cookie consent banner ("LinkedIn respects your privacy" with Accept/Reject buttons) is visible at the top or bottom of the page, click "Accept" or "Reject" to dismiss it immediately.
- Filter Overlay: If the "Filter only Jobs by" panel or any filter popup is open on the left blocking the page layout, click the close "X" button on it to dismiss it.
- If you see a "Sign In" modal or "contextual-sign-in-modal" blocking the page, it means you are on a PUBLIC page. Navigate away to the logged-in job search URL instead.
- NEVER try to click an Apply button on a public linkedin.com/jobs/view/ page — these require login and will always show a blocking modal.
- After login and CAPTCHA solving, verify you are logged in by checking the URL does NOT contain "checkpoint" or "challenge".
- Prefer "Easy Apply" button (LinkedIn's built-in form) over external "Apply" buttons that open other websites.
- For Easy Apply forms: fill each field (phone, years of experience, etc.) using professional values for Aakash Solanki (Python developer, 3+ years experience, based in India).
- If a LinkedIn "Easy Apply" modal opens, work through it step by step: fill fields, click "Next", fill more fields, click "Review", then "Submit application".
"""

        user_content = f"""OVERALL GOAL: {task_prompt}

CURRENT PAGE:
- URL: {page_url}
- Title: {page_title}

INTERACTIVE ELEMENTS ON PAGE:
{dom_tree}

PREVIOUS ACTIONS HISTORY:
{history_text or "No actions taken yet."}

Identify the single next best action to take to make progress towards the goal."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        response = await self.chat(
            messages=messages,
            temperature=0.1,
            max_tokens=512,
        )

        return response.choices[0].message.content

    async def analyze_page(
        self,
        page_snapshot: str,
        goal: str,
    ) -> dict:
        """
        Analyze a page snapshot and determine what to do next.

        Args:
            page_snapshot: Current page accessibility tree / simplified DOM.
            goal: The overall goal the agent is trying to achieve.

        Returns:
            Dict with 'analysis' and 'next_action' keys.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a web page analyzer. Given a page snapshot and a goal, "
                    "determine: 1) Is the goal already achieved? "
                    "2) What's blocking progress (CAPTCHA, popup, login, etc.)? "
                    "3) What's the single best next action?\n\n"
                    "Respond as JSON: "
                    '{"goal_achieved": bool, "blockers": [str], "next_action": str, "confidence": float}'
                ),
            },
            {
                "role": "user",
                "content": f"GOAL: {goal}\n\nPAGE SNAPSHOT:\n{page_snapshot[:10000]}",
            },
        ]

        response = await self.chat(
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )

        import json
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM page analysis as JSON")
            return {
                "goal_achieved": False,
                "blockers": ["Unable to parse page"],
                "next_action": "Retry page analysis",
                "confidence": 0.1,
            }

    async def solve_captcha_instruction(
        self,
        captcha_type: str,
        page_context: str,
    ) -> str:
        """
        Generate instructions for solving a specific CAPTCHA type.

        Args:
            captcha_type: 'recaptcha_v2', 'recaptcha_v3', 'hcaptcha', 'cloudflare_turnstile', etc.
            page_context: The surrounding page HTML context.

        Returns:
            Strategy string for the CAPTCHA solver.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a CAPTCHA-solving strategist. Given a CAPTCHA type "
                    "and page context, suggest the best resolution approach. "
                    "Consider: Anti-Captcha API parameters, fallback strategies, "
                    "and whether to use audio challenge, image challenge, or token."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"CAPTCHA TYPE: {captcha_type}\n"
                    f"PAGE CONTEXT:\n{page_context[:5000]}"
                ),
            },
        ]

        response = await self.chat(
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
        )

        return response.choices[0].message.content

    async def analyze_dom_action(
        self,
        dom_tree: str,
        action_description: str,
        action_type: str,
        value: Optional[str] = None,
    ) -> dict:
        """
        Given a Page-Agent style DOM tree and an action description,
        ask the LLM to pick the correct element index and confirm the action.

        This replaces brittle CSS selectors with dynamic, LLM-powered
        element resolution — the core of the Page-Agent integration.

        Args:
            dom_tree: Serialized DOM text from PageAgentDOMParser.
            action_description: Human-readable description of what to do.
            action_type: 'click', 'type', 'fill', 'select', etc.
            value: Text to type (if applicable).

        Returns:
            Dict with 'element_index' (int) and optional 'xpath' / 'confidence'.
        """
        import json as _json

        value_hint = f'\n  "value": "{value}"' if value else ""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a web automation assistant. You are given a list of "
                    "interactive elements on the current web page, each identified by "
                    "an index number like [1], [2], etc.\n\n"
                    "Your job: Given an action description and the element list, "
                    "identify which element index best matches the intended target.\n\n"
                    "OUTPUT FORMAT (JSON only, no markdown):\n"
                    '{"element_index": <number>, "confidence": <0.0-1.0>, "reason": "<short explanation>"}\n\n'
                    "If NO element matches, return: "
                    '{"element_index": null, "confidence": 0, "reason": "no match"}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"ACTION TO PERFORM: {action_type.upper()} — {action_description}"
                    + (f'\nVALUE TO TYPE: "{value}"' if value else "")
                    + f"\n\nINTERACTIVE ELEMENTS ON PAGE:\n{dom_tree}"
                ),
            },
        ]

        response = await self.chat(
            messages=messages,
            temperature=0.1,
            max_tokens=256,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        try:
            return _json.loads(raw)
        except Exception:
            logger.warning(f"Failed to parse LLM DOM action response: {raw}")
            return {"element_index": None, "confidence": 0, "reason": "parse_error"}



# ── Singleton factory ─────────────────────────────────────────────

_llm_instances: dict[str, LLMClient] = {}


def get_llm_client(
    user_api_key: Optional[str] = None,
    user_id: str = "default",
) -> LLMClient:
    """
    Get or create an LLM client instance for a user.
    Cached by user_id to avoid re-creation.
    """
    cache_key = f"{user_id}:{user_api_key or 'global'}"
    if cache_key not in _llm_instances:
        _llm_instances[cache_key] = LLMClient(user_api_key=user_api_key)
    return _llm_instances[cache_key]
