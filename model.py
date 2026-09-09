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
