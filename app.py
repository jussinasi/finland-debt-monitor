import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Finland Sovereign Debt Monitor", page_icon="🇫🇮", layout="wide")

BASE = "https://api.tutkihallintoa.fi/central-government-debt/v1"

# ── Data fetching ──────────────────────────────────────────────────────────────
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

# ── Sidebar ────────────────────────────────────────────────────────────────────
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
    ])

    st.divider()
    st.markdown("Source: [Valtiokonttori API](https://avoindata.tutkihallintoa.fi)")
    st.markdown("Built with Streamlit · [GitHub](https://github.com/jussinasi/finland-debt-monitor)")

# ── Main ───────────────────────────────────────────────────────────────────────
st.title("🇫🇮 Finland Sovereign Debt Risk Monitor")

# ── OVERVIEW ──────────────────────────────────────────────────────────────────
if page == "📊 Overview":
    st.subheader("Central Government Debt · Key Metrics")

    with st.spinner("Loading data…"):
        df_gdp = load_debt_gdp()
        df_irs = load_interest_rate_sensitivity()
        df_cash = load_liquid_cash()

    latest_gdp = df_gdp.iloc[-1]
    latest_irs = df_irs.iloc[-1]
    latest_cash = df_cash.iloc[-1]

    # Key metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gross debt (% GDP)", f"{latest_gdp['percentOfGdp']:.1f}%",
              delta=f"{latest_gdp['percentOfGdp'] - df_gdp.iloc[-2]['percentOfGdp']:.1f}pp")
    m2.metric("Debt per capita", f"€{latest_gdp['debtPerCapita']:,.0f}")
    m3.metric("Avg maturity (years)", f"{latest_irs['averageMaturity']:.1f}y")
    m4.metric("Liquid cash (% of debt)", f"{latest_cash['percentOfDebt']:.1f}%")

    st.divider()

    # Debt/GDP chart
    fig = px.area(df_gdp, x="year", y="percentOfGdp",
                  title="Central Government Debt (% of GDP) · 2000–present",
                  labels={"percentOfGdp": "% of GDP", "year": "Year"},
                  color_discrete_sequence=["#1d6fa4"])
    fig.add_hline(y=60, line_dash="dash", line_color="red", line_width=1.5,
                  annotation_text="EU SGP: 60%", annotation_position="top right")
    fig.update_layout(plot_bgcolor="white", yaxis=dict(gridcolor="#eee"))
    st.plotly_chart(fig, use_container_width=True)

    # Narrative
    debt_pct = latest_gdp['percentOfGdp']
    debt_total = latest_gdp['totalEur'] / 1e9
    yoy = latest_gdp['percentOfGdp'] - df_gdp.iloc[-2]['percentOfGdp']

    if debt_pct > 60:
        st.error(
            f"**Finland's central government debt stands at {debt_pct:.1f}% of GDP ({debt_total:.1f}bn €) "
            f"as of {int(latest_gdp['year'])}**, exceeding the EU SGP 60% reference value. "
            f"The debt ratio {'increased' if yoy > 0 else 'decreased'} by {abs(yoy):.1f}pp year-on-year. "
            f"Current average maturity is {latest_irs['averageMaturity']:.1f} years with a "
            f"refixing period of {latest_irs['averageFixing']:.1f} years."
        )
    else:
        st.success(
            f"**Finland's central government debt stands at {debt_pct:.1f}% of GDP ({debt_total:.1f}bn €) "
            f"as of {int(latest_gdp['year'])}**, within the EU SGP 60% reference value. "
            f"The debt ratio {'increased' if yoy > 0 else 'decreased'} by {abs(yoy):.1f}pp year-on-year."
        )

# ── REFINANCING RISK ──────────────────────────────────────────────────────────
elif page == "⚠️ Refinancing Risk":
    st.subheader("Refinancing Risk · Debt Redemption Profile")
    st.caption("Annual redemptions by instrument type · Source: Valtiokonttori")

    with st.spinner("Loading redemption data…"):
        df = load_redemptions()

    # Aggregate by year
    by_year = df.groupby("year").agg(
        total_redemptions=("redemptions", "sum"),
        total_interests=("interests", "sum")
    ).reset_index()
    by_year["total_bn"] = by_year["total_redemptions"] / 1e9
    by_year["interests_bn"] = by_year["total_interests"] / 1e9

    # Key metrics
    current_year = datetime.now().year
    next_3y = by_year[by_year["year"] <= current_year + 3]["total_redemptions"].sum() / 1e9
    next_1y = by_year[by_year["year"] == current_year + 1]["total_redemptions"].sum() / 1e9
    total = by_year["total_redemptions"].sum() / 1e9

    m1, m2, m3 = st.columns(3)
    m1.metric("Maturing within 1 year", f"€{next_1y:.1f}bn")
    m2.metric("Maturing within 3 years", f"€{next_3y:.1f}bn")
    m3.metric("Total scheduled redemptions", f"€{total:.1f}bn")

    # Stacked bar by product
    fig = px.bar(
        df.assign(redemptions_bn=df["redemptions"]/1e9),
        x="year", y="redemptions_bn", color="product",
        title="Annual Debt Redemptions by Instrument (€bn)",
        labels={"redemptions_bn": "€ billion", "year": "Year", "product": "Instrument"},
        color_discrete_map={
            "Serial bonds": "#1d6fa4",
            "Treasury bills": "#f4a261",
            "Other debt": "#2a9d8f",
        }
    )
    fig.update_layout(plot_bgcolor="white", yaxis=dict(gridcolor="#eee"), barmode="stack")
    st.plotly_chart(fig, use_container_width=True)

    # Concentration risk narrative
    peak_year = by_year.loc[by_year["total_bn"].idxmax()]
    st.divider()

    if next_1y > 20:
        st.error(
            f"⚠️ **High near-term refinancing pressure:** €{next_1y:.1f}bn matures within the next year "
            f"and €{next_3y:.1f}bn within 3 years. "
            f"Peak redemption year is **{int(peak_year['year'])}** with €{peak_year['total_bn']:.1f}bn. "
            f"Concentration in short maturities increases vulnerability to market disruptions."
        )
    else:
        st.info(
            f"📋 **Refinancing profile:** €{next_1y:.1f}bn matures within the next year "
            f"and €{next_3y:.1f}bn within 3 years. "
            f"Peak redemption year is **{int(peak_year['year'])}** with €{peak_year['total_bn']:.1f}bn."
        )

    with st.expander("📄 Raw data"):
        st.dataframe(by_year[["year", "total_bn", "interests_bn"]].rename(columns={
            "year": "Year", "total_bn": "Redemptions (€bn)", "interests_bn": "Interest (€bn)"
        }), use_container_width=True, hide_index=True)

# ── INTEREST RATE RISK ────────────────────────────────────────────────────────
elif page == "📈 Interest Rate Risk":
    st.subheader("Interest Rate Risk · Sensitivity of Central Government Debt")
    st.caption("Average maturity, refixing period and duration · Source: Valtiokonttori")

    with st.spinner("Loading interest rate sensitivity data…"):
        df = load_interest_rate_sensitivity()
        df_recent = df[df["date"].dt.year >= 2010].copy()

    latest = df.iloc[-1]

    m1, m2, m3 = st.columns(3)
    m1.metric("Average maturity", f"{latest['averageMaturity']:.2f} years",
              help="How long until the average euro of debt is repaid")
    m2.metric("Average refixing period", f"{latest['averageFixing']:.2f} years",
              help="How quickly interest rate changes pass through to debt costs")
    m3.metric("Duration", f"{latest['duration']:.2f} years",
              help="Price sensitivity to interest rate changes")

    # Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_recent["date"], y=df_recent["averageMaturity"],
                             name="Average maturity", line=dict(color="#1d6fa4", width=2)))
    fig.add_trace(go.Scatter(x=df_recent["date"], y=df_recent["averageFixing"],
                             name="Refixing period", line=dict(color="#e76f51", width=2)))
    fig.add_trace(go.Scatter(x=df_recent["date"], y=df_recent["duration"],
                             name="Duration", line=dict(color="#2a9d8f", width=2, dash="dot")))
    fig.update_layout(
        title="Interest Rate Sensitivity Indicators (years)",
        hovermode="x unified", plot_bgcolor="white",
        yaxis=dict(gridcolor="#eee", title="Years"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Budget impact calculator
    st.subheader("💰 Interest Rate Shock Calculator")
    st.caption("Estimate budget impact of a parallel interest rate shift")

    debt_total = load_debt_gdp().iloc[-1]["totalEur"]
    fixing = latest["averageFixing"]
    rollover_share = 1 / fixing if fixing > 0 else 0.2

    shock = st.slider("Interest rate shock (percentage points)", 0.0, 3.0, 1.0, 0.25)
    impact = debt_total * rollover_share * (shock / 100)

    col1, col2 = st.columns(2)
    col1.metric("Annual budget impact", f"€{impact/1e6:.0f}m",
                delta=f"+{shock:.2f}pp shock", delta_color="inverse")
    col2.metric("Rollover share (1/refixing)", f"{rollover_share*100:.1f}% of debt/year")

    st.info(
        f"A **{shock:.2f}pp** parallel shift in interest rates would increase Finland's annual "
        f"interest expenses by approximately **€{impact/1e6:.0f}m** ({impact/1e9:.2f}bn €), "
        f"based on a refixing period of {fixing:.1f} years "
        f"implying ~{rollover_share*100:.1f}% of debt reprices annually."
    )

# ── LIQUIDITY BUFFER ──────────────────────────────────────────────────────────
elif page == "💧 Liquidity Buffer":
    st.subheader("Liquidity Buffer · Liquid Cash Funds")
    st.caption("State Treasury liquid cash position · Source: Valtiokonttori")

    with st.spinner("Loading liquidity data…"):
        df = load_liquid_cash()
        df_recent = df[df["date"].dt.year >= 2010].copy()

    latest = df.iloc[-1]
    cash_bn = latest["cashFundsEndOfMonth"] / 1e9
    pct = latest["percentOfDebt"]

    # Monthly spending estimate (rough: ~€5bn/month)
    monthly_spend_estimate = 5.0
    months_coverage = cash_bn / monthly_spend_estimate

    m1, m2, m3 = st.columns(3)
    m1.metric("Liquid cash (latest)", f"€{cash_bn:.1f}bn")
    m2.metric("As % of total debt", f"{pct:.1f}%")
    m3.metric("Est. months of coverage", f"~{months_coverage:.1f} months",
              help="Rough estimate based on ~€5bn monthly government expenditure")

    # Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_recent["date"],
        y=df_recent["cashFundsEndOfMonth"] / 1e9,
        name="Liquid cash (€bn)",
        fill="tozeroy",
        line=dict(color="#1d6fa4", width=2),
        fillcolor="rgba(29,111,164,0.15)"
    ))
    fig.update_layout(
        title="Liquid Cash Funds (€bn)",
        hovermode="x unified", plot_bgcolor="white",
        yaxis=dict(gridcolor="#eee", title="€ billion"),
        xaxis=dict(title="")
    )
    st.plotly_chart(fig, use_container_width=True)

    if months_coverage < 3:
        st.error(
            f"⚠️ **Low liquidity buffer:** Current cash of €{cash_bn:.1f}bn covers approximately "
            f"**{months_coverage:.1f} months** of estimated expenditure. "
            f"This represents {pct:.1f}% of total debt — below comfortable levels."
        )
    elif months_coverage < 6:
        st.warning(
            f"**Moderate liquidity buffer:** Current cash of €{cash_bn:.1f}bn covers approximately "
            f"**{months_coverage:.1f} months** of estimated expenditure ({pct:.1f}% of debt)."
        )
    else:
        st.success(
            f"✅ **Adequate liquidity buffer:** Current cash of €{cash_bn:.1f}bn covers approximately "
            f"**{months_coverage:.1f} months** of estimated expenditure ({pct:.1f}% of debt)."
        )

# ── DSA SIMULATOR ─────────────────────────────────────────────────────────────
elif page == "🔮 DSA Simulator":
    st.subheader("Debt Sustainability Analysis · Finland")
    st.caption("Model: Δd ≈ (r − g) · d + primary deficit · Source: Valtiokonttori + Eurostat")

    with st.spinner("Loading debt data…"):
        df_gdp = load_debt_gdp()

    latest = df_gdp.iloc[-1]
    debt0 = latest["percentOfGdp"]

    st.markdown(f"**Starting point ({int(latest['year'])}):** Gross debt **{debt0:.1f}% GDP**")

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
        if st.button("↺ Reset to defaults"):
            for k, v in [("r_b", 3.5), ("g_b", 1.2), ("pb_b", -2.5),
                         ("r_s", 5.0), ("g_s", 0.0), ("pb_s", -3.5),
                         ("r_c", 3.5), ("g_c", 1.2), ("pb_c", -0.5)]:
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
        r_c  = st.slider("Interest rate r (%)", 0.0, 8.0, 3.5, 0.1, key="r_c")
    with col_c2:
        g_c  = st.slider("GDP growth g (%)", -2.0, 5.0, 1.2, 0.1, key="g_c")
    with col_c3:
        pb_c = st.slider("Primary balance (% GDP)", -6.0, 4.0, -0.5, 0.1, key="pb_c")

    years = list(range(int(latest["year"]), int(latest["year"]) + 13))
    t_b = sim(debt0, pb_b, r_b, g_b)
    t_s = sim(debt0, pb_s, r_s, g_s)
    t_c = sim(debt0, pb_c, r_c, g_c)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=t_b, name="Baseline",
                             line=dict(color="#1d6fa4", width=2.5), mode="lines+markers"))
    fig.add_trace(go.Scatter(x=years, y=t_s, name="Stress",
                             line=dict(color="#e63946", width=2, dash="dash"), mode="lines+markers"))
    fig.add_trace(go.Scatter(x=years, y=t_c, name="Consolidation",
                             line=dict(color="#2a9d8f", width=2, dash="dot"), mode="lines+markers"))
    fig.add_hline(y=60, line_dash="dash", line_color="red", line_width=1.5,
                  annotation_text="SGP: 60%", annotation_position="bottom right")
    fig.update_layout(
        title=f"Finland Debt-to-GDP Trajectory {years[0]}–{years[-1]}",
        hovermode="x unified", plot_bgcolor="white",
        yaxis=dict(gridcolor="#eee", title="Gross debt (% GDP)"),
        xaxis=dict(title="Year", dtick=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

    # Required pb
    pb_star_b = pb_star(r_b, g_b, debt0)
    gap_b = pb_b - pb_star_b

    v1, v2, v3 = st.columns(3)
    def vcard(label, end, start, rg, pb_cur, pb_req, gap):
        if gap >= 0 and end < 60:
            vl, vc, bg, bc = "✅ Stabilising", "#1a7f37", "#f0fdf4", "#86efac"
        elif gap >= -1 or end < 70:
            vl, vc, bg, bc = "⚠️ At risk", "#92400e", "#fffbeb", "#fcd34d"
        else:
            vl, vc, bg, bc = "❌ Unsustainable", "#b91c1c", "#fef2f2", "#fca5a5"
        d = "📈 Rising" if end > start+1 else ("📉 Falling" if end < start-1 else "→ Stable")
        st.markdown(f"""
        <div style="background:{bg};border:1.5px solid {bc};border-radius:10px;padding:14px;text-align:center;">
            <div style="font-size:0.8em;color:#64748b;text-transform:uppercase;">{label}</div>
            <div style="font-size:1.8em;font-weight:800;color:{vc};">{end:.1f}%</div>
            <div style="font-size:0.82em;color:#475569;">by {years[-1]} · {d}</div>
            <div style="font-size:0.9em;font-weight:700;color:{vc};margin:6px 0 4px 0;">{vl}</div>
            <div style="font-size:0.75em;color:#64748b;">r−g = {rg:+.1f}pp</div>
            <div style="font-size:0.75em;color:#64748b;">Stabilising pb*: {pb_req:+.1f}% GDP</div>
            <div style="font-size:0.75em;color:#64748b;">Gap: {gap:+.1f}pp</div>
        </div>""", unsafe_allow_html=True)

    with v1: vcard("Baseline",      t_b[-1], debt0, r_b-g_b, pb_b, pb_star_b, gap_b)
    with v2: vcard("Stress",        t_s[-1], debt0, r_s-g_s, pb_s, pb_star(r_s,g_s,debt0), pb_s-pb_star(r_s,g_s,debt0))
    with v3: vcard("Consolidation", t_c[-1], debt0, r_c-g_c, pb_c, pb_star(r_c,g_c,debt0), pb_c-pb_star(r_c,g_c,debt0))

    st.divider()
    why = f"driven by r > g dynamics ({r_b:.1f}% vs {g_b:.1f}%)" if r_b > g_b else f"supported by favourable r−g ({r_b:.1f}% vs {g_b:.1f}%)"
    if gap_b < -1 and t_b[-1] > 60:
        st.error(
            f"**Key takeaway:** Finland's debt is on an **unfavourable upward trajectory** under baseline, "
            f"rising from **{debt0:.1f}%** to **{t_b[-1]:.1f}% GDP** by {years[-1]}. "
            f"This is {why}. "
            f"Stabilising debt requires a primary balance of **{pb_star_b:+.1f}% GDP** "
            f"— an adjustment of **{abs(gap_b):.1f}pp** from the current **{pb_b:+.1f}%**."
        )
    elif t_b[-1] > debt0 + 5:
        st.warning(
            f"**Key takeaway:** Debt is **rising** from {debt0:.1f}% to {t_b[-1]:.1f}% GDP by {years[-1]}, "
            f"{why}. Stabilising pb* = {pb_star_b:+.1f}% GDP (gap: {abs(gap_b):.1f}pp)."
        )
    else:
        st.success(
            f"**Key takeaway:** Debt trajectory is **broadly sustainable**, "
            f"projected at {t_b[-1]:.1f}% GDP by {years[-1]}, {why}."
        )
