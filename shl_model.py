import os, json
base_elo = {
    "Frolunda HC":1580,"Skelleftea AIK":1565,"Farjestad BK":1560,"Vaxjo Lakers":1545,
    "Lulea HF":1535,"Rogle BK":1510,"Orebro HK":1495,"Linkoping HC":1485,
    "Timra IK":1480,"Malmo Redhawks":1470,"Leksands IF":1465,"HV71":1450,
    "Brynäs IF":1440,"MoDo Hockey":1420
}
def win_prob(e1,e2,ha=40): return 1/(1+10**(-((e1+ha)-e2)/400))
def fair(p): return round(100/p,2) if p>1 else 99.0

ratings={}
if os.path.exists("ratings_auto.json"):
    try: ratings=json.load(open("ratings_auto.json"))
    except: pass

fixtures=[
    ("Frolunda HC","Leksands IF"),
    ("Skelleftea AIK","HV71"),
    ("Farjestad BK","Rogle BK"),
    ("Vaxjo Lakers","Lulea HF"),
    ("Orebro HK","Malmo Redhawks"),
]

html="""<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>body{background:#08120f;color:#fff;font-family:Arial;padding:10px;margin:0}.card{background:#12291f;border-radius:16px;padding:14px;margin:14px 0;border:1px solid #1a3a2a}.green{background:#00ff88;color:#000;border-radius:12px;padding:4px 10px;float:right;font-size:11px;font-weight:bold}.sec{color:#00ff88;font-weight:bold;margin-top:14px;font-size:11px;text-transform:uppercase;border-top:1px solid #1a3a2a;padding-top:10px}.row{display:flex;align-items:center;flex-wrap:wrap;margin:6px 0;font-size:13px}input{background:#000;color:#00ff88;border:1px solid #00ff88;border-radius:8px;width:62px;padding:6px;text-align:center;margin-left:8px;font-weight:bold}.badge{background:#2a2a2a;color:#999;padding:4px 8px;border-radius:8px;font-size:11px;margin-left:8px;min-width:125px}.acca{position:sticky;bottom:0;background:#0f231a;border:2px solid #00ff88;border-radius:14px;padding:12px;margin-top:20px}.tick{width:18px;height:18px;accent-color:#00ff88;margin-right:6px}</style>
<script>let sel={};function chk(id,f){let i=document.getElementById(id);let b=document.getElementById(id+'_b');let v=parseFloat(i.value);if(isNaN(v)){b.innerText='Enter B365';b.style.background='#2a2a2a';upd();return;}let e=((v/f)-1)*100;if(v>f){b.style.background='#00ff88';b.style.color='#000';b.innerText='VALUE '+v+'>'+f+' (+'+e.toFixed(1)+'%)'}else{b.style.background='#ff4444';b.style.color='#fff';b.innerText='NO VALUE ('+e.toFixed(1)+'%)'}upd();}
function tog(cb,id,prob,label){if(cb.checked)sel[id]={prob:prob,label:label};else delete sel[id];upd();}
function upd(){let bar=document.getElementById('acca');let keys=Object.keys(sel);if(keys.length==0){bar.innerHTML='<b>🏒 SHL ACCA BUILDER:</b> Tick 2-3 games from DIFFERENT matches. Same-game blocked by B365.';return;}let tp=1;let bProd=1;let valid=true;let legs='';for(let k of keys){let pr=sel[k].prob;tp*=(pr/100);let inp=document.getElementById(k);let bv=parseFloat(inp?inp.value:NaN);if(isNaN(bv))valid=false;else bProd*=bv;legs+='<div>'+sel[k].label+' '+pr.toFixed(1)+'% @ '+(isNaN(bv)?'--':bv)+'</div>';}let fair=tp>0?1/tp:0;let pct=tp*100;let h='<b>🎯 '+keys.length+'-LEG SHL ACCA</b><div style=margin:6px 0>'+legs+'</div><div>True '+pct.toFixed(3)+'% → Fair '+fair.toFixed(2)+'</div>';if(!valid)h+='<div style=color:#ffaa00>Enter B365 for all ticked</div>';else{let edge=((bProd/fair)-1)*100;let col=edge>0?'#00ff88':'#ff4444';let txt=edge>0?'VALUE ✅':'NO VALUE ❌';h+='<div>B365 Acca '+bProd.toFixed(2)+' → <span style=background:'+col+';color:#000;padding:3px 8px;border-radius:8px;font-weight:bold>'+txt+' '+edge.toFixed(1)+'%</span></div>';}bar.innerHTML=h;}</script></head><body>
<h2>🇸🇪 SHL V6 FULL • 4 MARKETS + ACCA BUILDER</h2><div style='opacity:0.6;font-size:11px'>Same model as snooker: ELO + Poisson | Home +3% | Avg 5.6 goals</div>"""

for idx,(home,away) in enumerate(fixtures):
    eH=ratings.get(home,base_elo.get(home,1500)); eA=ratings.get(away,base_elo.get(away,1500))
    pH=win_prob(eH,eA,40)*100; pA=100-pH
    expH=2.8+(eH-eA)/400; expA=2.8-(eH-eA)/400; tot=expH+expA
    overProb=max(35,min(78,50+(tot-5.5)*22)); plH=pH*0.58; btts=78+(tot-5.5)*3
    html+=f"""<div class='card'><b>{home} vs {away}</b><span class='green'>{pH:.1f}% Home</span>
<div class='sec'>1. Match Win</div><div class='row'>{home} {pH:.1f}% → Fair {fair(pH)} <input id='w1_{idx}' oninput="chk('w1_{idx}',{fair(pH)})"><span id='w1_{idx}_b' class='badge'>Enter</span></div><div class='row'>{away} {pA:.1f}% → Fair {fair(pA)} <input id='w2_{idx}' oninput="chk('w2_{idx}',{fair(pA)})"><span id='w2_{idx}_b' class='badge'>Enter</span></div>
<div class='sec'>2. Puck Line -1.5</div><div class='row'>{home} -1.5 {plH:.1f}% → Fair {fair(plH)} <input id='pl1_{idx}' oninput="chk('pl1_{idx}',{fair(plH)})"><span id='pl1_{idx}_b' class='badge'>Enter</span></div><div class='row'>{away} +1.5 {100-plH:.1f}% → Fair {fair(100-plH)} <input id='pl2_{idx}' oninput="chk('pl2_{idx}',{fair(100-plH)})"><span id='pl2_{idx}_b' class='badge'>Enter</span></div>
<div class='sec'>3. Total Over 5.5 — DUAL + ACCA</div><div class='row'><input type='checkbox' class='tick' onchange="tog(this,'ov_{idx}',{overProb},'{home} Over 5.5')">Over 5.5 {overProb:.1f}% → Fair {fair(overProb)} xG {tot:.1f} <input id='ov_{idx}' oninput="chk('ov_{idx}',{fair(overProb)})"><span id='ov_{idx}_b' class='badge'>Enter</span></div><div class='row'>Under {100-overProb:.1f}% → Fair {fair(100-overProb)} <input id='un_{idx}' oninput="chk('un_{idx}',{fair(100-overProb)})"><span id='un_{idx}_b' class='badge'>Enter</span></div>
<div class='sec'>4. Correct Score 4-2 + 5-2 + BTTS</div><div class='row'><input type='checkbox' class='tick' onchange="tog(this,'cs42_{idx}',{pH*0.12},'{home} 4-2')">{home} 4-2 ~{pH*0.12:.1f}% → Fair {fair(pH*0.12)} <input id='cs42_{idx}' oninput="chk('cs42_{idx}',{fair(pH*0.12)})"><span id='cs42_{idx}_b' class='badge'>Enter</span></div><div class='row'><input type='checkbox' class='tick' onchange="tog(this,'cs52_{idx}',{pH*0.08},'{home} 5-2')">{home} 5-2 ~{pH*0.08:.1f}% → Fair {fair(pH*0.08)} <input id='cs52_{idx}' oninput="chk('cs52_{idx}',{fair(pH*0.08)})"><span id='cs52_{idx}_b' class='badge'>Enter</span></div><div class='row'>BTTS {btts:.1f}% → Fair {fair(btts)} <input id='bt_{idx}' oninput="chk('bt_{idx}',{fair(btts)})"><span id='bt_{idx}_b' class='badge'>Enter</span></div></div>"""

html+="<div id='acca' class='acca'><b>🏒 SHL ACCA BUILDER:</b> Tick 2-3 Totals / Wins from different matches.</div></body></html>"
os.makedirs("docs",exist_ok=True)
open("docs/index.html","w",encoding="utf-8").write(html)
print("SHL V6 built")
