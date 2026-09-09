import os, json, math, random, csv, unicodedata
from datetime import datetime

os.makedirs("docs", exist_ok=True)
open("docs/.nojekyll","w").close()

SHL = ["Frolunda","Farjestad","Leksands","Skelleftea","Rogle","Vaxjo Lakers","HV71","Linkoping","Lulea","Orebro","MODO","Timra","Malmo","Brynas"]
CZECH = ["Sparta Prague","Pardubice","Kometa Brno","Trinec","Litvinov","Liberec","Plzen","Ceske Budejovice","Vitkovice","Hradec Kralove","Olomouc","Karlovy Vary","Kladno","Mlada Boleslav"]

def normalize(name):
    name = unicodedata.normalize('NFKD', name).encode('ASCII','ignore').decode().strip()
    alias = {"Frolunda HC":"Frolunda","Vaxjo":"Vaxjo Lakers","Dynamo Pardubice":"Pardubice","Mountfield HK":"Hradec Kralove","Mountfield":"Hradec Kralove","CEZ Motor Ceske Budejovice":"Ceske Budejovice","BK Mlada Boleslav":"Mlada Boleslav"}
    return alias.get(name, name)

ALL_TEAMS = [normalize(t) for t in SHL+CZECH]
ratings = {t:1500 for t in ALL_TEAMS}
K, HOME_ADV = 24, 60

def win_prob(r1,r2,hadv): return 1/(1+10**((r2-(r1+hadv))/400))
def poisson(lam,k):
    if k<0 or lam<=0: return 0
    return (lam**k * math.exp(-lam))/math.factorial(k)
def cs_prob(lh,la,h,a): return poisson(lh,h)*poisson(la,a)*100
def puck_line_prob(lh,la,margin=2):
    tot=0.0
    for hh in range(0,13):
        for aa in range(0,13):
            if hh-aa >= margin: tot+=poisson(lh,hh)*poisson(la,aa)
    return tot*100
def team_total_over(lam, line):
    # P > line
    n = int(line)+1
    p_under = sum(poisson(lam,k) for k in range(0,n))
    return round((1-p_under)*100,1)
def btts_at_least(lh,la,min_g):
    ph = 1 - sum(poisson(lh,k) for k in range(0,min_g))
    pa = 1 - sum(poisson(la,k) for k in range(0,min_g))
    return round(ph*pa*100,1)
def race_to(lh,la,N):
    ph = 1 - sum(poisson(lh,k) for k in range(0,N))
    pa = 1 - sum(poisson(la,k) for k in range(0,N))
    if ph+pa <0.01: return 50.0,50.0
    # prob who gets there first ~ proportional + both can fail
    denom = ph+pa
    return round(ph/denom*100,1), round(pa/denom*100,1)

# --- ELO FROM results.csv ---
elo_log=[]
if os.path.exists("results.csv"):
    rows=[]
    with open("results.csv", newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try: rows.append((r['date'], normalize(r['home']), normalize(r['away']), int(r['hg']), int(r['ag'])))
            except: continue
    rows.sort(key=lambda x: x[0])
    for date,h,a,hg,ag in rows:
        if h not in ratings: ratings[h]=1500
        if a not in ratings: ratings[a]=1500
        rh,ra = ratings[h], ratings[a]
        exp_h = win_prob(rh,ra,HOME_ADV)
        res = 1 if hg>ag else 0 if hg<ag else 0.5
        ratings[h]= rh + K*(res-exp_h)
        ratings[a]= ra + K*((1-res)-(1-exp_h))
        elo_log.append(f"{date} {h} {hg}-{ag} {a}")

json.dump({k:int(v) for k,v in ratings.items()}, open("ratings_auto.json","w"), indent=2)

# --- V8.5 FIX: NO DUPLICATE TEAMS ---
def make_fixtures_no_dup(teams,n=4):
    teams=[normalize(t) for t in teams]
    random.shuffle(teams)
    fix=[]
    used=set()
    # simple pairing without reuse
    for i in range(0, min(n*2, len(teams)), 2):
        if i+1 < len(teams):
            h=teams[i]; a=teams[i+1]
            if h not in used and a not in used:
                fix.append((h,a))
                used.add(h); used.add(a)
    return fix[:n]

games=[]
for league, teams, hadv, avg_base in [("SHL",SHL,35,5.35),("CZECH",CZECH,65,5.75)]:
    for h,a in make_fixtures_no_dup(teams,4):
        h=normalize(h); a=normalize(a)
        rh=ratings.get(h,1500); ra=ratings.get(a,1500)
        p_home = win_prob(rh,ra,hadv)
        fair = round(1/p_home,2) if p_home>0.01 else 9.99

        # V8.5 Real xG 4.2-6.2
        diff = (rh - ra)/400.0
        lh = avg_base*0.52 + diff*0.45 + random.uniform(-0.18,0.18)
        la = avg_base*0.48 - diff*0.35 + random.uniform(-0.18,0.18)
        lh=max(1.6,min(3.8,lh)); la=max(1.2,min(3.4,la))
        tot=lh+la

        under=sum(poisson(tot,k) for k in range(0,6))
        over=round((1-under)*100,1)
        if p_home>=0.5: p_pl=round(puck_line_prob(lh,la,2),1)
        else: p_pl=round(puck_line_prob(la,lh,2),1)

        if p_home>=0.5: scores=[(3,2),(4,2),(3,1),(2,1)]
        else: scores=[(2,3),(2,4),(1,3),(1,2)]
        s=[round(cs_prob(lh,la,sh,sa),1) for sh,sa in scores]

        # NEW MARKETS from your screenshots
        tt_over_25 = team_total_over(lh,2.5)
        tt_over_35 = team_total_over(lh,3.5)
        btts2 = btts_at_least(lh,la,2)
        btts3 = btts_at_least(lh,la,3)
        race2_h, race2_a = race_to(lh,la,2)
        race3_h, race3_a = race_to(lh,la,3)

        games.append({"league":league,"home":h,"away":a,"rh":int(rh),"ra":int(ra),
                      "p_home":round(p_home*100,1),"fair":fair,"p_pl":p_pl,"over":over,
                      "scores":scores,"s":s,"lam":round(tot,2),"lh":round(lh,2),"la":round(la,2),
                      "tt25":tt_over_25,"tt35":tt_over_35,"btts2":btts2,"btts3":btts3,
                      "r2h":race2_h,"r3h":race3_h,"p_raw":p_home})

games.sort(key=lambda x: x["p_home"], reverse=True)

html=f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V8.5 Team Totals + Race</title><style>
body{{font-family:system-ui;background:#0b1220;color:#fff;padding:12px;margin:0}}
.card{{background:#151e33;border-radius:14px;padding:14px;margin:12px 0;border:1px solid #1e2a4a}}
.badge{{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:800}}.shl{{background:#00d084;color:#000}}.czech{{background:#ff3b3b}}
.small{{font-size:13px;line-height:1.7;opacity:0.95}}.top{{background:linear-gradient(135deg,#00d084,#00a86b);color:#000}}.elo{{font-size:11px;opacity:0.5}}
.val{{color:#00ff88;font-weight:800}}
</style></head><body>
<h2>V8.5 Team Totals + BTTS2/3 + Race 🏒</h2>
<p style="opacity:0.6">{datetime.now().strftime('%d %b %H:%M')} | {len(elo_log)} results | No duplicate fixtures</p>
<div class="card top"><b>Best 3x:</b> {games[0]['home']} {games[0]['p_home']}% + {games[1]['home']} {games[1]['p_home']}% + {games[2]['home']} {games[2]['p_home']}%<br>
<span class="small">xG {games[0]['lam']} | {games[1]['lam']} | {games[2]['lam']}</span></div>
"""

for g in games:
    winner=g['home'] if g['p_raw']>=0.5 else g['away']
    cs_text=" | ".join([f"{sh}-{sa} {sp}%" for (sh,sa),sp in zip(g["scores"],g["s"])])
    # value flags vs typical bookie lines from your screenshots
    flag_tt = " <span class=val>VALUE Over 2.5</span>" if g['tt25']>62 else ""
    flag_btts2 = " <span class=val>VALUE</span>" if 50 <= g['btts2'] <= 60 else ""
    html+=f"""<div class="card"><span class="badge {g['league'].lower()}">{g['league']}</span> <span class="elo">ELO {g['rh']} vs {g['ra']} | xG {g['lam']} ({g['lh']}-{g['la']})</span><br>
<b>{g['home']} vs {g['away']}</b> - Fav: {winner}<br><div class="small">
Home: {g['p_home']}% | Fair {g['fair']} | Puck -1.5 {g['p_pl']}% | Over 5.5 {g['over']}%<br>
<b>CS:</b> {cs_text}<br>
<b>Team Totals ({g['home']}):</b> Over 2.5 {g['tt25']}% (Fair {round(100/g['tt25'],2) if g['tt25']>0 else 0}){flag_tt} | Over 3.5 {g['tt35']}% (Fair {round(100/g['tt35'],2) if g['tt35']>0 else 0})<br>
<b>Both to Score:</b> AtLeast 2 {g['btts2']}% (Fair {round(100/g['btts2'],2) if g['btts2']>0 else 0}){flag_btts2} | AtLeast 3 {g['btts3']}% (Fair {round(100/g['btts3'],2) if g['btts3']>0 else 0})<br>
<b>Race To:</b> 2 Goals {g['home']} {g['r2h']}% vs {g['away']} {100-g['r2h']:.1f}% | 3 Goals {g['home']} {g['r3h']}%<br>
</div></div>"""

html+=f"""<div class="card"><b>How to use vs your screenshots</b><br><span class="small">
Team Totals: If model 61% and bookie 1.60 (62.5%) = no bet. If model 68% and bookie 1.60 = VALUE<br>
BTTS At Least 2: Your screenshot Yes 1.80 (55.5%). If model 58% = bet Yes<br>
Race To 3: Your screenshot 2.10 (47.6%). If model 58% (Fair 1.72) = VALUE on 2.10
</span></div>
</body></html>"""

open("docs/index.html","w",encoding="utf-8").write(html)
print(f"V8.5 built - {len(games)} games, no dups, BTTS2 range {min(g['btts2'] for g in games)}-{max(g['btts2'] for g in games)}")
