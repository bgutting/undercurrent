# Undercurrent

Watches the changelogs of ten tech companies, tags every change by theme, and writes a weekly report on what moved, including threads that connect two or more companies, with every claim linked to its source.

No coding is needed to set it up. It takes about 20 minutes of clicking, and most of that is waiting.

---

## What you'll need

1. **A GitHub account** (free). Render deploys code from GitHub.
2. **A Render account.** Sign up at render.com with your GitHub account, which links the two. Add a payment method: the database, queue and website run free, but the background worker and the two scheduled jobs are paid. Check Render's pricing page for current rates; at this size it's a few dollars a month.
3. **An Anthropic API key.** Create one at console.anthropic.com (API Keys → Create Key) and add a little credit. Undercurrent uses a small, cheap model to tag entries and a stronger one once a week for the report. Expect a few dollars a month at most.

## Step 1: Put the code on GitHub

1. On github.com, click **+** (top right) → **New repository**.
2. Name it `undercurrent`, choose **Private**, and click **Create repository**.
3. On the empty repository page, click the link **uploading an existing file**.
4. Unzip `undercurrent.zip` on your computer. Open the `undercurrent` folder and drag **everything inside it** (the `app` and `tests` folders, `render.yaml`, `requirements.txt`, this README) into the upload area.
5. Click **Commit changes**.

Check that `render.yaml` appears at the top level of the repository, not inside a subfolder. That's the one thing that has to be right.

## Step 2: Create everything on Render with the Blueprint

`render.yaml` is a **Blueprint**: a description of all six pieces of the app, so Render can create them in one go instead of you clicking each one together.

1. In the Render dashboard, click **New** → **Blueprint**.
2. Pick your `undercurrent` repository. Render reads `render.yaml` and lists what it will create:
   - `undercurrent-web`: the website
   - `undercurrent-worker`: the background worker that does the actual work
   - `undercurrent-hourly`: a scheduled job that queues a check of every source each hour
   - `undercurrent-weekly`: a scheduled job that queues the report on Mondays
   - `undercurrent-queue`: a Key Value instance (Render's Redis) used as the job queue
   - `undercurrent-db`: a Postgres database
3. It will ask for two values:
   - **SITE_PASSWORD**: make one up. The site will ask for it, so strangers can't run up your API bill.
   - **ANTHROPIC_API_KEY**: paste your key.
4. Click **Apply** (or **Deploy Blueprint**).

Render now builds everything, which takes about 3–6 minutes. You can watch each service's progress in the dashboard.

## Step 3: Open it

1. Click `undercurrent-web` in the dashboard. Its address is near the top (something like `undercurrent-web-xxxx.onrender.com`).
2. Open it. When the browser asks for a login, type anything as the username and your SITE_PASSWORD as the password.

At first you'll see **"No report yet."** That's expected. On its first start, the worker collects the last ~90 days from every source, tags them, and then writes the first report automatically. That takes roughly 5–15 minutes. Meanwhile, the **Sources** page shows each company being checked, and **Entries** fills up as items arrive.

After that, it runs on its own: sources are checked hourly, and a new report appears every Monday morning. The **Write a report now** button makes one whenever you like.

---

## Things worth noticing about Render while you do this

This is the actual point of the exercise.

- **Blueprint vs. dashboard.** Everything was created from one file. Now change something in the dashboard (an environment variable, say), then look at `render.yaml`. They've drifted apart. How does Render handle that tension, and how does it tell you?
- **The wiring you didn't do.** Open `undercurrent-worker` → **Environment**. `DATABASE_URL` and `REDIS_URL` were filled in for you from the Blueprint. The queue has no public address at all; services reach it over Render's **private network**.
- **Logs.** Open `undercurrent-worker` → **Logs** and watch the first collection happen live: `ingest render: 41 candidates, 41 new`, and so on.
- **Cron jobs.** Open `undercurrent-hourly`. There's a **Trigger Run** button. Press it, then watch the worker's logs pick up the jobs. That's the queue in action.
- **Deploys from git.** On GitHub, open `app/sources.py`, click the pencil icon, change something small (remove a source, for instance), and commit. Render notices and redeploys automatically. That's the "git push to deploy" experience, done from a browser.
- **Failure.** Some sources will probably fail at some point, since sites block bots, time out, or change their layout. The **Sources** page marks failing rows in red with the reason, and the worker logs show the retries. How failure feels is a big part of how a platform feels.
- **Free-tier edges.** After 15 idle minutes the website goes to sleep, and the next visit takes about a minute to wake it. The free database **expires after 30 days** (with a 14-day grace period). If you want to keep the history, upgrade `undercurrent-db` to the smallest paid plan before then; the data carries over. The free queue lives in memory, so a restart empties it, which is harmless here because the hourly job refills it.

## How it works

```
 hourly cron ──► queue ──► worker ──► fetch source ──► new entries ──► Postgres
                               │                                         │
                               └──► tag entries (fast model) ◄───────────┘
 weekly cron ──► queue ──► worker ──► theme counts (code) + entries ──► report (stronger model)
                                                                          │
                                             website ◄────────────────────┘
```

- **Sources** come in three kinds: RSS/Atom feeds (Anthropic, Vercel, Cloudflare, AWS), Render's own machine-readable changelog, and ordinary web pages (OpenAI, Gemini, Databricks, Snowflake, Modal). For web pages, Undercurrent keeps a snapshot, compares each new fetch with it, and asks the model to pull out only what's genuinely new.
- **Busy feeds are filtered.** Cloudflare keeps only developer-platform and AI items; AWS keeps only Bedrock and agent items. The patterns are in `app/sources.py`.
- **Themes** come from a fixed list in `app/themes.py`, so counts stay comparable week to week.
- **Trend numbers are computed by code, not the model.** "Rising" means busier in the last two weeks than the six before. "Breadth" is how many different companies touched a theme.
- **Honesty guards.** Every claim in a report must cite entries. Any cross-source thread that doesn't cite at least two different companies is deleted automatically before you see it, and the report says how many were removed. "Nothing connects this week" is an allowed answer.

## Changing things

- **Sources:** `app/sources.py`. Each source is a short block with instructions at the top of the file.
- **Themes:** `app/themes.py`.
- **Report style and rules:** the `REPORT_SYSTEM` text in `app/llm.py`. It's plain English.
- **Report day and time:** `schedule` under `undercurrent-weekly` in `render.yaml` (times are UTC).

Edit on GitHub, commit, and Render redeploys.

## Troubleshooting

- **A source is red with "almost empty" or a 403 error.** The site either builds its page with JavaScript or blocks automated visitors. Everything else keeps working without it.
- **Nothing is happening at all.** Check `undercurrent-worker` → **Logs**. A missing or wrong `ANTHROPIC_API_KEY` shows up there. Fix it under **Environment**; the worker restarts on its own.
- **The worker logs mention a model not being found.** The model names are set in `app/config.py`. You can override them without editing code by adding `FAST_MODEL` or `REPORT_MODEL` under the worker's **Environment**.
- **The site says "Password required" in a loop.** The username can be anything, but the password must exactly match SITE_PASSWORD (in `undercurrent-web` → **Environment**).
