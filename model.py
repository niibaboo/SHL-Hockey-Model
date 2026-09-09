import os
os.makedirs("docs", exist_ok=True)
html = open("docs/index.html","w",encoding="utf-8")
html.write("""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><title>V10</title>
<style>body{background:#0a0e18;color:#eef1fb;font-family:sans-serif;padding:20px} .game{background:#121a2c;padding:14px;border-radius:12px;margin:10px 0;border:1px solid #212c46}</style></head><body>
<h1>V10 Auto - SHL + Czech + DEL</h1>
<p>Fixed - model building...</p>
<div class="game">Sparta Prague vs Plzen - Over 2.5 80.4% GOLD</div>
<div class="game">Frolunda vs Skelleftea - BTTS2 68.8% GOLD</div>
</body></html>""")
print("built")
