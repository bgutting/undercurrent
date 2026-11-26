"""The sources Undercurrent watches.

To add or remove a source, edit this list and redeploy. Each source needs:
  key       short unique id (letters and dashes; never change it once data exists)
  name      display name
  layer     which part of the stack it represents (used to group in reports)
  kind      "feed"   - an RSS or Atom feed
            "render" - Render's machine-readable changelog.md
            "page"   - an ordinary web page; Undercurrent compares snapshots
                       and asks the model to pull out whatever is new
  url       where to fetch it
  include   optional list of patterns; when given, only entries whose title
            matches one of them are kept (for very busy feeds)
"""

SOURCES = [
    # --- Model providers ---
    {
        "key": "anthropic",
        "name": "Anthropic",
        "layer": "Model providers",
        "kind": "feed",
        "url": "https://platform.claude.com/docs/en/release-notes/feed.xml",
    },
    {
        "key": "openai",
        "name": "OpenAI",
        "layer": "Model providers",
        "kind": "page",
        "url": "https://developers.openai.com/changelog",
    },
    {
        "key": "gemini",
        "name": "Google Gemini",
        "layer": "Model providers",
        "kind": "page",
        "url": "https://ai.google.dev/gemini-api/docs/changelog",
    },
    # --- App and deploy platforms ---
    {
        "key": "render",
        "name": "Render",
        "layer": "App platforms",
        "kind": "render",
        "url": "https://render.com/changelog.md",
    },
    {
        "key": "vercel",
        "name": "Vercel",
        "layer": "App platforms",
        "kind": "feed",
        "url": "https://vercel.com/atom",
    },
    {
        "key": "cloudflare",
        "name": "Cloudflare",
        "layer": "App platforms",
        "kind": "feed",
        "url": "https://developers.cloudflare.com/changelog/rss/index.xml",
        # Cloudflare posts 40+ items a week across networking, security, etc.
        # Keep the developer-platform and AI ones.
        "include": [
            r"\bWorkers?\b", r"\bAgents?\b", r"\bAI\b", r"Durable Objects",
            r"\bD1\b", r"\bR2\b", r"Containers?", r"Sandbox", r"Workflows?",
            r"\bQueues\b", r"\bKV\b", r"Browser Rendering", r"Vectorize",
            r"\bMCP\b", r"Hyperdrive", r"Wrangler", r"\bPages\b",
        ],
    },
    # --- Data platforms ---
    {
        "key": "databricks",
        "name": "Databricks",
        "layer": "Data platforms",
        "kind": "page",
        "url": "https://docs.databricks.com/aws/en/release-notes/product/",
    },
    {
        "key": "snowflake",
        "name": "Snowflake",
        "layer": "Data platforms",
        "kind": "page",
        "url": "https://docs.snowflake.com/en/release-notes/new-features",
    },
    # --- AI compute and sandboxes ---
    {
        "key": "modal",
        "name": "Modal",
        "layer": "AI compute",
        "kind": "page",
        "url": "https://modal.com/changelog",
    },
    # --- The incumbent ---
    {
        "key": "aws",
        "name": "AWS (Bedrock & agents)",
        "layer": "Incumbent",
        "kind": "feed",
        "url": "https://aws.amazon.com/about-aws/whats-new/recent/feed/",
        # The full AWS feed is dozens of items a day. Keep the agent/AI layer.
        "include": [r"Bedrock", r"AgentCore", r"durable functions", r"MicroVM"],
    },
]

BY_KEY = {s["key"]: s for s in SOURCES}
