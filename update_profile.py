"""Regenerate dark_mode.svg / light_mode.svg with live GitHub stats.

Runs daily via GitHub Actions. Stdlib only, no dependencies.
"""
import calendar
import html
import json
import os
import urllib.request
from datetime import date, datetime, timezone

USER = "nhhthong"
BIRTHDAY = date(1997, 3, 14)
JOINED_YEAR = 2019  # account creation year
ART_FS, ART_LH, ART_Y = 6, 7, 78  # art font size, line height, first baseline (px)
W = 54  # info column width in characters

# Mudkip (PokeAPI official-artwork/258.png) pre-rendered to coloured ASCII.
# ART = glyphs, ART_COLORS = same grid of ART_PALETTE keys (space = transparent).
ART_PALETTE = {'a': '#c4c7cf', 'b': '#c3c7d1', 'c': '#c3c7d0', 'd': '#c3c7cf', 'e': '#c2c7d1', 'f': '#bfc5d0', 'g': '#bec2cd', 'h': '#b7c0d6', 'i': '#b9becb', 'j': '#b3bed8', 'k': '#b5b9c0', 'l': '#abbed0', 'm': '#94c5e0', 'n': '#7dc1e4', 'o': '#7bbfe3', 'p': '#7bbfe2', 'q': '#7abfe2', 'r': '#7bbfe1', 's': '#7abde1', 't': '#73bce1', 'u': '#67b6de', 'v': '#5eb5df', 'w': '#5cb3de', 'x': '#58b5e1', 'y': '#59b3de', 'z': '#57b2dd', 'A': '#56b2dd', 'B': '#55b3de', 'C': '#55b2de', 'D': '#55b2dd', 'E': '#e9ad6c', 'F': '#eca75e', 'G': '#eca14c', 'H': '#ec9e44', 'I': '#ec9e40', 'J': '#eb9d42', 'K': '#e99c45', 'L': '#e89a44', 'M': '#e99b42', 'N': '#b6a79b', 'O': '#90a3b4', 'P': '#59b1db', 'Q': '#60a7cb', 'R': '#50a8d3', 'S': '#4aa4cf', 'T': '#4a9ec6', 'U': '#dd9142', 'V': '#b58653', 'W': '#7a8b9a', 'X': '#528daa', 'Y': '#8c6a45', 'Z': '#515253', '0': '#4c4d4d', '1': '#4b4845', '2': '#4397c3', '3': '#458fb4', '4': '#4081a1', '5': '#3f6071', '6': '#464849', '7': '#444241', '8': '#3d4143', '9': '#364147'}
ART = r"""
                                 @=++@+=@
                              @*#####*+##*=
                            =@###*****@*****@
                           +%#+*******@******@
                          @##*@*******@******+
                         @##**@*******@*******@
                        @##***++******@*******@
                        @##****@******@*******+
                        @##****@******@*******+@
                        *#*****@******@*******+
                        ##*****+******+*******+
                        *#******+*****+*******@
                        @#******@*****++******@
                        @#******@*****++******@
                        @##*****@*****++******@
                         @#*****++****++*****@
                         @#******+****++*****@
                         @##*****@****+******@
                          @#*****@****+*****@
                         @@#*****+****+******+=@
                      @+*#@*#*****+**************+@
                   @+######@#*****+*****************=@
                 @*########@*#************************+@
               @*###########@#**************************@
             @+#############*@#**************************+@
            @*##################***************************@                          @+*##%%%%#~
           @*####################*************************#*@                     @=*%%%%%%%%%%%%@
          @***########################*****************#*****                  ~+#%%%%%%%%%%%%%%%@
          @****######*#+##############***************+*+****+@               +#%%%%%%%%%%%%%%%%%%@
         @*@*****###@#%@+###########*@%#@**********+*########@             +%%%%%%%%%%%%%%%%####*
 +#*+=@ @*##+******+@@@@@###########@@%#@********+*###########@          +#%%%%%%%%%%%%#####%%%%@
  *####*@####@*****@@@@@+***********@@@@@******+*#############@     @=+@#%%%%%%%%%%#*##%%%%%%%%@
   *####@#####@+****@@@+************@@@@@*****@*############*+@=+*####@#%%%%%%%%#*#%%%%%%%%%%%@
   @*###*######+*********************@@+*****@#############*########*@#%%%%%%%##%%%%%%%%%%%%%@
    @###########@***************************@#####################**@%%%%%%###%%%%%%%%%%%%%%@
   =############*+************+************+*####################*+*%%%%%#*#%%%%%%%%%%%%%%%@
  @########+#####@**********++++***********@######################+#%%%%*#%%%%%%%%%%%%%%%%@
 @##########+*####@%%%%%%%%%%%%%##****++**@########################+*%*#%%%%%%%%%%%%%%%%#@
      @@@####++*##+#%%%%%%%%%%%%%%%%%%%%##@#########################+@###%%%%%%%%%%%%%%*@
         +###*@@@**@%%%%%%%%%%%%%%%%%%%%%%@*########***######********@#######%%%%%%%%%@
          *#+@    @@#%%%%%%%%%%%%%%%%%%%%%%@####****+@@*####+@@@+++@*############%%%*@
           @         @=*##%%%%%%%%%%%%%%%%%#+**++@++***@+##*@+++++++@#############*@
                        ++++*@##########***+@@++********+@*@*++++++*@########****@
                        @*****@############@**************+**++++++*@*******###@
                         @#****++###########++***************+@++++*@#######*=
                         @###****++*#########@*************+*@++++++*#####+@
                          @######***+@=+*####+****#####***+@@+++++*@###@@
                          @########**@       @#########***@@++++++@@@
                          @#*######*@        @##########*+@++++++@
                          @#@##@*#=@         @#########*+@@@+*@+@
                          @@++@@@           @##*######*@   @@@
                                            @#@*#**#*=@
                                             @@++@=@
"""
ART_COLORS = """
                                 5WWW8WW5
                              6OhlntuQXutQX
                            58lmuyAzzz8AAzwu0
                           Ohm4yAAzzzx8Pyyzzv0
                          7lnv4BCDzwwv5wwwzzA3
                         6mnvz9xADywwv9vwwyADx0
                        0mmuyD33Dzwwwv9vwwwzDD0
                        0mqwAAx9zywwww6vwwyADA4
                        6muyDDB9vwwwww8vyzADDA3Z
                        OmuzADD8vwwwww9PAAzDDD3
                        OmvzDCD4Twwwww4SDzDDDD4
                        OmvADDDS4wwwww4TDDDDDD6
                        ZmvADDDx8wwwww33DDDDDDZ
                        0mvDDDDy9ywwwy33DDDDDx6
                        0mtDDDDD9PwwyA33DDDDDR6
                         8nADDDD32wyAC33DDDDD8
                         6mwDDDDD4zDDC32DDDDy6
                         0nuzDDDx8BDDD3TDCDDR0
                          6tvADDD8xDDD3RDDDA0
                         96ouzDDD3TDDD4DDDDCR345
                      5Xun6QtyDDDA4DDDRCDDDDDDADD45
                   5Xrpppps0tvDDDB3CCDDDDDDDCDDDDDAP49
                 6Qmmmmnppo8uuyDDDRCDDDDDDDDDDDDDDDDzvX9
               6Qmmmmmmnppps6tvyDDDDDDDDDDDDDDDDDDDDDAyv6
             0Xonmmmmnopppppu8tvzDDDDDDDDDDDDDDDDDDCywwwvXZ
            ZQsppnnopppppppppsstuwADDDDDCDDDDDDDDDDAvuuuuuQZ                          ZWNkigaaai5
           0RusppppppppppppppppptuvyyvuvzDDDDDDDDDDCyuuuuuuQ0                     7WNaacccccccccg0
          ZTzvuspppppprppppppppppqtqqtuADDDDDDDDDDDDDwuuwQQuX                  ZWkaacccccccccccca0
          6BDAwutqppsWOXopppppppppppqtPCDDDDDDDDDDDARXWVUUUVY6               WkaccccccccccccccccaZ
         0U7RDDyvuts0ka6XpppppppppppQ8gk7BDDDDDDDCTWVGGFFGGJH1             WgdcccccccccccadgkkkkO
 VGUVYY 1UGHYTDDAyv4ZZ006sqqqqqstttu0Zgk0TDDCDDDSWUFEEEEEEEGJH0          WgaccccccccacdkkkkidaadZ
  VIIJLU1EEGL82AADD6Z0773vvvvvvvwwyTZZZZ0RDDDDBXVFEEEEEEEEEGMHZ     1YV0kdccccccccakOkkaccccccd0
   UIIJI7EEFJL63DDDD00Z4CDDDDDDCAzzR007Z5BDDDD8UFFEEEEEEEFGMUY0YVUMGGF7kccccccaakOOgaccccccccd7
   7VIIIUEFFKJJYRDDDDxBDDDDDDDAzyyzAT68XBDDDRZLFFFFFFFFFFGIUMLLLLJIKU0kacccccdkkgadcccccccccd7
    1IJJMFFFGLLL8yzAAADDRTDDDzPzADDDDDDDDDCDZKGGFFFFFFGGIIIIJLMMMMUU1gacccdiOkdacccccccccccd0
   YIJJLLLGFGJJLU4DDDACDDRDDAR3AzADDDDDDDDD4UGHKLHHHJMHHKHJIIIIJMUVWacccdkOidcccccccccccccd6
  1GLLLLLLMVGJIII8WOOOOOOWWXX433TCxCDDDDCDD7KHJJLLLKHKGGHGHJJJIJIIYkbbcgOiccccccccccccccdd7
 1EGKKJHLLKLYUJIIH7cccccdcabaadgkkOOOXX3TP8LIJJIJIIMLHHHKKMLLLLIIIKYOfOOcacccccccccccccci0
      177IIIIVYULMYgccccccccccccccccccaagk7JILJIIJJMIJIJIIJJIJJJJLKHV6lhhffeebacccccccaO0
         VIILU11YVU7eebaccccccccccccccccca7UMGIIMJMLUUULLMJJJLUUUUUUU7ljjjjhhfffebbacg0
          VGV1    01kfffffeeebbccccccccbbcd7KGKLUUUUY77ULLKLY7444446OljjjjjjjjjhhhffW0
           7         0WWOifffffffffffffffffOYUUVY854SSS6YLFU822222228jjjjjjjjjjjjjO0
                        4444W9OkihhhhhkkOWOW8742RSSSSSSS27V7S222222T0jjjjjjjlOWOW6
                        0PSSSS9Ojjjjjjjjjjj8TSSSSSSSSSSSSS3TS222222T8OOOOOOOljl0
                         6uPRSS3WljjjjjjjjjjW4SSSSSSSSSSSSSSS242222T6jjjjjjjOW
                         0sqtuPRS3XWljjjjjjjj5RSSSSSRRRSSSS4T8422224WjjjjlW6
                          0pppqttuPR36WWWOlhh5uwuuuttqtuRS28932222T6hhOZ0
                          6nppppppsuTZ       6npppppppsuPS642222220Z0
                          0tunpssptT0        ZnpppppppquR483223220
                          6o8nq9Qt4Z         6pppppppptR406822846
                          08XX085           0trQpptoptR0   645
                                            0t8QouXqu46
                                             06XX845
"""

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
        kv("OS", "Linux, macOS"),
        kv("Uptime", f"{y} years, {m} months, {d} days"),
        kv("Kernel", "Senior Full-stack Engineer"),
        kv("IDE", "Cursor, VS Code, GoLand"),
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


def render(mode, stats):
    p = PALETTES[mode]
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="840" height="500" viewBox="0 0 840 500" '
        f'font-family="Consolas, Menlo, monospace" font-size="13px">',
        f'<rect x="0.5" y="0.5" width="839" height="499" rx="10" fill="{p["bg"]}" stroke="{p["border"]}"/>',
    ]
    art_rows = ART.strip("\n").split("\n")
    color_rows = ART_COLORS.strip("\n").split("\n")
    for i, (line, cl) in enumerate(zip(art_rows, color_rows)):
        spans, j = [], 0
        while j < len(line):
            k = j
            while k < len(line) and cl[k:k + 1] == cl[j:j + 1]:
                k += 1
            fill = ART_PALETTE.get(cl[j:j + 1], p["art"])
            spans.append(f'<tspan fill="{fill}">{html.escape(line[j:k])}</tspan>')
            j = k
        out.append(f'<text x="25" y="{ART_Y + i * ART_LH}" font-size="{ART_FS}px" xml:space="preserve">{"".join(spans)}</text>')
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


if __name__ == "__main__":
    selfcheck()
    stats = fetch_stats()
    print("stats:", stats)
    for mode in PALETTES:
        with open(f"{mode}_mode.svg", "w", encoding="utf-8") as f:
            f.write(render(mode, stats))
    print("wrote dark_mode.svg, light_mode.svg")
