import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from agent.splunk_client import SplunkClient
from agent.anomaly import detect_anomalies, summarise_anomalies

# ── Page config ──────────────────────────────────────────
st.set_page_config(
    page_title="Ops Autopilot",
    page_icon="🤖",
    layout="wide"
)

# ── Custom CSS ────────────────────────────────────────────
st.markdown("""
<style>
    .chart-label {
        font-size: 13px;
        font-weight: 600;
        color: #aaaaaa;
        margin-bottom: 2px;
        padding-left: 4px;
    }
    .anomaly-card {
        background: #2a1a1a;
        border-left: 4px solid #e74c3c;
        border-radius: 6px;
        padding: 14px 16px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────
st.title("🤖 Ops Autopilot")
st.caption("AI-powered anomaly detection and incident response — powered by Splunk")
st.divider()

# ── Load data ────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_data():
    try:
        sc = SplunkClient()
        df = sc.get_metrics(earliest="-48h", latest="now")
        return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)

with st.spinner("Connecting to Splunk and fetching metrics..."):
    df, error = load_data()

if error:
    st.error(f"❌ Could not connect to Splunk: {error}")
    st.stop()

if df.empty:
    st.warning("⚠️ No data returned from Splunk. Make sure index=ops_metrics has data.")
    st.stop()

# ── Run anomaly detection ─────────────────────────────────
anomaly_df = detect_anomalies(df)
summary    = summarise_anomalies(anomaly_df)

# ── Status bar ───────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    if summary:
        st.error(f"🚨 {len(summary)} Anomaly Type(s) Detected")
    else:
        st.success("✅ All Systems Normal")

with col2:
    st.metric("Data Points Analysed", f"{len(df):,}")

with col3:
    st.metric("Anomalous Points", f"{len(anomaly_df):,}")

with col4:
    st.metric("Last Checked", datetime.now().strftime("%H:%M:%S"))

st.divider()

# ── Anomaly summary cards ─────────────────────────────────
if summary:
    st.subheader("⚠️ Active Anomalies")
    cols = st.columns(len(summary))
    for i, s in enumerate(summary):
        with cols[i]:
            st.markdown(f"""
            <div class="anomaly-card">
                <b>{s['label']}</b><br><br>
                <small>Metric:</small> <code>{s['metric']}</code><br>
                <small>Peak:</small> <b>{s['peak_value']}</b><br>
                <small>Z-score:</small> <b>{s['peak_z']}</b><br>
                <small>Points flagged:</small> {s['count']}<br>
                <small>Peak time:</small> {str(s['peak_time'])[:19]}
            </div>
            """, unsafe_allow_html=True)
    st.divider()

# ── Charts ────────────────────────────────────────────────
st.subheader("📈 System Metrics (48h)")
st.write("")

metrics = [
    ("cpu_pct",      "CPU Usage (%)",        "#e74c3c"),
    ("memory_pct",   "Memory Usage (%)",     "#3498db"),
    ("request_rate", "Request Rate (req/s)", "#2ecc71"),
    ("error_rate",   "Error Rate",           "#f39c12"),
]

for metric, label, color in metrics:
    if metric not in df.columns:
        continue

    # FIX 1 — label written outside plotly, no overlap
    st.markdown(f'<div class="chart-label">📊 {label}</div>',
                unsafe_allow_html=True)

    fig = go.Figure()

    # Main metric line
    fig.add_trace(go.Scatter(
        x=df["_time"], y=df[metric],
        mode="lines",
        name=label,
        line=dict(color=color, width=1.5),
        showlegend=False,
    ))

    # FIX 2 — only show high z-score anomalies, filters out noise
    if not anomaly_df.empty and metric in anomaly_df["metric"].values:
        ano = anomaly_df[anomaly_df["metric"] == metric].copy()
        ano_filtered = ano[ano["z_score"].abs() > 3.5]
        if not ano_filtered.empty:
            fig.add_trace(go.Scatter(
                x=ano_filtered["_time"],
                y=ano_filtered["value"],
                mode="markers",
                name="Anomaly",
                marker=dict(
                    color="red",
                    size=10,
                    symbol="x",
                    line=dict(width=2, color="red")
                ),
                showlegend=True,
            ))

    # FIX 3 — pink shaded band around the peak anomaly time
    if summary:
        for s in summary:
            if s["metric"] == metric:
                peak_time = pd.to_datetime(s["peak_time"])
                fig.add_vrect(
                    x0=peak_time - pd.Timedelta(minutes=30),
                    x1=peak_time + pd.Timedelta(minutes=30),
                    fillcolor="red",
                    opacity=0.08,
                    line_width=0,
                    annotation_text="Peak",
                    annotation_position="top left",
                    annotation_font_size=10,
                    annotation_font_color="red",
                )

    # FIX 4 — t=10 removes internal title space, no overlap
    fig.update_layout(
        height=230,
        margin=dict(l=10, r=10, t=10, b=30),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            tickfont=dict(size=11),
        ),
        legend=dict(
            orientation="h",
            y=1.0,
            x=1.0,
            xanchor="right",
            yanchor="bottom",
            font=dict(size=11),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.write("")  # breathing room between charts

st.divider()

# ── Latest runbook ────────────────────────────────────────
st.subheader("📋 Latest AI Runbook")

runbooks_dir = os.path.join(os.path.dirname(__file__), '..', 'runbooks')

if os.path.exists(runbooks_dir):
    files = sorted(
        [f for f in os.listdir(runbooks_dir) if f.endswith(".md")],
        reverse=True
    )
    if files:
        latest = os.path.join(runbooks_dir, files[0])
        with open(latest, "r", encoding="utf-8") as f:
            content = f.read()
        st.markdown(content)
        st.caption(f"Source: `{files[0]}`")
    else:
        st.info("No runbooks generated yet. Run the agent first.")
else:
    st.info("Runbooks folder not found. Run agent/main.py first.")

st.divider()

# ── Raw data expander ─────────────────────────────────────
with st.expander("🔍 View Raw Metrics Data"):
    st.dataframe(df.tail(100), use_container_width=True)

# ── Auto refresh ──────────────────────────────────────────
st.caption("Dashboard auto-refreshes every 60 seconds via cache TTL.")
if st.button("🔄 Refresh Now"):
    st.cache_data.clear()
    st.rerun()