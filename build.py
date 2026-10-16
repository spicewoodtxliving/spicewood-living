#!/usr/bin/env python3
"""Build the Spicewood Living site.

Edit content in:
  data/weeks/YYYY-MM-DD.json   one file per Monday roundup (newest = current week)
  data/businesses.json         Local Businesses listings
  src/pages/*.html             page sections ({{root}} = path back to the site root)
  src/layout.html              header, footer, <head>
  assets/site.css, site.js     shared styles and behavior

Then run:  python3 build.py            -> writes the live site into the repo root
           python3 build.py --preview  -> also writes preview/ for the claude.ai preview
"""
import glob, html, json, os, re, shutil, sys
from datetime import date

SITE = "https://spicewoodtxliving.com"
ROOT = os.path.dirname(os.path.abspath(__file__))
E = lambda s: html.escape(str(s or ""), quote=True)

def read(p): return open(os.path.join(ROOT, p), encoding="utf-8").read()
def write(p, s):
    p = os.path.join(ROOT, p); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(s)
def nice(d): return f"{d:%B} {d.day}, {d.year}"

NAV = [("index.html", "home", "Home"), ("this-week.html", "week", "This Week"),
       ("local-businesses.html", "directory", "Local Businesses"),
       ("moving-to-spicewood.html", "moving", "Moving Here"),
       ("advertise.html", "advertise", "Advertise"), ("newsletter.html", "newsletter", "Newsletter")]

PAGES = {
 "home": ("index.html", "home.html", "Spicewood Living | Spicewood, TX News, Events & Local Guide",
          "What's happening in Spicewood, Texas: this week's events and local news, Spicewood businesses, and a guide to moving to Spicewood and Lake Travis."),
 "week": ("this-week.html", "this-week.html", "This Week in Spicewood, TX: Events & Local News | Spicewood Living",
          "Live music, events, new openings and local news in Spicewood, Texas, updated every Monday."),
 "directory": ("local-businesses.html", "local-businesses.html", "Spicewood, TX Local Businesses: Wineries, Breweries & More | Spicewood Living",
          "Spicewood, Texas wineries, breweries, distilleries, restaurants, shops and parks along Hwy 71 and Lake Travis."),
 "moving": ("moving-to-spicewood.html", "moving-to-spicewood.html", "Moving to Spicewood, TX: Schools, Neighborhoods & What to Know | Spicewood Living",
          "Thinking about moving to Spicewood, Texas? School districts, neighborhoods, septic and water, and a first-month checklist."),
 "advertise": ("advertise.html", "advertise.html", "Advertise Your Spicewood Business | Spicewood Living",
          "Get your Spicewood, Texas business listed for free, or reach locals and newcomers with a Featured spot."),
 "newsletter": ("newsletter.html", "newsletter.html", "This Week in Spicewood Newsletter | Spicewood Living",
          "Get This Week in Spicewood every Monday: new openings, live music, and local news. Short, local, and free."),
}
ORDER = ["home", "week", "directory", "moving", "advertise", "newsletter"]

def nav_html(page, root):
    return "".join(f'<a href="{root}{href}"' + (' aria-current="page"' if key == page else "") + f">{label}</a>"
                   for href, key, label in NAV)

def pager(page, root):
    if page == "home": return ""
    i = ORDER.index(page)
    prev = NAV[i - 1]; nxt = NAV[i + 1] if i + 1 < len(NAV) else None
    s = f'<nav class="pager" aria-label="Page navigation"><a href="{root}{prev[0]}">← {prev[2]}</a>'
    if nxt: s += f'<a href="{root}{nxt[0]}">{nxt[2]} →</a>'
    return s + "</nav>"

def sources(lst, cls=""):
    return " · ".join(f'<a{cls} href="{E(x["url"])}" target="_blank" rel="noopener">{E(x["name"])}</a>' for x in lst)

def render_lead(L):
    ps = "".join(f"\n      <p>{E(p)}</p>" for p in L["paragraphs"])
    return (f'<article class="lead-story">\n      <span class="tag">{E(L["tag"])}</span>\n      <h2 style="font-size:clamp(1.6rem,3.5vw,2.1rem)">{E(L["headline"])}</h2>{ps}\n'
            f'      <p class="src">Sources: {sources(L["sources"])}</p>\n    </article>')

def render_news(items):
    return "\n        ".join(
        f'<article>\n          <span class="label">{E(n["label"])}</span>\n          <h3 style="font-family:var(--display);font-size:1.25rem;line-height:1.2">{E(n["headline"])}</h3>\n'
        f'          <p>{E(n["body"])}</p>\n          <span class="src">{sources(n["sources"], " class=\"src\"")}</span>\n        </article>' for n in items)

def render_events(evts):
    out = []
    for e in sorted(evts, key=lambda x: x["date"]):
        d = date.fromisoformat(e["date"])
        where = e["venue"] + (f' · {e["time"]}' if e.get("time") else "")
        out.append(f'<li data-date="{E(e["date"])}"><div class="date"><span class="mo">{d:%b} · {d:%a}</span><span class="dy">{d.day}</span></div>'
                   f'<div class="ev"><h4>{E(e["title"])}</h4><p>{E(where)}</p><a class="src" href="{E(e["url"])}" target="_blank" rel="noopener">Details</a></div></li>')
    return "\n          ".join(out)

def events_jsonld(evts):
    data = [{"@context": "https://schema.org", "@type": "Event", "name": e["title"], "startDate": e["date"],
             "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "eventStatus": "https://schema.org/EventScheduled",
             "location": {"@type": "Place", "name": e["venue"], "address": {"@type": "PostalAddress", "addressLocality": "Spicewood", "addressRegion": "TX", "addressCountry": "US"}},
             "url": e["url"]} for e in evts]
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>" if data else ""

def build(preview=False):
    weeks = sorted(glob.glob(os.path.join(ROOT, "data/weeks/*.json")))
    weeks = [(date.fromisoformat(os.path.basename(p)[:10]), json.load(open(p, encoding="utf-8"))) for p in weeks]
    cur_d, cur = weeks[-1]
    biz = json.load(open(os.path.join(ROOT, "data/businesses.json"), encoding="utf-8"))
    layout = read("src/layout.html")
    outputs = {}

    def page(page_key, out, body, title, desc, root="", jsonld=""):
        if page_key != "home":
            cls = ' class="newsletter"' if page_key == "newsletter" else ""
            body = f'<section{cls}>\n{body}\n  <div class="wrap">{pager(page_key, root)}</div>\n</section>'
        doc = layout
        for k, v in {"title": E(title), "description": E(desc), "canonical": f"{SITE}/{'' if out == 'index.html' else out}",
                     "jsonld": jsonld, "nav": nav_html(page_key, root), "page": page_key, "body": body}.items():
            doc = doc.replace("{{" + k + "}}", v)
        outputs[out] = doc.replace("{{root}}", root)

    def past_list(exclude, root):
        items = [f'<li><a href="{root}weeks/{d.isoformat()}.html">Week of {nice(d)}</a></li>' for d, _ in reversed(weeks) if d != exclude]
        return '<ul class="past-weeks">' + "".join(items) + "</ul>" if items else '<p class="empty">The archive starts this week.</p>'

    def week_body(d, w, root, live, heading, permalink):
        b = read("src/pages/this-week.html")
        b = b.replace("{{week_label}}", f"Week of {nice(d)}").replace("{{week_heading}}", E(heading))
        b = b.replace("{{lead}}", render_lead(w["lead"]) + (f'\n    <p class="permalink"><a href="{root}weeks/{d.isoformat()}.html">Permanent link to this week</a></p>' if permalink else ""))
        b = b.replace("{{events}}", "\n          " + render_events(w["events"]) + "\n        ")
        b = b.replace('id="events"', f'id="events" data-live="{1 if live else 0}"')
        b = b.replace("{{news}}", render_news(w["news"]))
        b = b.replace("{{past_weeks}}", past_list(d, root))
        return b

    for key in ORDER:
        out, src, title, desc = PAGES[key]
        if key == "week":
            body = week_body(cur_d, cur, "", True, "What's new around town", True)
            page(key, out, body, title, desc, jsonld=events_jsonld(cur["events"])); continue
        body = read("src/pages/" + src)
        if key == "home":
            body = body.replace("{{week_label}}", f"Week of {nice(cur_d)}").replace("{{teaser}}", E(cur["teaser"])).replace("{{biz_count}}", str(len(biz)))
        if key == "directory":
            cats = ["All"] + sorted({b["category"] for b in biz}, key=[b["category"] for b in biz].index)
            body = body.replace("{{chips}}", "".join(f'<button type="button" class="chip" aria-pressed="{str(c == "All").lower()}" data-c="{E(c)}">{E(c)}</button>' for c in cats))
            body = body.replace("{{listings}}", "\n      " + "\n      ".join(
                f'<div class="biz" data-cat="{E(b["category"])}"><span class="cat">{E(b["category"])}</span><h4>{E(b["name"])}</h4><p>{E(b["description"])}</p><span class="addr">{E(b["address"])}</span></div>' for b in biz) + "\n    ")
        page(key, out, body, title, desc)

    for d, w in weeks:
        body = week_body(d, w, "../", False, f"This Week in Spicewood: {nice(d)}", False)
        page("week", f"weeks/{d.isoformat()}.html", body, f"This Week in Spicewood: {nice(d)} | Spicewood Living",
             f"Events, openings and local news in Spicewood, Texas for the week of {nice(d)}.", root="../", jsonld=events_jsonld(w["events"]))

    for out, doc in outputs.items(): write(out, doc)
    today = date.today().isoformat()
    urls = [f"{SITE}/"] + [f"{SITE}/{PAGES[k][0]}" for k in ORDER[1:]] + [f"{SITE}/weeks/{d.isoformat()}.html" for d, _ in weeks]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\nDisallow: /preview/\nSitemap: {SITE}/sitemap.xml\n")

    if preview:
        prev = os.path.join(ROOT, "preview"); shutil.rmtree(prev, ignore_errors=True)
        for out, doc in outputs.items():
            doc = doc.replace('href="index.html"', 'href="./"').replace('href="../index.html"', 'href="../"')
            if out == "index.html":  # the claude.ai preview adds its own page skeleton
                doc = re.sub(r"^<!doctype html>\s*<html[^>]*>\s*<head>\s*", "", doc)
                doc = re.sub(r"</head>\s*<body[^>]*>", "", doc).replace("</body>\n</html>", "")
            if out == "index.html": doc = re.sub(r"<title>.*?</title>", "<title>Spicewood Living</title>", doc, count=1)
            write("preview/" + out, doc)
        for f in ["assets/site.css", "assets/site.js", "logo-white.png", "logo-color.png", "hero-sunset.jpg", "madison-flyer-v3.jpg"]:
            os.makedirs(os.path.dirname(os.path.join(prev, f)) or prev, exist_ok=True); shutil.copy(os.path.join(ROOT, f), os.path.join(prev, f))
    print(f"Built {len(outputs)} pages (current week: {cur_d}).")

if __name__ == "__main__":
    build(preview="--preview" in sys.argv)
