# ABC Company · Nimbus (LaunchDarkly SE homework)

This is a small **fictional** SaaS landing page (“Nimbus Workspace”) for ABC Company — you do not need a real product. It uses the **LaunchDarkly Python server SDK** with **Server-Sent Events** so the hero section updates **without a full page reload** when you change a flag in LaunchDarkly.

## Requirements

- Python **3.10+** (3.14 used in development)
- A LaunchDarkly **trial** account and a **Server-side SDK** key for the environment you want to use

## Setup

```bash
cd LaunchD
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

1. **`LAUNCHDARKLY_SDK_KEY`** — from **Account settings → Projects → [your project] → [environment]**: copy the **Server-side SDK ID** (starts with `sdk-`).
2. **`FEATURE_FLAG_KEY`** — must match a **boolean** flag you create in that same environment (default in the sample: `hero-component-v2`).

### New to feature flags?

- A **feature flag** is just a remote-controlled switch (often boolean) stored in LaunchDarkly. Your code **asks LaunchDarkly for the current value** for a given **flag key** and **user/context**. You change behavior in the UI without redeploying.

There are **two different strings** beginners often mix up — both belong in `.env`, but they are **not** interchangeable:

| Name in `.env` | What it is | Where it comes from |
|----------------|------------|---------------------|
| **`LAUNCHDARKLY_SDK_KEY`** | Password for **your running app** so LaunchDarkly will stream flag data to it | LaunchDarkly → your **project** → pick **environment** (e.g. **Test**) → **Server-side SDK key** (`sdk-…`) |
| **`FEATURE_FLAG_KEY`** | The **name of one flag** your code evaluates (you choose it) | When you **create** a flag in LaunchDarkly, you set its **key** (e.g. `hero-component-v2`). Put **that exact key** in `.env`. |

You do **not** paste the flag key into the LaunchDarkly “SDK key” field — the SDK key field only ever gets the **`sdk-…`** value.

### “SDK is not connected” in the LaunchDarkly UI

That indicator means LaunchDarkly has **not seen a successful connection** from an SDK using **this environment’s** server-side key yet.

1. Put **`LAUNCHDARKLY_SDK_KEY`** in `.env` (the **`sdk-…`** key from the **same** environment where your flag lives — usually **Test** while you experiment).
2. Restart the app and leave it running:  
   `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
3. Wait **30–60 seconds** after startup; refresh the LaunchDarkly **Support / debugger** or environment status page if your UI shows SDK health there.
4. Confirm you did **not** accidentally run without `.env` (wrong working directory): run `uvicorn` from the **`LaunchD`** folder where `.env` lives).
5. Use **one environment consistently**: Test **SDK key** + flags created/edited while the **Test** environment is selected in the LaunchDarkly UI (mixing Test SDK with Production-only flags causes confusion).

If `LAUNCHDARKLY_SDK_KEY` is empty or wrong, this sample runs in **offline** mode (no connection), and the dashboard will stay “not connected.”

Optional (for `POST /api/remediate`):

- **`LAUNCHDARKLY_API_ACCESS_TOKEN`** — create a token with **Writer** (or higher) under **Account settings → Authorization**.
- **`LAUNCHDARKLY_PROJECT_KEY`** — project key from the URL or project settings.
- **`LAUNCHDARKLY_ENVIRONMENT_KEY`** — often `test` on a trial; must match the environment whose flag you are toggling.

## LaunchDarkly configuration (minimal)

1. Create a **boolean** flag whose key equals **`FEATURE_FLAG_KEY`** (e.g. `hero-component-v2`).
2. For **Part 1 (release & remediate)**:
   - Turn the flag **on** to show the “new hero”; **off** for the original hero. The running app listens for flag changes over the SDK stream and pushes updates to the browser over **SSE**.
3. For **Part 2 (targeting)**:
   - Add **context attributes** that match the form: `email`, `plan`, `region` (and you can use `name` / `key` as needed).
   - In the flag’s targeting, build **individual** or **rule-based** rules (e.g. `plan` equals `enterprise`, or email ends with `@abc.com`).
4. Open the app, fill in **Targeting context**, click **Save context**, and confirm the evaluation changes as you adjust rules in LaunchDarkly.

## Run

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**.

If **`LAUNCHDARKLY_SDK_KEY`** is missing, the SDK runs in **offline** mode and the flag stays at the default (`false`) — useful only for smoke-testing the UI.

## What maps to the assignment

| Requirement | Where |
|-------------|--------|
| Flag wraps a feature | Hero section variants toggled by boolean flag |
| Instant release / rollback without reload | `flag_tracker.add_listener` + SSE (`/events/stream`) |
| Remediation trigger | Optional `POST /api/remediate` or toggle in LaunchDarkly UI |
| Context attributes | `email`, `plan`, `region`, `name` on LaunchDarkly user context |
| Individual / rule targeting | Configure in LaunchDarkly against those attributes |

## Extra credit

Experimentation and AI configs are **not** implemented here; add them in LaunchDarkly when you’re ready.
