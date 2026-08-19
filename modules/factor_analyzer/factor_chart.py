import plotly.graph_objects as go
from modules.factor_analyzer.factor_worker import FACTOR_NAMES, FactorResult

PAGE_STYLE = (
    "html, body { margin:0; padding:0; height:100%; background:#0D0D0D; }"
    ".plotly-graph-div { height:100% !important; width:100% !important; }"
)

FACTOR_COLORS = {"Mkt-RF": "#2B5EA7", "SMB": "#E8C547", "HML": "#E74C3C", "MOM": "#4CAF50"}

def _dark_layout(fig: go.Figure, **kwargs) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0D0D0D",
        plot_bgcolor="#141414",
        autosize=True,
        margin=dict(l=60, r=30, t=50, b=50),
        font=dict(color="#E8E8E8"),
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


def build_loadings_html(result: FactorResult) -> str:
    betas = [result.coefficients[f] for f in FACTOR_NAMES]
    tstats = [result.tstats[f] for f in FACTOR_NAMES]
    colors = ["#2B5EA7" if abs(t) >= 2 else "#5A5A5A" for t in tstats]

    fig = go.Figure(go.Bar(
        x=FACTOR_NAMES, y=betas, marker_color=colors,
        text=[f"t={t:.2f}" for t in tstats], textposition="outside",
    ))
    fig.add_hline(y=0, line_color="#3A3A3A")
    fig.update_yaxes(title_text="Factor Loading (beta)")
    _dark_layout(fig, title=f"Factor Loadings (R²={result.r_squared:.2f})", showlegend=False)
    return _to_html(fig)


def build_rolling_betas_html(result: FactorResult) -> str:
    fig = go.Figure()
    for factor in FACTOR_NAMES:
        fig.add_trace(go.Scatter(
            x=result.rolling_betas.index, y=result.rolling_betas[factor],
            mode="lines", name=factor, line=dict(color=FACTOR_COLORS[factor], width=1.5),
        ))
    fig.update_yaxes(title_text="Rolling Beta")
    _dark_layout(fig, title="Rolling Factor Betas (60-day window)")
    return _to_html(fig)


def build_rolling_alpha_html(result: FactorResult) -> str:
    fig = go.Figure(go.Scatter(
        x=result.rolling_alpha.index, y=result.rolling_alpha,
        mode="lines", line=dict(color="#2B5EA7", width=1.5),
    ))
    fig.add_hline(y=0, line_color="#3A3A3A")
    fig.update_yaxes(title_text="Daily Alpha")
    _dark_layout(fig, title="Rolling Alpha (60-day window)", showlegend=False)
    return _to_html(fig)


def build_fit_html(result: FactorResult) -> str:
    predicted = result.coefficients["const"]
    for factor in FACTOR_NAMES:
        predicted = predicted + result.coefficients[factor] * result.factors[factor]

    actual = result.portfolio_returns
    axis_min = min(predicted.min(), actual.min())
    axis_max = max(predicted.max(), actual.max())

    fig = go.Figure(go.Scatter(
        x=predicted, y=actual, mode="markers",
        marker=dict(color="#2B5EA7", size=5, opacity=0.6),
    ))
    fig.add_trace(go.Scatter(
        x=[axis_min, axis_max], y=[axis_min, axis_max],
        mode="lines", line=dict(color="#5A5A5A", dash="dash"), showlegend=False,
    ))
    fig.update_xaxes(title_text="Model-predicted return")
    fig.update_yaxes(title_text="Actual return")
    _dark_layout(fig, title="Actual vs. Predicted Returns", showlegend=False)
    return _to_html(fig)


CHART_TABS = [
    {
        "key": "loadings",
        "label": "Factor Loadings",
        "description": (
            "Full-sample regression betas for each factor. Blue bars are "
            "statistically significant (|t| >= 2); grey bars are not "
            "distinguishable from zero at conventional confidence."
        ),
        "build": build_loadings_html,
    },
    {
        "key": "rolling_betas",
        "label": "Rolling Betas",
        "description": (
            "Factor betas recomputed from a trailing 60-day window, rolled "
            "forward one day at a time. Shows how the portfolio's factor "
            "exposures have shifted over time rather than a single static "
            "number."
        ),
        "build": build_rolling_betas_html,
    },
    {
        "key": "rolling_alpha",
        "label": "Rolling Alpha",
        "description": (
            "The regression intercept from the same 60-day rolling window — "
            "the portion of return the four factors don't explain."
        ),
        "build": build_rolling_alpha_html,
    },
    {
        "key": "fit",
        "label": "Actual vs. Predicted",
        "description": (
            "Each day's actual portfolio return plotted against the "
            "full-sample model's predicted return for that day. Points "
            "close to the dashed 45-degree line mean the four-factor model "
            "explains that day's move well."
        ),
        "build": build_fit_html,
    },
]