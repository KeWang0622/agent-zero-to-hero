"""
Render a demo GIF of `python agent.py "build me Tetris..."` running.

Generates a sequence of PNG frames using PIL with a Catppuccin Mocha
terminal aesthetic, then composes them into a GIF.

Output: assets/launch.gif (1200x720, ~10 seconds, ~30 fps)
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import shutil

# ---- Catppuccin Mocha palette --------------------------------------------
BASE     = (30, 30, 46)
MANTLE   = (24, 24, 37)
SURFACE  = (49, 50, 68)
TEXT     = (205, 214, 244)
SUBTEXT  = (166, 173, 200)
OVERLAY  = (108, 112, 134)
BLUE     = (137, 180, 250)
MAUVE    = (203, 166, 247)
GREEN    = (166, 227, 161)
YELLOW   = (249, 226, 175)
RED      = (243, 139, 168)
PEACH    = (250, 179, 135)
TEAL     = (148, 226, 213)

# ---- font ---------------------------------------------------------------
FONT_PATH = "/System/Library/Fonts/SFNSMono.ttf"
FONT_BOLD = "/System/Library/Fonts/SFNSMono.ttf"

W, H = 1200, 720
PAD = 24
LINE_H = 22
FONT_SIZE = 16

# ---- terminal state machine ---------------------------------------------

def render_frame(lines: list[tuple[str, tuple]], title="agent-zero-to-hero"):
    """Render one terminal frame. lines is a list of (text, color) tuples."""
    img = Image.new("RGB", (W, H), BASE)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    # macos title bar
    draw.rectangle([0, 0, W, 36], fill=MANTLE)
    for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = 18 + i * 20
        draw.ellipse([cx - 6, 14, cx + 6, 26], fill=color)
    draw.text((W // 2 - 90, 9), f"{title} — agent.py", font=font, fill=SUBTEXT)

    # body
    y = PAD + 36
    for text, color in lines:
        draw.text((PAD, y), text, font=font, fill=color)
        y += LINE_H
        if y > H - PAD:
            break

    return img


# ---- the script ---------------------------------------------------------
# real output from a live agent.py run captured earlier this session

PROMPT = '> build me a hello.py with a function that prints "agent-zero-to-hero is alive", then run it'

# unfold per-frame: build the panel header, then the prompt typing, then
# the agent's streamed response, then tool calls, then final.

frames = []

def add_frame(content_lines):
    """content_lines is a list-of-(text, color). Each call appends one frame."""
    frames.append(render_frame(list(content_lines)))


# ---- act 1: panel header (1 frame) ----------------------------------------
panel_top = "╭─ agent-zero-to-hero · session 7f11a792f670 ─────────────────────╮"
panel_mid = "│ model claude-sonnet-4-6 · cwd /tmp/demo · streaming=on · cache=on │"
panel_bot = "╰────────────────────────────────────────────────────────────────────╯"

base_lines = [
    (panel_top, OVERLAY),
    (panel_mid, OVERLAY),
    (panel_bot, OVERLAY),
    ("", TEXT),
    ("/help for commands · ctrl-d to exit", OVERLAY),
    ("", TEXT),
]
add_frame(base_lines)
add_frame(base_lines)  # double for emphasis at start

# ---- act 2: type the prompt ----------------------------------------------
for i in range(0, len(PROMPT) + 1, 3):
    typed = PROMPT[:i] + ("▌" if i < len(PROMPT) else "")
    add_frame(base_lines + [(typed, TEXT)])

# pause on full prompt
for _ in range(4):
    add_frame(base_lines + [(PROMPT, TEXT), ("", TEXT)])

# ---- act 3: agent thinks ------------------------------------------------
thinking = base_lines + [
    (PROMPT, TEXT),
    ("", TEXT),
    ("I'll create the file and run it.", TEXT),
    ("", TEXT),
    ("  turn 0 · $0.0067 · in 348 · out 110 · cache_w 1080", OVERLAY),
]
for _ in range(3):
    add_frame(thinking)

# ---- act 4: tool call 1 — Write -----------------------------------------
write_call = thinking + [
    ("● Write(hello.py)", GREEN),
]
add_frame(write_call)

write_done = write_call + [
    ("  ⎿  wrote 85 chars to hello.py", TEXT),
]
for _ in range(3):
    add_frame(write_done)

# ---- act 5: turn 2 — Bash ------------------------------------------------
bash_pre = write_done + [
    ("", TEXT),
    ("  turn 1 · $0.0028 · in 482 · out 165 · cache_r 1080 · cache_w 1425", OVERLAY),
]
add_frame(bash_pre)

bash_call = bash_pre + [
    ("● Bash$ python hello.py", GREEN),
]
add_frame(bash_call)

bash_done = bash_call + [
    ("  ⎿  agent-zero-to-hero is alive", TEXT),
]
for _ in range(3):
    add_frame(bash_done)

# ---- act 6: final -------------------------------------------------------
final = bash_done + [
    ("Done — created `hello.py` with a `hello()` function and executed it.", TEXT),
    ("", TEXT),
    ("  turn 2 · $0.0026 · in 690 · out 191 · cache_r 2160 · cache_w 1770", OVERLAY),
    ("", TEXT),
    ("$0.0122 · in 690 out 191 cache_r 2160 cache_w 1770", BLUE),
    ("", TEXT),
    ("> ▌", TEXT),
]
for _ in range(8):
    add_frame(final)


# ---- compose ------------------------------------------------------------
def main():
    out_dir = Path(__file__).resolve().parent.parent / "assets"
    out_dir.mkdir(exist_ok=True)
    gif_path = out_dir / "launch.gif"

    print(f"rendering {len(frames)} frames...")

    # save all frames as PNGs first, then ffmpeg → GIF
    tmp = Path("/tmp/agent_demo_frames")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    for i, frame in enumerate(frames):
        frame.save(tmp / f"frame_{i:04d}.png")

    # use PIL's built-in GIF encoder for simplicity
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=120,        # ms per frame ≈ 8 fps
        loop=0,
        optimize=True,
    )
    size_kb = gif_path.stat().st_size // 1024
    print(f"  wrote {gif_path} ({size_kb} KB, {len(frames)} frames)")


if __name__ == "__main__":
    main()
