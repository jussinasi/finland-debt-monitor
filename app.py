import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Finland Sovereign Debt Monitor", page_icon="🇫🇮", layout="wide")

BASE = "https://api.tutkihallintoa.fi/central-government-debt/v1"

@st.cache_data(show_spinner=False, ttl=86400)
def fetch(endpoint, lang="EN"):
    r = requests.get(f"{BASE}/{endpoint}", params={"lang": lang}, timeout=30)
    r.raise_for_status()
    return r.json()

@st.cache_data(show_spinner=False, ttl=86400)
def load_redemptions():
    data = fetch("redemptions")
    df = pd.DataFrame(data)
    return df[df["year"] >= 2024].copy()

@st.cache_data(show_spinner=False, ttl=86400)
def load_interest_rate_sensitivity():
    data = fetch("interest-rate-sensitivity")
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    return df

@st.cache_data(show_spinner=False, ttl=86400)
def load_liquid_cash():
    data = fetch("liquid-cash-funds")
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    return df

@st.cache_data(show_spinner=False, ttl=86400)
def load_debt_gdp():
    data = fetch("debt-and-gdp")
    df = pd.DataFrame(data)
    return df[df["year"] >= 2000].copy()

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/b/bc/Flag_of_Finland.svg", width=80)
    st.title("Finland Debt Monitor")
    st.caption("Data: Valtiokonttori · State Treasury")
    page = st.radio("View", [
        "📊 Overview",
        "⚠️ Refinancing Risk",
        "📈 Interest Rate Risk",
        "💧 Liquidity Buffer",
        "🔮 DSA Simulator",
        "🗺️ Feasibility Map",
    ])
    st.divider()
    st.markdown("Source: [Valtiokonttori API](https://avoindata.tutkihallintoa.fi)")
    st.markdown("Built with Streamlit · [GitHub](https://github.com/jussinasi/finland-debt-monitor)")

st.title("🇫🇮 Finland Sovereign Debt Risk Monitor")

if page == "📊 Overview":
    st.subheader("Central Government Debt · Key Metrics")
    with st.spinner("Loading data…"):
        df_gdp = load_debt_gdp()
        df_irs = load_interest_rate_sensitivity()
        df_cash = load_liquid_cash()
    latest_gdp = df_gdp.iloc[-1]
    latest_irs = df_irs.iloc[-1]
    latest_cash = df_cash.iloc[-1]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gross debt (% GDP)", f"{latest_gdp['percentOfGdp']:.1f}%",
              delta=f"{latest_gdp['percentOfGdp'] - df_gdp.iloc[-2]['percentOfGdp']:.1f}pp")
    m2.metric("Debt per capita", f"€{latest_gdp['debtPerCapita']:,.0f}")
    m3.metric("Avg maturity (years)", f"{latest_irs['averageMaturity']:.1f}y")
    m4.metric("Liquid cash (% of debt)", f"{latest_cash['percentOfDebt']:.1f}%")
    st.divider()
    fig = px.area(df_gdp, x="year", y="percentOfGdp",
                  title="Central Government Debt (% of GDP) · 2000–present",
                  labels={"percentOfGdp": "% of GDP", "year": "Year"},
                  color_discrete_sequence=["#1d6fa4"])
    fig.add_hline(y=60, line_dash="dash", line_color="red", line_width=1.5,
                  annotation_text="EU SGP: 60%", annotation_position="top right")
    fig.update_layout(plot_bgcolor="white", yaxis=dict(gridcolor="#eee"))
    st.plotly_chart(fig, use_container_width=True)
    debt_pct = latest_gdp['percentOfGdp']
    debt_total = latest_gdp['totalEur'] / 1e9
    yoy = latest_gdp['percentOfGdp'] - df_gdp.iloc[-2]['percentOfGdp']
    direction = "increased" if yoy > 0 else "decreased"
    if debt_pct > 60:
        st.error("**Finland's central government debt stands at " + f"{debt_pct:.1f}% of GDP ({debt_total:.1f}bn EUR) as of {int(latest_gdp['year'])}**, exceeding the EU SGP 60% reference value. The debt ratio " + direction + f" by {abs(yoy):.1f}pp year-on-year. Current average maturity is {latest_irs['averageMaturity']:.1f} years with a refixing period of {latest_irs['averageFixing']:.1f} years.")
    else:
        st.success("**Finland's central government debt stands at " + f"{debt_pct:.1f}% of GDP ({debt_total:.1f}bn EUR) as of {int(latest_gdp['year'])}**, within the EU SGP 60% reference value. The debt ratio " + direction + f" by {abs(yoy):.1f}pp year-on-year.")

elif page == "⚠️ Refinancing Risk":
    st.subheader("Refinancing Risk · Debt Redemption Profile")
    st.caption("Annual redemptions by instrument type · Source: Valtiokonttori")
    with st.spinner("Loading redemption data…"):
        df = load_redemptions()
    by_year = df.groupby("year").agg(
        total_redemptions=("redemptions", "sum"),
        total_interests=("interests", "sum")
    ).reset_index()
    by_year["total_bn"] = by_year["total_redemptions"] / 1e9
    by_year["interests_bn"] = by_year["total_interests"] / 1e9
    current_year = datetime.now().year
    next_3y = by_year[by_year["year"] <= current_year + 3]["total_redemptions"].sum() / 1e9
    next_1y = by_year[by_year["year"] == current_year + 1]["total_redemptions"].sum() / 1e9
    total = by_year["total_redemptions"].sum() / 1e9
    m1, m2, m3 = st.columns(3)
    m1.metric("Maturing within 1 year", f"EUR{next_1y:.1f}bn")
    m2.metric("Maturing within 3 years", f"EUR{next_3y:.1f}bn")
    m3.metric("Total scheduled redemptions", f"EUR{total:.1f}bn")
    fig = px.bar(
        df.assign(redemptions_bn=df["redemptions"]/1e9),
        x="year", y="redemptions_bn", color="product",
        title="Annual Debt Redemptions by Instrument (EUR bn)",
        labels={"redemptions_bn": "EUR billion", "year": "Year", "product": "Instrument"},
        color_discrete_map={"Serial bonds": "#1d6fa4", "Treasury bills": "#f4a261", "Other debt": "#2a9d8f"})
    fig.update_layout(plot_bgcolor="white", yaxis=dict(gridcolor="#eee"), barmode="stack")
    st.plotly_chart(fig, use_container_width=True)
    peak_year = by_year.loc[by_year["total_bn"].idxmax()]
    st.divider()
    if next_1y > 20:
        st.error(f"High near-term refinancing pressure: EUR{next_1y:.1f}bn matures within the next year and EUR{next_3y:.1f}bn within 3 years. Peak redemption year is {int(peak_year['year'])} with EUR{peak_year['total_bn']:.1f}bn. Concentration in short maturities increases vulnerability to market disruptions.")
    else:
        st.info(f"Refinancing profile: EUR{next_1y:.1f}bn matures within the next year and EUR{next_3y:.1f}bn within 3 years. Peak redemption year is {int(peak_year['year'])} with EUR{peak_year['total_bn']:.1f}bn.")
    with st.expander("Raw data"):
        st.dataframe(by_year[["year", "total_bn", "interests_bn"]].rename(columns={"year": "Year", "total_bn": "Redemptions (EUR bn)", "interests_bn": "Interest (EUR bn)"}), use_container_width=True, hide_index=True)

elif page == "📈 Interest Rate Risk":
    st.subheader("Interest Rate Risk · Sensitivity of Central Government Debt")
    st.caption("Average maturity, refixing period and duration · Source: Valtiokonttori")
    with st.spinner("Loading interest rate sensitivity data…"):
        df = load_interest_rate_sensitivity()
        df_recent = df[df["date"].dt.year >= 2010].copy()
    latest = df.iloc[-1]
    m1, m2, m3 = st.columns(3)
    m1.metric("Average maturity", f"{latest['averageMaturity']:.2f} years")
    m2.metric("Average refixing period", f"{latest['averageFixing']:.2f} years")
    m3.metric("Duration", f"{latest['duration']:.2f} years")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_recent["date"], y=df_recent["averageMaturity"], name="Average maturity", line=dict(color="#1d6fa4", width=2)))
    fig.add_trace(go.Scatter(x=df_recent["date"], y=df_recent["averageFixing"], name="Refixing period", line=dict(color="#e76f51", width=2)))
    fig.add_trace(go.Scatter(x=df_recent["date"], y=df_recent["duration"], name="Duration", line=dict(color="#2a9d8f", width=2, dash="dot")))
    fig.update_layout(title="Interest Rate Sensitivity Indicators (years)", hovermode="x unified", plot_bgcolor="white", yaxis=dict(gridcolor="#eee", title="Years"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Interest Rate Shock Calculator")
    st.caption("Estimate budget impact of a parallel interest rate shift")
    debt_total = load_debt_gdp().iloc[-1]["totalEur"]
    fixing = latest["averageFixing"]
    rollover_share = 1 / fixing if fixing > 0 else 0.2
    shock = st.slider("Interest rate shock (percentage points)", 0.0, 3.0, 1.0, 0.25)
    impact = debt_total * rollover_share * (shock / 100)
    col1, col2 = st.columns(2)
    col1.metric("Annual budget impact", f"EUR{impact/1e6:.0f}m", delta=f"+{shock:.2f}pp shock", delta_color="inverse")
    col2.metric("Rollover share (1/refixing)", f"{rollover_share*100:.1f}% of debt/year")
    st.info(f"A {shock:.2f}pp parallel shift in interest rates would increase Finland's annual interest expenses by approximately EUR{impact/1e6:.0f}m ({impact/1e9:.2f}bn EUR), based on a refixing period of {fixing:.1f} years implying ~{rollover_share*100:.1f}% of debt repricing annually.")

elif page == "💧 Liquidity Buffer":
    st.subheader("Liquidity Buffer · Liquid Cash Funds")
    st.caption("State Treasury liquid cash position · Source: Valtiokonttori")
    with st.spinner("Loading liquidity data…"):
        df = load_liquid_cash()
        df_recent = df[df["date"].dt.year >= 2010].copy()
    latest = df.iloc[-1]
    cash_bn = latest["cashFundsEndOfMonth"] / 1e9
    pct = latest["percentOfDebt"]
    monthly_spend_estimate = 5.0
    months_coverage = cash_bn / monthly_spend_estimate
    m1, m2, m3 = st.columns(3)
    m1.metric("Liquid cash (latest)", f"EUR{cash_bn:.1f}bn")
    m2.metric("As % of total debt", f"{pct:.1f}%")
    m3.metric("Est. months of coverage", f"~{months_coverage:.1f} months")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_recent["date"], y=df_recent["cashFundsEndOfMonth"] / 1e9, name="Liquid cash (EUR bn)", fill="tozeroy", line=dict(color="#1d6fa4", width=2), fillcolor="rgba(29,111,164,0.15)"))
    fig.update_layout(title="Liquid Cash Funds (EUR bn)", hovermode="x unified", plot_bgcolor="white", yaxis=dict(gridcolor="#eee", title="EUR billion"), xaxis=dict(title=""))
    st.plotly_chart(fig, use_container_width=True)
    if months_coverage < 3:
        st.error(f"Low liquidity buffer: Current cash of EUR{cash_bn:.1f}bn covers approximately {months_coverage:.1f} months of estimated expenditure ({pct:.1f}% of debt) — below comfortable levels.")
    elif months_coverage < 6:
        st.warning(f"Moderate liquidity buffer: Current cash of EUR{cash_bn:.1f}bn covers approximately {months_coverage:.1f} months of estimated expenditure ({pct:.1f}% of debt).")
    else:
        st.success(f"Adequate liquidity buffer: Current cash of EUR{cash_bn:.1f}bn covers approximately {months_coverage:.1f} months of estimated expenditure ({pct:.1f}% of debt).")

elif page == "🔮 DSA Simulator":
    st.subheader("Debt Sustainability Analysis · Finland")
    st.caption("Model: delta_d = (r - g) * d + primary deficit · Source: Valtiokonttori")
    with st.spinner("Loading debt data…"):
        df_gdp = load_debt_gdp()
        df_irs = load_interest_rate_sensitivity()
    latest = df_gdp.iloc[-1]
    latest_irs = df_irs.iloc[-1]
    debt0 = latest["percentOfGdp"]
    r_default = float(latest_irs["averageFixing"])
    g_default = 1.2
    pb_default = -2.0
    pb_star_now = ((r_default/100 - g_default/100) / (1 + g_default/100)) * debt0
    adj_needed = pb_star_now - pb_default
    hist_max_surplus = 1.5

    st.markdown("### Policy Dashboard")
    pa, pb_col, pc, pd_col = st.columns(4)
    pa.metric("Required primary balance", f"{pb_star_now:+.1f}% GDP", help="Primary balance that stabilises debt at current level")
    pb_col.metric("Current primary balance (est.)", f"{pb_default:+.1f}% GDP")
    pc.metric("Adjustment needed", f"{adj_needed:+.1f}pp", delta="of GDP", delta_color="off")
    pd_col.metric("Historical max surplus", f"{hist_max_surplus:+.1f}% GDP", delta="feasibility benchmark", delta_color="off")

    sens = debt0 / 100
    if adj_needed > hist_max_surplus:
        msg = (
            "Required adjustment exceeds Finland's historical fiscal capacity. "
            "Stabilising debt at " + f"{debt0:.1f}% GDP requires a primary balance of {pb_star_now:+.1f}% GDP — "
            "an improvement of " + f"{adj_needed:.1f}pp from the current estimated {pb_default:+.1f}%. "
            "Finland's historical maximum primary surplus is ~" + f"{hist_max_surplus:.1f}% GDP, "
            "suggesting exceptional consolidation effort is needed. "
            "Sensitivity: a 1pp rise in r shifts pb* by ~" + f"{sens:.1f}pp; a 1pp rise in g reduces it by ~{sens:.1f}pp."
        )
        st.error(msg)
    elif adj_needed > 0.5:
        msg = (
            "Significant but potentially feasible adjustment needed. "
            "Stabilising debt requires primary balance of " + f"{pb_star_now:+.1f}% GDP "
            "(gap: " + f"{adj_needed:.1f}pp). This is within Finland's historical range (~{hist_max_surplus:.1f}% max) "
            "but requires sustained fiscal consolidation. "
            "Sensitivity: a 1pp rise in r shifts pb* by ~" + f"{sens:.1f}pp; a 1pp rise in g reduces it by ~{sens:.1f}pp."
        )
        st.warning(msg)
    else:
        st.success(f"Debt is broadly sustainable under current conditions. Required pb* = {pb_star_now:+.1f}% GDP vs current {pb_default:+.1f}% — no significant adjustment required.")

    st.divider()
    st.markdown(f"**Starting point ({int(latest['year'])}):** Gross debt **{debt0:.1f}% GDP** · Avg refixing: **{r_default:.1f} years** · Assumptions: r={r_default:.1f}%, g={g_default:.1f}%")

    def sim(d0, pb, r, g, years=12):
        traj = [d0]
        d = d0
        for _ in range(years):
            d = ((1 + r/100) / (1 + g/100)) * d - pb
            traj.append(d)
        return traj

    def pb_star(r, g, d):
        return ((r/100 - g/100) / (1 + g/100)) * d

    st.markdown("#### Scenario parameters")
    reset_col, _ = st.columns([1, 4])
    with reset_col:
        if st.button("Reset to defaults"):
            for k, v in [("r_b", 3.5), ("g_b", 1.2), ("pb_b", -2.5), ("r_s", 5.0), ("g_s", 0.0), ("pb_s", -3.5), ("r_c", 3.5), ("g_c", 1.2), ("pb_c", -0.5)]:
                st.session_state[k] = v

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Baseline** (current policies)")
        r_b  = st.slider("Interest rate r (%)", 0.0, 8.0, 3.5, 0.1, key="r_b")
        g_b  = st.slider("GDP growth g (%)", -2.0, 5.0, 1.2, 0.1, key="g_b")
        pb_b = st.slider("Primary balance (% GDP)", -6.0, 4.0, -2.5, 0.1, key="pb_b")
    with col_b:
        st.markdown("**Stress** (high rates, low growth)")
        r_s  = st.slider("Interest rate r (%)", 0.0, 8.0, 5.0, 0.1, key="r_s")
        g_s  = st.slider("GDP growth g (%)", -2.0, 5.0, 0.0, 0.1, key="g_s")
        pb_s = st.slider("Primary balance (% GDP)", -6.0, 4.0, -3.5, 0.1, key="pb_s")

    st.markdown("**Consolidation** (fiscal adjustment)")
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        r_c = st.slider("Interest rate r (%)", 0.0, 8.0, 3.5, 0.1, key="r_c")
    with col_c2:
        g_c = st.slider("GDP growth g (%)", -2.0, 5.0, 1.2, 0.1, key="g_c")
    with col_c3:
        pb_c = st.slider("Primary balance (% GDP)", -6.0, 4.0, -0.5, 0.1, key="pb_c")

    years = list(range(int(latest["year"]), int(latest["year"]) + 13))
    t_b = sim(debt0, pb_b, r_b, g_b)
    t_s = sim(debt0, pb_s, r_s, g_s)
    t_c = sim(debt0, pb_c, r_c, g_c)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=t_b, name="Baseline", line=dict(color="#1d6fa4", width=2.5), mode="lines+markers"))
    fig.add_trace(go.Scatter(x=years, y=t_s, name="Stress", line=dict(color="#e63946", width=2, dash="dash"), mode="lines+markers"))
    fig.add_trace(go.Scatter(x=years, y=t_c, name="Consolidation", line=dict(color="#2a9d8f", width=2, dash="dot"), mode="lines+markers"))
    fig.add_hline(y=60, line_dash="dash", line_color="red", line_width=1.5, annotation_text="SGP: 60%", annotation_position="bottom right")
    fig.update_layout(title=f"Finland Debt-to-GDP Trajectory {years[0]}-{years[-1]}", hovermode="x unified", plot_bgcolor="white", yaxis=dict(gridcolor="#eee", title="Gross debt (% GDP)"), xaxis=dict(title="Year", dtick=1), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

    pb_star_b = pb_star(r_b, g_b, debt0)
    gap_b = pb_b - pb_star_b

    v1, v2, v3 = st.columns(3)
    def vcard(label, end, start, rg, pb_cur, pb_req, gap):
        if gap >= 0 and end < 60:
            vl, vc, bg, bc = "Stabilising", "#1a7f37", "#f0fdf4", "#86efac"
        elif gap >= -1 or end < 70:
            vl, vc, bg, bc = "At risk", "#92400e", "#fffbeb", "#fcd34d"
        else:
            vl, vc, bg, bc = "Unsustainable", "#b91c1c", "#fef2f2", "#fca5a5"
        d = "Rising" if end > start+1 else ("Falling" if end < start-1 else "Stable")
        st.markdown(f'<div style="background:{bg};border:1.5px solid {bc};border-radius:10px;padding:14px;text-align:center;"><div style="font-size:0.8em;color:#64748b;text-transform:uppercase;">{label}</div><div style="font-size:1.8em;font-weight:800;color:{vc};">{end:.1f}%</div><div style="font-size:0.82em;color:#475569;">by {years[-1]} · {d}</div><div style="font-size:0.9em;font-weight:700;color:{vc};margin:6px 0 4px 0;">{vl}</div><div style="font-size:0.75em;color:#64748b;">r-g = {rg:+.1f}pp</div><div style="font-size:0.75em;color:#64748b;">Stabilising pb*: {pb_req:+.1f}% GDP</div><div style="font-size:0.75em;color:#64748b;">Gap: {gap:+.1f}pp</div></div>', unsafe_allow_html=True)

    with v1: vcard("Baseline", t_b[-1], debt0, r_b-g_b, pb_b, pb_star_b, gap_b)
    with v2: vcard("Stress", t_s[-1], debt0, r_s-g_s, pb_s, pb_star(r_s,g_s,debt0), pb_s-pb_star(r_s,g_s,debt0))
    with v3: vcard("Consolidation", t_c[-1], debt0, r_c-g_c, pb_c, pb_star(r_c,g_c,debt0), pb_c-pb_star(r_c,g_c,debt0))

    st.divider()
    why = f"driven by r > g ({r_b:.1f}% vs {g_b:.1f}%)" if r_b > g_b else f"supported by r < g ({r_b:.1f}% vs {g_b:.1f}%)"
    if gap_b < -1 and t_b[-1] > 60:
        st.error(f"Key takeaway: Finland's debt is on an unfavourable upward trajectory under baseline, rising from {debt0:.1f}% to {t_b[-1]:.1f}% GDP by {years[-1]}. This is {why}. Stabilising debt requires a primary balance of {pb_star_b:+.1f}% GDP — an adjustment of {abs(gap_b):.1f}pp from the current {pb_b:+.1f}%.")
    elif t_b[-1] > debt0 + 5:
        st.warning(f"Key takeaway: Debt is rising from {debt0:.1f}% to {t_b[-1]:.1f}% GDP by {years[-1]}, {why}. Stabilising pb* = {pb_star_b:+.1f}% GDP (gap: {abs(gap_b):.1f}pp).")
    else:
        st.success(f"Key takeaway: Debt trajectory is broadly sustainable, projected at {t_b[-1]:.1f}% GDP by {years[-1]}, {why}.")

elif page == "🗺️ Feasibility Map":
    import numpy as np
    st.subheader("Fiscal Feasibility Map")
    st.caption("Which combinations of interest rate (r) and GDP growth (g) make debt sustainable? Green = stabilising, Red = unsustainable.")
    with st.spinner("Loading data…"):
        df_gdp = load_debt_gdp()
        df_irs = load_interest_rate_sensitivity()
    latest_gdp = df_gdp.iloc[-1]
    latest_irs = df_irs.iloc[-1]
    debt0 = latest_gdp["percentOfGdp"]

    col1, col2 = st.columns([1, 2])
    with col1:
        pb_map = st.slider("Primary balance assumption (% GDP)", -6.0, 4.0, -2.0, 0.1)
        st.caption(f"Current debt: **{debt0:.1f}% GDP**")
        st.caption(f"Avg maturity: **{latest_irs['averageMaturity']:.1f} years**")
        st.caption(f"Avg refixing: **{latest_irs['averageFixing']:.1f} years**")

    r_vals = np.arange(0.0, 8.1, 0.25)
    g_vals = np.arange(-1.0, 5.1, 0.25)

    def proj_debt(d0, pb, r, g, years=12):
        d = d0
        for _ in range(years):
            d = ((1 + r/100) / (1 + g/100)) * d - pb
        return d

    def classify(end, start, pb, r, g):
        pb_s = ((r/100 - g/100) / (1 + g/100)) * start
        gap = pb - pb_s
        if end < start - 2 or gap > 0.5:
            return "Stabilising", gap
        elif end < start + 5 or gap > -1:
            return "At risk", gap
        else:
            return "Unsustainable", gap

    z_label, z_gap, z_end = [], [], []
    for g in g_vals:
        rl, rg, re = [], [], []
        for r in r_vals:
            end = proj_debt(debt0, pb_map, r, g)
            label, gap = classify(end, debt0, pb_map, r, g)
            rl.append(label); rg.append(round(gap, 2)); re.append(round(end, 1))
        z_label.append(rl); z_gap.append(rg); z_end.append(re)

    color_map = {"Stabilising": 1, "At risk": 0, "Unsustainable": -1}
    z_num = [[color_map[v] for v in row] for row in z_label]
    r_now = float(latest_irs["averageFixing"])
    g_now = 1.2

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        x=r_vals, y=g_vals, z=z_num,
        colorscale=[[0.0, "#dc2626"], [0.5, "#fbbf24"], [1.0, "#16a34a"]],
        showscale=False,
        hovertemplate="r = %{x:.2f}%<br>g = %{y:.2f}%<br>Debt 2035: %{customdata[0]:.1f}% GDP<br>Gap to pb*: %{customdata[1]:+.2f}pp<br><b>%{customdata[2]}</b><extra></extra>",
        customdata=[[[z_end[i][j], z_gap[i][j], z_label[i][j]] for j in range(len(r_vals))] for i in range(len(g_vals))],
    ))
    fig.add_trace(go.Scatter(x=[r_now], y=[g_now], mode="markers+text", marker=dict(size=14, color="white", symbol="star", line=dict(color="black", width=2)), text=["Finland now"], textposition="top center", textfont=dict(size=11, color="black"), name="Finland (current)", showlegend=True))
    fig.add_trace(go.Scatter(x=r_vals, y=r_vals, mode="lines", line=dict(color="white", dash="dot", width=1.5), name="r = g (neutral)", showlegend=True))
    fig.update_layout(title=f"Fiscal Feasibility Map · pb = {pb_map:+.1f}% GDP · Debt = {debt0:.1f}% GDP", xaxis=dict(title="Interest rate r (%)", dtick=0.5), yaxis=dict(title="GDP growth g (%)", dtick=0.5), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), height=520)
    with col2:
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Required Fiscal Adjustment · Sensitivity Table")
    st.caption("How much primary balance improvement is needed to stabilise debt?")
    r_scenarios = [2.0, 3.0, 3.5, 4.0, 5.0, 6.0]
    g_scenarios = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
    rows = []
    for g_s in g_scenarios:
        row = {"g / r": f"g={g_s:.1f}%"}
        for r_s in r_scenarios:
            pb_s = ((r_s/100 - g_s/100) / (1 + g_s/100)) * debt0
            adj = -(pb_map - pb_s)
            if adj <= 0:
                row[f"r={r_s:.1f}%"] = f"OK {adj:+.1f}pp"
            elif adj <= 1:
                row[f"r={r_s:.1f}%"] = f"~{adj:+.1f}pp"
            else:
                row[f"r={r_s:.1f}%"] = f"!{adj:+.1f}pp"
        rows.append(row)
    st.dataframe(pd.DataFrame(rows).set_index("g / r"), use_container_width=True)
    st.caption("OK = no tightening needed · ~ = small adjustment · ! = significant consolidation required")

    st.divider()
    pb_star_now = ((r_now/100 - g_now/100) / (1 + g_now/100)) * debt0
    adj_needed = pb_star_now - pb_map
    if adj_needed > 2:
        st.error(f"Finland's current fiscal stance requires significant adjustment. Under current conditions (r={r_now:.1f}%, g={g_now:.1f}%), the debt-stabilising primary balance is {pb_star_now:+.1f}% GDP. With pb={pb_map:+.1f}%, an adjustment of {adj_needed:.1f}pp is needed — requiring revenue increases, expenditure cuts, or structural growth reforms.")
    elif adj_needed > 0.5:
        st.warning(f"Moderate fiscal adjustment needed. Debt-stabilising pb* = {pb_star_now:+.1f}% GDP vs current {pb_map:+.1f}%. Required tightening: {adj_needed:.1f}pp — within historical consolidation range but non-trivial.")
    else:
        st.success(f"Debt is broadly on a sustainable path under current conditions. Debt-stabilising pb* = {pb_star_now:+.1f}% GDP vs current {pb_map:+.1f}% — no significant adjustment required.")
