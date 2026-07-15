# AutoWebAgent — Developer Agent Handoff
## Version: ULTRA (designed for any LLM — even cheap ones)
> Read EVERY word before touching any code. This document programs HOW you think.

---

# ═══════════════════════════════════════════
# PART 0 — YOUR BRAIN UPGRADE (most important)
# ═══════════════════════════════════════════

## 0.0 — WHO YOU ARE RIGHT NOW

You are a **senior autonomous developer** working on AutoWebAgent.
You have been on this project for months. You know every file.
You do NOT ask basic questions. You explore, think, then act.
You work like Claude Sonnet — methodical, precise, minimal, correct.

If you feel uncertain: **read more code. The answer is always already there.**

---

## 0.1 — THE ONLY WAY YOU WORK (no exceptions)

Every single task follows this exact order. Never skip steps.

```
STEP 1: UNDERSTAND (before touching anything)
    → Read the request 2 times
    → Ask yourself: "What does the user ACTUALLY want?"
    → NOT what they literally said. What result do they expect?

STEP 2: EXPLORE (read the code)
    → Find the relevant files
    → Read the specific functions involved
    → Understand current behavior BEFORE changing anything

STEP 3: FIND ROOT CAUSE (for bugs)
    → Read the error message EXACTLY
    → Find the EXACT line causing it
    → Understand WHY it happens
    → NEVER fix a symptom. Fix the cause.

STEP 4: PLAN (2 sentences in your head)
    → "I will change X in file Y to do Z"
    → "This will NOT break A and B because..."

STEP 5: IMPLEMENT (minimal, clean)
    → Change only what needs changing
    → No extra refactoring. No new abstractions.
    → No new dependencies.

STEP 6: DEPLOY (always)
    → docker cp the file → docker restart
    → If frontend: docker compose build frontend

STEP 7: VERIFY (always)
    → Check logs for errors
    → If possible, run the task and confirm it works
```

---

## 0.2 — HOW TO THINK ABOUT A BUG (decision tree)

```
User says "X is broken"
        ↓
[CHECK LOGS FIRST — always]
docker logs autowebagent-backend 2>&1 | grep -iE "(Error|error|Exception|failed)" | tail -50
        ↓
Do you see an error message?
    YES → Read it carefully. What file? What line? What exception type?
    NO  → Run the task manually, watch logs in real time:
          docker logs autowebagent-backend -f

        ↓
Is the error in YOUR code or a library?
    YOUR CODE → trace the variable/logic causing it
    LIBRARY   → check what you're passing to the library (wrong type? wrong value?)

        ↓
What type of error is it?
    TypeError/AttributeError → wrong data type. Cast it. Check the variable.
    KeyError                 → dict key doesn't exist. Add .get() with default.
    TimeoutError             → network/browser issue. Add wait or retry.
    403/Forbidden            → proxy blocked. Trigger proxy rotation.
    CAPTCHA not solving      → check sitekey, check isInvisible flag, check API key balance

        ↓
Fix it at the source. Not with try/except that hides the error.
```

---

## 0.3 — HOW TO THINK ABOUT A FEATURE REQUEST (decision tree)

```
User says "Add feature X"
        ↓
What does X do technically?
(Write it in one sentence: "X means that when [event], [action] happens")

        ↓
Where in the codebase does this belong?
    Agent behavior?     → service.py or llm.py
    Browser action?     → stealth.py or captcha_solver.py
    Proxy logic?        → proxy/service.py
    UI change?          → tasks/page.tsx
    API endpoint?       → router.py + models.py

        ↓
Does similar code already exist?
    YES → Copy the pattern, modify it. Don't reinvent.
    NO  → Write the minimal new code.

        ↓
What could break?
    List 2-3 things mentally
    Make sure your change doesn't affect them

        ↓
Implement → Deploy → Verify
```

---

## 0.4 — ANTI-PATTERNS (things you must NEVER do)

```
❌ NEVER guess. If you don't know — read the code.
❌ NEVER fix without understanding why it broke.
❌ NEVER add try/except to hide errors. Fix the actual problem.
❌ NEVER hardcode user data (emails, passwords, names) in system prompts.
❌ NEVER add site-specific rules in llm.py (no LinkedIn-only, Bombardier-only rules).
❌ NEVER rebuild the whole Docker stack when only a .py file changed.
   (Use docker cp + docker restart instead — saves 3 minutes every time)
❌ NEVER write 50 lines when 5 lines work.
❌ NEVER create new files/classes/abstractions unless absolutely necessary.
❌ NEVER say "I think this might work". Know why it works.
❌ NEVER ignore the logs. The answer is almost always in the logs.
```

---

## 0.5 — EXAMPLE: HOW TO THINK (internal monologue model)

User says: *"CAPTCHA is not being solved on LinkedIn"*

**WRONG thinking (weak LLM):**
> "I'll add more CAPTCHA solving logic and try all possible options"

**CORRECT thinking (Claude-style):**
> 1. Check logs first → find exact error
> 2. Logs show: `"CapSolver error: Invalid input, check captcha type or pageUrl and invisible"`
> 3. Root cause search: what are we sending to CapSolver?
> 4. Read captcha_solver.py → we're sending `isInvisible=True`
> 5. WHY is that wrong? LinkedIn uses a legacy sitekey, which is a VISIBLE challenge, but the iframe URL has `invisible` in it → so our detection thinks it's invisible, but it's not
> 6. FIX: only set `isInvisible` when we are NOT using the legacy sitekey override
> 7. Change 1 line. Deploy. Test. Done.

**This is the exact level of thinking required for every task.**

---

## 0.6 — HOW TO COMMUNICATE WITH THE USER

```
DO:
    ✅ Be direct and brief
    ✅ Say what you changed and WHY (1-2 sentences max)
    ✅ Show a before/after diff for important changes
    ✅ If something is unclear, ask ONE specific question
    ✅ State what you verified

DON'T:
    ❌ "Great question!"
    ❌ Long explanations of things that didn't change
    ❌ Asking multiple questions at once
    ❌ Saying "I think" when you know
    ❌ Promising things you haven't verified
```

---

# ═══════════════════════════════════════════
# PART 1 — PROJECT OVERVIEW
# ═══════════════════════════════════════════

**AutoWebAgent** = A platform where users write plain English tasks and an AI agent does them in a real browser.

Example task:
> "Go to linkedin.com, log in with email X and password Y, search Python Developer jobs in India, apply via Easy Apply, show job title and company"

The agent handles: login, cookie popups, CAPTCHA, OTP codes, proxy rotation, form filling, loop detection — all automatically.

**Stack:**
| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI |
| Browser | Playwright (async, headless Chromium) |
| AI Brain | DeepSeek LLM (OpenAI-compatible API) |
| Database | MongoDB via Beanie ODM |
| Queue | Redis |
| Proxies | Webshare API (100 residential IPs) |
| CAPTCHA | CapSolver API |
| Frontend | Next.js 14, TypeScript |

---

# ═══════════════════════════════════════════
# PART 2 — FILE MAP (what every file does)
# ═══════════════════════════════════════════

```
backend/app/
├── main.py
│   PURPOSE: FastAPI app setup. Registers all routers. Sets CORS.
│   TOUCH WHEN: Adding a new feature module/router.
│
├── core/config.py
│   PURPOSE: All settings from .env via pydantic-settings.
│   TOUCH WHEN: Adding a new environment variable.
│
├── core/database.py
│   PURPOSE: Connects MongoDB, initializes Beanie with all models.
│   TOUCH WHEN: Adding a new MongoDB collection/model.
│
├── core/llm.py  ⭐
│   PURPOSE: DeepSeek LLM client. Two key methods:
│     - generate_task_plan(): OLD static planner (less used)
│     - get_next_action(): ACTIVE — called every step, returns next JSON action
│   TOUCH WHEN: Improving agent decision-making, changing prompt.
│   CRITICAL RULE: System prompt must be GENERIC. No site-specific rules.
│                  No user data. Agent reads everything from task_prompt.
│
├── features/agent/service.py  ⭐⭐
│   PURPOSE: THE MAIN AGENT LOOP. execute_task() runs the entire automation.
│   TOUCH WHEN: Agent behavior, retry logic, OTP detection, loop detection.
│
├── features/agent/stealth.py
│   PURPOSE: Makes browser look human. navigate_with_human_wait() detects
│            403 blocks and raises Exception to trigger proxy rotation.
│            Also: mouse movements, typing delays, fingerprint spoofing.
│   TOUCH WHEN: WAF bypass improvements, human behavior tuning.
│
├── features/agent/captcha_solver.py
│   PURPOSE: Detects CAPTCHA type → sends to CapSolver API → injects token.
│            Handles reCAPTCHA v2/v3/Enterprise and hCaptcha.
│            Has 4 fallback strategies for solving.
│   TOUCH WHEN: CAPTCHA solving fails, new CAPTCHA types appear.
│
├── features/agent/dom_parser.py
│   PURPOSE: Reads the browser DOM and returns a numbered text list of
│            interactive elements for the LLM to understand the page.
│   TOUCH WHEN: LLM can't find elements, element detection is wrong.
│
├── features/sessions/service.py
│   PURPOSE: Creates Playwright browser contexts with proxy. Rotates proxy
│            when current one is blocked. Stores proxy config on context.
│   TOUCH WHEN: Session management, proxy rotation behavior.
│
├── features/proxy/service.py
│   PURPOSE: Fetches proxies from Webshare API. Verifies them against
│            the target URL before using. Force-refreshes on rotation.
│   TOUCH WHEN: Proxy fetch, verification, caching behavior.
│
├── features/tasks/models.py
│   PURPOSE: MongoDB TaskDocument model. Contains all task state.
│   TOUCH WHEN: Adding new fields to tasks.
│
├── features/tasks/router.py
│   PURPOSE: Task endpoints: create, list, get, cancel, delete, submit-input.
│   TOUCH WHEN: Adding task-related API endpoints.
│
└── features/auth/router.py
    PURPOSE: Login, register, refresh token.
    TOUCH WHEN: Auth changes.

frontend/src/app/dashboard/
├── tasks/page.tsx  ⭐
│   PURPOSE: Main UI. Create task, list tasks, view task detail,
│            OTP input popup, cancel/delete buttons.
│   TOUCH WHEN: Any UI change on the tasks page.
│
├── sessions/page.tsx
│   PURPOSE: View and manage browser sessions.
│
└── settings/page.tsx
    PURPOSE: Configure API keys, proxy settings.
```

---

# ═══════════════════════════════════════════
# PART 3 — THE AGENT LOOP (know this cold)
# ═══════════════════════════════════════════

**File:** `backend/app/features/agent/service.py` — function `execute_task()`

```
Task enters execute_task()
    │
    ├─→ Create browser session with proxy
    │
    └─→ MAIN LOOP (repeats until done or max_steps reached):
            │
            ├─ 1. CAPTCHA CHECK
            │      captcha_info = await detect_captcha(page)
            │      if captcha_info:
            │          await handle_captcha_flow(page, captcha_info)
            │
            ├─ 2. OTP PAGE CHECK
            │      If URL has "checkpoint" OR text has "verification code":
            │          task.status = "waiting_user_input"
            │          await task.save()
            │          [PAUSE — wait for user to submit OTP via frontend]
            │
            ├─ 3. DOM SERIALIZATION
            │      dom_text = serialize_to_text(page)  # numbered element list
            │
            ├─ 4. LLM DECISION
            │      step_json = await llm.get_next_action(
            │          task_prompt, page_url, page_title, dom_text, history
            │      )
            │      # Returns: {action, selector, value, description}
            │
            ├─ 5. LOOP DETECTION
            │      If last 3 descriptions are identical:
            │          Override step → scroll 500px to break loop
            │
            ├─ 6. EXECUTE ACTION
            │      result = await _execute_action(page, step_json)
            │      │
            │      └─ If 403/blocked/timeout:
            │              context = await rotate_session_proxy(target_url=current_url)
            │              page = await context.new_page()
            │              retry action
            │
            ├─ 7. RECORD STEP
            │      task.steps_executed.append({step, action, description, success, error})
            │      task.screenshots.append(screenshot_base64)
            │      await task.save()
            │
            └─ 8. CHECK COMPLETION
                   if step.action == "complete" → break, task done
                   if step_count >= max_steps  → break, task failed
```

---

# ═══════════════════════════════════════════
# PART 4 — LLM PROMPT (the agent's brain)
# ═══════════════════════════════════════════

**File:** `backend/app/core/llm.py` — `get_next_action()`

### THE GOLDEN RULE:
```
System prompt = UNIVERSAL rules only
Task prompt   = ALL user-specific data (credentials, names, goals)
```

**Why?** The same system prompt runs for LinkedIn, Bombardier, Razorpay, Amazon — any site. If you put LinkedIn rules in the system prompt, Bombardier breaks. Always generic.

### What the LLM receives every step:
```python
system_prompt = """...universal reasoning rules, popup handling, loop recovery..."""

user_message = f"""
GOAL: {task_prompt}      ← User wrote this. Contains ALL their data.
CURRENT URL: {page_url}
CURRENT TITLE: {page_title}
ELEMENTS: {dom_tree}     ← Numbered list of clickable/typeable elements
HISTORY: {history_text}  ← What was done before
"""
```

### What the LLM must return (strict JSON):
```json
{
  "action": "navigate|click|type|select_option|press_key|scroll|wait|extract|complete",
  "selector": "CSS selector (only if very stable)",
  "value": "URL or text to type or key name or scroll pixels",
  "description": "Short human description"
}
```

---

# ═══════════════════════════════════════════
# PART 5 — PROXY SYSTEM
# ═══════════════════════════════════════════

**File:** `backend/app/features/proxy/service.py`

```python
# Get a working proxy (normal use):
proxy = await get_proxy_config()

# Get a NEW proxy when current one is blocked (rotation):
proxy = await rotate_proxy(target_url="https://parts.bombardier.com")
#                           ↑ CRITICAL: test against actual site, not Google
```

**How rotate_proxy() works internally:**
```
1. Clear the proxy cache (force fresh fetch from Webshare)
2. Get 100 proxies from Webshare API
3. Shuffle list randomly
4. For each proxy (up to 10 tries):
    → Make HTTP request to target_url using this proxy
    → If 200 response: USE THIS PROXY, return it
    → If timeout/403/error: skip, try next proxy
5. Return the first working proxy
```

**Why target_url matters:**
A proxy might work for google.com but be blocked by bombardier.com.
Always test the proxy against the REAL site the agent is trying to access.

---

# ═══════════════════════════════════════════
# PART 6 — CAPTCHA SYSTEM
# ═══════════════════════════════════════════

**File:** `backend/app/features/agent/captcha_solver.py`

### Detection Flow:
```
1. Scan all iframes on the page
2. Is any iframe URL a reCAPTCHA URL? (contains "google.com/recaptcha")
    YES → Extract sitekey from URL parameter "k"
          Is "size=invisible" in URL? → set invisible=True
          Is "enterprise" in URL? → set enterprise=True
3. Is there a <input name="captchaSiteKey"> element on the page?
    YES → This is LinkedIn's legacy captcha input
          Read its value (different sitekey)
          Set using_legacy_sitekey = True
          Set is_enterprise = True (LinkedIn uses enterprise)
4. Return captcha_info dict with type, sitekey, invisible, enterprise flags
```

### Solving Flow (4 attempts, in order):
```
Attempt 1: ReCaptchaV2EnterpriseTask         (with proxy credentials)
Attempt 2: ReCaptchaV2Task                   (with proxy, non-enterprise fallback)
Attempt 3: ReCaptchaV2EnterpriseTaskProxyLess (no proxy needed)
Attempt 4: ReCaptchaV2TaskProxyLess           (no proxy, non-enterprise) ← usually works
```

### CRITICAL BUG (ALREADY FIXED — understand why, don't revert):
```python
# THE BUG WAS:
payload["isInvisible"] = True  # Set whenever invisible=True in frame URL

# WHY IT FAILED: LinkedIn's checkpoint iframe URL contains "size=invisible"
# but LinkedIn actually shows a VISIBLE challenge. Sending isInvisible=True
# made CapSolver's algorithm fail with "Invalid input" error.

# THE FIX:
if captcha_info.get("invisible") and not using_legacy_sitekey:
    payload["isInvisible"] = True
# Rule: if using LinkedIn's legacy sitekey → NEVER send isInvisible
```

---

# ═══════════════════════════════════════════
# PART 7 — OTP DETECTION
# ═══════════════════════════════════════════

**File:** `backend/app/features/agent/service.py` (~line 219)

```python
is_verification_page = False

# TRIGGER 1: URL contains "checkpoint" (LinkedIn-specific)
if "checkpoint" in current_url_lower:
    is_verification_page = True

# TRIGGER 2: Very specific OTP text on the page
for keyword in [
    "verification code",
    "enter the code",
    "enter the 6-digit",
    "enter the one-time"
]:
    if keyword in page_text_lower:
        is_verification_page = True
        break
```

**WHAT WAS REMOVED AND WHY (do not re-add these):**
```python
# These were too broad — caused FALSE POSITIVES on Bombardier:
"sent to"          # Bombardier says "Order sent to your address" → false trigger
"security check"   # Some pages have "security check" in footer text → false trigger
"verification"     # Too broad — appears on many normal pages → false trigger
```

**Effect when detected:**
```
task.status = "waiting_user_input"
task.user_input_required = True
task.user_input_prompt = "Enter verification code"
await task.save()
→ Frontend shows OTP popup
→ User types code
→ POST /api/v1/tasks/{id}/submit-input {value: "123456"}
→ task resumes
```

---

# ═══════════════════════════════════════════
# PART 8 — DOM PARSER
# ═══════════════════════════════════════════

**File:** `backend/app/features/agent/dom_parser.py`

Converts browser DOM to numbered text list like:
```
[1] BUTTON: "Sign In" (id=login-btn)
[2] INPUT text: placeholder="Email" (name=email)
[3] INPUT password: placeholder="Password"
[4] A: "Forgot password?" href=/reset
```

**FIXED BUG — always in effect:**
```python
# OLD (crashed when input value was integer like 0 or 3):
label += f" value={el['value'][:30]}"

# NEW (always cast to str first):
label += f" value={str(el['value'])[:30]}"
```

---

# ═══════════════════════════════════════════
# PART 9 — STEALTH & HUMAN BEHAVIOR
# ═══════════════════════════════════════════

**File:** `backend/app/features/agent/stealth.py`

### Key functions:

**`navigate_with_human_wait(page, url)`**
```
1. Navigate to URL
2. Wait for load
3. Check page status and title
4. If status 403/503 OR title contains "forbidden/blocked":
    raise Exception("Access Blocked: Status 403. Proxy needs rotation.")
    # This Exception bubbles up to service.py which triggers proxy rotation
```

**`inject_stealth_scripts(page)`**
```
Overrides:
- navigator.webdriver = false (hides automation)
- navigator.plugins (fake browser plugins)
- navigator.languages (fake locale)
- window.chrome (fake Chrome object)
```

**`type_like_human(page, selector, text)`**
```
Types each character with random delay 50-150ms
Occasionally makes a typo and corrects it
```

---

# ═══════════════════════════════════════════
# PART 10 — FRONTEND (tasks page)
# ═══════════════════════════════════════════

**File:** `frontend/src/app/dashboard/tasks/page.tsx`

### What this page does:
- Shows task list (polls every 3 seconds)
- "New Task" form at top → creates task → shows in list
- Eye icon (👁) → opens task detail panel (right side)
- Detail panel shows: status, screenshots, executed steps, generated plan, extracted data
- If task `status === "waiting_user_input"` → shows amber OTP popup automatically

### OTP Popup flow:
```
Polling detects task.status === "waiting_user_input"
→ setOtpTask(task) → renders OTP modal
→ User types code → clicks Submit
→ POST /api/v1/tasks/{task.id}/submit-input {value: "code"}
→ Task resumes
```

### FIXED BUG (do not revert):
```typescript
// OLD: Auto-opened detail panel every time a task was created:
const createdTask = await api.post('/tasks', body);
setSelectedTask(createdTask);  // ← THIS WAS REMOVED

// NEW: User must click eye icon manually to open detail panel
const createdTask = await api.post('/tasks', body);
// (no setSelectedTask call)
```

---

# ═══════════════════════════════════════════
# PART 11 — DEPLOYMENT (copy-paste commands)
# ═══════════════════════════════════════════

### After changing a backend .py file:
```bash
docker cp ./backend/app/features/agent/service.py \
    autowebagent-backend:/app/app/features/agent/service.py
docker restart autowebagent-backend
```

### After changing frontend .tsx file:
```bash
docker compose build frontend && docker compose up -d frontend
```

### Full rebuild (only when requirements.txt or Dockerfile changed):
```bash
docker compose down && docker compose up --build -d
```

### Watch logs in real time:
```bash
docker logs autowebagent-backend -f
```

### Filter logs for errors only:
```bash
docker logs autowebagent-backend 2>&1 | grep -iE "(error|failed|exception|blocked|403)" | tail -50
```

### Check what's running:
```bash
docker ps
```

---

# ═══════════════════════════════════════════
# PART 12 — ENVIRONMENT VARIABLES
# ═══════════════════════════════════════════

```env
# Required for agent to work:
DEEPSEEK_API_KEY=...          # LLM brain
WEBSHARE_API_KEY=...          # 100 residential proxies
CAPSOLVER_API_KEY=...         # CAPTCHA solving

# Optional:
ANTICAPTCHA_API_KEY=...       # CAPTCHA fallback service

# Infrastructure:
MONGODB_URI=mongodb://mongodb:27017
REDIS_URL=redis://redis:6379/0
BROWSER_HEADLESS=true
MAX_CONCURRENT_SESSIONS_PER_USER=5
SECRET_KEY=...                # JWT signing
```

---

# ═══════════════════════════════════════════
# PART 13 — DEBUGGING (step-by-step guide)
# ═══════════════════════════════════════════

### Step 1: Check logs
```bash
docker logs autowebagent-backend 2>&1 | tail -100
```

### Step 2: Find the failing task in DB
```python
# Save as: /tmp/debug.py
import asyncio, sys
sys.path.insert(0, '/app')
from app.core.database import init_database
from app.features.tasks.models import TaskDocument

async def main():
    await init_database()
    tasks = await TaskDocument.find_all().sort("-created_at").limit(1).to_list()
    t = tasks[0]
    print(f"\nTask ID:  {t.id}")
    print(f"Status:   {t.status}")
    print(f"Error:    {t.error_message}")
    print(f"\n--- Steps ---")
    for s in t.steps_executed:
        icon = "✅" if s.get("success") else "❌"
        print(f"{icon} Step {s.get('step'):2d}: [{s.get('action'):12s}] {s.get('description','')[:60]}")
        if not s.get("success"):
            print(f"         Error: {s.get('error', '')[:120]}")

asyncio.run(main())
```
```bash
docker cp /tmp/debug.py autowebagent-backend:/app/debug.py
docker exec autowebagent-backend python /app/debug.py
```

### Step 3: Common error → cause → fix

| Error Message | Cause | Fix |
|--------------|-------|-----|
| `'int' object is not subscriptable` | Slicing el['value'] directly | `str(el['value'])[:30]` |
| `CapSolver: Invalid input, check invisible` | Sending isInvisible=True for visible CAPTCHA | Don't set isInvisible for legacy sitekey |
| `Access Blocked: Status 403` | Proxy IP is banned by target site | `rotate_proxy(target_url=...)` |
| `TimeoutError: waiting for selector` | Element not found / page not loaded | Add wait step before action |
| `waiting_user_input` but no OTP exists | OTP detection false positive | Tighten keyword list in service.py |
| Agent loops on same button | No loop detection / button doesn't open anything | Loop detection → scroll → find alternative |

---

# ═══════════════════════════════════════════
# PART 14 — ALL BUGS FIXED (never revert)
# ═══════════════════════════════════════════

| # | Bug | File:Line | Root Cause | Fix |
|---|-----|-----------|------------|-----|
| 1 | `int` crash in DOM parser | dom_parser.py ~190 | `el['value'][:30]` fails on int | `str(el['value'])[:30]` |
| 2 | 403 block not triggering proxy rotation | stealth.py ~922 | navigate didn't raise on 403 | Raise Exception on 403/forbidden |
| 3 | Rotated proxy is still blocked | proxy/service.py | Used cached proxy list | force_refresh=True + test against target_url |
| 4 | CapSolver "Invalid input" on LinkedIn | captcha_solver.py ~943 | isInvisible=True for visible captcha | Only set when not using_legacy_sitekey |
| 5 | Wrong enterprise flag | captcha_solver.py ~909 | Set is_enterprise=False for legacy key | Set is_enterprise=True for legacy sitekey |
| 6 | Only 2 CapSolver attempts | captcha_solver.py ~948 | No fallback chain | 4 attempts: Enterprise→NonEnterprise × Proxy+ProxyLess |
| 7 | Agent loops on same button | service.py ~407 | No detection for repeated actions | If same description 3x → scroll to break |
| 8 | Detail panel auto-opens | tasks/page.tsx ~269 | setSelectedTask called after create | Removed that line |
| 9 | OTP false positive on Bombardier | service.py ~222 | Broad keywords triggered on normal pages | Tightened to very specific OTP phrases only |

---

# ═══════════════════════════════════════════
# PART 15 — OPEN TASKS (prioritized)
# ═══════════════════════════════════════════

```
HIGH PRIORITY:
[ ] LinkedIn Easy Apply: agent skips to next job when Easy Apply not found
    → File: llm.py (system prompt) + service.py (loop detection)
    → Status: Partially fixed, needs testing

[ ] Resume PDF upload in Easy Apply form
    → File: service.py (_execute_action) — add "upload_file" action type
    → Need: file_path from user in task prompt

MEDIUM PRIORITY:
[ ] Proxy blacklist — don't retry blocked IPs within same session
    → File: proxy/service.py — maintain Set() of blocked IPs
[ ] Proxy verification timeout too slow (80s worst case)
    → File: proxy/service.py — reduce timeout, run checks in parallel

LOW PRIORITY:
[ ] Structured data extraction (currently free-form text in description)
[ ] Admin dashboard: proxy pool health + CAPTCHA solve rate
[ ] Per-user task concurrency limit
[ ] Bombardier full flow verification after proxy fixes
```

---

# ═══════════════════════════════════════════
# PART 16 — CODING RULES (non-negotiable)
# ═══════════════════════════════════════════

```python
# 1. Always use loguru, never print():
from loguru import logger
logger.info("message")
logger.warning("message")
logger.error("message")
logger.success("message")  # for successful completions

# 2. MongoDB with Beanie (always async):
doc = await TaskDocument.find_one(TaskDocument.id == task_id)
await doc.save()
tasks = await TaskDocument.find_all().sort("-created_at").to_list()

# 3. Store proxy on context (captcha_solver reads this):
context._proxy_config = {
    "host": proxy["host"],
    "port": proxy["port"],
    "username": proxy.get("username"),
    "password": proxy.get("password"),
}

# 4. FastAPI endpoints follow this pattern:
@router.post("/tasks/{task_id}/action")
async def do_action(task_id: str, body: SomeModel, current_user = Depends(get_current_user)):
    result = await SomeService.do_the_work(task_id, body, current_user)
    return result

# 5. NEVER put site-specific logic in llm.py:
# WRONG:
if "linkedin" in page_url:
    prompt += "LinkedIn-specific instructions..."

# CORRECT: generic rules only, agent figures out site from context
```


---

*You now have complete knowledge AND the thinking framework to work on this project.*
*Apply Part 0 religiously. The code in Parts 1-16 is the what. Part 0 is the how.*
*Work like Claude: methodical, minimal, correct.*

---

# ═══════════════════════════════════════════
# PART 17 — FULL ARCHITECTURE FLOW DIAGRAM
# ═══════════════════════════════════════════

```
USER (browser)
    │
    │  POST /api/v1/tasks  {"prompt": "Go to linkedin..."}
    ▼
FRONTEND (Next.js :3000)
    │
    │  HTTP to backend
    ▼
BACKEND (FastAPI :8000)
    │
    ├── tasks/router.py → creates TaskDocument in MongoDB
    │                     status = "pending"
    │
    ├── Background worker picks up task
    │
    └── agent/service.py → execute_task()
            │
            ├── sessions/service.py
            │       → create Playwright browser context
            │       → attach proxy (Webshare residential IP)
            │       → inject stealth scripts
            │       → store context._proxy_config
            │
            ├── LOOP START ──────────────────────────────────────────┐
            │                                                         │
            ├── captcha_solver.py                                     │
            │       → scan page iframes for CAPTCHA                  │
            │       → if found: call CapSolver API → get token       │
            │       → inject token into page DOM                     │
            │       → click submit if needed                         │
            │                                                         │
            ├── OTP detection (inline in service.py)                 │
            │       → check URL + page text for OTP signals          │
            │       → if detected: pause task, notify frontend        │
            │       → [wait for user to submit OTP]                  │
            │       → resume                                          │
            │                                                         │
            ├── dom_parser.py                                         │
            │       → serialize interactive DOM → numbered text       │
            │                                                         │
            ├── core/llm.py → get_next_action()                      │
            │       → send: goal + url + title + dom + history        │
            │       → DeepSeek API returns JSON action                │
            │                                                         │
            ├── LOOP DETECTION                                        │
            │       → same action 3x? → inject scroll                │
            │                                                         │
            ├── _execute_action(page, action_json)                   │
            │       → navigate / click / type / scroll / extract     │
            │       → 403 detected? → rotate proxy (Webshare)        │
            │                       → verify against target_url      │
            │                       → new context + new page          │
            │                       → retry action                    │
            │                                                         │
            ├── Save screenshot + step to MongoDB                    │
            │                                                         │
            └── action=="complete"? → DONE ──────────────────────────┘
                step_count > max? → FAILED

    │
    ▼
MONGODB (stores all task state, screenshots, steps)
    │
    ▼
FRONTEND polls every 3s → shows live progress + screenshots
```

---

# ═══════════════════════════════════════════
# PART 18 — SESSION LIFECYCLE (detailed)
# ═══════════════════════════════════════════

```
CREATE SESSION:
    1. pick proxy from Webshare pool
       → verify proxy works (GET google.com or target_url)
    2. playwright.chromium.launch(headless=True)
    3. browser.new_context(proxy={server, username, password})
    4. inject_stealth_scripts(context)       # patch navigator.webdriver etc
    5. apply_fingerprint_overrides(context)  # canvas, WebGL, screen size
    6. context._proxy_config = {...}         # store for captcha_solver
    7. SessionDocument saved in MongoDB
    8. status = "active"

DURING SESSION (each step):
    page = await context.new_page()
    → inject stealth into page too
    → navigate_with_human_wait(page, url)
    → check 403 → raise if blocked
    → execute action on page
    → take screenshot
    → close page (or reuse for next step)

PROXY ROTATION (when blocked):
    1. rotate_proxy(target_url=current_url)
       → flush cache
       → fetch 100 fresh proxies from Webshare
       → test each against target_url
       → return first working one
    2. await context.close()          # close old blocked context
    3. new context with new proxy     # fresh identity
    4. restore cookies if any         # maintain session state
    5. context._proxy_config updated
    6. new page from new context

CLOSE SESSION:
    1. await context.close()
    2. SessionDocument.status = "closed"
    3. await session.save()
```

---

# ═══════════════════════════════════════════
# PART 19 — HOW TO ADD A NEW FEATURE
# ═══════════════════════════════════════════

Follow this template EXACTLY every time.

## Template: Adding a new agent ACTION type

**Example: adding "upload_file" action**

### Step 1 — Add to dom_parser.py (if needed for detection)
```python
# If the action needs to find a file input element:
if el.tag_name == "input" and el.type == "file":
    elements.append({
        "index": idx,
        "type": "file_input",
        "label": f'INPUT file: name={el.name}'
    })
```

### Step 2 — Add to service.py _execute_action()
```python
elif action == "upload_file":
    # value = local file path to upload
    file_path = value  # agent gets this from task prompt
    if selector:
        file_input = await page.query_selector(selector)
    else:
        file_input = await page.query_selector('input[type="file"]')
    if file_input:
        await file_input.set_input_files(file_path)
        logger.info(f"📎 Uploaded file: {file_path}")
        return {"success": True, "description": f"Uploaded {file_path}"}
    else:
        raise Exception("File input not found")
```

### Step 3 — Update llm.py action list in system prompt
```python
# In the OUTPUT FORMAT section:
"action": "navigate|click|type|select_option|press_key|scroll|wait|extract|upload_file|screenshot|solve_captcha|complete",
```

### Step 4 — Deploy and test
```bash
docker cp ./backend/app/features/agent/service.py autowebagent-backend:/app/app/features/agent/service.py
docker cp ./backend/app/core/llm.py autowebagent-backend:/app/app/core/llm.py
docker restart autowebagent-backend
```

---

## Template: Adding a new API endpoint

**Example: adding GET /tasks/{id}/screenshots**

### Step 1 — Add to tasks/router.py
```python
@router.get("/{task_id}/screenshots")
async def get_task_screenshots(
    task_id: str,
    current_user: UserDocument = Depends(get_current_user)
):
    task = await TaskDocument.find_one(
        TaskDocument.id == PydanticObjectId(task_id),
        TaskDocument.user_id == str(current_user.id)
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"screenshots": task.screenshots}
```

### Step 2 — No model change needed (field already exists)

### Step 3 — Test it
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/v1/tasks/TASK_ID/screenshots
```

---

## Template: Adding a new MongoDB field

**Example: adding `retry_count` to TaskDocument**

### Step 1 — Add to tasks/models.py
```python
class TaskDocument(Document):
    # ... existing fields ...
    retry_count: int = 0          # ← add with default value
    last_retry_at: Optional[datetime] = None
```

### Step 2 — Use it in service.py
```python
task.retry_count += 1
task.last_retry_at = datetime.utcnow()
await task.save()
```

### Step 3 — No migration needed
Beanie/MongoDB adds new fields automatically with their default values.
Old documents without the field will return the default (0, None, etc.).

---

# ═══════════════════════════════════════════
# PART 20 — PROMPT ENGINEERING GUIDE
# ═══════════════════════════════════════════

## What makes a GOOD task prompt

The agent reads everything from the task prompt. Give it exactly what it needs.

### ✅ GOOD prompt structure:
```
[SITE]: Where to go
[CREDENTIALS]: How to log in
[GOAL]: What to do (be specific about the end result)
[FORM DATA]: Any data needed to fill forms
[SUCCESS SIGNAL]: How the agent knows it's done
```

### ✅ GOOD prompt examples:

**Price lookup:**
```
Go to https://parts.bombardier.com, log in with ID: C5021346 and 
password: Fourstar753. Accept cookies. Search for part number "DK120/90". 
Find and display its price.
```

**Job application:**
```
Go to linkedin.com, log in with email: john@email.com and password: Pass123.
Search for "Python Developer" jobs in India. Apply to a job using Easy Apply 
with: Name: John Doe, Phone: +91 9999999999, Experience: 3 years, 
Title: Python Developer. Show the job title and company name after applying.
```

**Form submission:**
```
Go to https://example.com/contact, fill the contact form with:
Name: Alice Smith, Email: alice@email.com, Message: "I am interested in 
your services." Submit the form and confirm submission was successful.
```

### ❌ BAD prompt examples:

```
# Too vague — agent doesn't know what "apply" means here:
"Apply for jobs on LinkedIn"

# Missing credentials — agent can't log in:
"Find the price on bombardier.com for part DK120/90"

# Missing form data — agent has to guess:
"Fill out the job application form"

# No success signal — agent doesn't know when to stop:
"Search for Python jobs"
```

### Rules for prompt writers:
1. Always include full URL (not just "LinkedIn" or "Amazon")
2. Always include login credentials if site requires login
3. Always specify what data to use for forms
4. Always describe what success looks like ("show price", "display job title", "confirm submission")
5. If multi-step: describe in order — agent follows sequence

---

# ═══════════════════════════════════════════
# PART 21 — Q&A: COMMON SCENARIOS
# ═══════════════════════════════════════════

**Q: Agent executed the action but the page didn't change. Now what?**
```
A: Loop detection handles this (3x same action → scroll to break).
   If it keeps happening: check if an overlay/popup is blocking.
   The agent should dismiss popups first — if it's not doing that,
   the DOM parser might not be including the popup elements.
   Fix: check dom_parser.py — is the overlay div being included in output?
```

**Q: Agent clicks the right button but nothing happens. Why?**
```
A: Common causes:
   1. Popup overlay is blocking the click (visually looks fine, but click goes to overlay)
      → Agent should dismiss overlays first
   2. JavaScript event listener not firing (click registered but no JS response)
      → Try: await page.evaluate("document.querySelector('btn').click()")
   3. Element is inside an iframe
      → Need to switch to iframe context first
   4. Element is outside viewport (not scrolled into view)
      → Add scroll action before click
```

**Q: CAPTCHA keeps failing even with CapSolver. What do I check?**
```
A: Check in order:
   1. Is the CAPSOLVER_API_KEY set correctly in .env?
      → docker exec autowebagent-backend env | grep CAPSOLVER
   2. Is CapSolver account balance > 0?
      → Check dashboard.capsolver.com
   3. Is the sitekey being extracted correctly?
      → Add logger.info(f"sitekey: {sitekey}") in detect_captcha()
   4. Is isInvisible being set incorrectly?
      → Read Part 6 of this document — the LinkedIn fix
   5. Is the pageUrl correct? CapSolver verifies sitekey against URL.
      → Log the page_url being sent to CapSolver
```

**Q: Proxy rotation is happening but agent still gets blocked. Why?**
```
A: The rotated proxy might ALSO be blocked by the target site.
   Current code tests up to 10 proxies against target_url.
   If ALL 10 are blocked → still fails.
   
   Fix options:
   a) Increase max retry count in rotate_proxy()
   b) Add a blacklist of recently blocked proxy IPs
   c) Use different proxy provider or residential proxies
   d) Add delay between rotation attempts
```

**Q: Agent submits the form but shows "complete" too early. Why?**
```
A: LLM returned "complete" based on wrong signal.
   Common cause: confirmation text is similar to intermediate page text.
   
   Fix: In llm.py system prompt, make completion signal stricter:
   "Return 'complete' ONLY when you see words like:
   'Application submitted', 'Thank you', 'Order confirmed',
   'Successfully submitted', or a confirmation ID/number is shown."
```

**Q: Task shows "waiting_user_input" but there's no OTP being asked. Why?**
```
A: False positive in OTP detection.
   Check service.py lines 219-233.
   One of the keywords matched something on a normal page.
   
   Fix: Add logger to print what text matched:
   logger.debug(f"OTP detection trigger: '{keyword}' found in page text")
   Run task, see what matched, remove or tighten that keyword.
```

**Q: Frontend shows task as "running" but backend already finished it. Why?**
```
A: Task status not saved properly, or polling missed the update.
   Check: is task.save() being called after status change?
   Also: frontend polls every 3s — max 3s delay is normal.
   If stuck permanently: check backend logs for unhandled exception.
```

**Q: Agent is filling forms with wrong data. Why?**
```
A: The LLM is not reading the task prompt carefully enough,
   OR the task prompt is missing the data.
   
   Fix 1: Add data more explicitly in task prompt:
   "Fill Name field with: John Doe" (not just "use my details")
   
   Fix 2: Check llm.py — is task_prompt being passed correctly?
   Add logger.debug(f"task_prompt: {task_prompt[:200]}") to verify.
```

---

# ═══════════════════════════════════════════
# PART 22 — LLM RESPONSE VALIDATION
# ═══════════════════════════════════════════

The LLM sometimes returns malformed responses. Here's how the code handles it, and what to watch for.

### Valid response (agent proceeds):
```json
{"action": "click", "selector": "button[type='submit']", "description": "Click login button"}
```

### Common malformed responses and handling:

**1. Wrapped in markdown code block:**
```
```json
{"action": "click", ...}
```
```
→ Fixed in service.py: strips ` ```json ` and ` ``` ` before parsing

**2. Extra text before/after JSON:**
```
I will click the login button.
{"action": "click", ...}
```
→ Fixed: regex extracts first `{...}` block

**3. Missing required field:**
```json
{"selector": "button", "description": "Click it"}
```
→ Falls back to: `{"action": "wait", "value": "2", "description": "Wait - LLM parse error"}`

**4. Invalid action value:**
```json
{"action": "press_enter", ...}
```
→ This would fail at _execute_action. Fix: add "press_enter" as alias for press_key+Enter
  OR the LLM validation should default unknown actions to "wait"

**Where validation happens:** `service.py` around line 395:
```python
try:
    cleaned = next_step_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[7:] if cleaned.startswith("```json") else cleaned[3:]
        cleaned = cleaned.rstrip("`").strip()
    step = json.loads(cleaned)
except Exception as ex:
    logger.error(f"Failed to parse LLM response: {next_step_text} → {ex}")
    step = {"action": "wait", "value": "2", "description": "Wait due to parse error"}
```

**How to improve validation** (if LLM keeps returning bad JSON):
```python
# Add after parsing: validate required fields
if "action" not in step or step["action"] not in VALID_ACTIONS:
    logger.warning(f"Invalid action in LLM response: {step}")
    step = {"action": "wait", "value": "2", "description": "Invalid action fallback"}
```

---

# ═══════════════════════════════════════════
# PART 23 — GIT WORKFLOW
# ═══════════════════════════════════════════

### Commit message format:
```
<type>: <short description>

Types:
  fix      → bug fix
  feat     → new feature
  refactor → code restructure (no behavior change)
  docs     → documentation only
  deploy   → deployment/config changes
  debug    → temporary debug code (remove before merge)

Examples:
  fix: prevent isInvisible flag on LinkedIn legacy sitekey
  feat: add upload_file action type to agent
  fix: tighten OTP detection to avoid Bombardier false positives
  refactor: extract proxy verification into separate function
  docs: update AGENT_HANDOFF with session lifecycle
```

### Daily workflow:
```bash
# Before starting work — pull latest:
git pull origin main

# After making changes — stage and commit:
git add backend/app/features/agent/service.py
git commit -m "fix: description of what you fixed"

# Push:
git push origin main

# If you changed multiple files for one fix, stage all at once:
git add .
git commit -m "fix: description"
git push
```

### What to NEVER commit:
```
❌ .env file (has secrets)
❌ __pycache__/ directories
❌ *.pyc files
❌ node_modules/
❌ .next/ build directory
❌ Temporary debug scripts (debug.py, test_task.py etc)
```

### .gitignore already covers most of these. Check with:
```bash
git status  # shows what would be committed
git diff    # shows exact changes before committing
```

### If you accidentally committed .env or secrets:
```bash
# Remove from git tracking (keep file locally):
git rm --cached .env
git commit -m "fix: remove .env from tracking"
git push
# Then rotate all API keys immediately
```

---

# ═══════════════════════════════════════════
# PART 24 — QUICK REFERENCE CARD
# ═══════════════════════════════════════════

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUICK REFERENCE                              │
├─────────────────────────────────────────────────────────────────┤
│ HOT RELOAD BACKEND    docker cp FILE container:/app/PATH        │
│                       docker restart autowebagent-backend       │
│                                                                 │
│ REBUILD FRONTEND      docker compose build frontend             │
│                       docker compose up -d frontend             │
│                                                                 │
│ FULL REBUILD          docker compose down                       │
│                       docker compose up --build -d              │
│                                                                 │
│ WATCH LOGS            docker logs autowebagent-backend -f       │
│                                                                 │
│ FILTER ERRORS         docker logs autowebagent-backend 2>&1 \   │
│                       | grep -iE "(error|failed|403)" | tail -30│
│                                                                 │
│ CHECK CONTAINERS      docker ps                                 │
│                                                                 │
│ EXEC IN CONTAINER     docker exec autowebagent-backend python \ │
│                       /app/debug.py                             │
├─────────────────────────────────────────────────────────────────┤
│ KEY FILES                                                       │
│ Agent loop:    backend/app/features/agent/service.py            │
│ LLM prompt:    backend/app/core/llm.py                          │
│ CAPTCHA:       backend/app/features/agent/captcha_solver.py     │
│ Stealth:       backend/app/features/agent/stealth.py            │
│ DOM parser:    backend/app/features/agent/dom_parser.py         │
│ Proxy:         backend/app/features/proxy/service.py            │
│ Sessions:      backend/app/features/sessions/service.py         │
│ Task model:    backend/app/features/tasks/models.py             │
│ Frontend UI:   frontend/src/app/dashboard/tasks/page.tsx        │
├─────────────────────────────────────────────────────────────────┤
│ WHEN SOMETHING BREAKS → CHECK IN THIS ORDER:                    │
│ 1. docker logs → find error line                                │
│ 2. Trace to root cause in code                                  │
│ 3. Fix root cause (not symptom)                                 │
│ 4. docker cp + docker restart                                   │
│ 5. Run task again → verify                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

*Total sections: 25. This document is your complete operating manual.*
*Part 0 = HOW to think. Parts 1-25 = WHAT to know.*
*Read Part 0 first. Always.*

---

# ═══════════════════════════════════════════
# PART 25 — WORKING WITH OTHER AGENTS
# (Multi-Agent Collaboration Guide)
# ═══════════════════════════════════════════

This section explains how YOU (the developer agent) work WITH other AI agents —
both receiving work FROM them and handing work OFF to them.

---

## 25.1 — THE TWO TYPES OF AGENTS IN THIS PROJECT

```
TYPE 1: DEVELOPER AGENT (that's you reading this)
    Role: Fix bugs, add features, edit code, deploy, verify
    Tools: Read files, write files, run terminal commands, docker
    Triggered by: User saying "fix X", "add Y", "why is Z broken?"

TYPE 2: BROWSER AUTOMATION AGENT (the one inside execute_task())
    Role: Control a real browser to complete user tasks
    "Tools": navigate, click, type, scroll, extract, solve_captcha
    Triggered by: User submitting a task prompt on the frontend
    Brain: DeepSeek LLM via get_next_action() in llm.py
```

These two agents are completely separate. You (Type 1) write the code that
Type 2 runs. Type 2 never writes code. Type 1 never controls a browser directly.

---

## 25.2 — HOW TO RECEIVE A HANDOFF (you are the NEW agent)

When you receive this document, you are picking up work from a previous developer agent.

### What to do FIRST (before touching anything):

```
STEP 1: Read Part 0 of this document (the thinking rules)
STEP 2: Read Part 13 (bugs fixed) — understand what was done, don't undo it
STEP 3: Read Part 15 (open issues) — understand what still needs work
STEP 4: Check the current state of the system:
         curl http://localhost:8000/health
         docker logs autowebagent-backend 2>&1 | tail -30
STEP 5: Ask the user what they want to work on today
STEP 6: Only then start working
```

### Common mistakes new agents make (don't do these):
```
❌ Starting to code immediately without reading the handoff
❌ Re-implementing something that was already fixed
❌ Reverting a bug fix because you don't understand why it's there
❌ Asking "what does this project do?" — read this document
❌ Hardcoding user data in llm.py (it was removed intentionally — see Part 4)
❌ Setting isInvisible=True for ALL CAPTCHAs (see Part 6 — LinkedIn bug)
❌ Using docker compose up --build for a simple .py file change (3 min wasted each time)
```

---

## 25.3 — HOW TO GIVE A HANDOFF (you are leaving, another agent continues)

When you finish a session and a new agent will continue:

### Step 1 — Update this document
Add any new bugs you fixed to Part 13 (Bugs Fixed table).
Add any new open issues to Part 15 (Open Issues).
Add any new patterns or conventions you established to Part 16 (Coding Rules).

### Step 2 — Leave clear state
```bash
# Make sure code is deployed and working:
docker ps  # all containers running?
curl http://localhost:8000/health  # everything healthy?

# Make sure changes are committed:
git status  # no uncommitted changes
git log --oneline -5  # last 5 commits look correct?
```

### Step 3 — Write a brief state summary at the TOP of this doc
Add a section like this at the very top (after the title):

```markdown
## ⚡ CURRENT STATE (Last updated: [date] by [agent])
- What was working: [X, Y, Z]
- What was just fixed: [bug A, bug B]  
- What the user wanted next: [feature X]
- Known issue to be aware of: [thing to watch out for]
- Last successful task tested: [task description]
```

---

## 25.4 — HOW THE BROWSER AGENT WORKS (Type 2 — the one you build)

Understanding this helps you debug and improve it.

### The Browser Agent's "world":
```
It sees:    Current page URL, page title, DOM elements as numbered text
It knows:   The task goal, previous actions taken
It decides: One action at a time (JSON: {action, selector, value, description})
It cannot:  Remember across tasks, learn from experience, write code
```

### The Browser Agent's decision cycle (every step):
```
PERCEIVE:
    → What URL am I on?
    → What elements are visible?
    → What have I already done?
    → Is there a popup/CAPTCHA blocking me?

THINK:
    → What is my goal?
    → What is the closest next step?
    → What could be blocking me?

ACT:
    → Output one JSON action
    → Execute it
    → Observe result
    → Repeat
```

### How YOU (developer agent) can make the Browser Agent smarter:

```
Better DOM parsing → agent sees more/better elements → makes better decisions
    File: dom_parser.py

Better system prompt → agent reasons better → fewer loops, better decisions
    File: core/llm.py → get_next_action() → system_prompt

Better loop detection → agent breaks out of stuck states faster
    File: agent/service.py → LOOP DETECTION section

Better action execution → clicks work more reliably
    File: agent/service.py → _execute_action()

Better CAPTCHA solving → fewer task failures
    File: agent/captcha_solver.py
```

---

## 25.5 — COMMUNICATION PATTERNS BETWEEN AGENTS

### Pattern 1: Sequential Handoff (most common)
```
Agent A works → finishes → updates AGENT_HANDOFF.md → Agent B reads → continues

Example:
    Agent A: "Fixed CAPTCHA isInvisible bug, added proxy blacklist"
    Agent A: Updates Part 13 and Part 15 in this doc
    Agent A: Commits and pushes
    Agent B: Reads this doc, sees what was done, continues with open issues
```

### Pattern 2: User as Intermediary
```
User describes what happened to Agent A
    ↓
User copies the description and tells Agent B
    ↓
Agent B does NOT need to re-read logs from Agent A's session

This is why the handoff doc exists — so the user doesn't have to
explain the whole project every time a new agent starts.
```

### Pattern 3: Parallel Work (rare — avoid conflicts)
```
If two agents are working on the SAME codebase at the same time:
    → They MUST work on different files
    → Never edit the same file in parallel (merge conflicts)
    → Agree on who owns which file before starting

Safe parallel split:
    Agent A: backend (service.py, captcha_solver.py)
    Agent B: frontend (page.tsx, UI changes)
```

---

## 25.6 — HOW TO UNDERSTAND WHAT THE PREVIOUS AGENT DID

If this document is not fully up to date, reconstruct history from git:

```bash
# See all recent commits:
git log --oneline -20

# See what changed in a specific commit:
git show <commit-hash>

# See what changed in last 5 commits (full diff):
git diff HEAD~5 HEAD

# Find when a specific file was last changed:
git log --oneline -- backend/app/core/llm.py

# See who changed a specific line:
git blame backend/app/features/agent/service.py | grep "isInvisible"
```

---

## 25.7 — HOW TO TEST THAT THE PREVIOUS AGENT'S WORK IS STILL WORKING

Before adding new features, verify the system is in a known-good state:

```bash
# 1. All containers up?
docker ps

# 2. No errors in recent logs?
docker logs autowebagent-backend 2>&1 | grep -iE "(error|exception|failed)" | tail -20

# 3. Health check passing?
curl http://localhost:8000/health

# 4. Run a simple test task (no login required):
# Go to frontend → Create task:
# "Go to https://httpbin.org/html, find the heading text, and display it."
# This tests: navigate, DOM parse, extract, complete — without proxy/CAPTCHA
```

---

## 25.8 — THE AGENT'S KNOWLEDGE vs YOUR KNOWLEDGE

```
BROWSER AGENT knows:
    ✅ How to interact with a web page
    ✅ What the current page shows
    ✅ What actions were taken before
    ❌ Code logic
    ❌ Why something is broken
    ❌ How to fix bugs
    ❌ History beyond current task

YOU (developer agent) know:
    ✅ All of the above via this document
    ✅ How to read and write code
    ✅ How to run docker commands
    ✅ How to debug from logs
    ✅ The full project history
    ❌ What's currently visible on the browser screen (you can only read logs/screenshots)
```

This is why debugging is done by reading logs, not by "watching" the browser.
The screenshots saved in task.screenshots[] are your window into what the agent saw.

---

## 25.9 — GOLDEN RULES FOR MULTI-AGENT WORK

```
1. READ BEFORE WRITING
   Never write code in a project you haven't read this handoff for.

2. LEAVE IT BETTER THAN YOU FOUND IT
   Fix at least one thing every session. Update this doc with what you fixed.

3. DON'T BREAK EXISTING TESTS
   Run a simple task after every change to confirm nothing broke.

4. ONE AGENT, ONE RESPONSIBILITY
   If you're fixing a bug, fix THAT bug. Don't refactor unrelated code.
   If you're adding a feature, add THAT feature. Don't fix bugs while at it.
   (Unless the bug is directly in your path — then fix it and note it clearly)

5. COMMUNICATE THROUGH CODE AND DOCS
   Other agents can't read your mind. Leave comments in code for non-obvious logic.
   Update this document with anything that would confuse the next agent.

6. TRUST BUT VERIFY
   If this document says "Bug X was fixed" — verify it before assuming it works.
   The document could be stale. The code is the truth.
```

---

## 25.10 — EXAMPLE: FULL HANDOFF WORKFLOW

Here's what a perfect handoff looks like:

**Agent A ends their session:**
```
1. Agent A committed: "fix: add proxy blacklist to prevent blocked IP reuse"
2. Agent A committed: "feat: auto-retry failed tasks up to 3 times"
3. Agent A committed: "feat: rich health check endpoint"
4. Agent A updated AGENT_HANDOFF.md:
   - Added bugs to Part 13
   - Removed completed items from Part 15
   - Added state summary at top of doc
5. Agent A pushed everything: git push
```

**Agent B starts their session:**
```
1. Agent B reads AGENT_HANDOFF.md from top
2. Agent B reads Part 0 (behavior rules) — internalizes them
3. Agent B reads the state summary at the top
4. Agent B checks system: docker ps, curl /health
5. Agent B asks user: "What should I work on today?"
6. User says: "LinkedIn Easy Apply still not working"
7. Agent B looks at Part 15 — "LinkedIn Easy Apply: agent skips to next job" is listed
8. Agent B starts working on THAT issue
9. Agent B follows Part 0 process: read logs → root cause → fix → deploy → verify
```

This is how agents collaborate effectively even without real-time communication.

---
