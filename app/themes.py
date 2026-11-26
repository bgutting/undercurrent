"""The fixed theme vocabulary every entry is tagged with.

Trends only work if the tags are consistent week to week, so the model must
choose from this list rather than inventing labels. Edit freely, but note that
renaming a theme splits its history.
"""

THEMES = {
    "agent-runtimes": "Running agents in production: agent frameworks, hosted agent runtimes, tool use, computer use",
    "sandboxes": "Isolated code execution: sandboxes, microVMs, ephemeral environments for untrusted or agent-written code",
    "durable-workflows": "Durable execution and orchestration: workflows, long-running jobs, retries, step functions",
    "state-and-memory": "Persistent state for apps and agents: memory, sessions, shared filesystems, stateful compute",
    "interop-mcp": "Interoperability: MCP, A2A, connectors, plugins, agent-to-service protocols",
    "models": "New models, model versions, model availability on a platform",
    "pricing-billing": "Pricing, billing, plans, quotas, rate limits",
    "data-governance": "Catalogs, lineage, access policies, data sharing, governance",
    "ai-in-data": "AI features inside data platforms: AI SQL, data agents, semantic layers, vector search over data",
    "developer-tooling": "CLIs, SDKs, IDE and coding-agent integrations, local dev experience",
    "observability": "Logs, metrics, tracing, evals, monitoring",
    "security-identity": "Auth, OIDC, SSO, secrets, permissions, guardrails",
    "compliance-gov": "Compliance and government: FedRAMP, GovCloud, HIPAA, certifications, data residency",
    "compute-infra": "Instances, GPUs, regions, scaling, networking, performance",
    "databases-storage": "Databases, caches, object storage, queues",
}


def describe() -> str:
    return "\n".join(f"- {k}: {v}" for k, v in THEMES.items())
