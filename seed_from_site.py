# Copyright (c) 2026 Kuo-Chen Wu (吳國禎). All Rights Reserved.
"""從現行 index.html 萃取內容播種資料庫（需要 node）。出貨包已附播種完成的 data/cv.db，
一般不需執行本檔；僅在你手動改過網站資料、想把 DB 重新同步時使用。"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from app.db import engine, SessionLocal
from app.models import Base, Journal, Conference, Competition, Patent, Education, SkillGroup, Role, Experience

SITE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "robinsixrainbow.github.io", "index.html")
src = open(SITE, encoding="utf-8").read()

def grab(name):
    i = src.index(f"const {name} = " + "{"); j = src.index("{", i); d = 0
    for k in range(j, len(src)):
        if src[k] == "{": d += 1
        elif src[k] == "}":
            d -= 1
            if d == 0: return src[i:k+2]

js = grab("I18N") + "\n" + grab("CV_DATA") + "\nconsole.log(JSON.stringify({I18N,CV_DATA}));"
out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True)
d = json.loads(out.stdout)
I, C = d["I18N"], d["CV_DATA"]

Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
db = SessionLocal()
for s, j in enumerate(C["journals"]):
    db.add(Journal(sort=s, **{k: j.get(k, "") for k in ("q","authors","title","journal","vol","doi")}))
for s, c in enumerate(C["conferences"]):
    db.add(Conference(sort=s, venue=c.get("venue",""), meta_text=c.get("meta",""), title=c.get("title",""), invited=bool(c.get("invited"))))
for s, c in enumerate(C["competition"]):
    db.add(Competition(sort=s, **{k: c.get(k, "") for k in ("year","award","body")}))
for reg, arr in C["patents"].items():
    for s, p in enumerate(arr):
        db.add(Patent(region=reg, sort=s, pid=p.get("id",""), date=p.get("date",""), title=p.get("title","")))

def tri(field, idx, key):
    return {f"{field}_{lang}": I[lang][key][idx].get(field.replace("star_s","star").replace("star_t","star").replace("star_a","star").replace("star_r","star"), "") for lang in ("en","zh","ja")}

n = len(I["en"]["education"])
for i in range(n):
    row = {}
    for f in ("school","degree","date","place"):
        for lang in ("en","zh","ja"):
            row[f"{f}_{lang}"] = I[lang]["education"][i][f]
    db.add(Education(sort=i, **row))
for i in range(len(I["en"]["skills"])):
    row = {}
    for lang in ("en","zh","ja"):
        row[f"ttl_{lang}"] = I[lang]["skills"][i]["ttl"]
        row[f"items_{lang}"] = "\n".join(I[lang]["skills"][i]["items"])
    db.add(SkillGroup(sort=i, **row))
for i in range(len(I["en"]["currentRoles"])):
    row = {}
    for f in ("label","org"):
        for lang in ("en","zh","ja"):
            row[f"{f}_{lang}"] = I[lang]["currentRoles"][i][f]
    db.add(Role(sort=i, **row))
for i in range(len(I["en"]["experience"])):
    row = {}
    for f in ("role","date","org","project"):
        for lang in ("en","zh","ja"):
            row[f"{f}_{lang}"] = I[lang]["experience"][i][f]
    for sk in ("S","T","A","R"):
        for lang in ("en","zh","ja"):
            row[f"star_{sk.lower()}_{lang}"] = I[lang]["experience"][i]["star"][sk]
    db.add(Experience(sort=i, **row))
db.commit()
with engine.connect() as c:
    c.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE);")
engine.dispose()
print("seeded ✔  journals=%d conf=%d comp=%d patents=%d edu=%d skills=%d roles=%d exp=%d" % (
    len(C["journals"]), len(C["conferences"]), len(C["competition"]),
    sum(len(v) for v in C["patents"].values()), n, len(I["en"]["skills"]),
    len(I["en"]["currentRoles"]), len(I["en"]["experience"])))
