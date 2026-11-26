"""Theme counts over time — computed in code, not by the model.

The model is good at reading entries and bad at counting. So the numbers in
"Themes on the move" come from here, and the model only gets to comment on
them.
"""
from datetime import datetime, timedelta

from .themes import THEMES


def weekly_table(rows, period_end: datetime, weeks: int) -> dict:
    """rows: iterable of (theme, source_key, when).

    Returns {theme: {"counts": [w0, w1, ...], "sources": [set, set, ...]}}
    where w0 is the most recent 7 days before period_end.
    """
    table = {t: {"counts": [0] * weeks, "sources": [set() for _ in range(weeks)]} for t in THEMES}
    for theme, source, when in rows:
        if theme not in table or when is None:
            continue
        age_days = (period_end - when).total_seconds() / 86400
        if age_days < 0:
            age_days = 0
        w = int(age_days // 7)
        if w >= weeks:
            continue
        table[theme]["counts"][w] += 1
        table[theme]["sources"][w].add(source)
    return table


def rising_themes(table: dict, min_recent: int = 3, min_ratio: float = 1.5) -> list[dict]:
    """Themes busier in the last two weeks than in the six before.

    Compares the last 2 weeks with the average 2-week stretch in weeks 3-8.
    'breadth' is how many different companies touched the theme recently —
    the thing that separates an industry move from one company's busy month.
    """
    out = []
    for theme, d in table.items():
        c = d["counts"]
        recent = c[0] + c[1]
        older = c[2:]
        baseline = (sum(older) / len(older) * 2) if older else 0.0
        ratio = (recent + 1) / (baseline + 1)
        breadth = len(d["sources"][0] | d["sources"][1])
        if recent >= min_recent and ratio >= min_ratio:
            out.append({
                "theme": theme,
                "recent": recent,
                "baseline": round(baseline, 1),
                "ratio": round(ratio, 1),
                "breadth": breadth,
                "sources": sorted(d["sources"][0] | d["sources"][1]),
            })
    out.sort(key=lambda r: (r["breadth"], r["ratio"]), reverse=True)
    return out


def broad_themes(table: dict, min_sources: int = 3) -> list[dict]:
    """Themes that at least `min_sources` companies touched in the last two weeks."""
    out = []
    for theme, d in table.items():
        srcs = d["sources"][0] | d["sources"][1]
        if len(srcs) >= min_sources:
            out.append({"theme": theme, "breadth": len(srcs), "sources": sorted(srcs),
                        "recent": d["counts"][0] + d["counts"][1]})
    out.sort(key=lambda r: r["breadth"], reverse=True)
    return out


def history_weeks(rows, period_end: datetime) -> int:
    """How many whole weeks of data exist — used to warn when trends are thin."""
    oldest = None
    for _, _, when in rows:
        if when is not None and (oldest is None or when < oldest):
            oldest = when
    if oldest is None:
        return 0
    return max(0, int((period_end - oldest) / timedelta(days=7)))


def serializable(table: dict) -> dict:
    return {t: {"counts": d["counts"], "sources": [sorted(s) for s in d["sources"]]}
            for t, d in table.items()}
