"""Génère les 15 pages « familles de contrôles » du site (controles/<slug>.html), relie la page /controles à ces
pages et met à jour sitemap.xml.

    python tools/gen_familles.py [chemin du dépôt AuditM365_Licence]   (par défaut C:\\dev\\AuditM365_Licence)

Sources : catalogue (config/controls/*.yaml : titre, sévérité, référentiels, liens Microsoft) et guides de correction
(config/guides/*.yaml : temps, précaution, étapes dans le portail, vérification) de l'application ; textes publics
(« ce qui est vérifié », « valeur attendue », introductions) dans tools/familles_data.py.
Les scripts PowerShell des guides restent dans l'application (non publiés).
Le dossier tools/ est exclu des fichiers servis (.assetsignore).
"""
import glob
import html
import json
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(__file__))
from familles_data import FAMILLES, TEXTES  # noqa: E402

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\AuditM365_Licence"
BASE = "https://audit.m365intune.com"
DATE_ISO, DATE_FR = "2026-11-18", "18 novembre 2026"
SEV = {"critical": ("crit", "Critique"), "high": ("high", "Élevée"), "medium": ("med", "Moyenne"), "low": ("low", "Faible")}

e = lambda s: html.escape(str(s), quote=True)


def linkify(s):
    out = e(s)
    def rep(m):
        url = m.group(0).rstrip(".,;:)")
        rest = m.group(0)[len(url):]
        return f'<a href="{url}" rel="noopener" target="_blank">{url.replace("https://", "")}</a>{rest}'
    return re.sub(r"https?://[^\s<»]+", rep, out)


# ── sources de l'application ────────────────────────────────────────────────────────────────────────────────────
controls = []
for f in sorted(glob.glob(os.path.join(APP, "config", "controls", "*.yaml"))):
    controls += yaml.safe_load(open(f, encoding="utf-8"))["controls"]
guides = {}
for f in glob.glob(os.path.join(APP, "config", "guides", "*.yaml")):
    guides.update(yaml.safe_load(open(f, encoding="utf-8"))["guides"])
byid = {c["id"]: c for c in controls}
assert len(byid) == 86, len(byid)
assert set(TEXTES) == set(byid), set(TEXTES) ^ set(byid)
for f in FAMILLES:
    f["ids"] = [c["id"] for c in controls if c["id"].split("-")[0] in f["prefixes"]]
assert sum(len(f["ids"]) for f in FAMILLES) == 86
for cid, g in guides.items():
    assert isinstance(g.get("portal", []), list) and isinstance(g.get("verify", []), list), cid

# ── navigation et pied de page repris de la page /controles ─────────────────────────────────────────────────────
cat_path = os.path.join(SITE, "controles.html")
cat = open(cat_path, encoding="utf-8").read()
NAV = cat[cat.index("<!-- NAV -->"):cat.index("<!-- HERO -->")].strip()
FOOT = cat[cat.index('<div class="sn-foot sn-wrap"'):cat.index("<script>", cat.index('<div class="sn-foot sn-wrap"'))].strip()
assert 'href="/controles" class="on"' in NAV

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:Inter,system-ui,sans-serif;background:var(--sn-ink);color:var(--sn-on-d);line-height:1.6;-webkit-font-smoothing:antialiased;overflow-x:hidden}
.fam-hero{padding-top:48px;padding-bottom:40px;background:radial-gradient(ellipse 70% 70% at 25% -20%,rgba(47,107,255,.17),transparent 62%)}
.crumbs{font-size:14px;color:var(--sn-on-d3);margin-bottom:30px}
.crumbs a{color:var(--sn-on-d2);text-decoration:none}.crumbs a:hover{color:#fff}
.crumbs span{margin:0 8px;color:var(--sn-on-d3)}
.eyebrow{color:#9db8ff;font-weight:600;font-size:14px;margin-bottom:12px}
.fam-hero h1{font:800 clamp(30px,4vw,50px)/1.1 'Inter Tight',Inter,sans-serif;letter-spacing:-.02em;max-width:980px}
.lead{font-size:18px;color:var(--sn-on-d2);max-width:780px;margin:18px 0 24px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:28px}
.chips span{border:1px solid var(--sn-line-d);background:rgba(255,255,255,.03);border-radius:20px;padding:5px 12px;font-size:13px;color:var(--sn-on-d2)}
.chips b{color:#fff}
.cta-row{display:flex;gap:12px;flex-wrap:wrap}
.fam-body{display:grid;grid-template-columns:250px minmax(0,1fr);gap:56px;padding-top:28px;padding-bottom:64px;align-items:start}
.toc{position:sticky;top:96px;font-size:14px;max-height:calc(100vh - 120px);overflow:auto}
.toc p{font-weight:700;margin-bottom:10px}
.toc ol{list-style:none;border-left:1px solid var(--sn-line-d)}
.toc a{display:block;padding:6px 0 6px 14px;color:var(--sn-on-d3);text-decoration:none;line-height:1.35}
.toc a:hover{color:#fff}
.toc i{display:block;font:600 11px ui-monospace,Consolas,monospace;color:#7fa3ff;font-style:normal}
.ctls{max-width:900px;min-width:0}
.ctl{background:var(--sn-ink2);border:1px solid var(--sn-line-d);border-radius:16px;padding:28px 30px;margin-bottom:22px;scroll-margin-top:96px}
.ctl header{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;margin-bottom:18px}
.ctl h2{font:700 21px/1.3 'Inter Tight',Inter,sans-serif;flex:1 1 280px}
.cid{font:600 12px ui-monospace,Consolas,monospace;color:#9db8ff;background:rgba(47,107,255,.14);border-radius:6px;padding:3px 8px;white-space:nowrap}
.sev{font-size:12px;font-weight:700;border-radius:6px;padding:3px 9px;white-space:nowrap}
.sev.crit{background:rgba(239,68,68,.15);color:#f87171}.sev.high{background:rgba(245,158,11,.15);color:#fbbf24}
.sev.med{background:rgba(59,130,246,.15);color:#93c5fd}.sev.low{background:rgba(16,185,129,.15);color:#6ee7b7}
.facts{display:grid;grid-template-columns:1.4fr 1fr;gap:12px;margin-bottom:16px}
.facts div{background:rgba(255,255,255,.025);border:1px solid var(--sn-line-d);border-radius:12px;padding:14px 16px}
.facts dt{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--sn-on-d3);margin-bottom:6px}
.facts dd{color:var(--sn-on-d2);font-size:15px}
.meta{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;font-size:13px;color:var(--sn-on-d3);margin-bottom:6px}
.meta b{color:var(--sn-on-d2);font-weight:600;margin-right:6px}
.fw{border:1px solid rgba(255,255,255,.14);border-radius:6px;padding:1px 7px;font-size:12px;color:var(--sn-on-d2)}
.caution{border-left:3px solid #f59e0b;background:rgba(245,158,11,.08);padding:12px 16px;border-radius:0 10px 10px 0;color:#f1e4c8;font-size:15px;margin-top:16px}
.ctl h3{font:700 15px/1.3 Inter,sans-serif;margin:22px 0 10px}
.steps{counter-reset:s;list-style:none}
.steps li{counter-increment:s;position:relative;padding-left:38px;margin-bottom:10px;color:var(--sn-on-d2);font-size:15px}
.steps li::before{content:counter(s);position:absolute;left:0;top:1px;width:24px;height:24px;border-radius:50%;background:rgba(47,107,255,.16);color:#9db8ff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center}
.verify{list-style:none}
.verify li{position:relative;padding-left:28px;margin-bottom:8px;color:var(--sn-on-d2);font-size:15px}
.verify li::before{content:'';position:absolute;left:4px;top:7px;width:12px;height:7px;border-left:2px solid #10b981;border-bottom:2px solid #10b981;transform:rotate(-45deg)}
.ctl a{color:#9db8ff;overflow-wrap:anywhere}
.ctl li,.ctl dd,.caution,.ctl h2{overflow-wrap:anywhere}
.portal{display:inline-flex;align-items:center;gap:6px;margin-top:4px;font-size:14px;font-weight:600;text-decoration:none}
.portal:hover{text-decoration:underline}
.refs{margin-top:16px;font-size:13px;color:var(--sn-on-d3)}
.fam-cta{background:linear-gradient(135deg,rgba(47,107,255,.2),rgba(31,85,224,.06));border:1px solid rgba(47,107,255,.35);border-radius:18px;padding:32px;margin-top:34px}
.fam-cta h2{font:700 26px/1.2 'Inter Tight',Inter,sans-serif;margin-bottom:10px}
.fam-cta p{color:var(--sn-on-d2);margin-bottom:20px;max-width:680px}
.fam-others{padding-bottom:96px}
.fam-others h2{font:700 24px/1.2 'Inter Tight',Inter,sans-serif;margin-bottom:18px}
.fam-others ul{list-style:none;display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px}
.fam-others a{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:14px 16px;border:1px solid var(--sn-line-d);border-radius:12px;background:var(--sn-ink2);color:var(--sn-on-d);text-decoration:none;font-size:15px;font-weight:500;transition:border-color .2s}
.fam-others a:hover{border-color:rgba(47,107,255,.6)}
.fam-others em{font-style:normal;font-size:12px;color:#9db8ff;background:rgba(47,107,255,.12);border-radius:10px;padding:1px 9px;white-space:nowrap}
@media(max-width:1000px){.fam-body{grid-template-columns:1fr;gap:0}.toc{display:none}}
@media(max-width:640px){.facts{grid-template-columns:1fr}.ctl{padding:22px 18px}.fam-cta{padding:24px 20px}.lead{font-size:16px}}
"""


def article(cid, slug):
    c, g = byid[cid], guides.get(cid, {})
    v, a = TEXTES[cid]
    cls, lab = SEV[c["severity_default"].lower()]
    fws = "".join(f'<span class="fw">{e(x)}</span>' for x in c.get("frameworks", []))
    parts = [f'<article class="ctl" id="{cid.lower()}">',
             f'<header><span class="cid">{cid}</span><h2>{e(c["title"])}</h2><span class="sev {cls}">Sévérité {lab.lower()}</span></header>',
             f'<dl class="facts"><div><dt>Ce qui est vérifié</dt><dd>{e(v)}</dd></div><div><dt>Valeur attendue</dt><dd>{e(a)}</dd></div></dl>']
    if g.get("time"):
        parts.append(f'<p class="meta"><b>Temps estimé</b>{e(g["time"])}</p>')
    if fws:
        parts.append(f'<p class="meta"><b>Référentiels</b>{fws}</p>')
    if g.get("caution"):
        parts.append(f'<p class="caution"><strong>À savoir avant de commencer :</strong> {linkify(g["caution"])}</p>')
    if g.get("portal"):
        parts.append('<h3>Corriger dans le portail</h3><ol class="steps">' + "".join(f"<li>{linkify(s)}</li>" for s in g["portal"]) + "</ol>")
    if g.get("portal_link"):
        parts.append(f'<a class="portal" href="{e(g["portal_link"])}" rel="noopener" target="_blank">Ouvrir la page dans le portail Microsoft <span aria-hidden="true">↗</span></a>')
    if g.get("verify"):
        parts.append('<h3>Vérifier la correction</h3><ul class="verify">' + "".join(f"<li>{linkify(s)}</li>" for s in g["verify"]) + "</ul>")
    refs = [r for r in c.get("references", []) if str(r).startswith("http")]
    if refs:
        parts.append('<p class="refs">Documentation Microsoft : ' + " · ".join(
            f'<a href="{e(r)}" rel="noopener" target="_blank">{e(r.replace("https://", ""))}</a>' for r in refs) + "</p>")
    parts.append("</article>")
    return "\n".join(parts)


def page(fam):
    slug, ids, n = fam["slug"], fam["ids"], len(fam["ids"])
    url = f"{BASE}/controles/{slug}"
    sevs = [byid[i]["severity_default"].lower() for i in ids]
    chips = [f"<span><b>{n}</b> contrôles</span>"]
    for k, (_, lab) in SEV.items():
        if sevs.count(k):
            chips.append(f"<span><b>{sevs.count(k)}</b> {lab.lower()}{'s' if sevs.count(k) > 1 else ''}</span>")
    chips.append(f"<span>Mis à jour le {DATE_FR}</span>")
    toc = "".join(f'<li><a href="#{i.lower()}"><i>{i}</i>{e(byid[i]["title"])}</a></li>' for i in ids)
    others = "".join(f'<li><a href="/controles/{o["slug"]}">{e(o["nom"])}<em>{len(o["ids"])}</em></a></li>'
                     for o in FAMILLES if o is not fam)
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Accueil", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Contrôles", "item": BASE + "/controles"},
            {"@type": "ListItem", "position": 3, "name": fam["nom"], "item": url}]},
        {"@type": "TechArticle", "headline": fam["h1"], "description": fam["desc"], "inLanguage": "fr-FR",
         "url": url, "dateModified": DATE_ISO, "image": BASE + "/img/dashboard.png",
         "author": {"@id": BASE + "/#org"}, "publisher": {"@id": BASE + "/#org"},
         "isPartOf": {"@type": "WebSite", "name": "AuditM365", "url": BASE + "/"}}]}
    body = "\n".join(article(i, slug) for i in ids)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(fam["title"])}</title>
  <meta name="description" content="{e(fam["desc"])}">
  <link rel="canonical" href="{url}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="AuditM365">
  <meta property="og:locale" content="fr_FR">
  <meta property="og:title" content="{e(fam["title"])}">
  <meta property="og:description" content="{e(fam["desc"])}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{BASE}/img/dashboard.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="/favicon.ico" sizes="any">
  <link rel="icon" type="image/png" href="/img/icon-192.png">
  <link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Inter+Tight:wght@600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/site.css">
  <style>{CSS}  </style>
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>

{NAV}

<main>
<div class="fam-hero sn-wrap">
  <nav class="crumbs" aria-label="Fil d'Ariane"><a href="/">Accueil</a><span>›</span><a href="/controles">Contrôles</a><span>›</span>{e(fam["nom"])}</nav>
  <p class="eyebrow">Guide de correction · {n} contrôles</p>
  <h1>{e(fam["h1"])}</h1>
  <p class="lead">{e(fam["intro"])}</p>
  <div class="chips">{"".join(chips)}</div>
  <div class="cta-row"><a class="sn-btn sn-btn-p" href="/#essai">Auditer mon tenant : essai gratuit 24 h</a><a class="sn-btn sn-btn-g" href="/controles">Les 86 contrôles</a></div>
</div>

<div class="fam-body sn-wrap">
  <aside class="toc" aria-label="Contrôles de cette page"><p>Dans cette page</p><ol>{toc}</ol></aside>
  <div class="ctls">
{body}
    <section class="fam-cta">
      <h2>Ces {n} contrôles, sur votre tenant</h2>
      <p>AuditM365 les évalue en lecture seule, depuis votre poste, et ajoute à chaque écart les chiffres de votre tenant (comptes, stratégies ou appareils concernés) et un script PowerShell à relire avant de l'exécuter.</p>
      <div class="cta-row"><a class="sn-btn sn-btn-p" href="/#essai">Essai gratuit 24 h</a><a class="sn-btn sn-btn-g" href="/#demo">Voir la démo</a></div>
    </section>
  </div>
</div>

<section class="fam-others sn-wrap" aria-label="Autres familles de contrôles">
  <h2>Les autres familles de contrôles</h2>
  <ul>{others}</ul>
</section>
</main>

{FOOT}

<script src="/site.js" defer></script>
<script src="/chat/chat.js" defer></script>
</body>
</html>
"""


os.makedirs(os.path.join(SITE, "controles"), exist_ok=True)
for fam in FAMILLES:
    with open(os.path.join(SITE, "controles", fam["slug"] + ".html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page(fam))

# ── page /controles : titre de chaque contrôle relié à son guide + lien par domaine ────────────────────────────
slug_of = {cid: f["slug"] for f in FAMILLES for cid in f["ids"]}
def link_title(m):
    cid, title = m.group(1), m.group(2)
    return f'<span class="cid">{cid}</span><span class="ctitle"><a href="/controles/{slug_of[cid]}#{cid.lower()}">{title}</a></span>'
cat = re.sub(r'<span class="cid">([A-Z]+-\d{3})</span><span class="ctitle">(?!<a )(.*?)</span>', link_title, cat)
def add_guide(m):
    sec = m.group(0)
    if "dom-guide" in sec:
        return sec
    cid = re.search(r'<span class="cid">([A-Z]+-\d{3})</span>', sec).group(1)
    fam = next(f for f in FAMILLES if f["slug"] == slug_of[cid])
    return sec.replace("</ul>", f'</ul>\n      <a class="dom-guide" href="/controles/{fam["slug"]}">Guide de correction des {len(fam["ids"])} contrôles <span aria-hidden="true">→</span></a>', 1)
cat = re.sub(r'<section class="dom">.*?</section>', add_guide, cat, flags=re.S)
MARK = "/* liens vers les guides de correction (pages familles) */"
if MARK not in cat:
    cat = cat.replace("  </style>", f"""    {MARK}
    .ctitle a {{ color: inherit; text-decoration: none; }}
    .ctitle a:hover {{ color: #9db8ff; text-decoration: underline; }}
    .dom-guide {{ display: inline-block; margin-top: 12px; font-size: 14px; font-weight: 600; color: #9db8ff; text-decoration: none; }}
    .dom-guide:hover {{ text-decoration: underline; }}
  </style>""", 1)
open(cat_path, "w", encoding="utf-8", newline="\n").write(cat)

# ── plan du site ────────────────────────────────────────────────────────────────────────────────────────────────
sm_path = os.path.join(SITE, "sitemap.xml")
sm = open(sm_path, encoding="utf-8").read()
sm = re.sub(r"\s*<url><loc>https://audit\.m365intune\.com/controles/[^<]+</loc>.*?</url>", "", sm)
add = "".join(f"\n  <url><loc>{BASE}/controles/{f['slug']}</loc><lastmod>{DATE_ISO}</lastmod></url>" for f in FAMILLES)
sm = re.sub(r"(<url><loc>https://audit\.m365intune\.com/controles</loc><lastmod>)[^<]+(</lastmod></url>)",
            lambda m: m.group(1) + DATE_ISO + m.group(2) + add, sm)
open(sm_path, "w", encoding="utf-8", newline="\n").write(sm)
print(f"{len(FAMILLES)} pages écrites dans controles/, /controles relié, sitemap : {sm.count('<url>')} adresses")
