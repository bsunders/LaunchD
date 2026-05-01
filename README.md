# ABC Company · Nimbus (LaunchDarkly SE homework)

Fictional SaaS landing page that demonstrates:

- **Part 1 — Release & remediate:** boolean feature flag, **listener** + **SSE** (no full page reload), remediation via UI or API.
- **Part 2 — Target:** **context attributes** (`email`, `plan`, `region`, `name`) for individual and rule-based targeting in LaunchDarkly.
- **Extra credit — Experimentation:** **custom events** for conversion metrics tied to the hero CTAs.
- **Extra credit — AI configs:** **completion-mode AI Config** drives prompts/model for the support chat (`launchdarkly-server-sdk-ai` + OpenAI).

Stack: **Python**, **FastAPI**, **LaunchDarkly server SDK**, **LaunchDarkly AI SDK**, optional **OpenAI**.

---

## Submitting your solution (GitHub)

Upload this project to a **public GitHub repository**. Reviewers should be able to:

1. **Clone** the repo and follow the sections **Prerequisites**, **Install and run** (below).
2. Copy **`.env.example`** to **`.env`** and fill in values from their LaunchDarkly project (see **Environment variables**).
3. Create the LaunchDarkly resources listed in **LaunchDarkly UI setup (checklist)** so keys in `.env` match flags and configs they **create** in their account.

**Do not commit secrets.** Keep **`LAUNCHDARKLY_SDK_KEY`**, **`OPENAI_API_KEY`**, and any API tokens **out of git**. The repo should only contain **`.env.example`** (placeholders), not a real `.env`.

---

## Prerequisites and environment assumptions

These are the assumptions this sample makes about the machine running it:

| Assumption | Detail |
|------------|--------|
| **Operating system** | macOS, Linux, or Windows — any OS where **Python 3.9+** runs and you can use a terminal. |
| **Python** | **3.9 or newer** (development used a recent 3.x). Verify with `python3 --version`. |
| **Network** | Outbound **HTTPS** to LaunchDarkly so the server SDK can stream flag updates. Optional: HTTPS to **OpenAI** if you enable live chat completions. |
| **Local port** | **TCP port 8000** on `127.0.0.1` is free for the web server (change the port in the run command if needed). |
| **LaunchDarkly account** | You can log into LaunchDarkly, create a **boolean** flag, optional **AI Config** and **metric**, and copy the **server-side SDK key** for one environment (e.g. Test). |
| **Same environment** | Flags, AI configs, and metrics must live in the **same LaunchDarkly environment** as the **server-side SDK key** you put in `.env`. |

No Docker or database is required. No cloud hosting is required for local execution.

---

## Install and run (step by step)

### 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd LaunchD
```

### 2. Create a virtual environment

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (cmd):**

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit **`.env`** (create this file locally; it is gitignored):

1. Set **`LAUNCHDARKLY_SDK_KEY`** to your **server-side** SDK key from LaunchDarkly: **Account settings → Projects → [your project] → Environments → [environment] → SDK key** (starts with `sdk-`).  
   - Without this value, the app still starts in **offline** mode, but flag evaluations will not reflect your LaunchDarkly project.
2. Align **`FEATURE_FLAG_KEY`**, **`LAUNCHDARKLY_AI_CONFIG_KEY`**, and **`EXPERIMENT_CONVERSION_EVENT_KEY`** with resources **you create** in LaunchDarkly (see table below and **LaunchDarkly UI setup**).

### 5. Start the application

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or, from the repo root after the venv exists:

```bash
chmod +x start.sh   # once
./start.sh
```

You should see logging that LaunchDarkly is **online** if `LAUNCHDARKLY_SDK_KEY` is set, or a warning about **offline mode** if it is empty.

### 6. Open the app and sanity-check

- Browser: **http://127.0.0.1:8000**
- API (same evaluation context as the browser after cookies are set):

```bash
curl -s http://127.0.0.1:8000/api/variation
```

Expect JSON with `flag_key`, `variation`, `evaluation_reason`, and `attributes`.

### Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Hero stays on “original” / flag appears off | Boolean flag missing in LD, wrong **`FEATURE_FLAG_KEY`**, or SDK **offline** (empty `LAUNCHDARKLY_SDK_KEY`). |
| No instant updates when toggling in LD | **`LAUNCHDARKLY_SDK_KEY`** set, network allows LD streaming; watch server logs for SDK errors. |
| Chat shows “config only” | **`OPENAI_API_KEY`** unset — intentional fallback; add key for live completions. |
| Port in use | Run on another port: `uvicorn app.main:app --reload --host 127.0.0.1 --port 8001` and open that port in the browser. |
| `remediate.sh` / `hero-off.sh` returns **404** or wrong UI after “success” | **`LD_PROJECT_KEY`**, **`LD_ENVIRONMENT_KEY`**, **`LD_FLAG_KEY`** must match your LaunchDarkly URL and SDK environment (see **Remediation** below). |
| No observability data in LaunchDarkly | Confirm **`LAUNCHDARKLY_OBSERVABILITY=1`**, valid **`LAUNCHDARKLY_SDK_KEY`**, outbound HTTPS to OTLP, and that Observability is enabled for your LD account. |

---

## Optional helper scripts

| Script | Purpose |
|--------|---------|
| **`start.sh`** | Activates `.venv` and runs **uvicorn** on port 8000. |
| **`hero-on.sh`** / **`hero-off.sh`** | Call **`remediate.sh`** to turn the hero flag **on** or **off** via the REST API (Part 1 **curl** remediation). |
| **`remediate.sh`** | Lower-level: `./remediate.sh on\|off`. Uses LaunchDarkly **semantic patch** (`turnFlagOn` / `turnFlagOff`). Requires **`LD_API_TOKEN`** (and usually **`LD_PROJECT_KEY`**, **`LD_ENVIRONMENT_KEY`**) — see `.env.example` comments. |

Make scripts executable once: `chmod +x start.sh remediate.sh hero-on.sh hero-off.sh`.

---

## Environment variables (`.env`)

| Variable | Purpose |
|----------|---------|
| **`LAUNCHDARKLY_SDK_KEY`** | **Server-side** SDK key (`sdk-…`) for your LD environment (e.g. **Test**). Replace the placeholder in `.env`; never commit the real value. |
| **`FEATURE_FLAG_KEY`** | **Boolean** flag key controlling the hero (default `hero-component-v2`). **You must create** this flag in LaunchDarkly with that exact key (or change the variable to match the key you chose). |
| **`LAUNCHDARKLY_AI_CONFIG_KEY`** | **Completion-mode AI Config** key in LaunchDarkly for the chat (default `nimbus-support-chat`). **Create** the AI Config with this key, or change the variable. |
| **`EXPERIMENT_CONVERSION_EVENT_KEY`** | Custom event name sent when users click hero CTAs (default `nimbus-hero-cta-click`). **Use the same string** when you define the **metric** for experiments in LaunchDarkly. |
| **`OPENAI_API_KEY`** | Required for **live** LLM replies in chat. If unset, the app still evaluates the AI Config and returns metadata (model name, system prompt preview) without calling OpenAI. |
| **`OPENAI_DEFAULT_MODEL`** | Fallback model name in code when LaunchDarkly does not override (default `gpt-4o-mini`). |
| **`LAUNCHDARKLY_OBSERVABILITY`** | Set **`1`** / **`true`** to enable the official **`launchdarkly-observability`** plugin (OpenTelemetry → LaunchDarkly Observability). Only when **`LAUNCHDARKLY_SDK_KEY`** is set; see note below. |
| **`OTEL_SERVICE_NAME`** | Service name on spans (default **`nimbus`**). |
| **`OTEL_SERVICE_VERSION`** | Service version (default **`dev`**). |
| **`OTEL_EXPORTER_OTLP_ENDPOINT`** | Optional OTLP override; default targets LaunchDarkly. See [Python observability](https://launchdarkly.com/docs/sdk/observability/python). |

Optional (only for **`remediate.sh`** / **`hero-*.sh`**, not used by the Python app): **`LD_API_TOKEN`**, **`LD_PROJECT_KEY`**, **`LD_ENVIRONMENT_KEY`**, **`LD_FLAG_KEY`** per `.env.example`.

**Observability:** LaunchDarkly may require Observability to be enabled on your account. With **`LAUNCHDARKLY_OBSERVABILITY`** unset, behavior matches the app without the plugin.

**Seeing data in LaunchDarkly:** set **`LAUNCHDARKLY_OBSERVABILITY=1`**, keep a valid **`LAUNCHDARKLY_SDK_KEY`**, then run the app. The code calls **`observe.record_log`** on startup and wraps each request in **`observe.start_span("nimbus.http.request", ...)`** (see `app/observe_ld.py` and `app/main.py`) so traces/logs are not only from implicit SDK hooks. Open the app in a browser (or `curl`); telemetry is batched—OTLP **force_flush** runs on startup; traffic may take a short time to appear in the LD Observability UI.

---

## LaunchDarkly UI setup (checklist)

### 1. Feature flag (Parts 1 & 2)

1. Create a **boolean** flag whose key **exactly matches** `FEATURE_FLAG_KEY` (e.g. `hero-component-v2`).
2. Turn it **on** to “release” the new hero, **off** to roll back (instantly via SSE).
3. For **targeting**, use the context shown on the page: **individual** (e.g. target by **context key** or **email**) and **rule-based** (e.g. **plan**, **region**). Save the **Targeting context** form and watch **Last evaluation reason** update.

### 2. AI Config (extra credit)

1. In LaunchDarkly, create an **AI Config** in **completion** mode with key **exactly** `LAUNCHDARKLY_AI_CONFIG_KEY` (default `nimbus-support-chat`).
2. Set **provider** to **OpenAI** and choose a **model** (you can change both later without redeploying).
3. Edit **messages** (system / user templates); optional template variables `userName`, `userEmail`, `userPlan` are supplied from the session context.
4. Add **`OPENAI_API_KEY`** to `.env` so the app can call OpenAI; metrics from generations are reported through the AI SDK when you use the managed model path.

### 3. Experimentation (extra credit)

1. **Metric:** Create a **custom** metric whose event key matches **`EXPERIMENT_CONVERSION_EVENT_KEY`** (default `nimbus-hero-cta-click`). Use event **count** (or add numeric `metric_value` later if you extend the code).
2. **Experiment:** Create an experiment on **`FEATURE_FLAG_KEY`**, add your metric as a **goal**, allocate traffic, and **start** the experiment.
3. **Measure:** Click the hero **Start free trial** / **See Nimbus in action** buttons (they **POST** `/api/events/hero-cta`, which calls `track()` + `flush`). Let the experiment run until LaunchDarkly has enough data for the UI to compare variations.

### 4. Remediation (Part 1)

Toggle the flag **off** in the LaunchDarkly UI, or patch it with the REST API (see below).

### Remediate with the REST API (`curl` or `hero-*.sh`)

Use an **API access token** from **Account settings → Authorization → Access tokens** — **not** the `sdk-…` key. **Writer** (or higher) scope. Export **`LD_API_TOKEN`**; set **`LD_PROJECT_KEY`**, **`LD_ENVIRONMENT_KEY`**, and **`LD_FLAG_KEY`** to match the flag URL  
`https://app.launchdarkly.com/<project-key>/<environment-key>/features/<flag-key>`  
(Defaults `default` / `test` are often wrong — your **`LD_ENVIRONMENT_KEY`** must match the environment of **`LAUNCHDARKLY_SDK_KEY`**.)

**Preferred:** run **`./hero-off.sh`** or **`./hero-on.sh`** (see **Optional helper scripts**). They call **`remediate.sh`**, which uses LaunchDarkly’s **semantic patch** (`turnFlagOn` / `turnFlagOff`).

**Raw `curl`** (turn off; same as `hero-off.sh` with default keys):

```bash
export LD_API_TOKEN='your-api-access-token'

curl -s -X PATCH \
  "https://app.launchdarkly.com/api/v2/flags/default/hero-component-v2" \
  -H "Authorization: ${LD_API_TOKEN}" \
  -H "Content-Type: application/json; domain-model=launchdarkly.semanticpatch" \
  -d '{"environmentKey":"test","instructions":[{"kind":"turnFlagOff"}]}'
```

### Extra credit: integrations

Optional: explore [LaunchDarkly integrations](https://docs.launchdarkly.com/integrations) (observability, Slack, etc.)—not required for a complete submission.

---

## What maps to the homework PDF

| PDF expectation | Where |
|-----------------|-------|
| Flag wraps a feature | Hero toggles via boolean `FEATURE_FLAG_KEY` |
| Listener / no reload | `flag_tracker.add_listener` → SSE `/events/stream` → `EventSource` |
| Remediate (UI / curl / browser) | LD UI or REST `curl` above |
| Context + individual + rule targeting | Form → `email`, `plan`, `region`, `name`; rules in LaunchDarkly |
| Experimentation: metric + experiment + measure | `track(EXPERIMENT_CONVERSION_EVENT_KEY)` on hero CTA; configure metric + experiment in LD |
| AI Config: change prompts/models quickly | `LAUNCHDARKLY_AI_CONFIG_KEY` + `LDAIClient.create_model` + OpenAI |
| (Optional) AI experiments | Use LaunchDarkly experiment/monitoring on AI metrics after enabling live chat |

---

## Project layout (hints for reviewers)

| Path | Role |
|------|------|
| `app/ld_service.py` | SDK init, `flag_tracker.add_listener`, SSE broadcast |
| `app/ai_service.py` | AI Config evaluation + managed chat |
| `app/main.py` | Routes: `/`, `/api/context`, `/api/variation`, `/events/stream`, `/api/events/hero-cta`, `/api/chat` |
| `templates/index.html` | Hero, targeting form, chat UI |
| `remediate.sh`, `hero-on.sh`, `hero-off.sh` | REST remediation (semantic patch); optional **`start.sh`** to launch uvicorn |
| `launchdarkly-observability` (dependency) | Optional **`ObservabilityPlugin`** wired in **`app/ld_service.py`** when **`LAUNCHDARKLY_OBSERVABILITY=1`** |

### Hero stuck on “off”?

Create the boolean flag in LaunchDarkly with key **exactly** equal to `FEATURE_FLAG_KEY`. Until it exists, evaluation stays at the default (`false`).
