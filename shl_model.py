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

elo_log=[]
if os.path.exists("results.csv"):
    rows=[]
    with open("results.csv", newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append((r['date'], normalize(r['home']), normalize(r['away']), int(r['hg']), int(r['ag'])))
            except:
                continue
    rows.sort(key=lambda x: x[0])
    for date,h,a,hg,ag in rows:
        if h not in ratings: ratings[h]=1500
        if a not in ratings: ratings[a]=1500
        rh,ra = ratings[h], ratings[a]
        exp_h = win_prob(rh,ra,HOME_ADV)
        res = 1 if hg>ag else 0 if hg<ag else 0.5
        ratings[h]= rh + K*(res-exp_h)
        ratings[a]= ra + K*((1-res)-(1-exp_h))
        elo_log.append(date)

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
        tt15_h=team_total_over(lh,1.5); tt25_h=team_total_over(lh,2.5); tt35_h=team_total_over(lh,3.5)
        tt15_a=team_total_over(la,1.5); tt25_a=team_total_over(la,2.5); tt35_a=team_total_over(la,3.5)
        btts2=btts_at_least(lh,la,2); btts3=btts_at_least(lh,la,3)
        r2h,_=race_to(lh,la,2); r3h,_=race_to(lh,la,3)
        games.append({"league":league,"home":h,"away":a,"rh":int(rh),"ra":int(ra),"p_home":round(p_home*100,1),
                      "fair":fair,"p_pl":p_pl,"over":over,"scores":scores,"s":s,"lam":round(tot,2),
                      "lh":round(lh,2),"la":round(la,2),
                      "tt15_h":tt15_h,"tt25_h":tt25_h,"tt35_h":tt35_h,
                      "tt15_a":tt15_a,"tt25_a":tt25_a,"tt35_a":tt35_a,
                      "btts2":btts2,"btts3":btts3,"r2h":r2h,"r3h":r3h,"p_raw":p_home})

# Sort by best Over 2.5
games.sort(key=lambda x: max(x['tt25_h'],x['tt25_a'],x['p_home'],x['btts2']), reverse=True)

top_lines=[]
for g in games:
    if g['tt25_h']>=65:
        top_lines.append(g['home'] + " Over 2.5 " + str(g['tt25_h']) + "% vs " + g['away'] + " - GOLD")
    if g['tt25_a']>=65:
        top_lines.append(g['away'] + " Over 2.5 " + str(g['tt25_a']) + "% at " + g['home'] + " - GOLD")
    if g['btts2']>=65:
        top_lines.append("BTTS2 " + str(g['btts2']) + "% " + g['home'] + " vs " + g['away'] + " - GOLD")
    if g['p_home']>=70:
        top_lines.append(g['home'] + " Win " + str(g['p_home']) + "% - GOLD")

top_html = "<br>".join(top_lines[:8]) if top_lines else "No Over 2.5 65%+ today - wait for better games"

html_start = "<!DOCTYPE html><html><head><meta name=viewport content='width=device-width,initial-scale=1'><title>V8.8 Gold Over2.5</title><style>body{font-family:system-ui;background:#0b1220;color:#fff;padding:12px;margin:0}.card{background:#151e33;border-radius:14px;padding:14px;margin:12px 0;border:1px solid #1e2a4a}.card.gold{border:2px solid #00ff88;background:#14243a}.badge{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:800}.shl{background:#00d084;color:#000}.czech{background:#ff3b3b}.small{font-size:13px;line-height:1.7;opacity:0.95}.elo{font-size:11px;opacity:0.5}.hi{background:#00ff88;color:#000;padding:3px 8px;border-radius:6px;font-weight:900}.hi2{background:#ffd60a;color:#000;padding:2px 6px;border-radius:6px;font-weight:700}</style></head><body>"
html_start += "<h2>V8.8 GOLD Over 2.5 65%+ 💰</h2><p style=opacity:0.6>" + datetime.now().strftime('%d %b %H:%M') + " | " + str(len(elo_log)) + " results | " + str(len(top_lines)) + " GOLD picks</p>"
html_start += "<div class=card style='background:linear-gradient(135deg,#00ff88,#00d084);color:#000'><b>REAL GOLD 65%+ (Over 2.5 / BTTS2 / Win 70%+):</b><br><span class=small>" + top_html + "</span></div>"

html_body=""
for g in games:
    is_gold = max(g['tt25_h'],g['tt25_a'],g['btts2'])>=65 or g['p_home']>=70
    cls = "card gold" if is_gold else "card"
    def fmt_gold(p):
        if p>=65:
            return "<span class=hi>" + str(p) + "% GOLD</span>"
        if p>=58:
            return "<span class=hi2>" + str(p) + "%</span>"
        return str(p) + "%"
    def fmt_win(p):
        if p>=70:
            return "<span class=hi>" + str(p) + "% GOLD</span>"
        if p>=65:
            return "<span class=hi2>" + str(p) + "%</span>"
        return str(p) + "%"
    cs_text=""
    for (sh,sa),sp in zip(g["scores"],g["s"]):
        cs_text += str(sh) + "-" + str(sa) + " " + str(sp) + "% | "
    winner=g['home'] if g['p_raw']>=0.5 else g['away']
    html_body += "<div class='" + cls + "'><span class='badge " + g['league'].lower() + "'>" + g['league'] + "</span> <span class=elo>ELO " + str(g['rh']) + " vs " + str(g['ra']) + " | xG " + str(g['lam']) + " (" + str(g['lh']) + "-" + str(g['la']) + ")</span><br>"
    html_body += "<b>" + g['home'] + " vs " + g['away'] + "</b> - Fav: " + winner + "<br><div class=small>"
    html_body += "Home Win: " + fmt_win(g['p_home']) + " | Fair " + str(g['fair']) + " | Over 5.5 " + fmt_gold(g['over']) + "<br>"
    html_body += "<b>CS:</b> " + cs_text + "<br>"
    html_body += "<b>" + g['home'] + " Totals:</b> Over 1.5 " + str(g['tt15_h']) + "% | Over 2.5 " + fmt_gold(g['tt25_h']) + " | Over 3.5 " + str(g['tt35_h']) + "%<br>"
    html_body += "<b>" + g['away'] + " Totals:</b> Over 1.5 " + str(g['tt15_a']) + "% | Over 2.5 " + fmt_gold(g['tt25_a']) + " | Over 3.5 " + str(g['tt35_a']) + "%<br>"
    html_body += "<b>Both to Score:</b> AtLeast 2 " + fmt_gold(g['btts2']) + " | AtLeast 3 " + str(g['btts3']) + "%<br>"
    html_body += "<b>Race To:</b> 2 Goals " + g['home'] + " " + fmt_gold(g['r2h']) + "<br>"
    html_body += "</div></div>"

html_end="</body></html>"
open("docs/index.html","w",encoding="utf-8").write(html_start+html_body+html_end)
print("V8.8 GOLD built - " + str(len(top_lines)) + " gold picks")
