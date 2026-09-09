import os, json, math, random
from datetime import datetime

os.makedirs("docs", exist_ok=True)
open("docs/.nojekyll","w").close()

# Teams
SHL = ["Frolunda","Färjestad","Leksands","Skelleftea","Rogle","Vaxjo Lakers","HV71","Linkoping","Lulea","Orebro","MODO","Timra","Malmo","Brynäs"]
CZECH = ["Sparta Prague","Dynamo Pardubice","Kometa Brno","Trinec","Litvinov","Liberec","Plzen","Ceske Budejovice","Vítkovice","Hradec Kralove","Olomouc","Karlovy Vary","Kladno","Mlada Boleslav"]

# Mock ratings - replace with your ELO file if you have ratings_auto.json
ratings = {t: 1500+random.randint(-80,80) for t in SHL+CZECH}

def win_prob(r1,r2,home_adv):
    return 1/(1+10**((r2-(r1+home_adv))/400))

def poisson(lam,k): return (lam**k * math.exp(-lam))/math.factorial(k)

games = []
# Build 4 SHL + 4 Czech games today
for league, teams, hadv, avg in [("SHL",SHL,30,5.6),("CZECH",CZECH,65,5.9)]:
    for i in range(0,4):
        h = random.choice(teams); a = random.choice([t for t in teams if t!=h])
        p_home = win_prob(ratings[h],ratings[a],hadv)
        # Puck line -1.5 approx
        p_pl = p_home*0.62 # simplified
        fair = round(1/p_home,2) if p_home>0 else 2.0
        # Total 5.5
        lam = avg
        over = sum(poisson(lam,k) for k in range(6,15))
        games.append({"league":league,"home":h,"away":a,"p_home":round(p_home*100,1),"fair":fair,"p_pl":round(p_pl*100,1),"over5_5":round(over*100,1)})

# Build HTML
html = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SHL + Czech V7</title><style>body{{font-family:system-ui;background:#0b1220;color:#fff;padding:12px}}.card{{background:#151e33;border-radius:12px;padding:12px;margin:10px 0}}.badge{{padding:2px 8px;border-radius:6px;font-size:12px}}.shl{{background:#00d084}}.czech{{background:#ff3b3b}} button{{width:100%;padding:12px;background:#00d084;border:0;border-radius:10px;font-weight:bold}}</style></head><body>
<h2>SHL + Czech V7 LIVE 💥</h2><p>{datetime.now().strftime('%d %b %Y')} - {len(games)} games - Czech = Big Odds</p>
"""
for g in games:
    edge = "🔥 VALUE" if g["league"]=="CZECH" and g["p_home"]>62 else ""
    html+=f"""<div class="card"><span class="badge {g['league'].lower()}">{g['league']}</span> {edge}<br><b>{g['home']} vs {g['away']}</b><br>
    Home: {g['p_home']}% | Fair: {g['fair']}<br>Puck -1.5: {g['p_pl']}% | Over 5.5: {g['over5_5']}%<br>
    <input type="checkbox" onchange="addAcca('{g['home']}',{g['p_home']})"> Add to Acca</div>"""

html+="""
<div class="card"><h3>Acca Builder</h3><div id="acca"></div><p id="total"></p></div>
<script>let picks=[];function addAcca(team,p){picks.push({team,p});let comb=picks.reduce((a,b)=>a*(b.p/100),1);document.getElementById('acca').innerHTML=picks.map(x=>x.team+' '+x.p+'%').join('<br>');document.getElementById('total').innerHTML='Combined: '+(comb*100).toFixed(1)+'% | Fair: '+(1/comb).toFixed(2)}</script>
</body></html>"""

open("docs/index.html","w",encoding="utf-8").write(html)
json.dump(ratings, open("ratings_auto.json","w"))
print(f"V7 built {len(games)} games")
