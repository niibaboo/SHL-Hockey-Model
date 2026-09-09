import csv, math, os
from datetime import datetime
from collections import defaultdict
FIXTURES_FILE="fixtures.csv"
RESULTS_FILE="results.csv"
OUTPUT_FILE="docs/index.html"
LEAGUE_AVGS={"SHL":5.2,"CZECH":5.4,"DEL":6.1}
K=20
HOME_ADV=55
def poisson_over(lmbda, line):
    if lmbda<=0: return 0.0
    p=0.0
    for k in range(int(line)+1):
        p+=math.exp(-lmbda)*(lmbda**k)/math.factorial(k)
    return 1-p
def load_results():
    ratings=defaultdict(lambda:1500)
    form=defaultdict(list)
    results=[]
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE,encoding='utf-8') as f:
            reader=csv.DictReader(f)
            for r in reader:
                try:
                    h=r['home'].strip(); a=r['away'].strip()
                    hg=int(r['hg']); ag=int(r['ag'])
                    results.append(r)
                    form[h].append((hg,ag))
                    form[a].append((ag,hg))
                    rh,ra=ratings[h],ratings[a]
                    eh=1/(1+10**((ra-rh-HOME_ADV)/400))
                    sh=1 if hg>ag else 0.5 if hg==ag else 0
                    ratings[h]=rh+K*(sh-eh)
                    ratings[a]=ra+K*((1-sh)-(1-eh))
                except: continue
    return ratings,form,results
def load_fixtures():
    fixtures=[]
    if os.path.exists(FIXTURES_FILE):
        with open(FIXTURES_FILE,encoding='utf-8') as f:
            reader=csv.DictReader(f)
            for row in reader:
                if row.get('home'): fixtures.append(row)
    return fixtures
def team_stats(team, form):
    games=form.get(team,[])[-5:]
    if not games: return None
    scored=sum(g[0] for g in games)/len(games)
    conceded=sum(g[1] for g in games)/len(games)
    dots_html="".join(['<span class="w"></span>' if gf>ga else '<span class="l"></span>' if gf<ga else '<span class="d"></span>' for gf,ga in reversed(games)])
    detail=", ".join([str(gf)+"-"+str(ga) for gf,ga in reversed(games)])
    return {"avg_s":scored,"avg_c":conceded,"dots":dots_html,"detail":detail,"count":len(games)}
ratings,form,results_data=load_results()
fixtures=load_fixtures()
games_html_parts=[]
insights_list=[]
for fx in fixtures:
    league=fx.get('league','SHL').upper().strip()
    home=fx['home'].strip(); away=fx['away'].strip()
    date_raw=fx.get('date','')
    try: d=datetime.fromisoformat(date_raw).strftime("%d Sep")
    except: d=date_raw[:10]
    hs=team_stats(home,form); aws=team_stats(away,form)
    rh=ratings.get(home,1500); ra=ratings.get(away,1500)
    avg_goals=LEAGUE_AVGS.get(league,5.4)
    h_mult=(hs['avg_s']/2.5) if hs else 1.0
    a_mult=(aws['avg_s']/2.5) if aws else 1.0
    h_xg=max(0.8,min(4.5,avg_goals/2*(1+(rh-ra)/800)*h_mult))
    a_xg=max(0.8,min(4.5,avg_goals/2*(1+(ra-rh)/800)*a_mult))
    total_xg=h_xg+a_xg
    o15_h=poisson_over(h_xg,1.5); o25_h=poisson_over(h_xg,2.5); o35_h=poisson_over(h_xg,3.5)
    o15_a=poisson_over(a_xg,1.5); o25_a=poisson_over(a_xg,2.5); o35_a=poisson_over(a_xg,3.5)
    over55=poisson_over(total_xg,5.5); btts2=o15_h*o15_a
    win_h=1/(1+10**((ra-rh-HOME_ADV)/400))
    is_gold_game=(o25_h>=0.59 or o25_a>=0.59 or btts2>=0.60 or over55>=0.60 or win_h>=0.63)
    if o25_h>=0.59:
        ctx="{:.1f} scored vs {:.1f} conceded".format(hs['avg_s'],hs['avg_c']) if hs else ""
        insights_list.append((o25_h,home+" Over 2.5",ctx,league))
    if o25_a>=0.59:
        ctx="{:.1f} scored vs {:.1f} conceded".format(aws['avg_s'],aws['avg_c']) if aws else ""
        insights_list.append((o25_a,away+" Over 2.5",ctx,league))
    if btts2>=0.60:
        insights_list.append((btts2,"BTTS2 - "+home+" vs "+away,"",league))
    def chip_html(p,label,is_gold=False):
        c="chip is-gold" if (is_gold and p>=0.59) else "chip"
        return '<span class="'+c+'">'+label+' {:.1f}%'.format(p*100)+'</span>'
    def team_block(name,stats,o15,o25,o35):
        if not stats:
            return '<div class="team"><div class="team__head"><span class="team__name">'+name+'</span><span class="form-dots empty">no matches logged</span></div><div class="chips">'+chip_html(o15,"O1.5")+' '+chip_html(o25,"O2.5",True)+' '+chip_html(o35,"O3.5")+'</div><span class="no-data">No result history yet</span></div>'
        gold25=o25>=0.59
        return '<div class="team"><div class="team__head"><span class="team__name">'+name+'</span><span class="form-dots">'+stats["dots"]+'</span></div><div class="chips">'+chip_html(o15,"O1.5")+' '+chip_html(o25,"O2.5",gold25)+' '+chip_html(o35,"O3.5")+'</div><details class="form-detail"><summary>avg {:.1f} scored - {:.1f} conceded - last {}</summary><p>{}</p></details></div>'.format(stats["avg_s"],stats["avg_c"],stats["count"],stats["detail"])
    win_cls="is-gold" if win_h>=0.63 else ""
    over_cls="is-gold" if over55>=0.60 else ""
    btts_cls="is-gold" if btts2>=0.60 else ""
    fav=home if win_h>0.5 else away
    block='<article class="game" data-league="'+league+'" data-gold="'+("1" if is_gold_game else "0")+'"><div class="game__meta"><span class="tag '+league+'">'+league+'</span><span class="game__date">'+d+'</span><span class="game__elo">ELO {:.0f} - {:.0f}<br>xG {:.2f}</span></div><h3 class="game__title">'+home+' vs '+away+'</h3><p class="game__fav">Favorite: <strong>'+fav+'</strong></p><div class="headline"><div class="stat '+win_cls+'"><span class="stat__label">Win</span><span class="stat__value">{:.1f}%</span></div><div class="stat '+over_cls+'"><span class="stat__label">Over 5.5</span><span class="stat__value">{:.1f}%</span></div><div class="stat '+btts_cls+'"><span class="stat__label">BTTS2</span><span class="stat__value">{:.1f}%</span></div></div>'+team_block(home,hs,o15_h,o25_h,o35_h)+team_block(away,aws,o15_a,o25_a,o35_a)+'</article>'
    block=block.format(rh,ra,total_xg,win_h*100,over55*100,btts2*100)
    games_html_parts.append(block)
insights_list=sorted(insights_list,key=lambda x:x[0],reverse=True)[:8]
insights_html="".join(['<div class="insight-row"><span class="dot '+lg+'"></span><span class="who">'+who+'<span class="ctx">'+ctx+'</span></span><span class="pct">{:.1f}%</span></div>'.format(prob*100) for prob,who,ctx,lg in insights_list])
if not insights_html:
    insights_html='<div class="insight-row">No gold today</div>'
games_html="\n".join(games_html_parts)
now_str=datetime.now().strftime("%d Sep %H:%M")
html_head='<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V10 Auto</title><style>body{margin:0;background:#0a0e18;color:#eef1fb;font-family:sans-serif;padding-bottom:20px}.topbar{position:sticky;top:0;background:#0a0e18;padding:14px;border-bottom:1px solid #212c46}.chip-btn{border:1px solid #212c46;background:#121a2c;color:#8b96b8;padding:6px 13px;border-radius:999px}.chip-btn.active{background:#eef1fb;color:#0a0e18}.insights{background:#121a2c;border-left:3px solid #22e0a0;border-radius:12px;padding:14px;margin:14px}.game{background:#121a2c;border:1px solid #212c46;border-radius:14px;padding:14px;margin:12px}.game[data-gold="1"]{border-left:3px solid #22e0a0}.tag{padding:3px 8px;border-radius:6px;font-size:10px}.tag.SHL{color:#2fd6c0;background:rgba(47,214,192,0.16)}.tag.CZECH{color:#ff6b7a;background:rgba(255,107,122,0.16)}.tag.DEL{color:#8fa3ff;background:rgba(143,163,255,0.16)}.stat{display:inline-block;width:32%;background:#0d1424;text-align:center;border-radius:9px;padding:8px}.stat.is-gold{background:rgba(34,224,160,0.14)}.chip{background:#0d1424;padding:4px 9px;border-radius:7px;font-size:11px}.chip.is-gold{color:#22e0a0;background:rgba(34,224,160,0.16)}.form-dots span{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:2px}.w{background:#22e0a0}.l{background:#ff6b7a}.d{background:#5b6588} </style></head><body>'
html_top='<div class="topbar"><h1>V10 Auto - SHL + Czech + DEL</h1><div>'+now_str+' - '+str(len(results_data))+' results - '+str(len(fixtures))+' fixtures</div><div><button class="chip-btn active" data-league="ALL">All</button><button class="chip-btn" data-league="SHL">SHL</button><button class="chip-btn" data-league="CZECH">Czech</button><button class="chip-btn" data-league="DEL">DEL</button><label><input type="checkbox" id="goldOnly"> Gold only</label></div></div><main><div class="insights"><h2>Gold reads</h2>'+insights_html+'</div>'
html_end='</main><script>var chips=document.querySelectorAll(".chip-btn");var goldToggle=document.getElementById("goldOnly");var games=document.querySelectorAll(".game");var activeLeague="ALL";function applyFilter(){games.forEach(function(g){var league=g.getAttribute("data-league");var gold=g.getAttribute("data-gold")==="1";var leagueOk=activeLeague==="ALL"||league===activeLeague;var goldOk=!goldToggle.checked||gold;g.style.display=(leagueOk&&goldOk)?"":"none";});}chips.forEach(function(c){c.addEventListener("click",function(){chips.forEach(function(x){x.classList.remove("active");});c.classList.add("active");activeLeague=c.getAttribute("data-league");applyFilter();});});goldToggle.addEventListener("change",applyFilter);</script></body></html>'
final_html=html_head+html_top+games_html+html_end
import os
os.makedirs("docs",exist_ok=True)
open("docs/index.html","w",encoding="utf-8").write(final_html)
print("built")
