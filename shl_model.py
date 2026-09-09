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
def team_total_over(lam, line):
    n = int(line)+1
    p_under = sum(poisson(lam,k) for k in range(0,n))
    return round((1-p_under)*100,1)
def btts_at_least(lh,la,min_g):
    ph = 1 - sum(poisson(lh,k) for k in range(0,min_g))
    pa = 1 - sum(poisson(la,k) for k in range(0,min_g))
    return round(ph*pa*100,1)

team_history = {t: [] for t in ALL_TEAMS}
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
        team_history[h].append((hg, ag, a))
        team_history[a].append((ag, hg, h))
        rh,ra = ratings[h], ratings[a]
        exp_h = win_prob(rh,ra,HOME_ADV)
        res = 1 if hg>ag else 0 if hg<ag else 0.5
        ratings[h]= rh + K*(res-exp_h)
        ratings[a]= ra + K*((1-res)-(1-exp_h))
        elo_log.append(date)
json.dump({k:int(v) for k,v in ratings.items()}, open("ratings_auto.json","w"), indent=2)

def get_form(team):
    lst = team_history.get(team, [])
    if not lst:
        return 2.5, 2.5, "0/0/0/0/0 scored | 0/0/0/0/0 conceded"
    last5 = lst[-5:][::-1]
    avg_sc = sum([x[0] for x in last5])/len(last5)
    avg_co = sum([x[1] for x in last5])/len(last5)
    goals_sc = "/".join([str(x[0]) for x in last5])
    goals_co = "/".join([str(x[1]) for x in last5])
    form = "".join(["W" if x[0]>x[1] else "L" if x[0]<x[1] else "D" for x in last5])
    details = ", ".join([f"{x[0]}-{x[1]} vs {x[2]}" for x in last5])
    txt = f"{goals_sc} scored (avg {avg_sc:.1f}) | {goals_co} conceded (avg {avg_co:.1f}) [{form}] - {details}"
    return avg_sc, avg_co, txt

def make_fixtures_no_dup(teams,n=4):
    teams=[normalize(t) for t in teams]; random.shuffle(teams)
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
        form_h_sc, form_h_co, txt_h = get_form(h)
        form_a_sc, form_a_co, txt_a = get_form(a)
        rh=ratings.get(h,1500); ra=ratings.get(a,1500)
        p_home = win_prob(rh,ra,hadv)
        fair = round(1/p_home,2) if p_home>0.01 else 9.99
        diff = (rh - ra)/400.0
        base_h = avg_base*0.52 + diff*0.30
        base_a = avg_base*0.48 - diff*0.25
        lh = max(1.0,min(4.5, form_h_sc*0.50 + form_a_co*0.30 + base_h*0.20 + random.uniform(-0.10,0.10)))
        la = max(1.0,min(4.5, form_a_sc*0.50 + form_h_co*0.30 + base_a*0.20 + random.uniform(-0.10,0.10)))
        tot=lh+la
        over=round((1-sum(poisson(tot,k) for k in range(0,6)))*100,1)
        tt15_h=team_total_over(lh,1.5); tt25_h=team_total_over(lh,2.5); tt35_h=team_total_over(lh,3.5)
        tt15_a=team_total_over(la,1.5); tt25_a=team_total_over(la,2.5); tt35_a=team_total_over(la,3.5)
        btts2=btts_at_least(lh,la,2)
        games.append({"league":league,"home":h,"away":a,"rh":int(rh),"ra":int(ra),"p_home":round(p_home*100,1),
                      "fair":fair,"over":over,"lam":round(tot,2),"lh":round(lh,2),"la":round(la,2),
                      "tt15_h":tt15_h,"tt25_h":tt25_h,"tt35_h":tt35_h,"tt15_a":tt15_a,"tt25_a":tt25_a,"tt35_a":tt35_a,
                      "btts2":btts2,"p_raw":p_home,"last5_h":txt_h,"last5_a":txt_a,
                      "form_h_sc":round(form_h_sc,1),"form_h_co":round(form_h_co,1),"form_a_sc":round(form_a_sc,1),"form_a_co":round(form_a_co,1)})

games.sort(key=lambda x: max(x['tt25_h'],x['tt25_a'],x['btts2']), reverse=True)
top_lines=[]
for g in games:
    if g['tt25_h']>=55: top_lines.append(f"{g['home']} Over 2.5 {g['tt25_h']}% [form {g['form_h_sc']} vs {g['form_a_co']} conc]")
    if g['tt25_a']>=55: top_lines.append(f"{g['away']} Over 2.5 {g['tt25_a']}% [form {g['form_a_sc']} vs {g['form_h_co']} conc]")
    if g['btts2']>=60: top_lines.append(f"BTTS2 {g['btts2']}% {g['home']} vs {g['away']}")
top_html = "<br>".join(top_lines[:8]) if top_lines else "No 55%+ today - cold form"

html_start = f"<!DOCTYPE html><html><head><meta name=viewport content='width=device-width,initial-scale=1'><title>V9.5 No CS</title><style>body{{font-family:system-ui;background:#0b1220;color:#fff;padding:12px;margin:0}}.card{{background:#151e33;border-radius:14px;padding:14px;margin:12px 0;border:1px solid #1e2a4a}}.card.gold{{border:2px solid #00ff88;background:#14243a}}.badge{{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:800}}.shl{{background:#00d084;color:#000}}.czech{{background:#ff3b3b}}.small{{font-size:13px;line-height:1.7;opacity:0.95}}.elo{{font-size:11px;opacity:0.5}}.form{{font-size:11px;background:#0f1a33;padding:7px 8px;border-radius:8px;margin:5px 0;opacity:0.95;border-left:3px solid #00ff88}}.hi{{background:#00ff88;color:#000;padding:3px 8px;border-radius:6px;font-weight:900}}.hi2{{background:#ffd60a;color:#000;padding:2px 6px;border-radius:6px;font-weight:700}}</style></head><body>"
html_start += f"<h2>V9.5 Clean - No Correct Score</h2><p style=opacity:0.6>{datetime.now().strftime('%d %b %H:%M')} | {len(elo_log)} results | 50% scored + 30% opp conceded + 20% ELO</p>"
html_start += "<div class=card style='background:linear-gradient(135deg,#00ff88,#00d084);color:#000'><b>GOLD Over 2.5 / BTTS2:</b><br><span class=small>" + top_html + "</span></div>"
html_body=""
for g in games:
    is_gold = max(g['tt25_h'],g['tt25_a'])>=55 or g['btts2']>=60
    cls = "card gold" if is_gold else "card"
    def fmt_gold(p,th=55):
        if p>=th: return f"<span class=hi>{p}% GOLD</span>"
        if p>=50: return f"<span class=hi2>{p}%</span>"
        return f"{p}%"
    winner=g['home'] if g['p_raw']>=0.5 else g['away']
    html_body += f"<div class='{cls}'><span class='badge {g['league'].lower()}'>{g['league']}</span> <span class=elo>ELO {g['rh']} vs {g['ra']} | xG {g['lam']} ({g['lh']}-{g['la']})</span><br>"
    html_body += f"<b>{g['home']} vs {g['away']}</b> - Fav: {winner}<br><div class=small>"
    html_body += f"Win: {fmt_gold(g['p_home'],63)} | Over 5.5: {fmt_gold(g['over'],55)}<br>"
    html_body += f"<b>{g['home']} Over:</b> 1.5 {g['tt15_h']}% | 2.5 {fmt_gold(g['tt25_h'],55)} | 3.5 {g['tt35_h']}%<br>"
    html_body += f"<div class=form>Last 5 {g['home']}: {g['last5_h']}</div>"
    html_body += f"<b>{g['away']} Over:</b> 1.5 {g['tt15_a']}% | 2.5 {fmt_gold(g['tt25_a'],55)} | 3.5 {g['tt35_a']}%<br>"
    html_body += f"<div class=form>Last 5 {g['away']}: {g['last5_a']}</div>"
    html_body += f"<b>BTTS2:</b> {fmt_gold(g['btts2'],60)}</div></div>"
open("docs/index.html","w",encoding="utf-8").write(html_start+html_body+"</body></html>")
print("V9.5 No CS built - clean")
