import os, json, math, random, csv
from datetime import datetime

os.makedirs("docs", exist_ok=True)
open("docs/.nojekyll","w").close()

SHL = ["Frolunda","Färjestad","Leksands","Skelleftea","Rogle","Vaxjo Lakers","HV71","Linkoping","Lulea","Orebro","MODO","Timra","Malmo","Brynas"]
CZECH = ["Sparta Prague","Dynamo Pardubice","Kometa Brno","Trinec","Litvinov","Liberec","Plzen","Ceske Budejovice","Vitkovice","Hradec Kralove","Olomouc","Karlovy Vary","Kladno","Mlada Boleslav"]
ALL_TEAMS = SHL+CZECH

# --- ELO ENGINE ---
ratings = {t: 1500 for t in ALL_TEAMS}
K = 20
HOME_ADV = 55 # ELO points for home

def win_prob(r1,r2,hadv):
    return 1/(1+10**((r2-(r1+hadv))/400))

def poisson(lam,k):
    if k<0 or lam<=0: return 0
    return (lam**k * math.exp(-lam))/math.factorial(k)

def cs_prob(lh,la,h,a):
    return poisson(lh,h)*poisson(la,a)*100

def puck_line_prob(lh,la,margin=2):
    total=0.0
    for h in range(0,13):
        for a in range(0,13):
            if h-a >= margin:
                total+=poisson(lh,h)*poisson(la,a)
    return total*100

# Load results.csv and build REAL ratings
elo_log = []
if os.path.exists("results.csv"):
    with open("results.csv", newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                h = row['home'].strip(); a = row['away'].strip()
                hg = int(row['hg']); ag = int(row['ag'])
                if h not in ratings: ratings[h]=1500
                if a not in ratings: ratings[a]=1500

                rh = ratings[h]; ra = ratings[a]
                exp_h = win_prob(rh,ra,HOME_ADV)
                result = 1 if hg>ag else 0 if hg<ag else 0.5

                # ELO update
                ratings[h] = rh + K*(result - exp_h)
                ratings[a] = ra + K*((1-result) - (1-exp_h))
                elo_log.append(f"{h} {hg}-{ag} {a} -> {int(ratings[h])}/{int(ratings[a])}")
            except: continue

# If no results file yet, use last season manual baseline
else:
    baseline = {"Frolunda":1610,"Färjestad":1605,"Skelleftea":1590,"Vaxjo Lakers":1580,
                "Sparta Prague":1670,"Trinec":1640,"Dynamo Pardubice":1630,"Kometa Brno":1600}
    for t,v in baseline.items():
        if t in ratings: ratings[t]=v

# Save real ratings
json.dump({k:int(v) for k,v in ratings.items()}, open("ratings_auto.json","w"), indent=2)

# --- Generate next fixtures (no dupes) ---
def make_fixtures(teams,n=4):
    used_h=set(); used_pairs=set(); fix=[]
    att=0
    while len(fix)<n and att<300:
        att+=1
        h=random.choice([t for t in teams if t not in used_h])
        a=random.choice([t for t in teams if t!=h])
        pair=frozenset((h,a))
        if pair in used_pairs: continue
        used_h.add(h); used_pairs.add(pair); fix.append((h,a))
    return fix

games=[]
for league, teams, hadv, avg in [("SHL",SHL,30,5.4),("CZECH",CZECH,65,5.9)]:
    for h,a in make_fixtures(teams,4):
        p_home = win_prob(ratings[h],ratings[a],hadv)
        fair = round(1/p_home,2) if p_home>0.01 else 2.0
        lh = (avg*0.52)*(p_home/0.5); la = (avg*0.48)*((1-p_home)/0.5)
        lh=max(0.8,lh); la=max(0.8,la); tot=lh+la
        under=sum(poisson(tot,k) for k in range(0,6))
        over=round((1-under)*100,1)
        if p_home>=0.5: p_pl=round(puck_line_prob(lh,la,2),1)
        else: p_pl=round(puck_line_prob(la,lh,2),1)
        if p_home>=0.5: scores=[(4,2),(5,2),(3,2),(4,3)]
        else: scores=[(2,4),(2,5),(2,3),(3,4)]
        s=[round(cs_prob(lh,la,sh,sa),1) for sh,sa in scores]
        btts=round((1-math.exp(-lh))*(1-math.exp(-la))*100,1)
        games.append({"league":league,"home":h,"away":a,"rh":int(ratings[h]),"ra":int(ratings[a]),
                      "p_home":round(p_home*100,1),"fair":fair,"p_pl":p_pl,"over":over,
                      "scores":scores,"s":s,"btts":btts,"p_raw":p_home,"lam":round(tot,1)})

games.sort(key=lambda x: x["p_home"], reverse=True)

# --- HTML ---
html=f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SHL + Czech V8.1 ELO</title><style>
body{{font-family:system-ui;background:#0b1220;color:#fff;padding:12px;margin:0}}
.card{{background:#151e33;border-radius:14px;padding:14px;margin:12px 0;border:1px solid #1e2a4a}}
.badge{{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:800}}.shl{{background:#00d084;color:#000}}.czech{{background:#ff3b3b}}
.small{{font-size:13px;line-height:1.6}}.top{{background:linear-gradient(135deg,#00d084,#00a86b);color:#000}}
.elo{{font-size:11px;opacity:0.5}}
</style></head><body>
<h2>V8.1 ELO REAL 🏒</h2>
<p style="opacity:0.6">{datetime.now().strftime('%d %b %H:%M')} | {len(elo_log)} games in ELO | Ratings from results.csv</p>
<div class="card top"><b>Best 3x Boost:</b> {games[0]['home']} ({games[0]['p_home']}%) + {games[1]['home']} + {games[2]['home']}</div>
"""

for g in games:
    winner=g['home'] if g['p_raw']>=0.5 else g['away']
    cs_text=" | ".join([f"{sh}-{sa} {sp}%" for (sh,sa),sp in zip(g["scores"],g["s"])])
    html+=f"""<div class="card"><span class="badge {g['league'].lower()}">{g['league']}</span> <span class="elo">ELO {g['rh']} vs {g['ra']} xG {g['lam']}</span><br>
<b>{g['home']} vs {g['away']}</b> Fav: {winner}<br><div class="small">
Home: {g['p_home']}% | Fair {g['fair']} | Puck -1.5 {g['p_pl']}% | Over 5.5 {g['over']}%<br>
<b>CS:</b> {cs_text}<br>BTTS {g['btts']}%</div></div>"""

html+=f"""<div class="card"><b>ELO Log (last 5)</b><br><span class="small">{'<br>'.join(elo_log[-5:]) if elo_log else 'No results.csv yet - using baseline'}</span></div>
<div class="card"><h3>How to update ELO</h3><span class="small">Just add new rows to results.csv:<br><code>2024-09-13,SHL,Frolunda,Malmo,3,1</code><br>Model auto-recalculates every build.</span></div>
</body></html>"""

open("docs/index.html","w",encoding="utf-8").write(html)
print(f"V8.1 built - {len(elo_log)} results, {len(games)} games")
