"""Statistics and figures shared by the analysis scripts (ground rule 4).

Every comparison is a per-circuit ratio ``other / Harvest-reference`` (mean
over seeds first).  Reported: n, geometric mean, W/T/L with a +-1% tie band
("win" = the other config beats the reference), p10 / p90, and a CDF figure.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import newexp_common  # noqa: F401  (sets sys.path)
import rq_plotstyle as style
from rq_common import geomean, read_rows  # noqa: F401

TIE = 0.01


def ratio_stats(r: pd.Series, prefix: str = "") -> dict:
    r = pd.to_numeric(r, errors="coerce").dropna()
    r = r[r > 0]
    if not len(r):
        return {f"{prefix}n": 0}
    return {f"{prefix}n": len(r), f"{prefix}geomean": geomean(r),
            f"{prefix}wins": int((r < 1 - TIE).sum()), f"{prefix}ties": int(((r - 1).abs() <= TIE).sum()),
            f"{prefix}losses": int((r > 1 + TIE).sum()),
            f"{prefix}p10": float(np.percentile(r, 10)), f"{prefix}p90": float(np.percentile(r, 90))}


def cdf_figure(series: dict, path, xlabel: str, title: str = "", ncols: int = 1, panels=None):
    """One CDF line per label: ``series[label] = per-circuit ratios``.

    ``panels``: optional list of (panel title, {label: ratios}) for side-by-side panels."""
    import matplotlib.pyplot as plt

    style.apply()
    panels = panels or [(title, series)]
    fig, axes = plt.subplots(1, len(panels), figsize=(4.2 * len(panels), 3.4), squeeze=False)
    for ax, (ptitle, data) in zip(axes[0], panels):
        for i, (label, r) in enumerate(data.items()):
            r = np.sort(pd.to_numeric(pd.Series(r), errors="coerce").dropna().values)
            if not len(r):
                continue
            y = np.arange(1, len(r) + 1) / len(r)
            ax.step(r, y, where="post", color=style.SERIES[i % len(style.SERIES)],
                    label=f"{label} (geomean {geomean(r):.3f})")
        ax.axvline(1, color=style.INK2, linewidth=1)
        ax.set_xscale("log")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("fraction of circuits")
        ax.set_title(ptitle)
        ax.legend(fontsize=7, loc="lower right")
    style.save(fig, path)


def md_table(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    def fmt(v):
        if isinstance(v, (float, np.floating)):
            return "" if v != v else format(v, floatfmt)
        return str(v)
    head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return head + "".join("| " + " | ".join(fmt(v) for v in row) + " |\n" for row in df.itertuples(index=False))


def check_validator(df: pd.DataFrame, name: str) -> int:
    """Number of in-tree rows with a violation or failed validation (ground rule 3)."""
    ok = df[df.status == "ok"]
    bad = ok[(pd.to_numeric(ok.n_violations, errors="coerce").fillna(0) > 0)
             | (ok.validated_pre.astype(str) != "True") | (ok.validated_post.astype(str) != "True")]
    print(f"{name}: {len(ok)} ok rows, {len(bad)} with validator failures; status {df.status.value_counts().to_dict()}")
    return len(bad)


CODE = newexp_common.ROOT.parent
BASELINE_SOURCES = {  # compiler -> RQ1 CSV holding its rows (seeds 42-51)
    "PureMagic": CODE / "harvest_magic_state_perf/results/rq/rq1/rq1.csv",
    "EAF": CODE / "harvest_magic_state/results/rq/rq1/rq1.csv",
    "Litinski": CODE / "harvest_magic_state/results/rq/rq1/rq1.csv",
    "O3LS": CODE / "harvest_magic_state/results/rq/rq1/rq1.csv",
}
RQ1_HARVEST = newexp_common.ROOT / "results/rq/rq1/rq1.csv"


def rq1_rows(models=("instant", "cultivation")) -> pd.DataFrame:
    """RQ1 rows of every compiler (Harvest = ``auto``), RQ1 set (no random circuits)."""
    frames, cache = [], {}
    for comp, path in {"Harvest": RQ1_HARVEST, **BASELINE_SOURCES}.items():
        if path not in cache:
            cache[path] = read_rows(path)
        d = cache[path]
        frames.append(d[d.compiler == comp])
    df = pd.concat(frames, ignore_index=True)
    return df[df.model.isin(models) & (df.family != "random")]
