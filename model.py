import csv, math, os
from datetime import datetime
from collections import defaultdict

FIXTURES_FILE='fixtures.csv'
RESULTS_FILE='results.csv'
OUTPUT_FILE='docs/index.html'
LEAGUE_AVGS={'SHL':5.2,'CZECH':5.4,'DEL':6.1}
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
        with open(RESULTS_FILE,encoding='utf-8') as ff:
            reader=csv.DictReader(ff)
            for r in reader:
                try:
                    h=r['home'].strip(); a=r['away'].strip()
                    hg=int(r['hg']); ag=int(r['ag'])
                    results.append(r)
                    form[h].append({'gf':hg,'ga':ag,'opp':a})
                    form[a].append({'gf':ag,'ga':hg,'opp':h})
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
        with open(FIXTURES_FILE,encoding='utf-8') as ff:
            reader=csv.DictReader(ff)
            for row in reader:
                if row.get('home'): fixtures.append(row)
    return fixtures

def team_stats(team, form):
    games=form.get(team,[])[-5:]
    if not games: return None
    scored=sum(g['gf'] for g in games)/len(games)
    conceded=sum(g['ga'] for g in games)/len(games)
    dots=''.join(['<span class="w"></span>' if g['gf']>g['ga'] else '<span class="l"></span>' if g['gf']<g['ga'] else '<span class="d"></span>' for g in reversed(games)])
    detail=', '.join([f"{g['gf']}-{g['ga']} vs {g['opp']}" for g in reversed(games)])
    return {'avg_s':scored,'avg_c':conceded,'dots':dots,'detail':detail,'count':len(games)}

ratings,form,results_data=load_results()
fixtures=load_fixtures()
games_html_parts=[]
insights_list=[]

for fx in fixtures:
    league=fx.get('league','SHL').upper().strip()
    home=fx['home'].strip(); away=fx['away'].strip()
    date_raw=fx.get('date','')
    try: d=datetime.fromisoformat(date_raw).strftime('%d Sep')
    except: d=date_raw[:10] if date_raw else ''
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
        ctx=f"{hs['avg_s']:.1f} scored vs {hs['avg_c']:.1f} conceded" if hs else ''
        insights_list.append((o25_h,f"{home} Over 2.5",ctx,league))
    if o25_a>=0.59:
        ctx=f"{aws['avg_s']:.1f} scored vs {aws['avg_c']:.1f} conceded" if aws else ''
        insights_list.append((o25_a,f"{away} Over 2.5",ctx,league))
    if btts2>=0.60:
        insights_list.append((btts2,f"BTTS2 - {home} vs {away}","",league))

    def chip(p,label,gold=False):
        c='chip is-gold' if (gold and p>=0.59) else 'chip'
        return f'<span class="{c}">{label} {p*100:.1f}%</span>'

    def team_block(name,stats,o15,o25,o35):
        if not stats:
            return f'<div class="team"><div class="team__head"><span class="team__name">{name}</span><span class="form-dots empty">no matches logged</span></div><div class="chips">{chip(o15,"O1.5")} {chip(o25,"O2.5",True)} {chip(o35,"O3.5")}</div><span class="no-data">No result history yet</span></div>'
        return f'<div class="team"><div class="team__head"><span class="team__name">{name}</span><span class="form-dots">{stats["dots"]}</span></div><div class="chips">{chip(o15,"O1.5")} {chip(o25,"O2.5",True)} {chip(o35,"O3.5")}</div><details class="form-detail"><summary>avg {stats["avg_s"]:.1f} scored · {stats["avg_c"]:.1f} conceded — last {stats["count"]}</summary><p>{stats["detail"]}</p></details></div>'

    win_cls='is-gold' if win_h>=0.63 else ''
    over_cls='is-gold' if over55>=0.60 else ''
    btts_cls='is-gold' if btts2>=0.60 else ''
    fav=home if win_h>0.5 else away
    block=f'<article class="game" data-league="{league}" data-gold="{1 if is_gold_game else 0}"><div class="game__meta"><span class="tag {league}">{league}</span><span class="game__date">{d}</span><span class="game__elo">ELO {rh:.0f} · {ra:.0f}<br>xG {total_xg:.1f} ({h_xg:.2f}–{a_xg:.2f})</span></div><h3 class="game__title">{home} <span class="vs">vs</span> {away}</h3><p class="game__fav">Favorite: <strong>{fav}</strong></p><div class="headline"><div class="stat {win_cls}"><span class="stat__label">Win</span><span class="stat__value">{win_h*100:.1f}%</span></div><div class="stat {over_cls}"><span class="stat__label">Over 5.5</span><span class="stat__value">{over55*100:.1f}%</span></div><div class="stat {btts_cls}"><span class="stat__label">BTTS2</span><span class="stat__value">{btts2*100:.1f}%</span></div></div>{team_block(home,hs,o15_h,o25_h,o35_h)}{team_block(away,aws,o15_a,o25_a,o35_a)}</article>'
    games_html_parts.append(block)

insights_list=sorted(insights_list,key=lambda x:x[0],reverse=True)[:10]
insights_html=''
for prob,who,ctx,lg in insights_list:
    if ctx:
        insights_html+=f'<div class="insight-row"><span class="dot {lg}"></span><span class="who">{who}<span class="ctx">{ctx}</span></span><span class="pct">{prob*100:.1f}%</span></div>'
    else:
        insights_html+=f'<div class="insight-row"><span class="dot {lg}"></span><span class="who">{who}</span><span class="pct">{prob*100:.1f}%</span></div>'
if not insights_html:
    insights_html='<div class="insight-row"><span class="who">No gold today</span></div>'

games_html='\n'.join(games_html_parts)
now_str=datetime.now().strftime('%d Sep %H:%M')

num_results = len(results_data)
num_fixtures = len(fixtures)
num_gold = sum(1 for part in games_html_parts if 'data-gold="1"' in part)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>V10 SHL+CZECH+DEL Auto</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#0a0e18;
  --surface:#121a2c;
  --surface-2:#0d1424;
  --line:#212c46;
  --ink:#eef1fb;
  --ink-dim:#8b96b8;
  --ink-faint:#5b6588;
  --green:#22e0a0;
  --amber:#ffcf5c;
  --red:#ff6b7a;
  --shl:#2fd6c0;
  --czech:#ff6b7a;
  --del:#8fa3ff;
}}
*{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%}}
body{{
  margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-variant-numeric:tabular-nums;padding-bottom:32px;
}}
h1,h2,h3,.num{{font-family:"Space Grotesk",-apple-system,sans-serif}}
a{{color:inherit}}
.topbar{{position:sticky;top:0;z-index:20;background:rgba(10,14,24,0.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:14px 16px 12px}}
.topbar h1{{margin:0;font-size:17px;font-weight:700;letter-spacing:0.2px}}
.topbar .meta{{margin:3px 0 12px;font-size:12px;color:var(--ink-dim)}}
.filters{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.chip-btn{{appearance:none;border:1px solid var(--line);background:var(--surface);color:var(--ink-dim);font-size:12.5px;font-weight:600;padding:6px 13px;border-radius:999px;cursor:pointer}}
.chip-btn.active{{background:var(--ink);color:#0a0e18;border-color:var(--ink)}}
.gold-toggle{{display:flex;align-items:center;gap:6px;margin-left:auto;font-size:12.5px;color:var(--ink-dim);font-weight:600}}
.gold-toggle input{{width:32px;height:18px;accent-color:var(--green)}}
main{{padding:14px 16px 0;max-width:640px;margin:0 auto}}
.insights{{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--green);border-radius:12px;padding:14px 15px;margin-bottom:18px}}
.insights h2{{margin:0 0 10px;font-size:13.5px;font-weight:700;color:var(--green)}}
.insight-row{{display:flex;align-items:baseline;gap:8px;padding:6px 0;border-top:1px solid var(--line);font-size:13px}}
.insight-row:first-of-type{{border-top:none}}
.dot{{width:7px;height:7px;border-radius:50%;flex:none;margin-top:5px}}
.dot.SHL{{background:var(--shl)}}
.dot.CZECH{{background:var(--czech)}}
.dot.DEL{{background:var(--del)}}
.insight-row .who{{flex:1;color:var(--ink)}}
.insight-row .pct{{font-weight:700;color:var(--green);font-family:"Space Grotesk",sans-serif}}
.insight-row .ctx{{display:block;font-size:11px;color:var(--ink-faint);font-weight:400}}
.section-label{{font-size:11.5px;color:var(--ink-faint);font-weight:600;margin:22px 2px 8px}}
.game{{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px 15px 15px;margin-bottom:12px}}
.game[data-gold="1"]{{border-left:3px solid var(--green)}}
.game__meta{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.tag{{font-size:10.5px;font-weight:700;letter-spacing:0.3px;padding:3px 8px;border-radius:6px}}
.tag.SHL{{background:rgba(47,214,192,0.16);color:var(--shl)}}
.tag.CZECH{{background:rgba(255,107,122,0.16);color:var(--czech)}}
.tag.DEL{{background:rgba(143,163,255,0.16);color:var(--del)}}
.game__date{{font-size:12px;color:var(--ink-dim)}}
.game__elo{{margin-left:auto;font-size:10.5px;color:var(--ink-faint);text-align:right;line-height:1.3}}
.game__title{{margin:2px 0 2px;font-size:16px;font-weight:600}}
.game__title .vs{{color:var(--ink-faint);font-weight:400;margin:0 5px;font-size:13px}}
.game__fav{{margin:0 0 12px;font-size:12px;color:var(--ink-dim)}}
.game__fav strong{{color:var(--ink);font-weight:600}}
.headline{{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:13px}}
.stat{{background:var(--surface-2);border-radius:9px;padding:8px 4px;text-align:center}}
.stat.is-gold{{background:rgba(34,224,160,0.14)}}
.stat__label{{display:block;font-size:10px;color:var(--ink-faint);margin-bottom:2px}}
.stat__value{{display:block;font-size:15px;font-weight:700;font-family:"Space Grotesk",sans-serif;color:var(--ink)}}
.stat.is-gold .stat__value{{color:var(--green)}}
.team{{padding:10px 0;border-top:1px solid var(--line)}}
.team__head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}}
.team__name{{font-size:13.5px;font-weight:600}}
.form-dots{{display:flex;gap:3px}}
.form-dots span{{width:8px;height:8px;border-radius:50%;display:inline-block}}
.form-dots .w{{background:var(--green)}}
.form-dots .l{{background:var(--red)}}
.form-dots .d{{background:var(--ink-faint)}}
.form-dots.empty{{font-size:10.5px;color:var(--ink-faint);font-weight:400}}
.chips{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px}}
.chip{{font-size:11.5px;background:var(--surface-2);color:var(--ink-dim);padding:4px 9px;border-radius:7px;font-weight:600}}
.chip.is-gold{{background:rgba(34,224,160,0.16);color:var(--green)}}
.form-detail{{font-size:11.5px;color:var(--ink-faint)}}
.form-detail summary{{cursor:pointer;list-style:none;color:var(--ink-dim)}}
.form-detail summary::-webkit-details-marker{{display:none}}
.form-detail summary::before{{content:"▸ ";display:inline-block}}
.form-detail[open] summary::before{{content:"▾ "}}
.form-detail p{{margin:6px 0 0;line-height:1.5}}
.no-data{{font-size:11.5px;color:var(--ink-faint);border:1px dashed var(--line);border-radius:7px;padding:6px 9px;display:inline-block}}
:focus-visible{{outline:2px solid var(--green);outline-offset:2px}}
</style>
</head>
<body>
<div class="topbar">
  <h1>V10 Auto — SHL + Czech + DEL</h1>
  <div class="meta">{now_str} · {num_results} results logged · {num_fixtures} real fixtures · {num_fixtures} games</div>
  <div class="filters">
    <button class="chip-btn active" data-league="ALL">All</button>
    <button class="chip-btn" data-league="SHL">SHL</button>
    <button class="chip-btn" data-league="CZECH">Czech</button>
    <button class="chip-btn" data-league="DEL">DEL</button>
    <label class="gold-toggle"><input type="checkbox" id="goldOnly"> Gold only</label>
  </div>
</div>
<main>
  <div class="insights">
    <h2>Gold reads — {num_gold} of {num_fixtures} games flagged</h2>
    {insights_html}
  </div>
  <div class="section-label">All {num_fixtures} fixtures</div>
  {games_html}
</main>
<script>
(function(){{
  var chips = document.querySelectorAll('.chip-btn');
  var goldToggle = document.getElementById('goldOnly');
  var games = document.querySelectorAll('.game');
  var activeLeague = 'ALL';
  function applyFilter(){{
    games.forEach(function(g){{
      var league = g.getAttribute('data-league');
      var gold = g.getAttribute('data-gold') === '1';
      var leagueOk = activeLeague === 'ALL' || league === activeLeague;
      var goldOk = !goldToggle.checked || gold;
      g.style.display = (leagueOk && goldOk) ? '' : 'none';
    }});
  }}
  chips.forEach(function(c){{
    c.addEventListener('click', function(){{
      chips.forEach(function(x){{ x.classList.remove('active'); }});
      c.classList.add('active');
      activeLeague = c.getAttribute('data-league');
      applyFilter();
    }});
  }});
  goldToggle.addEventListener('change', applyFilter);
}})();
</script>
</body>
</html>
"""

html = HTML_TEMPLATE.format(
    now_str=now_str,
    num_results=num_results,
    num_fixtures=num_fixtures,
    num_gold=num_gold,
    insights_html=insights_html,
    games_html=games_html,
)

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Wrote {OUTPUT_FILE}: {num_fixtures} games, {num_gold} gold, {num_results} results logged")
