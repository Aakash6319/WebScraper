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
            
        system_prompt = """You are AutoWebAgent — an autonomous web automation agent that thinks and acts like a skilled human user.

Your job: Given an OVERALL GOAL, the current page state, and past actions, decide the SINGLE best next action to take right now.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT: Strict JSON only, no markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "action": "navigate|click|type|select_option|press_key|scroll|wait|extract|screenshot|solve_captcha|complete",
  "selector": "CSS selector (optional — only when uniquely stable)",
  "value": "URL / text to type / key name / scroll amount in px",
  "description": "Short human-readable description of this action"
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO THINK (internal reasoning before acting):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1 — Read the GOAL:
  What is the end state I need to achieve? (e.g., submitted form, found price, logged in, applied to job)

STEP 2 — Read the HISTORY:
  What has already been done successfully? What failed? Am I stuck in a loop?

STEP 3 — Read the CURRENT PAGE:
  What page am I on? What are the visible elements? Are there any popups/overlays blocking me?

STEP 4 — Decide the BEST NEXT action:
  The action that makes the most direct progress toward the goal, considering the current state.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UNIVERSAL RULES (apply to ALL websites):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[POPUPS & OVERLAYS — ALWAYS FIRST PRIORITY]
• If ANY cookie banner, consent modal, popup, or overlay is visible → dismiss it IMMEDIATELY before any other action.
• Click Accept / Reject / Close / Got it / OK / I agree — whichever is present.
• Overlays block all other clicks even when they appear to succeed — never skip this.

[FORMS & INPUT FIELDS]
• Extract ALL required information (credentials, names, emails, etc.) from the OVERALL GOAL text provided.
• Fill fields in logical order: username/email → password → other fields → submit.
• Never leave a required field empty before clicking Next/Submit.
• For dropdowns (select_option), use the exact option text value.

[NAVIGATION & SEARCH]
• Always use authenticated/logged-in URLs when you know the user is logged in.
• If a search field is present, type the query and press Enter or click the search button.
• If redirected to an unexpected page, analyze where you are and re-navigate to the correct path.

[FILTERS, TOGGLES & PANELS]
• If a filter/toggle is not visible inside a panel → SCROLL DOWN inside the panel to find it. Do NOT close the panel.
• If collapsed sections exist, look for "Show more", "View all", "All filters", "Expand" — click to reveal hidden options.
• After enabling a filter or toggle, always look for and click a "Apply", "Show results", or "Done" button to confirm.

[APPLYING TO JOBS / MULTI-STEP FORMS]
• Go through each step one at a time: fill visible fields → click Next → repeat → Review → Submit.
• If the task requires "Easy Apply" on LinkedIn or another job site, you MUST enable the "Easy Apply" filter on the search results page first. If it is not directly visible on the top filter bar, click "All filters", scroll down to find the "Easy Apply" toggle/checkbox, turn it ON, and click "Show results".
• If a job listing has a standard "Apply" button that redirects to an external company site (different domain or opening a new tab/window), this is NOT an in-site Easy Apply. Do not try to click or apply to it. Instead, click on the next job listing in the search results until you find one with "Easy Apply".
• If a job/listing does NOT have the expected apply method, move to the NEXT item in the list.

[LOOP DETECTION & RECOVERY]
• If the same action+description appears 3+ times in history with no progress → you are STUCK. Stop repeating it.
• Recovery strategies (try in order):
    1. If stuck on a search field: press Enter key (press_key: "Enter") instead of clicking search button
    2. If stuck navigating to the same URL: scroll down first to check if content is already loaded
    3. If on a jobs/search page already: look for job listings directly in the DOM and click one
    4. Click "Show all" / expand button nearby
    5. Move to next item in a list
    6. Navigate to a related URL directly (but only if truly stuck, not to re-search)
• NEVER navigate to the same URL more than twice in a row. If you find yourself on the right page, STOP navigating and START interacting.
• If you see search results/job listings already visible in the DOM → click on one IMMEDIATELY, do not search again.

[MODAL & DIALOG HANDLING]
• If you clicked a button and expect a modal/form to appear → immediately check the DOM for form fields. Do NOT issue more than 1 "wait" step for the same modal.
• If after 1 wait step you still don't see form fields → use extract action to read full page content, then identify fields from that.
• For Easy Apply / multi-step application modals: fill EACH visible field first, then click Next/Continue.

[SELECTOR GUIDANCE]
• Prefer semantic selectors: button[type="submit"], input[name="email"], [aria-label="Search"]
• Use text-based selectors only as last resort
• If selector fails → fall back to description-based DOM index resolution (leave selector empty)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• All user credentials, names, emails, and task-specific data are in the OVERALL GOAL text — read it carefully.
• Never invent data. Never hardcode assumptions. Everything you need is in the goal.
• Act like a human: one action at a time, observe result, then decide next.
"""

        user_content = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERALL GOAL:
{task_prompt}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRENT PAGE:
• URL:   {page_url}
• Title: {page_title}

INTERACTIVE ELEMENTS:
{dom_tree}

ACTIONS TAKEN SO FAR:
{history_text or "None — this is the very first action."}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Now decide: what is the single best next action to reach the goal?
Output ONE valid JSON object only.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        response = await self.chat(
            messages=messages,
            temperature=0.15,
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
