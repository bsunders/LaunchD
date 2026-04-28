# ABC Company · Nimbus (LaunchDarkly SE homework)

Fictional SaaS landing page that demonstrates:

- **Part 1 — Release & remediate:** boolean feature flag, **listener** + **SSE** (no full page reload), remediation via UI or API.
- **Part 2 — Target:** **context attributes** (`email`, `plan`, `region`, `name`) for individual and rule-based targeting in LaunchDarkly.
- **Extra credit — Experimentation:** **custom events** for conversion metrics tied to the hero CTAs.
- **Extra credit — AI configs:** **completion-mode AI Config** drives prompts/model for the support chat (`launchdarkly-server-sdk-ai` + OpenAI).

Stack: **Python**, **FastAPI**, **LaunchDarkly server SDK**, **LaunchDarkly AI SDK**, optional **OpenAI**.

## Assumptions

- **Python 3.9+** (tested with 3.14 locally).
- Network access to LaunchDarkly and (for live chat) OpenAI.
- You create flags and AI resources in LaunchDarkly using the **same environment** as your **server-side SDK key**.

## Setup

```bash
cd LaunchD
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Environment variables (`.env`)

| Variable | Purpose |
|----------|---------|
| **`LAUNCHDARKLY_SDK_KEY`** | **Server-side** SDK key (`sdk-…`) for your LD environment (e.g. **Test**). |
| **`FEATURE_FLAG_KEY`** | **Boolean** flag key controlling the hero (default `hero-component-v2`). Create this flag in LaunchDarkly with that exact key. |
| **`LAUNCHDARKLY_AI_CONFIG_KEY`** | **Completion-mode AI Config** key in LaunchDarkly for the chat (default `nimbus-support-chat`). |
| **`EXPERIMENT_CONVERSION_EVENT_KEY`** | Custom event name sent when users click hero CTAs (default `nimbus-hero-cta-click`). Use this string when you define the **metric** for experiments. |
| **`OPENAI_API_KEY`** | Required for **live** LLM replies in chat. If unset, the app still evaluates the AI Config and returns metadata (model name, system prompt preview) without calling OpenAI. |
| **`OPENAI_DEFAULT_MODEL`** | Fallback model name in code when LaunchDarkly does not override (default `gpt-4o-mini`). |

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**.

### Quick checks

```bash
curl -s http://127.0.0.1:8000/api/variation
```

If **`LAUNCHDARKLY_SDK_KEY`** is missing, the SDK runs **offline** and flags use defaults; AI chat falls back to in-code defaults only.

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

### Remediate with `curl` (LaunchDarkly REST API)

Same as before: uses an **API access token** (not the `sdk-…` key). Example for project `default`, flag `hero-component-v2`, environment `test`:

```bash
export LD_API_TOKEN='your-api-access-token'

curl -s -X PATCH \
  "https://app.launchdarkly.com/api/v2/flags/default/hero-component-v2" \
  -H "Authorization: ${LD_API_TOKEN}" \
  -H "Content-Type: application/json-patch+json" \
  -d '[{"op":"replace","path":"/environments/test/on","value":false}]'
```

### Extra credit: integrations

Optional: explore [LaunchDarkly integrations](https://docs.launchdarkly.com/integrations) (observability, Slack, etc.)—not required for a complete submission.

---

## What maps to the homework PDF

| PDF expectation | Where |
|-----------------|--------|
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

### Hero stuck on “off”?

Create the boolean flag in LaunchDarkly with key **exactly** equal to `FEATURE_FLAG_KEY`. Until it exists, evaluation stays at the default (`false`).
