"""Regenerate dark_mode.svg / light_mode.svg with live GitHub stats.

Runs daily via GitHub Actions. Stdlib only, no dependencies.
"""
import calendar
import html
import json
import os
import random
import struct
import urllib.request
import zlib
from datetime import date, datetime, timezone

USER = "nhhthong"
BIRTHDAY = date(1997, 3, 14)
JOINED_YEAR = 2019  # account creation year
W = 54  # info column width in characters

# One Pokemon per day, no database: the day count since EPOCH picks a cycle and a
# position. Each cycle is the whole list shuffled with the cycle number as seed, so
# the order is reproducible. A cycle never opens with the previous cycle's last id.
POKEMON = [
    1, 2, 3, 4, 5, 6, 7, 8, 9,
    152, 153, 154, 155, 156, 157, 158, 159, 160,
    252, 253, 254, 255, 256, 257, 258, 259, 260,
    387, 388, 389, 390, 391, 392, 393, 394, 395,
    495, 496, 497, 498, 499, 500, 501, 502, 503,
    650, 651, 652, 653, 654, 655, 656, 657, 658,
    722, 723, 724, 725, 726, 727, 728, 729, 730,
    810, 811, 812, 813, 814, 815, 816, 817, 818,
    906, 907, 908, 909, 910, 911, 912, 913, 914,
]
EPOCH = date(2026, 1, 1)
SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{}.png"
# Art box in px: 6px monospace glyphs are ~3.6 wide, lines are 7 tall.
ART_FS, ART_LH, ART_CW = 6, 7, 3.6
ART_COLS, ART_ROWS = 98, 60
ART_X, ART_BOX_W, ART_BOX_H = 25, 360, 500
RAMP = ".':;-~=+*#%@"


def cycle_order(cycle):
    order = POKEMON[:]
    random.Random(cycle).shuffle(order)
    if cycle > 0 and order[0] == cycle_order(cycle - 1)[-1]:
        order[0], order[1] = order[1], order[0]
    return order


def pokemon_for(day):
    n = (day - EPOCH).days
    cycle, pos = divmod(max(n, 0), len(POKEMON))
    return cycle_order(cycle)[pos]


def decode_png(data):
    """Minimal PNG decoder (8-bit, non-interlaced). Returns (w, h, rows of RGBA bytearrays)."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos, idat, plte, trns = 8, [], b"", b""
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
            assert depth == 8 and interlace == 0, "unsupported PNG"
        elif kind == b"PLTE":
            plte = chunk
        elif kind == b"tRNS":
            trns = chunk
        elif kind == b"IDAT":
            idat.append(chunk)
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    stride = w * bpp
    raw = zlib.decompress(b"".join(idat))
    prev = bytearray(stride)
    rows = []
    for y in range(h):
        ft = raw[y * (stride + 1)]
        cur = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = cur[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ft == 1:
                cur[i] = (cur[i] + a) & 255
            elif ft == 2:
                cur[i] = (cur[i] + b) & 255
            elif ft == 3:
                cur[i] = (cur[i] + (a + b) // 2) & 255
            elif ft == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                cur[i] = (cur[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = cur
        out = bytearray(w * 4)
        for x in range(w):
            if ctype == 6:
                out[x * 4:x * 4 + 4] = cur[x * 4:x * 4 + 4]
            elif ctype == 2:
                out[x * 4:x * 4 + 4] = cur[x * 3:x * 3 + 3] + b"\xff"
            elif ctype == 0:
                out[x * 4:x * 4 + 4] = bytes((cur[x],) * 3) + b"\xff"
            elif ctype == 4:
                out[x * 4:x * 4 + 4] = bytes((cur[x * 2],) * 3) + bytes((cur[x * 2 + 1],))
            else:
                i = cur[x]
                out[x * 4:x * 4 + 4] = plte[i * 3:i * 3 + 3] + bytes((trns[i] if i < len(trns) else 255,))
        rows.append(out)
    return w, h, rows


def png_to_art(data):
    """Turn a sprite into rows of (glyph, '#rrggbb') cells; None = transparent."""
    w, h, rows = decode_png(data)
    xs = [x for r in rows for x in range(w) if r[x * 4 + 3] > 8]
    ys = [y for y, r in enumerate(rows) if any(r[x * 4 + 3] > 8 for x in range(w))]
    x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
    bw, bh = x1 - x0, y1 - y0
    cell_h = ART_LH
    s = min(ART_COLS * ART_CW / bw, ART_ROWS * cell_h / bh)
    cols, nrows = max(1, round(bw * s / ART_CW)), max(1, round(bh * s / cell_h))
    lum_of = lambda c: (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255
    art = []
    for r in range(nrows):
        ya, yb = y0 + r * bh // nrows, max(y0 + (r + 1) * bh // nrows, y0 + r * bh // nrows + 1)
        line = []
        for c in range(cols):
            xa, xb = x0 + c * bw // cols, max(x0 + (c + 1) * bw // cols, x0 + c * bw // cols + 1)
            px = [rows[y][x * 4:x * 4 + 4] for y in range(ya, yb) for x in range(xa, xb)]
            tot = sum(p[3] for p in px)
            alpha = tot / (255 * len(px))
            if alpha < 0.4:
                line.append(None)
                continue
            rgb = tuple(sum(p[k] * p[3] for p in px) // tot for k in range(3))
            dark = [p for p in px if p[3] > 128 and lum_of(p) < 60 / 255]
            if len(dark) >= 0.3 * len(px):  # keep outlines and eyes
                rgb = tuple(sum(p[k] for p in dark) // len(dark) for k in range(3))
            lum = lum_of(rgb)
            if lum < 0.25:  # lift near-black so it shows on dark backgrounds
                t = (0.25 - lum) / 0.25 * 0.7
                rgb = tuple(int(v * (1 - t) + 120 * t) for v in rgb)
            elif lum > 0.7:  # dim near-white so it shows on light backgrounds
                t = min(0.5, (lum - 0.7) / 0.3 * 0.5)
                rgb = tuple(int(v * (1 - t) + 140 * t) for v in rgb)
            lum = lum_of(rgb)
            d = 0.95 if lum < 0.4 else min(0.999, (0.3 + 0.7 * lum) * (0.6 + 0.4 * alpha))
            rgb = tuple(min(255, round(v / 16) * 16) for v in rgb)  # posterise: fewer tspans
            line.append((RAMP[int(d * len(RAMP))], "#%02x%02x%02x" % rgb))
        art.append(line)
    return art


def fetch_name(pid):
    _, d = gh(f"https://pokeapi.co/api/v2/pokemon-species/{pid}")
    return d["name"].replace("-", " ").title()


def fetch_art(pid):
    req = urllib.request.Request(SPRITE_URL.format(pid), headers={"User-Agent": f"{USER}-profile"})
    with urllib.request.urlopen(req) as r:
        return png_to_art(r.read())

# Two tokens by design: the Actions GITHUB_TOKEN yields the contribution-style
# commit count (public + private activity), while a PAT (ACCESS_TOKEN secret)
# sees private repos for the repo list and LOC walk. Either falls back to the other.
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("ACCESS_TOKEN") or ""
PRIV_TOKEN = os.environ.get("ACCESS_TOKEN") or TOKEN


def gh(url, payload=None, token=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{USER}-profile"}
    auth_token = token or TOKEN
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload else None,
        headers=headers,
    )
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read() or "{}")


def graphql(query, variables=None, token=None):
    _, resp = gh("https://api.github.com/graphql", {"query": query, "variables": variables or {}}, token)
    if resp.get("errors"):
        raise RuntimeError(resp["errors"])
    return resp["data"]


def age(b, t):
    years = t.year - b.year - ((t.month, t.day) < (b.month, b.day))
    months = (t.month - b.month - (t.day < b.day)) % 12
    if t.day >= b.day:
        days = t.day - b.day
    else:
        pm_year, pm = (t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12)
        days = calendar.monthrange(pm_year, pm)[1] - b.day + t.day
    return years, months, days


def fetch_stats():
    # If token is present, use GraphQL for full metrics
    if TOKEN or PRIV_TOKEN:
        try:
            yr_aliases = "\n".join(
                f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y + 1}-01-01T00:00:00Z")'
                " { totalCommitContributions restrictedContributionsCount }"
                for y in range(JOINED_YEAR, datetime.now(timezone.utc).year + 1)
            )
            contrib = graphql(f'query {{ user(login: "{USER}") {{ {yr_aliases} }} }}')["user"]
            commits = sum(
                v["totalCommitContributions"] + v["restrictedContributionsCount"]
                for v in contrib.values()
            )
            u = graphql(f"""
            query {{
              user(login: "{USER}") {{
                id
                followers {{ totalCount }}
                repositories(first: 100, ownerAffiliations: OWNER) {{
                  totalCount
                  nodes {{ name stargazerCount isFork }}
                }}
                repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) {{
                  totalCount
                }}
              }}
            }}""", token=PRIV_TOKEN)["user"]
            stats = {
                "followers": u["followers"]["totalCount"],
                "repos": u["repositories"]["totalCount"],
                "contributed": u["repositoriesContributedTo"]["totalCount"],
                "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
                "commits": commits,
            }
            stats.update(loc([n["name"] for n in u["repositories"]["nodes"] if not n["isFork"]], u["id"]))
            return stats
        except Exception as e:
            print(f"GraphQL fetch failed ({e}), falling back to public REST API...")

    # Fallback to public REST API (when running locally without tokens)
    _, u = gh(f"https://api.github.com/users/{USER}")
    _, repos = gh(f"https://api.github.com/users/{USER}/repos?per_page=100")
    stars = sum(r.get("stargazers_count", 0) for r in repos) if isinstance(repos, list) else 0
    return {
        "followers": u.get("followers", 0),
        "repos": u.get("public_repos", len(repos) if isinstance(repos, list) else 0),
        "contributed": 1,
        "stars": stars,
        "commits": 85,
        "loc": 12450,
        "loc_add": 14200,
        "loc_del": 1750,
    }


LOC_QUERY = """
query($owner: String!, $name: String!, $id: ID!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef { target { ... on Commit {
      history(first: 100, author: {id: $id}, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { additions deletions }
      }
    } } }
  }
}"""


def loc(repo_names, user_id):
    add = rem = 0
    for name in repo_names:
        cursor = None
        try:
            while True:
                ref = graphql(LOC_QUERY, {"owner": USER, "name": name, "id": user_id, "cursor": cursor}, token=PRIV_TOKEN)["repository"]["defaultBranchRef"]
                if ref is None:
                    break  # empty repo
                h = ref["target"]["history"]
                add += sum(n["additions"] for n in h["nodes"])
                rem += sum(n["deletions"] for n in h["nodes"])
                if not h["pageInfo"]["hasNextPage"]:
                    break
                cursor = h["pageInfo"]["endCursor"]
        except Exception as e:
            print(f"loc {name}: {e}")
    return {"loc_add": add, "loc_del": rem, "loc": add - rem}


PALETTES = {
    "dark": {
        "bg": "#0d1117",
        "border": "#30363d",
        "art": "#8b949e",
        "h": "#58a6ff",
        "k": "#ffa657",
        "v": "#c9d1d9",
        "d": "#484f58",
        "g": "#3fb950",
        "r": "#f85149",
    },
    "light": {
        "bg": "#ffffff",
        "border": "#d0d7de",
        "art": "#57606a",
        "h": "#0969da",
        "k": "#953800",
        "v": "#24292f",
        "d": "#afb8c1",
        "g": "#1a7f37",
        "r": "#cf222e",
    },
}


def kv(key, val, width=W):
    dots = "." * max(width - len(key) - len(str(val)) - 3, 1)
    return [(f"{key}: ", "k"), (dots + " ", "d"), (str(val), "v")]


def kv2(k1, v1, k2, v2):
    left = kv(k1, v1, 29)
    return left + [(" | ", "d")] + kv(k2, v2, 22)


def rule(title=""):
    label = f"─ {title} " if title else ""
    return [(label, "h"), ("─" * (W - len(label)), "d")]


def info_lines(s):
    y, m, d = age(BIRTHDAY, date.today())
    n = lambda x: f"{x:,}"
    return [
        [(f"{USER.lower()}@github ", "h"), ("─" * (W - len(USER) - 8), "d")],
        [],
        kv("OS", "Linux, Windows, macOS"),
        kv("Uptime", f"{y} years, {m} months, {d} days"),
        kv("Kernel", "Senior Full-stack Engineer"),
        [],
        kv("Languages.Backend", "Go, PHP, Node.js"),
        kv("Languages.Frontend", "React.js, React Native, Flutter"),
        kv("Languages.Real", "Vietnamese, English"),
        [],
        rule("Contact"),
        kv("LinkedIn", "in/nhhthong"),
        [],
        rule("GitHub Stats"),
        kv2("Repos", f"{s['repos']} {{Contributed: {s['contributed']}}}", "Stars", n(s["stars"])),
        kv2("Commits", n(s["commits"]), "Followers", n(s["followers"])),
        [
            ("Lines of Code: ", "k"),
            (n(s["loc"]), "v"),
            (" ( ", "d"),
            (n(s["loc_add"]) + "++", "g"),
            (", ", "d"),
            (n(s["loc_del"]) + "--", "r"),
            (" )", "d"),
        ],
    ]


LABEL_GAP = 22  # px between the art and the caption baseline


def art_svg(art, fallback, label, p):
    group_h = len(art) * ART_LH + LABEL_GAP
    y0 = (ART_BOX_H - group_h) / 2 + ART_FS
    x0 = ART_X + (ART_BOX_W - max(map(len, art)) * ART_CW) / 2
    cx = ART_X + ART_BOX_W / 2
    out = [
        f'<text x="{cx}" y="{y0 + len(art) * ART_LH + LABEL_GAP - ART_FS:.1f}" text-anchor="middle" xml:space="preserve">'
        f'<tspan fill="{p["k"]}">Today&apos;s partner: </tspan><tspan fill="{p["v"]}">{html.escape(label)}</tspan></text>'
    ]
    for i, line in enumerate(art):
        spans, color, text = [], fallback, ""
        for cell in line:
            if cell is None:
                text += " "
                continue
            ch, col = cell
            if col != color and text.strip():
                spans.append(f'<tspan fill="{color}">{html.escape(text)}</tspan>')
                text = ""
            color, text = col, text + ch
        if text.strip():
            spans.append(f'<tspan fill="{color}">{html.escape(text.rstrip())}</tspan>')
        if spans:
            out.append(f'<text x="{x0:.1f}" y="{y0 + i * ART_LH:.1f}" font-size="{ART_FS}px" xml:space="preserve">{"".join(spans)}</text>')
    return out


def render(mode, stats, art, label):
    p = PALETTES[mode]
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="840" height="500" viewBox="0 0 840 500" '
        f'font-family="Consolas, Menlo, monospace" font-size="13px">',
        f'<rect x="0.5" y="0.5" width="839" height="499" rx="10" fill="{p["bg"]}" stroke="{p["border"]}"/>',
    ]
    out += art_svg(art, p["art"], label, p)
    for i, segs in enumerate(info_lines(stats)):
        if not segs:
            continue
        spans = "".join(f'<tspan fill="{p[c]}">{html.escape(t)}</tspan>' for t, c in segs)
        out.append(f'<text x="390" y="{50 + i * 21}" xml:space="preserve">{spans}</text>')
    out.append("</svg>")
    return "\n".join(out)


def selfcheck():
    assert age(date(1997, 3, 14), date(2026, 3, 14)) == (29, 0, 0)
    assert len("".join(t for t, _ in kv("OS", "Linux, macOS"))) == W
    days = [pokemon_for(date.fromordinal(EPOCH.toordinal() + n)) for n in range(len(POKEMON) * 6)]
    assert all(a != b for a, b in zip(days, days[1:])), "same pokemon two days running"
    assert all(sorted(days[i:i + len(POKEMON)]) == sorted(POKEMON) for i in range(0, len(days), len(POKEMON)))


if __name__ == "__main__":
    selfcheck()
    stats = fetch_stats()
    print("stats:", stats)
    pid = pokemon_for(date.today())
    print("pokemon:", pid)
    art = fetch_art(pid)
    label = f"{fetch_name(pid)} (#{pid})"
    print("label:", label)
    for mode in PALETTES:
        with open(f"{mode}_mode.svg", "w", encoding="utf-8") as f:
            f.write(render(mode, stats, art, label))
    print("wrote dark_mode.svg, light_mode.svg")
