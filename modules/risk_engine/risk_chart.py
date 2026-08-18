import plotly.graph_objects as go

from modules.risk_engine.risk_worker import RiskResult

PAGE_STYLE = (
    "html, body { margin:0; padding:0; height:100%; background:#0D0D0D; }"
    ".plotly-graph-div { height:100% !important; width:100% !important; }"
)


def _dark_layout(fig: go.Figure, **kwargs) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0D0D0D",
        plot_bgcolor="#141414",
        font=dict(color="#E8E8E8"),
        autosize=True,
        margin=dict(l=60, r=30, t=50, b=50),
        **kwargs,
    )
    return fig


def _to_html(fig: go.Figure) -> str:
    div = fig.to_html(
        full_html=False,
        include_plotlyjs=True,
        config={"responsive": True, "displaylogo": False},
        default_width="100%",
        default_height="100%",
    )
    return f"<html><head><style>{PAGE_STYLE}</style></head><body>{div}</body></html>"


def build_correlation_html(result: RiskResult) -> str:
    fig = go.Figure(go.Heatmap(
        x=result.tickers, y=result.tickers, z=result.corr_matrix,
        colorscale="RdBu", zmid=0, zmin=-1, zmax=1,
        text=result.corr_matrix, texttemplate="%{text:.2f}",
        colorbar=dict(title="ρ"),
    ))
    _dark_layout(fig, title="Portfolio Correlation Matrix")
    return _to_html(fig)


def build_histogram_html(result: RiskResult) -> str:
    var_95 = result.var_table["historical"][1][0.95]
    cvar_95 = result.cvar_table["historical"][1][0.95]

    fig = go.Figure(go.Histogram(
        x=result.portfolio_returns, nbinsx=60,
        marker_color="#2B5EA7", name="Daily Return",
    ))
    fig.add_vline(x=var_95, line_color="#E8C547", line_width=2,
                   annotation_text="VaR 95%", annotation_position="top")
    fig.add_vline(x=cvar_95, line_color="#E74C3C", line_width=2,
                   annotation_text="CVaR 95%", annotation_position="top")
    fig.update_xaxes(title_text="1-day portfolio return")
    fig.update_yaxes(title_text="Frequency")
    _dark_layout(fig, title="Return Distribution (1-day, Historical)", showlegend=False)
    return _to_html(fig)


def build_rolling_var_html(result: RiskResult) -> str:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=result.rolling_var_dates, y=result.rolling_var_95,
        mode="lines", name="95% VaR", line=dict(color="#E8C547", width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=result.rolling_var_dates, y=result.rolling_var_99,
        mode="lines", name="99% VaR", line=dict(color="#E74C3C", width=1.5),
    ))
    fig.update_yaxes(title_text="VaR (1-day return)")
    _dark_layout(fig, title="Rolling VaR (252-day window)")
    return _to_html(fig)


CHART_TABS = [
    {
        "key": "correlation",
        "label": "Correlation",
        "description": (
            "Pairwise correlation of daily returns across the portfolio's "
            "holdings. Values close to +1 mean two positions tend to move "
            "together (little diversification benefit between them), values "
            "near 0 mean they move independently, and negative values mean "
            "they tend to move opposite each other."
        ),
        "build": build_correlation_html,
    },
    {
        "key": "histogram",
        "label": "Return Distribution",
        "description": (
            "Histogram of the portfolio's daily returns over the lookback "
            "window, with the 1-day 95% historical VaR and CVaR marked as "
            "vertical lines. VaR is the return threshold not expected to be "
            "breached on 95% of days; CVaR is the average return on the "
            "worst days beyond that threshold — the tail risk VaR alone "
            "doesn't capture."
        ),
        "build": build_histogram_html,
    },
    {
        "key": "rolling_var",
        "label": "Rolling VaR",
        "description": (
            "95% and 99% VaR recomputed from a trailing 252-trading-day "
            "window, rolled forward one day at a time. Shows how the "
            "portfolio's estimated risk has evolved as market conditions "
            "changed, rather than a single static number."
        ),
        "build": build_rolling_var_html,
    },
]