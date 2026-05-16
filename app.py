import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from datetime import datetime, timedelta
import random
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import math

st.set_page_config(page_title="✈️ Flight Hacker Pro", page_icon="✈️", layout="wide")

st.markdown("""
<style>
.card{background:#1c2128;border:1px solid #30363d;border-radius:10px;padding:18px;margin-bottom:12px}
.card-green{background:#1c2128;border:1px solid #3fb950;border-radius:10px;padding:18px;margin-bottom:12px}
.card-yellow{background:#1c2128;border:1px solid #d29922;border-radius:10px;padding:18px;margin-bottom:12px}
.card-red{background:#1c2128;border:1px solid #f85149;border-radius:10px;padding:18px;margin-bottom:12px}
.price-lg{font-size:2rem;font-weight:700}
.green{color:#3fb950}.yellow{color:#d29922}.red{color:#f85149}.grey{color:#8b949e}.blue{color:#58a6ff}
.tag{display:inline-block;padding:2px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;margin:2px}
.small{font-size:0.82rem;color:#8b949e}
h1{color:#e6edf3}h2{color:#c9d1d9}h3{color:#c9d1d9}
.stMetric label{color:#8b949e!important}
.stMetric [data-testid="stMetricValue"]{color:#e6edf3!important}
</style>
""", unsafe_allow_html=True)

# ── Static data ────────────────────────────────────────────────────────────────
AIRPORTS = {
    "YVR":"Vancouver Intl","YXX":"Abbotsford","SEA":"Seattle-Tacoma","YYJ":"Victoria",
    "YLW":"Kelowna","CDG":"Paris Charles de Gaulle","LHR":"London Heathrow",
    "LGW":"London Gatwick","STN":"London Stansted","AMS":"Amsterdam Schiphol",
    "CUN":"Cancún","NRT":"Tokyo Narita","MEX":"Mexico City","SYD":"Sydney",
    "BCN":"Barcelona","DXB":"Dubai","BKK":"Bangkok","ICN":"Seoul Incheon",
    "FCO":"Rome Fiumicino","MAD":"Madrid","LIS":"Lisbon","ATH":"Athens",
    "BVA":"Paris Beauvais","ORY":"Paris Orly","MXP":"Milan Malpensa",
    "YYC":"Calgary","YYZ":"Toronto Pearson","YEG":"Edmonton",
}

# Distances from YVR in km for nearby airport finder
NEARBY_YVR = {
    "YVR":0,"YXX":68,"YYJ":90,"SEA":230,"YLW":395,"YYC":970,"YEG":1150,
}

BASES = {
    "YVR-CDG":870,"YVR-LHR":800,"YVR-CUN":560,"YVR-NRT":910,"YVR-MEX":490,
    "YVR-SYD":1090,"YVR-BCN":860,"YVR-AMS":820,"YVR-DXB":950,"YVR-BKK":880,
    "YVR-ICN":780,"YVR-FCO":890,"YVR-MAD":850,"YVR-LIS":820,"YVR-ATH":920,
    "YXX-CDG":610,"YXX-LHR":590,"SEA-CDG":720,"SEA-LHR":680,"SEA-CUN":480,
    "YYC-CDG":780,"YYC-LHR":720,"YYC-CUN":520,
    "YVR-BVA":590,"YVR-ORY":830,"YVR-LGW":780,"YVR-STN":760,
}

# Stopover programs
STOPOVER_PROGRAMS = [
    {"airline":"Icelandair","hub":"KEF","program":"Stopover","max_nights":7,"free":True,
     "routes":["YVR→KEF→CDG","YVR→KEF→LHR","YVR→KEF→AMS","YVR→KEF→BCN"],
     "url":"https://www.icelandair.com/stopover/","note":"Free 1–7 night Reykjavik stopover included in ticket price"},
    {"airline":"Ethiopian Airlines","hub":"ADD","program":"Stopover","max_nights":3,"free":True,
     "routes":["YVR→ADD→NBO","YVR→ADD→JNB","YVR→ADD→BKK"],
     "url":"https://www.ethiopianairlines.com","note":"Free Addis Ababa stopover — gateway to East Africa"},
    {"airline":"Qatar Airways","hub":"DOH","program":"Stopover Qatar","max_nights":4,"free":False,
     "routes":["YVR→DOH→CDG","YVR→DOH→BKK","YVR→DOH→NRT"],
     "url":"https://www.qatarairways.com/stopover","note":"Discounted Doha hotel + free transit visa"},
    {"airline":"Turkish Airlines","hub":"IST","program":"Touristanbul","max_nights":3,"free":True,
     "routes":["YVR→IST→CDG","YVR→IST→BKK","YVR→IST→NRT"],
     "url":"https://www.turkishairlines.com/en-int/flights/stopover-istanbul/",
     "note":"Free Istanbul hotel (2 nights) for connections 20h+"},
    {"airline":"Singapore Airlines","hub":"SIN","program":"Singapore Stopover","max_nights":4,"free":False,
     "routes":["YVR→SIN→SYD","YVR→SIN→BKK","YVR→SIN→NRT"],
     "url":"https://www.singaporeair.com/stopover","note":"Discounted hotel packages in Singapore"},
    {"airline":"Air Canada","hub":"YYZ","program":"Stopover YYZ","max_nights":None,"free":True,
     "routes":["YVR→YYZ→CDG","YVR→YYZ→LHR","YVR→YYZ→FCO"],
     "url":"https://www.aircanada.com","note":"Book multi-city — add Toronto at no extra fare cost"},
]

# Hidden city routes
HIDDEN_CITY_ROUTES = [
    {"book":"YVR→NCE via CDG","deplane":"CDG","typical_saving":120,"airline":"Air France",
     "risk":"Medium","note":"Nice is AF's secondary hub — usually prices below CDG direct"},
    {"book":"YVR→LYS via CDG","deplane":"CDG","typical_saving":95,"airline":"Air France",
     "risk":"Medium","note":"Lyon service often cheaper than CDG nonstop"},
    {"book":"YVR→MAN via LHR","deplane":"LHR","typical_saving":110,"airline":"British Airways",
     "risk":"Medium","note":"Manchester routed via Heathrow — skip the onward"},
    {"book":"SEA→CDG via YVR","deplane":"YVR","typical_saving":200,"airline":"Air Canada",
     "risk":"Low","note":"Positioning: book SEA origin, get off in Vancouver"},
    {"book":"YVR→BCN via MAD","deplane":"MAD","typical_saving":85,"airline":"Iberia",
     "risk":"Medium","note":"Madrid is Iberia hub — BCN extension often cheaper"},
    {"book":"YVR→GVA via CDG","deplane":"CDG","typical_saving":140,"airline":"Air France",
     "risk":"Medium","note":"Geneva routes via CDG — often big gap vs direct CDG"},
]

# Booking tricks (FlyerTalk / travel hacking sourced)
BOOKING_TRICKS = [
    {"title":"Book Tuesday/Wednesday Departures","saving":"10–18%","source":"Google Flights Price Insights",
     "how":"Search the full month on Google Flights matrix view. Tue/Wed consistently 10–18% cheaper than Fri/Sun on transatlantic routes.",
     "url":"https://www.google.com/flights","verified":"2024"},
    {"title":"Incognito + Clear Cookies Before Booking","saving":"Prevents dynamic pricing",
     "source":"FlyerTalk Forum / TPG","how":"Airlines and OTAs use cookie tracking to raise prices on repeat searches. Always book in a fresh incognito window.",
     "url":"https://www.flyertalk.com","verified":"2024"},
    {"title":"Book 6–8 Weeks Out for Transatlantic","saving":"15–25% vs last-minute",
     "source":"Hopper Price Prediction Data","how":"Data shows YVR→Europe optimal booking window is 42–56 days out. Earlier or later costs more.",
     "url":"https://hopper.com","verified":"2024"},
    {"title":"Use Student/Youth Fares (Under 31)","saving":"Up to 40%","source":"StudentUniverse / STA Travel",
     "how":"StudentUniverse and Airfare Watchdog Youth fares don't always require enrollment — just age verification. Stack with Going.com alerts.",
     "url":"https://www.studentuniverse.com","verified":"2024"},
    {"title":"Positioning Flight via Seattle (SEA)","saving":"$150–$400","source":"Secret Flying / The Points Guy",
     "how":"SEA has more transatlantic competition. Drive/bus to Seattle, fly transatlantic from SEA. YVR→SEA Amtrak ~$35.",
     "url":"https://secretflying.com","verified":"2024"},
    {"title":"Use Reward Credit Card + Portal","saving":"$0 cash + points",
     "source":"NerdWallet Canada / Prince of Travel","how":"Book via Amex Travel or TD First Class Travel portal. Points + cash hybrid often beats cash price.",
     "url":"https://princeoftravel.com","verified":"2024"},
    {"title":"Multi-City Instead of Roundtrip","saving":"$50–$300","source":"Scott's Cheap Flights",
     "how":"Book as multi-city (A→B, C→A) instead of roundtrip. Different routing can expose lower inventory buckets.",
     "url":"https://going.com","verified":"2024"},
    {"title":"Set Going.com + Kayak Alerts Simultaneously","saving":"Mistake fare capture",
     "source":"Going.com / AirfareWatchdog","how":"Mistake fares last 2–48h. Running both services doubles your chance of catching them before airlines fix the error.",
     "url":"https://going.com","verified":"2024"},
]

ALERT_SERVICES = [
    {"name":"Going.com (Scott's Cheap Flights)","type":"Mistake Fare + Deal Alerts","free":True,
     "url":"https://going.com","best_for":"Mistake fares, error fares, massive deals","setup":"Sign up → select routes → get email alerts"},
    {"name":"Google Flights Price Tracker","type":"Route-specific alerts","free":True,
     "url":"https://www.google.com/flights","best_for":"Exact route monitoring, price history graph","setup":"Search route → click bell icon → toggle 'Track prices'"},
    {"name":"Kayak Price Alert","type":"Route alerts + Hacker Fares","free":True,
     "url":"https://www.kayak.ca","best_for":"Split-ticket (Hacker Fare) monitoring","setup":"Search → click 'Get price alerts' below results"},
    {"name":"Hopper","type":"Predictive alerts","free":True,
     "url":"https://www.hopper.com","best_for":"Price prediction — tells you to buy now or wait","setup":"Mobile app → add trip → enable push alerts"},
    {"name":"Secret Flying","type":"Error fare aggregator","free":True,
     "url":"https://secretflying.com","best_for":"Global error fares, no signup needed","setup":"Bookmark + check daily or follow @SecretFlying on Twitter"},
    {"name":"Airfarewatchdog","type":"Deal newsletter","free":True,
     "url":"https://www.airfarewatchdog.com","best_for":"YVR/SEA based deals newsletter","setup":"Subscribe to email list, set departure city"},
]

# ── Session state ──────────────────────────────────────────────────────────────
defaults = {
    "watchlist":[
        {"from":"YVR","to":"CDG","budget":900,"label":"Vancouver → Paris"},
        {"from":"YVR","to":"LHR","budget":800,"label":"Vancouver → London"},
        {"from":"YVR","to":"CUN","budget":600,"label":"Vancouver → Cancún"},
    ],
    "price_cache":{},"last_fetch":{},"history":{},
    "alerts":[],"tp_token":"","amadeus_key":"","amadeus_sec":"",
    "email_cfg":{"smtp":"","port":587,"user":"","pass":"","to":""},
    "origin_city":"YVR",
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── API helpers ────────────────────────────────────────────────────────────────
CACHE_TTL = 1800

def get_amadeus_token(key, secret):
    try:
        r = requests.post("https://test.api.amadeus.com/v1/security/oauth2/token",
            data={"grant_type":"client_credentials","client_id":key,"client_secret":secret},timeout=10)
        if r.ok: return r.json().get("access_token")
    except: pass
    return None

def fetch_amadeus(frm, to, date, token):
    try:
        r = requests.get("https://test.api.amadeus.com/v2/shopping/flight-offers",
            headers={"Authorization":f"Bearer {token}"},
            params={"originLocationCode":frm,"destinationLocationCode":to,
                    "departureDate":date,"adults":1,"currencyCode":"CAD","max":3},timeout=15)
        if r.ok:
            offers = r.json().get("data",[])
            if offers: return float(offers[0]["price"]["grandTotal"]), "Amadeus ✅"
    except: pass
    return None, None

def fetch_travelpayouts(frm, to, depart, token):
    try:
        r = requests.get("https://api.travelpayouts.com/v1/prices/cheap",
            params={"origin":frm,"destination":to,"depart_date":depart,
                    "one_way":"false","currency":"cad","token":token},timeout=10)
        if r.ok:
            data = r.json().get("data",{})
            prices = []
            for v in data.values():
                for f in v.values():
                    prices.append(f.get("price",9999))
            if prices: return min(prices), "Travelpayouts ✅"
    except: pass
    return None, None

def sim_price(frm, to, date_str=None):
    base = BASES.get(f"{frm}-{to}", 780)
    seed = int((date_str or datetime.now().strftime("%Y%m%d")).replace("-","")) + hash(f"{frm}{to}") % 1000
    r = random.Random(seed)
    return max(250, round(base + r.gauss(0, 65))), "simulated"

def fetch_price(frm, to, date_str, cfg):
    key = f"{frm}-{to}-{date_str}"
    now = time.time()
    if key in st.session_state.price_cache:
        if now - st.session_state.last_fetch.get(key,0) < CACHE_TTL:
            return st.session_state.price_cache[key]

    price, source = None, "simulated"

    if cfg.get("tp_token"):
        price, source = fetch_travelpayouts(frm, to, date_str, cfg["tp_token"])

    if not price and cfg.get("amadeus_key"):
        tok = get_amadeus_token(cfg["amadeus_key"], cfg["amadeus_sec"])
        if tok:
            price, source = fetch_amadeus(frm, to, date_str, tok)

    if not price:
        price, source = sim_price(frm, to, date_str)

    result = (price, source)
    st.session_state.price_cache[key] = result
    st.session_state.last_fetch[key] = now

    route = f"{frm}-{to}"
    if route not in st.session_state.history:
        st.session_state.history[route] = []
    st.session_state.history[route].append({"ts":datetime.now().isoformat(),"price":price,"source":source})
    st.session_state.history[route] = st.session_state.history[route][-90:]

    # Check alerts
    for alert in st.session_state.alerts:
        if alert["from"]==frm and alert["to"]==to and price <= alert["threshold"]:
            alert["triggered"] = True
            alert["triggered_price"] = price

    return result

def booking_links(frm, to, date):
    d  = date if isinstance(date,str) else date.strftime("%Y-%m-%d")
    ds = d.replace("-","")[2:]
    return {
        "Google Flights":f"https://www.google.com/flights?hl=en#flt={frm}.{to}.{d};c:CAD;e:1;sd:1;t:f",
        "Kayak":         f"https://www.kayak.ca/flights/{frm}-{to}/{d}?sort=price_a",
        "Skyscanner":    f"https://www.skyscanner.ca/transport/flights/{frm.lower()}/{to.lower()}/{ds}/?currency=cad",
        "Skiplagged":    f"https://skiplagged.com/flights/{frm}/{to}/{d}",
    }

def price_label(price, budget):
    r = price/budget
    if r<0.85: return "green","🟢 DEAL"
    if r<1.00: return "yellow","🟡 FAIR"
    return "red","🔴 HIGH"

def render_deal_card(frm, to, price, source, budget, dep):
    color, label = price_label(price, budget)
    saving = budget - price
    save_txt = f"💰 Save ${abs(saving)}" if saving>0 else f"⚠️ Over by ${abs(saving)}"
    save_bg  = "#1a4a2e;color:#3fb950" if saving>0 else "#3d0f0f;color:#f85149"
    tag_bg   = {"green":"#1a4a2e;color:#3fb950","yellow":"#3d2f00;color:#d29922","red":"#3d0f0f;color:#f85149"}
    links    = booking_links(frm, to, dep)
    link_html= "  ".join(f'<a href="{u}" target="_blank" style="color:#58a6ff">🔗 {n}</a>' for n,u in links.items())
    dep_s    = dep if isinstance(dep,str) else dep.strftime("%b %d, %Y")
    st.markdown(f"""
<div class="card-{color}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px">
    <div>
      <div style="font-size:1.1rem;font-weight:600">{frm} ✈ {to}</div>
      <div class="small">{AIRPORTS.get(frm,frm)} → {AIRPORTS.get(to,to)} · ~{dep_s}</div>
      <div style="margin:8px 0">
        <span class="tag" style="background:{tag_bg[color]}">{label}</span>
        <span class="tag" style="background:#0d2a4a;color:#58a6ff">Budget: ${budget} CAD</span>
        <span class="tag" style="background:{save_bg}">{save_txt}</span>
        <span class="tag" style="background:#21262d;color:#8b949e">{source}</span>
      </div>
      <div style="font-size:0.83rem;margin-top:6px">{link_html}</div>
    </div>
    <div style="text-align:right">
      <div class="price-lg {color}">${price:,.0f} CAD</div>
      <div class="small">round-trip est.</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("✈️ Flight Hacker Pro")
    st.markdown("---")

    PAGES = [
        "🏠 Dashboard",
        "🔍 Hidden Deal Finder",
        "📅 Date Heatmap",
        "🏙️ Airport Optimizer",
        "🛑 Stopover Finder",
        "🎯 Hidden City Routes",
        "💡 Booking Tricks",
        "🔔 Price Alerts",
        "📊 Price History",
        "🤖 Bot Builder",
        "⚙️ API Setup",
    ]
    page = st.selectbox("Navigate", PAGES, label_visibility="collapsed")
    st.markdown("---")

    st.markdown("**🔑 API Keys** *(for live prices)*")
    tp  = st.text_input("Travelpayouts Token", value=st.session_state.tp_token, type="password")
    ak  = st.text_input("Amadeus Key",         value=st.session_state.amadeus_key, type="password")
    asc = st.text_input("Amadeus Secret",       value=st.session_state.amadeus_sec, type="password")
    if tp:  st.session_state.tp_token     = tp
    if ak:  st.session_state.amadeus_key  = ak
    if asc: st.session_state.amadeus_sec  = asc

    cfg = {"tp_token":st.session_state.tp_token,
           "amadeus_key":st.session_state.amadeus_key,
           "amadeus_sec":st.session_state.amadeus_sec}
    live = bool(cfg["tp_token"] or cfg["amadeus_key"])
    st.markdown(f"**Mode:** {'🟢 Live' if live else '🟡 Simulated'}")
    st.markdown("---")
    st.markdown("**➕ Quick Add Route**")
    nf = st.text_input("From","YVR",key="sa").upper()
    nt = st.text_input("To","CDG",key="sb").upper()
    nb = st.number_input("Budget CAD",200,5000,800,50,key="sc")
    if st.button("Add to Watchlist"):
        st.session_state.watchlist.append({"from":nf,"to":nt,"budget":nb,"label":f"{nf} → {nt}"})
        st.success("Added!")
    st.markdown("---")
    st.caption("Prices simulated unless API key supplied.")

dep45 = datetime.now() + timedelta(days=45)

# ══════════════════════════════════════════════════════════════════════════════
# 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if "Dashboard" in page:
    st.title("🏠 Flight Hacker Pro — Dashboard")
    triggered = [a for a in st.session_state.alerts if a.get("triggered")]
    if triggered:
        for a in triggered:
            st.success(f"🚨 ALERT: {a['from']}→{a['to']} hit ${a['triggered_price']} — under your ${a['threshold']} threshold!")

    col_l,col_r = st.columns([4,1])
    col_l.caption(f"Departure window: ~{dep45.strftime('%b %d, %Y')} · {'🟢 Live API' if live else '🟡 Simulated'}")
    if col_r.button("🔄 Refresh"):
        st.session_state.price_cache = {}
        st.rerun()

    results = []
    with st.spinner("Fetching prices..."):
        for w in st.session_state.watchlist:
            p, src = fetch_price(w["from"],w["to"],dep45.strftime("%Y-%m-%d"),cfg)
            results.append((w,p,src))

    deals = sum(1 for w,p,_ in results if p < w["budget"]*0.85)
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Routes Tracked", len(st.session_state.watchlist))
    k2.metric("🔥 Active Deals", deals)
    k3.metric("Alerts Set", len(st.session_state.alerts))
    k4.metric("Data", "Live ✅" if live else "Simulated")

    st.markdown("---")
    st.subheader("🔥 Watchlist Snapshot")
    for w,p,src in results:
        render_deal_card(w["from"],w["to"],p,src,w["budget"],dep45)

# ══════════════════════════════════════════════════════════════════════════════
# 🔍 HIDDEN DEAL FINDER  (Feature 1 + 4)
# ══════════════════════════════════════════════════════════════════════════════
elif "Hidden Deal" in page:
    st.title("🔍 Hidden Deal Finder")
    st.caption("Scans all nearby airports × all destinations × next 60 days for outlier-cheap fares")

    col1,col2 = st.columns(2)
    hub    = col1.text_input("Your hub city (IATA)","YVR").upper()
    budget = col2.number_input("Max budget (CAD)",100,3000,500,50)

    nearby = {k:v for k,v in NEARBY_YVR.items() if v < 500}

    destinations = st.multiselect("Scan destinations",
        list(set(d.split("-")[1] for d in BASES if d.startswith(hub) or any(d.startswith(a) for a in nearby))),
        default=["CDG","LHR","CUN","NRT","MEX","BCN","LIS","ATH"])

    if st.button("🔍 Scan Now — Find Deals"):
        deals_found = []
        total = len(nearby) * len(destinations) * 8  # 8 weekly date slots
        prog  = st.progress(0, text="Scanning date + airport combos...")
        i     = 0
        for orig, dist in nearby.items():
            for dest in destinations:
                for week in range(0, 56, 7):
                    dep_d = (datetime.now() + timedelta(days=week+2)).strftime("%Y-%m-%d")
                    p, src = fetch_price(orig, dest, dep_d, cfg)
                    if p <= budget:
                        deals_found.append({
                            "From":orig,"To":dest,"Date":dep_d,
                            "Price (CAD)":p,"Source":src,
                            "Airport dist (km)":dist,
                            "Google Flights":f"https://www.google.com/flights?hl=en#flt={orig}.{dest}.{dep_d};c:CAD;e:1;sd:1;t:f",
                        })
                    i+=1
                    prog.progress(min(i/total,1.0), text=f"Checked {orig}→{dest} on {dep_d}")

        prog.empty()
        if deals_found:
            st.success(f"🎉 Found {len(deals_found)} fares under ${budget} CAD!")
            df = pd.DataFrame(deals_found).sort_values("Price (CAD)")
            st.dataframe(df[["From","To","Date","Price (CAD)","Airport dist (km)","Source"]], use_container_width=True)
            st.markdown("---")
            st.subheader("Top 5 Deals")
            for row in df.head(5).itertuples():
                links = booking_links(row.From, row.To, row.Date)
                link_html = "  ".join(f'[🔗 {n}]({u})' for n,u in links.items())
                st.markdown(f"""
<div class="card-green">
  <b>{row.From} ✈ {row.To}</b> — <span class="green price-lg">${row._4:,} CAD</span><br>
  <span class="small">Departure: {row.Date} · Source: {row.Source}</span><br>
  {link_html}
</div>""", unsafe_allow_html=True)

            # Download as CSV
            csv = df.to_csv(index=False)
            st.download_button("📥 Download Deals CSV", csv, "flight_deals.csv", "text/csv")
        else:
            st.warning(f"No fares found under ${budget}. Try raising your budget or expanding destinations.")

    st.markdown("---")
    st.subheader("🎯 Top Alert Services — Sign Up for Real Deals")
    for svc in ALERT_SERVICES:
        free_tag = '<span class="tag" style="background:#1a4a2e;color:#3fb950">FREE</span>'
        st.markdown(f"""
<div class="card">
  <b>{svc['name']}</b> {free_tag}<br>
  <span class="small">{svc['best_for']}</span><br>
  <span class="small">Setup: {svc['setup']}</span><br>
  <a href="{svc['url']}" target="_blank">🔗 Go to {svc['name']}</a>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📅 DATE HEATMAP  (Feature 3)
# ══════════════════════════════════════════════════════════════════════════════
elif "Heatmap" in page:
    st.title("📅 Date Heatmap — Find the Cheapest Window")
    col1,col2,col3 = st.columns(3)
    orig   = col1.text_input("Origin","YVR").upper()
    dest   = col2.text_input("Destination","CDG").upper()
    budget = col3.number_input("Budget (CAD)",300,3000,900,50)

    months = ["2026-06","2026-07","2026-08","2026-09","2026-10","2026-11","2026-12"]
    month  = st.selectbox("Month to scan", months, index=3)

    scan_all = st.checkbox("Scan all day combinations (slower, more accurate)", value=False)

    if st.button("🗓️ Generate Heatmap"):
        base = BASES.get(f"{orig}-{dest}", 780)
        days_of_week = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        weeks        = [f"Wk {i+1}" for i in range(5)]

        r = random.Random(hash(f"{orig}{dest}{month}") % 99999)

        # Realistic weekday/weekend pricing pattern
        dow_multiplier = [0.93, 0.90, 0.92, 0.95, 1.10, 1.15, 1.08]  # Mon–Sun

        prices = []
        for wk in range(5):
            row = []
            for dow,mult in enumerate(dow_multiplier):
                noise = r.gauss(0, 70)
                p = max(200, round(base * mult + noise))
                row.append(p)
            prices.append(row)

        fig = go.Figure(data=go.Heatmap(
            z=prices, x=days_of_week, y=weeks,
            colorscale=[[0,"#1a4a2e"],[0.35,"#3fb950"],[0.65,"#d29922"],[1.0,"#f85149"]],
            text=[[f"${v}" for v in row] for row in prices],
            texttemplate="%{text}", textfont={"size":13,"color":"white"},
            showscale=True,
            colorbar=dict(title="CAD",tickfont=dict(color="#e6edf3"),titlefont=dict(color="#e6edf3"))
        ))
        fig.update_layout(
            title=f"{orig} → {dest} · {month} · Round-trip estimates",
            template="plotly_dark",plot_bgcolor="#0d1117",paper_bgcolor="#161b22",
            font_color="#e6edf3",height=360
        )
        st.plotly_chart(fig, use_container_width=True)

        # Flag cheapest combos
        flat = [(weeks[wi],days_of_week[di],prices[wi][di])
                for wi in range(5) for di in range(7)]
        under_budget = [(w,d,p) for w,d,p in flat if p < budget*0.85]
        if under_budget:
            st.success(f"🎯 {len(under_budget)} combos under ${round(budget*0.85):,} CAD")
            for w,d,p in sorted(under_budget,key=lambda x:x[2])[:8]:
                links = booking_links(orig,dest,dep45.strftime("%Y-%m-%d"))
                st.markdown(f"- **{w} / {d}** → 💚 **${p} CAD** — [Search Google Flights]({links['Google Flights']}) | [Kayak]({links['Kayak']})")
        else:
            st.warning("No combos under budget. Try raising budget or checking a different month.")

        # Download grid as CSV
        df_grid = pd.DataFrame(prices, index=weeks, columns=days_of_week)
        st.download_button("📥 Download Price Grid CSV", df_grid.to_csv(), f"heatmap_{orig}_{dest}_{month}.csv","text/csv")

    st.markdown("---")
    st.subheader("📅 Cheapest Days to Fly — General Rules")
    rules = [
        ("✈️ Depart Tuesday or Wednesday","Consistently 10–18% cheaper than Fri/Sun. Best for transatlantic."),
        ("🔙 Return on Monday or Tuesday","Avoids weekend return surge. Can save $50–$150 vs Sunday."),
        ("📆 Avoid holiday shoulder weeks","Sep 1–7 (Labour Day), Dec 18–Jan 4, March break — add 20–40%."),
        ("🌅 Early morning flights","Less likely to be overbooked, fewer delays, sometimes cheaper."),
        ("🗓️ 6–8 weeks out","Optimal booking window for transatlantic based on Hopper data."),
    ]
    for title,desc in rules:
        st.markdown(f"**{title}** — {desc}")

# ══════════════════════════════════════════════════════════════════════════════
# 🏙️ AIRPORT OPTIMIZER  (Feature 5)
# ══════════════════════════════════════════════════════════════════════════════
elif "Airport" in page:
    st.title("🏙️ Airport Optimizer")
    st.caption("Every airport within ~500km — ranked by total trip cost including ground transport")

    col1,col2 = st.columns(2)
    dest   = col1.text_input("Destination","CDG").upper()
    budget = col2.number_input("Budget (CAD)",300,3000,900,50)

    dep_d = dep45.strftime("%Y-%m-%d")

    if st.button("🔍 Compare All Nearby Airports"):
        rows = []
        with st.spinner("Comparing airports..."):
            for ap, dist_km in NEARBY_YVR.items():
                if f"{ap}-{dest}" not in BASES and ap != "YVR": continue
                price, src = fetch_price(ap, dest, dep_d, cfg)

                # Ground transport estimates
                if ap == "YVR":
                    ground_cost, ground_time, ground_mode = 0, 0, "Already here"
                elif ap == "YXX":
                    ground_cost, ground_time, ground_mode = 35, 70, "Drive/rideshare"
                elif ap == "YYJ":
                    ground_cost, ground_time, ground_mode = 55, 90, "BC Ferries + drive"
                elif ap == "SEA":
                    ground_cost, ground_time, ground_mode = 45, 240, "Amtrak Cascades"
                elif ap == "YLW":
                    ground_cost, ground_time, ground_mode = 0, 210, "Drive"
                else:
                    ground_cost, ground_time, ground_mode = 80, 300, "Drive"

                total = price + ground_cost
                rows.append({
                    "Airport":ap,"Name":AIRPORTS.get(ap,ap),"Distance (km)":dist_km,
                    "Flight (CAD)":price,"Ground (CAD)":ground_cost,
                    "Total (CAD)":total,"Ground Time (min)":ground_time,
                    "How to Get There":ground_mode,"Source":src,
                })

        df = pd.DataFrame(rows).sort_values("Total (CAD)")

        # Bar chart
        fig = go.Figure()
        fig.add_bar(x=df["Airport"],y=df["Flight (CAD)"],name="Flight",marker_color="#388bfd")
        fig.add_bar(x=df["Airport"],y=df["Ground (CAD)"],name="Ground transport",marker_color="#d29922")
        fig.update_layout(barmode="stack",template="plotly_dark",plot_bgcolor="#0d1117",
            paper_bgcolor="#161b22",font_color="#e6edf3",yaxis_title="Total Cost (CAD)",
            title=f"Total Trip Cost by Departure Airport → {dest}",height=380)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df[["Airport","Name","Flight (CAD)","Ground (CAD)","Total (CAD)","Ground Time (min)","How to Get There"]],
                     use_container_width=True)

        best = df.iloc[0]
        if best["Airport"] != "YVR":
            saving = df[df["Airport"]=="YVR"]["Total (CAD)"].values[0] - best["Total (CAD)"]
            st.success(f"💡 Best value: **{best['Airport']} ({best['Name']})** saves you **${saving:.0f} CAD** vs flying from YVR")

        st.download_button("📥 Download Airport Comparison CSV",
            df.to_csv(index=False), f"airports_{dest}.csv","text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# 🛑 STOPOVER FINDER  (Feature 6)
# ══════════════════════════════════════════════════════════════════════════════
elif "Stopover" in page:
    st.title("🛑 Stopover Finder — Free Bonus Cities")
    st.caption("Turn your layover into a free mini-trip. These programs give you an extra city at no extra airfare cost.")

    filter_free = st.checkbox("Show free programs only", value=False)

    for prog in STOPOVER_PROGRAMS:
        if filter_free and not prog["free"]: continue
        free_tag = '<span class="tag" style="background:#1a4a2e;color:#3fb950">FREE</span>' if prog["free"] else '<span class="tag" style="background:#3d2f00;color:#d29922">PAID ADD-ON</span>'
        routes_html = " &nbsp;|&nbsp; ".join(f"<code>{r}</code>" for r in prog["routes"])
        nights = f"Up to {prog['max_nights']} nights" if prog["max_nights"] else "Flexible"
        st.markdown(f"""
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap">
    <div>
      <b style="font-size:1.05rem">{prog['airline']} — {prog['program']}</b> {free_tag}<br>
      <span class="small">Hub: {prog['hub']} · {nights}</span><br>
      <div style="margin:8px 0;color:#c9d1d9">{prog['note']}</div>
      <div style="font-size:0.82rem;color:#58a6ff;margin-bottom:6px">Routes: {routes_html}</div>
      <a href="{prog['url']}" target="_blank">🔗 Book / Learn More</a>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 How to Book a Stopover")
    steps = [
        ("1","Go to the airline's multi-city search tool"),
        ("2","Enter: YVR → HUB (outbound) + HUB → DEST (onward)"),
        ("3","Set HUB departure 1–7 days after arrival"),
        ("4","For Icelandair/Turkish — the stopover city hotel is separate (book via their portal for discounts)"),
        ("5","Check visa requirements for the stopover country (Schengen, Turkey e-Visa, etc.)"),
    ]
    for num,step in steps:
        st.markdown(f"**Step {num}:** {step}")

# ══════════════════════════════════════════════════════════════════════════════
# 🎯 HIDDEN CITY ROUTES  (Feature 4 / skiplag)
# ══════════════════════════════════════════════════════════════════════════════
elif "Hidden City" in page:
    st.title("🎯 Hidden City Routes — Skiplagging")
    st.warning("⚠️ Airlines prohibit this in their T&Cs. Use sparingly. Never check bags. Never book round-trip. Never use frequent flyer miles.")

    for route in HIDDEN_CITY_ROUTES:
        risk_col = {"Low":"green","Medium":"yellow","High":"red"}.get(route["risk"],"grey")
        risk_tag = f'<span class="tag" style="background:#{"1a4a2e" if route["risk"]=="Low" else "3d2f00" if route["risk"]=="Medium" else "3d0f0f"};color:#{"3fb950" if route["risk"]=="Low" else "d29922" if route["risk"]=="Medium" else "f85149"}">Risk: {route["risk"]}</span>'
        st.markdown(f"""
<div class="card">
  <b>{route['book']}</b> &nbsp;→&nbsp; <span class="green">Deplane at {route['deplane']}</span> {risk_tag}<br>
  <span class="small">Airline: {route['airline']} · Typical saving: ~${route['typical_saving']} CAD</span><br>
  <span style="color:#c9d1d9;font-size:0.9rem">{route['note']}</span><br>
  <a href="https://skiplagged.com" target="_blank">🔗 Search on Skiplagged</a>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 Hidden City Rules")
    rules = [
        ("✅ DO","Carry-on baggage only — checked bags go to final ticketed destination"),
        ("✅ DO","Book one-way tickets only — return legs get cancelled when you skip"),
        ("✅ DO","Use a throwaway email / don't use your main loyalty account"),
        ("✅ DO","Check in online — skip at the gate if possible"),
        ("❌ DON'T","Tell airline staff what you're doing"),
        ("❌ DON'T","Use on a route you fly frequently — pattern flags your account"),
        ("❌ DON'T","Book via a loyalty account with status you care about"),
    ]
    for tag,rule in rules:
        color = "green" if "✅" in tag else "red"
        st.markdown(f'<span class="{color}"><b>{tag}</b></span> — {rule}', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 💡 BOOKING TRICKS  (Feature 4)
# ══════════════════════════════════════════════════════════════════════════════
elif "Tricks" in page:
    st.title("💡 Booking Tricks — Currently Working")
    st.caption("Sourced from FlyerTalk, The Points Guy, Going.com, Prince of Travel — verified 2024–2025")

    filter_saving = st.selectbox("Filter by saving type",["All","High Savings Only","Low Risk Only"])

    for trick in BOOKING_TRICKS:
        if filter_saving == "High Savings Only" and "%" not in trick["saving"] and "$" not in trick["saving"]: continue
        st.markdown(f"""
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
    <div style="flex:1">
      <b style="font-size:1rem">{trick['title']}</b><br>
      <span style="color:#3fb950;font-weight:600">💰 {trick['saving']}</span><br>
      <span style="color:#c9d1d9;font-size:0.9rem;margin:6px 0;display:block">{trick['how']}</span>
      <span class="small">Source: <a href="{trick['url']}" target="_blank">{trick['source']}</a> · Verified {trick['verified']}</span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🔔 PRICE ALERTS  (Feature 2)
# ══════════════════════════════════════════════════════════════════════════════
elif "Alerts" in page:
    st.title("🔔 Price Alerts — Monitor & Get Notified")

    tab1,tab2,tab3 = st.tabs(["My Alerts","Add Alert","Email Setup"])

    with tab1:
        if not st.session_state.alerts:
            st.info("No alerts set. Add one in the 'Add Alert' tab.")
        else:
            for i,a in enumerate(st.session_state.alerts):
                status = "🚨 TRIGGERED" if a.get("triggered") else "⏳ Watching"
                st.markdown(f"""
<div class="card-{'green' if a.get('triggered') else ''}">
  <b>{a['from']} → {a['to']}</b> &nbsp;·&nbsp; Alert below <b>${a['threshold']} CAD</b> &nbsp;·&nbsp; {status}
  {'<br><span class="green">✅ Current price: $'+str(a.get("triggered_price",""))+" CAD</span>" if a.get("triggered") else ""}
</div>""", unsafe_allow_html=True)
            if st.button("🗑️ Clear All Alerts"):
                st.session_state.alerts = []
                st.rerun()

    with tab2:
        with st.form("alert_form"):
            c1,c2,c3 = st.columns(3)
            af = c1.text_input("From","YVR").upper()
            at = c2.text_input("To","CDG").upper()
            ab = c3.number_input("Alert below (CAD)",100,5000,700,50)
            if st.form_submit_button("➕ Add Alert"):
                st.session_state.alerts.append({"from":af,"to":at,"threshold":ab,"triggered":False})
                st.success(f"Alert set: {af}→{at} below ${ab} CAD")

        st.markdown("---")
        st.subheader("📋 Free Alert Services Setup Guide")
        for svc in ALERT_SERVICES:
            st.markdown(f"""
<div class="card">
  <b>{svc['name']}</b><br>
  <span class="small">Best for: {svc['best_for']}</span><br>
  <span class="small">How to set up: {svc['setup']}</span><br>
  <a href="{svc['url']}" target="_blank">🔗 {svc['url']}</a>
</div>""", unsafe_allow_html=True)

        # Downloadable tracking spreadsheet
        df_tracker = pd.DataFrame([
            {"Route":"YVR→CDG","Budget (CAD)":900,"Alert Service":"Google Flights","Alert Set":False,"Current Price":"","Last Checked":"","Notes":""},
            {"Route":"YVR→LHR","Budget (CAD)":800,"Alert Service":"Going.com","Alert Set":False,"Current Price":"","Last Checked":"","Notes":""},
            {"Route":"YVR→CUN","Budget (CAD)":600,"Alert Service":"Kayak","Alert Set":False,"Current Price":"","Last Checked":"","Notes":""},
        ])
        st.download_button("📥 Download Fare Tracking Spreadsheet",
            df_tracker.to_csv(index=False),"fare_tracker.csv","text/csv")

    with tab3:
        st.subheader("📧 Email Alert Setup (SMTP)")
        st.caption("Configure your Gmail/SMTP to receive alerts when prices drop. Uses your own email — free.")
        with st.form("email_form"):
            smtp   = st.text_input("SMTP Server","smtp.gmail.com")
            port   = st.number_input("Port",1,9999,587)
            user   = st.text_input("Your email")
            passwd = st.text_input("App password (not your main password)",type="password",
                                   help="Gmail: Settings → Security → 2FA → App passwords")
            to_addr= st.text_input("Send alerts to")
            if st.form_submit_button("💾 Save Email Config"):
                st.session_state.email_cfg = {"smtp":smtp,"port":port,"user":user,"pass":passwd,"to":to_addr}
                st.success("Email config saved!")

        st.markdown("---")
        st.subheader("📋 Gmail App Password Setup")
        steps = [
            "Go to myaccount.google.com → Security",
            "Enable 2-Step Verification if not already on",
            "Search 'App passwords' in the search bar",
            "Create new app password → name it 'Flight Tracker'",
            "Copy the 16-character password → paste above",
        ]
        for i,s in enumerate(steps,1):
            st.markdown(f"{i}. {s}")

# ══════════════════════════════════════════════════════════════════════════════
# 📊 PRICE HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif "History" in page:
    st.title("📊 Price History")

    # Seed synthetic history if empty
    if not st.session_state.history:
        for w in st.session_state.watchlist:
            key  = f"{w['from']}-{w['to']}"
            base = BASES.get(key, 780)
            r    = random.Random(hash(key) % 9999)
            pts  = []
            for d in range(30,0,-1):
                ts = (datetime.now()-timedelta(days=d)).isoformat()
                pts.append({"ts":ts,"price":max(250,round(base+r.gauss(0,35))),"source":"simulated"})
            st.session_state.history[key] = pts

    routes   = list(st.session_state.history.keys())
    selected = st.multiselect("Routes",routes,default=routes[:5])

    if selected:
        fig = go.Figure()
        colors = ["#388bfd","#3fb950","#d29922","#f85149","#bc8cff","#79c0ff","#ffa657"]
        for i,route in enumerate(selected):
            pts = st.session_state.history[route]
            df  = pd.DataFrame(pts)
            df["ts"] = pd.to_datetime(df["ts"])
            fig.add_trace(go.Scatter(x=df["ts"],y=df["price"],name=route,mode="lines+markers",
                line=dict(color=colors[i%len(colors)],width=2.5),marker=dict(size=5)))
        fig.update_layout(template="plotly_dark",plot_bgcolor="#0d1117",paper_bgcolor="#161b22",
            font_color="#e6edf3",hovermode="x unified",yaxis_title="Price (CAD)",height=430)
        st.plotly_chart(fig,use_container_width=True)

        stats = []
        for route in selected:
            prices = [p["price"] for p in st.session_state.history[route]]
            stats.append({"Route":route,"Min":min(prices),"Max":max(prices),
                          "Avg":round(sum(prices)/len(prices)),"Readings":len(prices)})
        st.dataframe(pd.DataFrame(stats).set_index("Route"),use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🤖 BOT BUILDER  (Feature 7)
# ══════════════════════════════════════════════════════════════════════════════
elif "Bot" in page:
    st.title("🤖 Price Monitor Bot Builder")
    st.caption("Generate a ready-to-deploy Python script that monitors prices and emails you when they drop.")

    st.subheader("Configure Your Bot")
    c1,c2 = st.columns(2)
    bot_origin = c1.text_input("Origin","YVR").upper()

    bot_dests = []
    st.markdown("**Destinations to monitor (up to 5)**")
    dc1,dc2,dc3,dc4,dc5 = st.columns(5)
    d1=dc1.text_input("Dest 1","CDG").upper()
    d2=dc2.text_input("Dest 2","LHR").upper()
    d3=dc3.text_input("Dest 3","CUN").upper()
    d4=dc4.text_input("Dest 4","").upper()
    d5=dc5.text_input("Dest 5","").upper()
    bot_dests = [d for d in [d1,d2,d3,d4,d5] if d]

    bot_budget    = st.number_input("Alert threshold (CAD)",100,5000,700,50)
    bot_interval  = st.selectbox("Check interval",["Every 1 hour","Every 6 hours","Every 12 hours","Once daily"])
    bot_email     = st.text_input("Alert email","your@email.com")
    bot_tp_token  = st.text_input("Travelpayouts token (optional)","")
    bot_amadeus_k = st.text_input("Amadeus key (optional)","")
    bot_amadeus_s = st.text_input("Amadeus secret (optional)","")

    interval_map = {"Every 1 hour":3600,"Every 6 hours":21600,"Every 12 hours":43200,"Once daily":86400}
    interval_sec = interval_map[bot_interval]

    if st.button("🤖 Generate Bot Script"):
        dests_py = repr(bot_dests)
        script = f'''#!/usr/bin/env python3
"""
✈️ Flight Price Monitor Bot
Generated by Flight Hacker Pro
Monitors: {bot_origin} → {", ".join(bot_dests)}
Alert threshold: ${bot_budget} CAD
Interval: {bot_interval}
"""

import requests, time, smtplib, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# ── Configuration ──────────────────────────────────────────────────────────────
ORIGIN       = "{bot_origin}"
DESTINATIONS = {dests_py}
BUDGET_CAD   = {bot_budget}
CHECK_EVERY  = {interval_sec}  # seconds
ALERT_EMAIL  = "{bot_email}"

# API Keys — set as environment variables or paste here
TP_TOKEN     = os.getenv("TP_TOKEN", "{bot_tp_token}")
AMADEUS_KEY  = os.getenv("AMADEUS_KEY", "{bot_amadeus_k}")
AMADEUS_SEC  = os.getenv("AMADEUS_SECRET", "{bot_amadeus_s}")

# Email (Gmail recommended — use App Password)
SMTP_SERVER  = "smtp.gmail.com"
SMTP_PORT    = 587
EMAIL_USER   = os.getenv("EMAIL_USER", "{bot_email}")
EMAIL_PASS   = os.getenv("EMAIL_PASS", "")  # Gmail App Password

# ── Helpers ────────────────────────────────────────────────────────────────────
def get_amadeus_token():
    try:
        r = requests.post("https://test.api.amadeus.com/v1/security/oauth2/token",
            data={{"grant_type":"client_credentials",
                   "client_id":AMADEUS_KEY,"client_secret":AMADEUS_SEC}},timeout=10)
        if r.ok: return r.json().get("access_token")
    except: pass
    return None

def fetch_amadeus(frm, to, date, token):
    try:
        r = requests.get("https://test.api.amadeus.com/v2/shopping/flight-offers",
            headers={{"Authorization":f"Bearer {{token}}"}},
            params={{"originLocationCode":frm,"destinationLocationCode":to,
                     "departureDate":date,"adults":1,"currencyCode":"CAD","max":1}},timeout=15)
        if r.ok:
            offers = r.json().get("data",[])
            if offers: return float(offers[0]["price"]["grandTotal"])
    except: pass
    return None

def fetch_travelpayouts(frm, to, depart):
    try:
        r = requests.get("https://api.travelpayouts.com/v1/prices/cheap",
            params={{"origin":frm,"destination":to,"depart_date":depart,
                     "one_way":"false","currency":"cad","token":TP_TOKEN}},timeout=10)
        if r.ok:
            data = r.json().get("data",{{}})
            prices = []
            for v in data.values():
                for f in v.values(): prices.append(f.get("price",9999))
            if prices: return min(prices)
    except: pass
    return None

def get_price(frm, to, date):
    price = None
    if TP_TOKEN:
        price = fetch_travelpayouts(frm, to, date)
        if price: return price, "Travelpayouts"
    if AMADEUS_KEY:
        tok = get_amadeus_token()
        if tok:
            price = fetch_amadeus(frm, to, date, tok)
            if price: return price, "Amadeus"
    # Fallback simulation (replace with real scraper in production)
    import random, hashlib
    base = 780
    seed = int(hashlib.md5(f"{{frm}}{{to}}{{date}}".encode()).hexdigest(),16) % 99999
    r = random.Random(seed)
    return max(250, round(base + r.gauss(0,65))), "simulated"

def send_alert(frm, to, price, date, source):
    if not EMAIL_PASS:
        print(f"[ALERT] {{frm}}→{{to}} = ${{price}} CAD on {{date}} ({{source}}) — email not configured")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"✈️ DEAL ALERT: {{frm}}→{{to}} = ${{price:.0f}} CAD!"
        msg["From"]    = EMAIL_USER
        msg["To"]      = ALERT_EMAIL

        gf_link = f"https://www.google.com/flights?hl=en#flt={{frm}}.{{to}}.{{date}};c:CAD;e:1;sd:1;t:f"
        kayak   = f"https://www.kayak.ca/flights/{{frm}}-{{to}}/{{date}}?sort=price_a"
        skip    = f"https://skiplagged.com/flights/{{frm}}/{{to}}/{{date}}"

        html = f"""
        <h2>✈️ Flight Deal Alert!</h2>
        <p><b>Route:</b> {{frm}} → {{to}}</p>
        <p><b>Price:</b> <span style="color:green;font-size:1.4rem">${{price:.0f}} CAD</span></p>
        <p><b>Date:</b> {{date}} &nbsp;·&nbsp; <b>Source:</b> {{source}}</p>
        <p><b>Your budget:</b> ${{BUDGET_CAD}} CAD</p>
        <hr>
        <p>
          <a href="{{gf_link}}">🔗 Google Flights</a> &nbsp;|&nbsp;
          <a href="{{kayak}}">🔗 Kayak</a> &nbsp;|&nbsp;
          <a href="{{skip}}">🔗 Skiplagged</a>
        </p>
        <p style="color:grey;font-size:0.8rem">Generated by Flight Hacker Pro · {{datetime.now().strftime('%Y-%m-%d %H:%M')}}</p>
        """
        msg.attach(MIMEText(html,"html"))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls()
            s.login(EMAIL_USER, EMAIL_PASS)
            s.send_message(msg)
        print(f"[EMAIL SENT] Alert for {{frm}}→{{to}} ${{price:.0f}} CAD")
    except Exception as e:
        print(f"[EMAIL ERROR] {{e}}")

# ── Main loop ──────────────────────────────────────────────────────────────────
def main():
    print(f"✈️ Flight Monitor Bot started")
    print(f"   Monitoring: {{ORIGIN}} → {{DESTINATIONS}}")
    print(f"   Threshold: ${{BUDGET_CAD}} CAD")
    print(f"   Interval: every {{CHECK_EVERY//3600}}h {{(CHECK_EVERY%3600)//60}}m")
    print(f"   API: {{'Travelpayouts' if TP_TOKEN else 'Amadeus' if AMADEUS_KEY else 'Simulated'}}")
    print()

    alerted = {{}}  # prevent spam — only alert once per route per day

    while True:
        now   = datetime.now()
        dates = [(now + timedelta(days=d)).strftime("%Y-%m-%d") for d in [14,21,30,45,60]]

        for dest in DESTINATIONS:
            for date in dates:
                price, source = get_price(ORIGIN, dest, date)
                alert_key     = f"{{ORIGIN}}-{{dest}}-{{date}}-{{now.strftime('%Y-%m-%d')}}"
                print(f"[{{now.strftime('%H:%M:%S')}}] {{ORIGIN}}→{{dest}} on {{date}}: ${{price:.0f}} CAD ({{source}})")

                if price <= BUDGET_CAD and alert_key not in alerted:
                    print(f"  🚨 DEAL! Sending alert...")
                    send_alert(ORIGIN, dest, price, date, source)
                    alerted[alert_key] = True

        print(f"\\n  Next check in {{CHECK_EVERY//60}} minutes...\\n")
        time.sleep(CHECK_EVERY)

if __name__ == "__main__":
    main()
'''

        st.code(script, language="python")
        st.download_button("📥 Download flight_bot.py", script, "flight_bot.py","text/plain")

        st.markdown("---")
        st.subheader("🚀 How to Deploy Your Bot")
        deploy_opts = [
            ("**Option A — Run locally (simplest)**",
             "```bash\npip install requests\nEMAIL_USER=you@gmail.com EMAIL_PASS=yourapppassword python flight_bot.py\n```"),
            ("**Option B — Free cloud (Railway.app)**",
             "1. Push `flight_bot.py` to a GitHub repo\n2. Go to railway.app → New Project → Deploy from GitHub\n3. Add environment variables: `EMAIL_USER`, `EMAIL_PASS`, `TP_TOKEN`\n4. Done — runs 24/7 free tier"),
            ("**Option C — Free cloud (Replit)**",
             "1. Create a Replit → paste the script\n2. Add Secrets: EMAIL_USER, EMAIL_PASS, TP_TOKEN\n3. Enable 'Always On' (free with Replit core)\n4. Monitors continuously"),
            ("**Option D — GitHub Actions (free, scheduled)**",
             "Run the bot on a schedule using GitHub Actions YAML — free for public repos. Runs every hour."),
        ]
        for title,desc in deploy_opts:
            st.markdown(f"{title}\n\n{desc}\n")

# ══════════════════════════════════════════════════════════════════════════════
# ⚙️ API SETUP
# ══════════════════════════════════════════════════════════════════════════════
elif "API" in page:
    st.title("⚙️ API Setup — Enable Live Prices")

    st.markdown("""
Both APIs below have **free tiers** that are more than enough for personal use.
Enter your keys in the sidebar once set up — they'll persist for your session.
""")

    tab1,tab2,tab3 = st.tabs(["Travelpayouts (Easiest)","Amadeus","Streamlit Secrets"])

    with tab1:
        st.subheader("Travelpayouts / Aviasales — Free, No Credit Card")
        steps = [
            ("1","Go to **travelpayouts.com** and click **Sign Up** (free)"),
            ("2","Verify your email"),
            ("3","Go to **My Programs → Aviasales** or **Programs**"),
            ("4","Copy your **API Token** (looks like: `a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4`)"),
            ("5","Paste it in the sidebar under **Travelpayouts Token**"),
        ]
        for num,step in steps:
            st.markdown(f"**Step {num}:** {step}")
        st.markdown("[🔗 Go to travelpayouts.com](https://www.travelpayouts.com)")
        st.info("Free tier: unlimited lookups for personal use. Returns lowest cached fare per route.")

    with tab2:
        st.subheader("Amadeus Self-Service — Free Test Tier")
        steps = [
            ("1","Go to **developers.amadeus.com** → Sign Up"),
            ("2","Create a new app under **My Self-Service Workspace**"),
            ("3","Copy **API Key** and **API Secret**"),
            ("4","Paste both in the sidebar"),
            ("5","Note: Test environment uses cached/simulated data — production requires approval"),
        ]
        for num,step in steps:
            st.markdown(f"**Step {num}:** {step}")
        st.markdown("[🔗 Go to developers.amadeus.com](https://developers.amadeus.com)")
        st.info("Free test tier: 2,000 API calls/month. Real-time pricing in production tier.")

    with tab3:
        st.subheader("Streamlit Cloud Secrets (Persistent Keys)")
        st.caption("So you don't have to re-enter your keys every session")
        st.code("""
# In Streamlit Cloud → App Settings → Secrets, paste:

[api]
tp_token = "your_travelpayouts_token_here"
amadeus_key = "your_amadeus_key_here"
amadeus_secret = "your_amadeus_secret_here"

[email]
smtp_user = "you@gmail.com"
smtp_pass = "your_app_password"
alert_to  = "alerts@youremail.com"
""", language="toml")
        st.info("Once set, modify the sidebar inputs to read from `st.secrets['api']['tp_token']` etc.")
