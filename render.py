import math

from rich.text import Text

from capture import metrics

BAR_WIDTH = 24
BLOCKS = " ▏▎▍▌▋▊▉"


def visible(token: str) -> str:
    return "".join(
        c if c.isprintable() or c in "\n\t" else repr(c)[1:-1] for c in token
    )


def fmt(value) -> str:
    if value is None:
        return "—"
    if math.isinf(value):
        return "inf"
    return f"{value:.2f}"


def bar(prob: float) -> str:
    cells = min(max(prob, 0.0), 1.0) * BAR_WIDTH
    full = int(cells)
    part = BLOCKS[int((cells - full) * 8)].strip()
    return ("█" * full + part).ljust(BAR_WIDTH)


DIM = "#6e6e6e"
FAINT = "#3a3a3a"
BRIGHT = "#ffffff"


def alt_line(chosen: bool, token: str, prob: float, current: bool = False) -> Text:
    line = Text(style="on #2e2e2e" if current else "")
    line.append("› " if chosen else "  ", style=BRIGHT)
    line.append(f"{repr(token)[:14]:<14} ", style=BRIGHT if chosen else "")
    line.append(bar(prob), style="#d8d8d8" if chosen else "#5a5a5a")
    line.append(f" {prob * 100:5.1f}%", style=BRIGHT if chosen else DIM)
    return line


def stat(text: Text, label: str, value: str) -> None:
    text.append(f"{label} ", style=DIM)
    text.append(f"{value:<8}")


def token_row(rec: dict) -> tuple:
    m = metrics(rec)
    other = next((a for a in rec["top_probs"] if a["token"] != rec["token"]), None)
    other_text = Text(f"{repr(other['token'])} {other['prob']:.2f}" if other else "—", style=DIM)
    return (
        Text(str(rec["pos"]), style=DIM, justify="right"),
        Text(repr(rec["token"])),
        Text(f"{rec['prob']:.2f}", justify="right"),
        Text(fmt(m["margin"]), style=DIM, justify="right"),
        other_text,
    )


def output_text(run: dict, selected: int) -> Text:
    text = Text(visible(run["meta"].get("prompt", "")), style=DIM)
    for i, rec in enumerate(run["records"]):
        token = visible(rec["token"])
        if i == selected:
            text.append(token.replace("\n", "↵\n") or "∅", style=f"#000000 on {BRIGHT}")
        else:
            text.append(token)
    return text


def alt_count(rec: dict) -> int:
    return len(rec["top_probs"]) + (metrics(rec)["rank"] is None)


def alts_text(rec: dict, cursor: int = 0) -> Text:
    m = metrics(rec)
    text = Text()
    text.append(f"pos {rec['pos']}  ", style=DIM)
    text.append(repr(rec["token"]), style=BRIGHT)
    text.append("\n\n")
    for i, alt in enumerate(rec["top_probs"]):
        chosen = alt["token"] == rec["token"]
        text.append_text(alt_line(chosen, alt["token"], alt["prob"], i == cursor))
        text.append("\n")
    if m["rank"] is None:
        last = len(rec["top_probs"]) == cursor
        text.append_text(alt_line(True, rec["token"], rec["prob"], last))
        text.append("  outside top-N\n", style=DIM)
    rank = "outside" if m["rank"] is None else str(m["rank"])
    text.append("\n")
    stat(text, "prob", fmt(rec["prob"]))
    stat(text, "surprise", fmt(m["surprise"]))
    stat(text, "margin", fmt(m["margin"]))
    text.append("\n")
    stat(text, "entropy", fmt(m["entropy"]))
    stat(text, "missing", fmt(m["missing"]))
    stat(text, "rank", rank)
    return text


def run_label(run: dict, prefix: str) -> Text:
    prompt = run["meta"].get("prompt", "").replace("\n", " ")
    text = Text(f"{prefix} ", style=DIM)
    text.append(prompt)
    return text
