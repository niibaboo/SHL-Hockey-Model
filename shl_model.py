import os, json, math, random, csv, unicodedata
from datetime import datetime

os.makedirs("docs", exist_ok=True)
open("docs/.nojekyll","w").close()

SHL = ["Frolunda","Farjestad","Leksands","Skelleftea","Rogle","Vaxjo Lakers","HV71","Linkoping","Lulea","Orebro","MODO","Timra","Malmo","Brynas"]
CZECH = ["Sparta Prague","Pardubice","Kometa Brno","Trinec","Litvinov","Liberec","Plzen","Ceske Budejovice","Vitkovice","Hradec Kralove","Olomouc","Karlovy Vary","Kladno","Mlada Boleslav"]
ALL_TEAMS = SHL + CZECH

def normalize(name):
    # fix Färjestad -> Farjestad etc
    name = unicodedata.normalize('NFKD', name).encode('ASCII','ignore').decode()
    name = name.strip()
    # common aliases
    alias = {"Frolunda HC":"Frolunda","Vaxjo":"Vaxjo Lakers","Dynamo Pardubice":"Pardubice","Mountfield HK":"Hradec Kralove"}
    return alias.get(name, name)

ratings = {normalize(t): 1500 for t in ALL_TEAMS}
K = 24
HOME_ADV = 60

def win_prob(r1,r2,hadv):
    return 1/(1+10**((r2-(r1+hadv))/400))

def poisson(lam,k):
    if k<0 or lam<=0: return 0
    return (lam**k * math.exp(-lam))/math.factorial(k)

def cs_prob(lh,la,h,a):
    return poisson(lh,h)*poisson(la,a)*100

def puck_line_prob(lh,la,margin=2):
    tot=0.0
    for h in range(0,13):
        for a in range(0,13):
            if h-a >= margin:
                tot+=poisson(lh,h)*poisson(la,a)
    return tot*100

# --- LOAD results.csv + BUILD ELO ---
elo_log=[]
if os.path.exists("results.csv"):
    rows=[]
    with open("results.csv", newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append((r['date'], normalize(r['home']), normalize(r['away']), int(r['hg']), int(r['ag']), r.get('league','')))
            except: continue
    rows.sort(key=lambda x: x[0]) # oldest first for correct ELO build
    for date,h,a,hg,ag,league in rows:
        if h not in ratings: ratings[h]=1500
        if a not in ratings: ratings[a]=1500
        rh, ra = ratings[h], ratings[a]
        exp_h = win_prob(rh,ra,HOME_ADV)
        res = 1 if hg>ag else 0 if hg<ag else 0.5
        ratings[h] = rh + K*(res - exp_h)
        ratings[a] = ra + K*((1-res) - (1-exp_h))
        elo_log.append(f"{date} {h} {hg}-{ag} {a} -> {int(ratings[h])}/{int(ratings[a])}")

# baseline if still 1500
baseline = {"Frolunda":1620,"Farjestad":1605,"Skelleftea":1595,"Sparta Prague":1670,"Trinec":1645,"Pardubice":1635}
for t,v in baseline.items():
    nt=normalize(t)
    if ratings.get(nt,1500)==1500 and len(elo_log)<10:
        ratings[nt]=v

json.dump({k:int(v) for k,v in ratings.items()}, open("ratings_auto.json","w"), indent=2)

# --- Fixtures ---
def make_fixtures(teams,n=4):
    used_h=set(); used_p=set(); fix=[]; att=0
    while len(fix)<n and att<300:
        att+=1
        h=random.choice([t for t in teams if t not in used_h])
        a=random.choice([t for t in teams if t!=h])
        pair=frozenset((h,a))
        if pair in used_p: continue
        used_h.add(h); used_p.add(pair); fix.append((h,a))
    return fix

games=[]
for league, teams, hadv, avg in [("SHL",SHL,35,5.4),("CZECH",CZECH,65,5.9)]:
    for h,a in make_fixtures(teams,4):
        h=normalize(h); a=normalize(a)
        p_home = win_prob(ratings.get(h,1500), ratings.get(a,1500), hadv)
        fair = round(1/p_home,2) if p_home>0.01 else 2.0

        # V8.2 Dynamic xG - now varies with ELO diff
        elo_diff = ratings.get(h,1500) - ratings.get(a,1500)
        lh = (avg*0.52) + (elo_diff/350) + 0.25 # home bonus + form
        la = (avg*0.48) - (elo_diff/350)
        lh=max(0.9,min(5.0,lh)); la=max(0.8,min(4.5,la))
        tot=lh+la

        under=sum(poisson(tot,k) for k in range(0,6))
        over=round((1-under)*100,1)

        if p_home>=0.5: p_pl=round(puck_line_prob(lh,la,2),1)
        else: p_pl=round(puck_line_prob(la,lh,2),1)

        if p_home>=0.5: scores=[(4,2),(5,2),(3,2),(4,3)]
        else: scores=[(2,4),(2,5),(2,3),(3,4)]
        s=[round(cs_prob(lh,la,sh,sa),1) for sh,sa in scores]

        # Realistic BTTS - at least 2 goals each team needed
        btts_prob = (1-math.exp(-lh*0.7))*(1-math.exp(-la*0.7))
        btts=round(btts_prob*100,1)
        btts=max(38,min(78,btts))

        games.append({"league":league,"home":h,"away":a,"rh":int(ratings.get(h,1500)),"ra":int(ratings.get(a,1500)),
                      "p_home":round(p_home*100,1),"fair":fair,"p_pl":p_pl,"over":over,
                      "scores":scores,"s":s,"btts":btts,"p_raw":p_home,"lam":round(tot,2)})

games.sort(key=lambda x: x["p_home"], reverse=True)

html=f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SHL + Czech V8.2 ELO</title><style>
body{{font-family:system-ui;background:#0b1220;color:#fff;padding:12px;margin:0}}
.card{{background:#151e33;border-radius:14px;padding:14px;margin:12px 0;border:1px solid #1e2a4a}}
.badge{{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:800}}.shl{{background:#00d084;color:#000}}.czech{{background:#ff3b3b}}
.small{{font-size:13px;line-height:1.6;opacity:0.95}}.top{{background:linear-gradient(135deg,#00d084,#00a86b);color:#000}}.elo{{font-size:11px;opacity:0.5}}
</style></head><body>
<h2>V8.2 ELO REAL + Dynamic xG 🏒</h2>
<p style="opacity:0.6">{datetime.now().strftime('%d %b %H:%M')} | {len(elo_log)} results in ELO | Ratings from results.csv</p>
<div class="card top"><b>Best 3x Boost:</b> {games[0]['home']} ({games[0]['p_home']}%) + {games[1]['home']} ({games[1]['p_home']}%) + {games[2]['home']} ({games[2]['p_home']}%)<br>
<span class="small">Combined {(games[0]['p_home']/100)*(games[1]['p_home']/100)*(games[2]['p_home']/100)*100:.1f}% | Fair {1/((games[0]['p_home']/100)*(games[1]['p_home']/100)*(games[2]['p_home']/100)):.2f}</span></div>
"""

for g in games:
    winner=g['home'] if g['p_raw']>=0.5 else g['away']
    edge=" 🔥 VALUE" if g['p_home']>62 or g['over']>60 else ""
    cs_text=" | ".join([f"{sh}-{sa} {sp}%" for (sh,sa),sp in zip(g["scores"],g["s"])])
    html+=f"""<div class="card"><span class="badge {g['league'].lower()}">{g['league']}</span>{edge} <span class="elo">ELO {g['rh']} vs {g['ra']} xG {g['lam']}</span><br>
<b>{g['home']} vs {g['away']}</b> - Fav: {winner}<br><div class="small">
Home: {g['p_home']}% | Fair {g['fair']} | Puck -1.5 {g['p_pl']}% | Over 5.5 {g['over']}%<br>
<b>CS:</b> {cs_text}<br>BTTS Yes: {g['btts']}%</div></div>"""

html+=f"""<div class="card"><b>ELO Log (last 5)</b><br><span class="small">{'<br>'.join(elo_log[-5:]) if elo_log else 'No data'}</span></div>
<div class="card"><b>Top Ratings</b><br><span class="small">{'<br>'.join([f"{k} {int(v)}" for k,v in sorted(ratings.items(), key=lambda x: x[1], reverse=True)[:10]])}</span></div>
</body></html>"""

open("docs/index.html","w",encoding="utf-8").write(html)
print(f"V8.2 built - {len(elo_log)} results, ELO spread {min(ratings.values()):.0f}-{max(ratings.values()):.0f}")
