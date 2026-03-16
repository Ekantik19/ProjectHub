import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

from core import (
    yield_curve,
    present_value,
    run_analysis,
    raw_t,
    raw_y,
    ACTUAL_MATURITIES,
)


st.set_page_config(page_title="Roll-Down Optimizer", layout="wide")


with st.sidebar:
    st.header("Controls")

    holding_months = st.slider(
        "Holding period (months)",
        min_value=1,
        max_value=60,
        value=6,
        step=1,
    )
    H = holding_months / 12  # convert to years

    face_value = st.number_input(
        "Face value ($)",
        min_value=100,
        max_value=1_000_000,
        value=1000,
        step=100,
    )

    selected_maturity = st.selectbox(
        "Bond maturity (P&L simulator)",
        options=ACTUAL_MATURITIES,
        index=6,  # default to 5Y
        format_func=lambda x: f"{x:.4g}Y",
    )


df = run_analysis(H=H, face_value=face_value)

optimal_row = df.loc[df["total_HPR"].idxmax()]
sweetspot_row = df.loc[df["roll_per_dur"].idxmax()]

optimal_maturity = float(optimal_row["maturity"])
sweetspot_maturity = float(sweetspot_row["maturity"])


st.title("Roll-Down Strategy Optimizer")

# PANEL 1 — Yield Curve
st.header("Panel 1 — Yield Curve")

t_smooth = np.linspace(0.083, 30, 400)
y_smooth = [float(yield_curve(t)) for t in t_smooth]

fig1 = go.Figure()

fig1.add_trace(go.Scatter(
    x=t_smooth,
    y=y_smooth,
    mode="lines",
    name="Nelson-Siegel fit",
    line=dict(color="#378add", width=2.5),
    hovertemplate="Maturity: %{x:.2f}Y<br>Yield: %{y:.3f}%<extra></extra>",
))

fig1.add_trace(go.Scatter(
    x=list(raw_t),
    y=list(raw_y),
    mode="markers",
    name="Market data",
    marker=dict(color="#e24b4a", size=9, symbol="circle"),
    hovertemplate="Maturity: %{x:.3g}Y<br>Yield: %{y:.2f}%<extra></extra>",
))

# 4c — layout and render
fig1.update_layout(
    xaxis_title="Maturity (Years)",
    yaxis_title="Yield (%)",
    height=350,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=40, b=40, l=60, r=20),
)

st.plotly_chart(fig1, use_container_width=True)

# PANEL 2 — HPR Breakdown + P&L Simulator
st.header("Panel 2 — HPR Breakdown & P&L Simulator")

fig2 = go.Figure()

fig2.add_trace(go.Bar(
    x=df["maturity"],
    y=df["carry_return"] * 100,
    name="Carry return",
    marker_color="#378add",
    hovertemplate="Maturity: %{x:.1f}Y<br>Carry: %{y:.3f}%<extra></extra>",
))

fig2.add_trace(go.Bar(
    x=df["maturity"],
    y=df["roll_down_return"] * 100,
    name="Roll-down return",
    marker_color="#1d9e75",
    hovertemplate="Maturity: %{x:.1f}Y<br>Roll-down: %{y:.3f}%<extra></extra>",
))

fig2.add_trace(go.Scatter(
    x=df["maturity"],
    y=df["total_HPR"] * 100,
    mode="lines",
    name="Total HPR",
    line=dict(color="#ef9f27", width=2),
    hovertemplate="Maturity: %{x:.1f}Y<br>Total HPR: %{y:.3f}%<extra></extra>",
))

fig2.add_vline(
    x=optimal_maturity,
    line_dash="dash",
    line_color="#e24b4a",
    annotation_text=f"{optimal_maturity:.1f}Y  Max HPR",
    annotation_position="top right",
    annotation_font=dict(color="#e24b4a", size=12),
)

fig2.add_vline(
    x=sweetspot_maturity,
    line_dash="dot",
    line_color="#534ab7",
    annotation_text=f"{sweetspot_maturity:.1f}Y  Sweet spot",
    annotation_position="top left",
    annotation_font=dict(color="#534ab7", size=12),
)

fig2.update_layout(
    barmode="group",
    xaxis_title="Maturity (Years)",
    yaxis_title="Return (%)",
    height=400,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=50, b=40, l=60, r=20),
)

st.plotly_chart(fig2, use_container_width=True)

st.subheader("P&L Simulator")
if selected_maturity <= H:
    st.warning(
        f"Selected maturity ({selected_maturity:.4g}Y) is shorter than or equal to the "
        f"holding period ({H:.4g}Y). Please select a longer bond or reduce the holding period."
    )
else:
    sim_yield_pct = float(yield_curve(selected_maturity))
    sim_yield = sim_yield_pct / 100
    coupon_rate = sim_yield

    price_today_sim = present_value(face_value, coupon_rate, coupon_rate, selected_maturity)

    new_mat = selected_maturity - H
    new_yield_pct = float(yield_curve(new_mat))
    new_yield = new_yield_pct / 100

    price_after_sim = present_value(face_value, coupon_rate, new_yield, new_mat)

    coupon_income = coupon_rate * face_value * H
    price_change = price_after_sim - price_today_sim
    total_pnl = coupon_income + price_change
    total_hpr_pct = (total_pnl / price_today_sim) * 100

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        label="Coupon income",
        value=f"${coupon_income:.2f}",
    )
    col2.metric(
        label="Price change",
        value=f"${price_change:+.2f}",
        delta=f"{(price_change / price_today_sim * 100):+.3f}%",
    )
    col3.metric(
        label="Total P&L",
        value=f"${total_pnl:+.2f}",
    )
    col4.metric(
        label="Total HPR",
        value=f"{total_hpr_pct:.3f}%",
    )

    with st.expander("Show bond details"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Bond maturity", f"{selected_maturity:.4g}Y")
        c2.metric("Entry yield", f"{sim_yield_pct:.3f}%")
        c3.metric("Price today", f"${price_today_sim:.2f}")
        c4, c5, c6 = st.columns(3)
        c4.metric("New maturity after roll", f"{new_mat:.4g}Y")
        c5.metric("Exit yield", f"{new_yield_pct:.3f}%")
        c6.metric("Price after hold", f"${price_after_sim:.2f}")

# Persons 2 and 3 add their panels below this line