"""Keeps the CorvexDevelops profile in step with its public repositories.

    python3 scripts/update.py        # run hourly by .github/workflows/update-profile.yml

- rewrites the open source table in profile/README.md, between <!-- repos:start --> and <!-- repos:end -->
- draws profile/activity.svg: the latest commits of the public repositories, animated (SMIL + CSS only)
Only public data: repository names, descriptions, commit titles and dates."""
import base64, datetime, json, os, pathlib, re, sys, urllib.request

ORG = "CorvexDevelops"
ROOT = pathlib.Path(__file__).resolve().parent.parent
CONF = json.loads((ROOT / "scripts" / "repos.json").read_text())
README = ROOT / "profile" / "README.md"
b64 = lambda p: base64.b64encode((ROOT / "scripts" / "fonts" / p).read_bytes()).decode()
FONT_CSS = (f"@font-face{{font-family:G;src:url(data:font/woff2;base64,{b64('GeistMono-Regular.woff2')}) format('woff2');font-weight:400}}"
            f"@font-face{{font-family:G;src:url(data:font/woff2;base64,{b64('GeistMono-Medium.woff2')}) format('woff2');font-weight:500}}"
            "text{font-family:G,ui-monospace,Menlo,monospace;white-space:pre}")
ESC = lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
OK, WEB = "#5BE49B", "#7FA7FF"


def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Accept": "application/vnd.github+json", "User-Agent": "corvex-profile"})
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok: req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def day(iso): return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d %b %Y").lstrip("0")


def collect():
    repos = [r for r in api(f"/orgs/{ORG}/repos?type=public&per_page=100") if not r["archived"] and not r["private"]]
    shown = [r for r in repos if r["name"] not in CONF["hide"] and "hide" not in (r.get("topics") or [])]
    order = {n: i for i, n in enumerate(CONF["order"])}
    shown.sort(key=lambda r: (order.get(r["name"], 99), r["name"].lower()))
    commits = []
    for r in repos:
        if r["name"] in CONF.get("no_activity", [".github"]): continue  # the profile's own updates and uploads are not news
        try:
            for c in api(f"/repos/{ORG}/{r['name']}/commits?per_page=5"):
                commits.append({"repo": CONF.get("alias", {}).get(r["name"], r["name"]), "sha": c["sha"][:7], "msg": c["commit"]["message"].split("\n")[0], "date": c["commit"]["author"]["date"]})
        except Exception as e:
            print("commits", r["name"], e, file=sys.stderr)
    commits.sort(key=lambda c: c["date"], reverse=True)
    return shown, commits[:8], sum(r["stargazers_count"] for r in repos)


def table(shown):
    rows = ["| Repository | What it is | Updated |", "|---|---|---|"]
    for r in shown:
        text = (CONF["text"].get(r["name"]) or r.get("description") or "New repository.").replace("|", "\\|")
        new = " <sup>new</sup>" if r["name"] not in CONF["text"] else ""
        rows.append(f"| [**{r['name']}**]({r['html_url']}){new} | {text} | {day(r['pushed_at'])} |")
    return "\n".join(rows)


def activity(commits, n_repos, stars):
    W, top, LH = 880, 92, 24
    rows = []
    for i, c in enumerate(commits):
        y = top + i * LH
        msg = c["msg"] if len(c["msg"]) <= 54 else c["msg"][:53] + "…"
        rows.append(f"""<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{1.2 + i * .2:.2f}s" dur=".3s" fill="freeze"/>
<animateTransform attributeName="transform" type="translate" from="-8 0" to="0 0" begin="{1.2 + i * .2:.2f}s" dur=".3s" fill="freeze"/>
<text x="24" y="{y}" style="font-size:12px"><tspan fill="#F5B041">{ESC(c["sha"])}</tspan>  <tspan fill="{WEB}">{ESC(c["repo"][:20].ljust(20))}</tspan> <tspan fill="#d6d6d6">{ESC(msg)}</tspan></text>
<text x="{W - 24}" y="{y}" style="font-size:11px" fill="#666" text-anchor="end">{ESC(day(c["date"]))}</text></g>""")
    if not rows:
        rows.append(f'<text x="24" y="{top}" fill="#888" style="font-size:12px">no public commits yet</text>')
    H = top + max(1, len(commits)) * LH + 40
    cmd = "git log --org CorvexDevelops --public"
    cw = 13 * .6
    steps = ";".join(f"{k * cw:.1f}" for k in range(len(cmd) + 1))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Latest public commits of CorvexDevelops, updated {stamp}">
<style>{FONT_CSS} .cur{{animation:b 1s steps(1) infinite}} @keyframes b{{50%{{opacity:0}}}} @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>
<defs><clipPath id="ty"><rect x="150" y="44" height="22" width="0"><animate attributeName="width" values="{steps}" calcMode="discrete" begin=".3s" dur="{len(cmd) * .035:.2f}s" fill="freeze"/></rect></clipPath></defs>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="#0A0A0A" stroke="#222"/>
<path d="M0 32.5H{W}" stroke="#1C1C1C"/><g fill="#2a2a2a"><circle cx="22" cy="16" r="5"/><circle cx="40" cy="16" r="5"/><circle cx="58" cy="16" r="5"/></g>
<text x="{W / 2}" y="20" fill="#666" text-anchor="middle" style="font-size:11px">live activity · refreshed every hour by GitHub Actions</text>
<g transform="translate({W - 74} 9)"><rect width="58" height="15" rx="3" fill="#111" stroke="#2a2a2a"/><circle cx="10" cy="7.5" r="3" fill="{OK}"><animate attributeName="opacity" values="1;.25;1" dur="1.4s" repeatCount="indefinite"/></circle><text x="18" y="11" fill="#9a9a9a" style="font-size:8.5px">LIVE</text></g>
<text x="24" y="60" style="font-size:13px"><tspan fill="{OK}">guest@corvex</tspan><tspan fill="#777">:</tspan><tspan fill="{WEB}">~</tspan><tspan fill="#777">$</tspan></text>
<text x="150" y="60" fill="#fff" style="font-size:13px" clip-path="url(#ty)">{cmd}</text>
{"".join(rows)}
<text x="24" y="{H - 14}" fill="#555" style="font-size:10px">{n_repos} public repositories · {stars} stars · updated {stamp}</text>
<rect class="cur" x="{W - 32}" y="{H - 25}" width="8" height="14" fill="#fff"/>
</svg>"""


def main():
    shown, commits, stars = collect()
    text = README.read_text()
    new, n = re.subn(r"<!-- repos:start -->.*?<!-- repos:end -->", f"<!-- repos:start -->\n{table(shown)}\n<!-- repos:end -->", text, flags=re.S)
    if not n: sys.exit("profile/README.md is missing <!-- repos:start --> / <!-- repos:end -->")
    README.write_text(new)
    (ROOT / "profile" / "activity.svg").write_text(activity(commits, len(shown), stars))
    print(f"{len(shown)} repositories, {len(commits)} commits")


if __name__ == "__main__":
    main()
