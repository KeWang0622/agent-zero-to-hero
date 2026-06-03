"""Build share-ready PNG assets that screenshot well on Twitter/X / LinkedIn / Slack.

Outputs into assets/share/:
  the-loop-poster.png    1600x1000  the 6-line loop, large, clean, attributable
  vs-frameworks.png      1600x900   LOC + concept comparison vs LangChain/CrewAI/smolagents
  motto-*.png  (×6)      1200x630   one share card per hero-chapter motto

All assets use Catppuccin Mocha + JetBrains Mono. Designed for the
"someone DM'd me this; I want to share it" moment.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import rcParams

# Palette
BASE     = "#1e1e2e"
MANTLE   = "#181825"
SURFACE  = "#313244"
TEXT     = "#cdd6f4"
SUBTEXT  = "#a6adc8"
OVERLAY  = "#6c7086"
BLUE     = "#89b4fa"
MAUVE    = "#cba6f7"
GREEN    = "#a6e3a1"
YELLOW   = "#f9e2af"
PINK     = "#f5c2e7"
PEACH    = "#fab387"
RED      = "#f38ba8"

rcParams["font.family"] = "monospace"

HERE = Path(__file__).resolve().parent.parent / "assets" / "share"
HERE.mkdir(parents=True, exist_ok=True)


def save(fig, name, dpi=140):
    out = HERE / name
    fig.savefig(out, dpi=dpi, bbox_inches="tight",
                facecolor=BASE, edgecolor="none")
    plt.close(fig)
    print(f"  wrote {out}")


# ---------- 1. The 6-line loop poster ------------------------------------

def loop_poster():
    """The marquee asset. Designed for someone to drop this image into a tweet
    with no caption and have the tweet still make sense."""
    fig, ax = plt.subplots(figsize=(16, 10), dpi=120)
    fig.patch.set_facecolor(BASE)
    ax.set_facecolor(BASE)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off")

    # Header
    ax.text(50, 92, "THE ENTIRE AGENT LOOP",
            ha="center", color=BLUE, fontsize=28, fontweight="bold")
    ax.text(50, 87, "every coding agent on Earth wraps these six lines",
            ha="center", color=SUBTEXT, fontsize=15, style="italic")

    # Code block — large, prominent, the focus of the poster
    code_lines = [
        ("while True:", TEXT),
        ("    r = client.messages.create(model=M, messages=msgs, tools=TOOLS)", TEXT),
        ('    msgs.append({"role": "assistant", "content": r.content})', TEXT),
        ('    if r.stop_reason != "tool_use":', TEXT),
        ("        return r", TEXT),
        ('    msgs.append({"role": "user", "content": run_all_tools(r.content)})', TEXT),
    ]

    # Code panel
    panel = patches.FancyBboxPatch(
        (5, 35), 90, 38,
        boxstyle="round,pad=1.2", facecolor=MANTLE, edgecolor=SURFACE, lw=2)
    ax.add_patch(panel)

    # Render lines monospace
    for i, (line, color) in enumerate(code_lines):
        ax.text(8, 67 - i * 5.5, line, color=color,
                fontsize=15, family="monospace", fontweight="bold")

    # Decorations
    # Bullet points around the code
    callouts = [
        (50, 28, "the model is stateless — the messages array IS the memory", BLUE),
        (50, 23, "tools, skills, MCP, sessions are layers around this loop", MAUVE),
        (50, 18, "no LangChain, no graph DSL, no framework — just the loop", PEACH),
    ]
    for x, y, text, color in callouts:
        ax.text(x, y, text, ha="center", color=color,
                fontsize=14, family="monospace")

    # Footer attribution
    ax.text(50, 8, "agent-zero-to-hero · github.com/KeWang0622/agent-zero-to-hero",
            ha="center", color=OVERLAY, fontsize=12, family="monospace")
    ax.text(50, 4, "build a Claude-Code-shaped harness from scratch · 20 chapters · ~5,000 LOC",
            ha="center", color=OVERLAY, fontsize=11, family="monospace", style="italic")

    save(fig, "the-loop-poster.png")


# ---------- 2. vs frameworks comparison ----------------------------------

def vs_frameworks():
    """Comparison table that gets screenshot-shared in framework debates."""
    fig, ax = plt.subplots(figsize=(16, 9), dpi=120)
    fig.patch.set_facecolor(BASE)
    ax.set_facecolor(BASE)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(50, 92, "FRAMEWORKS vs FROM-SCRATCH",
            ha="center", color=YELLOW, fontsize=24, fontweight="bold")
    ax.text(50, 87, "what each one teaches you, in May 2026",
            ha="center", color=SUBTEXT, fontsize=13, style="italic")

    # Headers
    cols = ["", "LangChain", "LangGraph", "CrewAI", "smolagents", "agent-zero-to-hero"]
    col_x = [3, 22, 38, 54, 70, 88]

    rows = [
        ("type",                  ["framework", "framework", "framework", "framework", "course / textbook"]),
        ("size",                  ["~120K LOC",  "~30K LOC",  "~25K LOC",  "~8K LOC",   "**~5,000 LOC**"]),
        ("agent loop visible?",   ["no",         "graph",     "agents+",   "yes",       "**6 lines**"]),
        ("you write the loop?",   ["no",         "no",        "no",        "no",        "**yes**"]),
        ("see compaction inside?", ["no",        "no",        "no",        "no",        "**ch10**"]),
        ("see MCP wire format?",  ["no",         "no",        "no",        "no",        "**ch13**"]),
        ("multi-provider in 50 LOC?",["no",      "no",        "no",        "kinda",     "**yes**"]),
        ("\"throw it away\" friendly?",["no",   "no",        "no",        "kinda",     "**yes**"]),
    ]

    # render headers
    for i, c in enumerate(cols):
        weight = "bold" if c else "normal"
        color = YELLOW if c == "agent-zero-to-hero" else (TEXT if c else TEXT)
        size = 11 if c == "agent-zero-to-hero" else 12
        ax.text(col_x[i], 80, c, color=color, fontsize=size,
                fontweight=weight, family="monospace", ha="left")

    # divider
    ax.plot([2, 98], [76, 76], color=SURFACE, lw=1)

    # rows
    for r, (label, vals) in enumerate(rows):
        y = 72 - r * 7.5
        ax.text(col_x[0], y, label, color=SUBTEXT, fontsize=11,
                family="monospace", fontweight="bold")
        for i, v in enumerate(vals):
            color = YELLOW if "**" in v else SUBTEXT
            v_clean = v.replace("**", "")
            weight = "bold" if "**" in v else "normal"
            ax.text(col_x[i+1], y, v_clean, color=color, fontsize=11,
                    family="monospace", fontweight=weight)

    # bottom note
    ax.text(50, 6, "frameworks tell you WHAT TO TYPE.   agent-zero-to-hero tells you WHAT'S UNDERNEATH.",
            ha="center", color=PEACH, fontsize=13, fontweight="bold", family="monospace")
    ax.text(50, 2, "github.com/KeWang0622/agent-zero-to-hero",
            ha="center", color=OVERLAY, fontsize=11, family="monospace")

    save(fig, "vs-frameworks.png")


# ---------- 3. Motto share cards (1 per hero chapter) --------------------

MOTTOS = [
    ("ch02", "messages array",
     "The messages array IS the memory.",
     "There is no other memory.", BLUE),
    ("ch05", "the loop",
     "An agent loop is just `while True`",
     "of one talking to the other.", MAUVE),
    ("ch08c", "prompt caching",
     "It's not a feature.",
     "It's a placement problem.", PEACH),
    ("ch10", "compaction",
     "Surgery, not garbage collection.",
     "Replace the older half with one synthetic message.", GREEN),
    ("ch11", "subagents",
     "Context isolation as a feature.",
     "10× cheaper.", PINK),
    ("ch13", "MCP wire",
     "Three method calls.",
     "JSON-RPC over stdio. That's all.", YELLOW),
]


def motto_card(chapter, name, line1, line2, accent):
    fig, ax = plt.subplots(figsize=(12, 6.3), dpi=120)
    fig.patch.set_facecolor(BASE)
    ax.set_facecolor(BASE)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off")

    # chapter tag (top-left)
    ax.text(4, 88, f"{chapter} · {name}", color=accent, fontsize=14,
            family="monospace", fontweight="bold")

    # quote — large, centered, the focus
    ax.text(50, 60, f"“{line1}", ha="center", color=TEXT,
            fontsize=24, family="monospace", fontweight="bold")
    ax.text(50, 45, f"{line2}”", ha="center", color=TEXT,
            fontsize=24, family="monospace", fontweight="bold")

    # accent bar
    ax.plot([15, 85], [32, 32], color=accent, lw=2)

    # attribution
    ax.text(50, 22, "agent-zero-to-hero",
            ha="center", color=accent, fontsize=14,
            family="monospace", fontweight="bold")
    ax.text(50, 14, "build a Claude-Code-shaped agent harness from scratch",
            ha="center", color=SUBTEXT, fontsize=11,
            family="monospace", style="italic")
    ax.text(50, 7, "github.com/KeWang0622/agent-zero-to-hero",
            ha="center", color=OVERLAY, fontsize=10, family="monospace")

    save(fig, f"motto-{chapter}.png")


def all_mottos():
    for ch, name, l1, l2, accent in MOTTOS:
        motto_card(ch, name, l1, l2, accent)


# ---------- run --------------------------------------------------------

if __name__ == "__main__":
    print("building share assets...")
    loop_poster()
    vs_frameworks()
    all_mottos()
    print("done.")
