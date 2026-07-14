# AutoWebAgent

> **Production-Grade AI-Powered Web Automation SaaS Platform with Ultra Stealth Anti-Detection**

---

## 🚀 What is AutoWebAgent?

AutoWebAgent lets you automate any web task using **natural language prompts**. Describe what you want — our DeepSeek-powered AI agent executes it with **military-grade stealth**, bypassing:

- ✅ **Cloudflare** (JS Challenges, Turnstile, WAF)
- ✅ **reCAPTCHA v2/v3**
- ✅ **hCaptcha**
- ✅ **DataDome**
- ✅ **PerimeterX**
- ✅ **Akamai**
- ✅ **Canvas/WebGL/AudioContext fingerprinting**
- ✅ **Headless detection**
- ✅ **TLS fingerprinting**

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    AutoWebAgent                           │
├──────────────┬──────────────────────┬────────────────────┤
│   Frontend   │       Backend        │    Services         │
│  (Next.js)   │     (FastAPI)        │                    │
│              │                      │  ┌──────────────┐  │
│  • Dashboard │  • Auth + JWT       │  │   MongoDB     │  │
│  • Tasks UI  │  • Agent Engine     │  └──────────────┘  │
│  • Sessions  │  • Stealth System   │  ┌──────────────┐  │
│  • Admin     │  • Captcha Solver   │  │    Redis      │  │
│              │  • Proxy Manager    │  └──────────────┘  │
│              │  • LLM Client       │  ┌──────────────┐  │
│              │                     │  │  Playwright   │  │
│              │                     │  │  + Stealth    │  │
│              │                     │  └──────────────┘  │
└──────────────┴──────────────────────┴────────────────────┘
```

---

## 📦 Tech Stack

| Layer       | Technology                                   |
|-------------|----------------------------------------------|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind |
| **Backend** | FastAPI (Python), Beanie ODM, Motor          |
| **Database** | MongoDB                                      |
| **Cache**   | Redis                                        |
| **AI**      | DeepSeek via LiteLLM                         |
| **Browser** | Playwright + Playwright-Stealth              |
| **CAPTCHA** | Anti-Captcha API                             |
| **Proxy**   | Webshare Rotating Residential Proxies        |
| **Deploy**  | Docker + Docker Compose                      |

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- (Or) Python 3.11+, Node.js 20+, MongoDB, Redis

### Option 1: Docker (Recommended)

```bash
# Clone the project
cd AutoWebAgent

# Start everything
docker-compose up --build

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

**Backend:**
```bash
cd backend
cp .env.example .env
# Edit .env with your API keys
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
cp .env.local.example .env.local  # if exists
npm install
npm run dev  # → http://localhost:3000
```

---

## 🔑 Required API Keys

| Service       | Get Key At                        | Required? |
|---------------|-----------------------------------|-----------|
| **DeepSeek**  | platform.deepseek.com             | ✅ Yes    |
| **Anti-Captcha** | anti-captcha.com               | Recommended |
| **Webshare Proxy** | webshare.io                   | Recommended |

> Keys can be set globally (superadmin `.env`) or per-user (Settings page).

---

## 🛡️ Ultra Stealth Features

AutoWebAgent implements the most comprehensive anti-detection system available:

### Fingerprint Spoofing
- **Canvas** — Deterministic noise per session (consistent fingerprint)
- **WebGL** — Vendor/Renderer spoofing matching real GPU profiles
- **AudioContext** — Subtle oscillator noise injection
- **Navigator** — hardwareConcurrency, deviceMemory, platform, plugins
- **WebRTC** — IP leak prevention
- **Fonts** — Realistic font enumeration

### Human Behavior Simulation
- **Bezier curve** mouse movements (no straight lines)
- **Variable typing speed** with random typos & corrections
- **Natural scrolling** with acceleration/deceleration
- **Randomized delays** using gamma distribution

### Headless Bypass
- `navigator.webdriver` removal
- Chrome runtime API spoofing
- Permission API patching
- `chrome.runtime` faking
- All known detection vectors covered

### Proxy + Fingerprint Consistency
- Sticky sessions maintain same proxy IP + fingerprint
- Country-level geo-targeting
- Automatic IP rotation when needed

---

## 📁 Project Structure

```
AutoWebAgent/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, Database, Security, LLM, Exceptions
│   │   ├── features/
│   │   │   ├── auth/       # Auth (models, schemas, service, routes)
│   │   │   ├── websites/   # Website configurations
│   │   │   ├── sessions/   # Browser session isolation
│   │   │   ├── agent/      # Core agent + stealth + captcha solver
│   │   │   ├── tasks/      # Task CRUD + execution tracking
│   │   │   ├── proxy/      # Proxy management & rotation
│   │   │   └── admin/      # Superadmin dashboard
│   │   ├── middleware/     # Rate limiting, security, logging
│   │   ├── utils/          # Helpers, logging config
│   │   └── main.py         # FastAPI entry point
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js App Router pages
│   │   ├── lib/            # API client, Auth context, Utils
│   │   └── components/     # Shared components
│   ├── Dockerfile
│   └── package.json
└── docker-compose.yml
```

---

## 🔐 Security

- **JWT** with access + refresh token rotation
- **Fernet encryption** for all stored API keys
- **Rate limiting** per IP/endpoint
- **Security headers** (CSP, HSTS, X-Frame-Options, etc.)
- **Password hashing** with bcrypt
- **CORS** configured for allowed origins only
- **Credential masking** in logs and API responses

---

## 📊 API Endpoints

| Prefix            | Description                    |
|-------------------|--------------------------------|
| `/api/v1/auth/*`  | Authentication & user mgmt     |
| `/api/v1/tasks/*` | Task CRUD & execution          |
| `/api/v1/sessions/*` | Browser session management  |
| `/api/v1/websites/*` | Website configurations      |
| `/api/v1/agent/*` | Direct agent control           |
| `/api/v1/proxy/*` | Proxy status & rotation        |
| `/api/v1/admin/*` | Superadmin controls            |

Full API docs: `http://localhost:8000/docs`

---

## 🧪 Development

```bash
# Backend lint
cd backend && ruff check .

# Frontend lint
cd frontend && npm run lint

# Run backend tests
cd backend && pytest

# Build for production
docker-compose -f docker-compose.yml build
```

---

## 📄 License

MIT License — See LICENSE file for details.

---

**Built with ❤️ using DeepSeek, FastAPI, Next.js, and Playwright.**
