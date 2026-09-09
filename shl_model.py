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
    return round(ph/(ph+pa)*100,1), round(pa/(ph+pa)*100,1)

def hl(p):
    # highlight if >65%
    return f"<span style='background:#ffd60a;color:#000;padding:2px 6px;border-radius:6px;font-weight:900'>{p}% 🔥 65%+</span>" if p>=65 else f"{p}%"

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
        elo_log.append(f"{date} {h}")

json.dump({k:int(v) for k,v in ratings.items()}, open("ratings_auto.json","w"), indent=2)

def make_fixtures_no_dup(teams,n=4):
    teams=[normalize(t) for t in teams]
    random.shuffle(teams)
    fix=[]; used=set()
    for i in range(0, min(n*2, len(teams)), 2):
        if i+1 < len(teams):
            h=teams[i]; a=teams[i+1]
            if h not in used and a not in used:
                fix.append((h,a)); used.add(h); used.add(a)
    return fix[:n]

games=[]
for league, teams, hadv, avg_base in [("SHL",SHL,35,5.35),("CZECH",CZECH,65,5.75)]:
    for h,a in make_fixtures_no_dup(teams,4):
        h=normalize(h); a=normalize(a)
        rh=ratings.get(h,1500); ra=ratings.get(a,1500)
        p_home = win_prob(rh,ra,hadv)
        fair = round(1/p_home,2) if p_home>0.01 else 9.99
        diff = (rh - ra)/400.0
        lh = avg_base*0.52 + diff*0.45 + random.uniform(-0.18,0.18)
        la = avg_base*0.48 - diff*0.35 + random.uniform(-0.18,0.18)
        lh=max(1.6,min(3.8,lh)); la=max(1.2,min(3.4,la))
        tot=lh+la
        over=round((1-sum(poisson(tot,k) for k in range(0,6)))*100,1)
        p_pl=round(puck_line_prob(lh,la,2),1) if p_home>=0.5 else round(puck_line_prob(la,lh,2),1)
        scores=[(3,2),(4,2),(3,1),(2,1)] if p_home>=0.5 else [(2,3),(2,4),(1,3),(1,2)]
        s=[round(cs_prob(lh,la,sh,sa),1) for sh,sa in scores]
        tt25=team_total_over(lh,2.5); tt15=team_total_over(lh,1.5); tt35=team_total_over(lh,3.5)
        btts2=btts_at_least(lh,la,2); btts3=btts_at_least(lh,la,3)
        r2h,_=race_to(lh,la,2); r3h,_=race_to(lh,la,3)
        games.append({"league":league,"home":h,"away":a,"rh":int(rh),"ra":int(ra),"p_home":round(p_home*100,1),
                      "fair":fair,"p_pl":p_pl,"over":over,"scores":scores,"s":s,"lam":round(tot,2),
                      "lh":round(lh,2),"la":round(la,2),"tt15":tt15,"tt25":tt25,"tt35":tt35,"btts2":btts2,"btts3":btts3,"r2h":r2h,"r3h":r3h,"p_raw":p_home})

games.sort(key=lambda x: x["p_home"], reverse=True)
high_count = sum(1 for g in games if max(g['p_home'],g['tt15'],g['tt25'],g['btts2'],g['r2h'],g['r3h'])>=65)

html=f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V8.6 65%+ Highlight</title><style>
body{{font-family:system-ui;background:#0b1220;color:#fff;padding:12px;margin:0}}
.card{{background:#151e33;border-radius:14px;padding:14px;margin:12px 0;border:1px solid #1e2a4a}}
.card.high{{border:2px solid #ffd60a;background:#1c2540
