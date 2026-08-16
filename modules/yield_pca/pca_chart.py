import plotly.graph_objects as go

from modules.yield_pca.pca_worker import PCAResult

COMPONENT_COLORS = {
    "Level": "#2B5EA7",
    "Slope": "#2ECC71",
    "Curvature": "#E74C3C",
}

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


def build_variance_html(result: PCAResult) -> str:
    fig = go.Figure(go.Bar(
        x=result.component_labels,
        y=result.explained_variance_ratio * 100,
        marker_color=[COMPONENT_COLORS[c] for c in result.component_labels],
    ))
    fig.update_yaxes(title_text="% of variance")
    _dark_layout(fig, title="Explained Variance by Component", showlegend=False)
    return _to_html(fig)


def build_loadings_html(result: PCAResult) -> str:
    fig = go.Figure()
    for i, label in enumerate(result.component_labels):
        fig.add_trace(go.Scatter(
            x=result.tenors, y=result.loadings[i],
            mode="lines+markers", name=label,
            line=dict(color=COMPONENT_COLORS[label], width=2),
        ))
    fig.update_xaxes(title_text="Tenor (years)")
    fig.update_yaxes(title_text="Loading")
    _dark_layout(fig, title="Factor Loadings by Tenor")
    return _to_html(fig)


def build_factor_scores_html(result: PCAResult) -> str:
    fig = go.Figure()
    for i, label in enumerate(result.component_labels):
        fig.add_trace(go.Scatter(
            x=result.dates, y=result.factor_scores[:, i],
            mode="lines", name=label,
            line=dict(color=COMPONENT_COLORS[label], width=1.5),
        ))
    fig.update_yaxes(title_text="Factor score")
    _dark_layout(fig, title="Historical Factor Scores")
    return _to_html(fig)


def build_contribution_html(result: PCAResult) -> str:
    fig = go.Figure(go.Bar(
        x=result.component_labels,
        y=result.current_contributions * 10000,
        marker_color=[COMPONENT_COLORS[c] for c in result.component_labels],
    ))
    fig.update_yaxes(title_text="bps")
    _dark_layout(fig, title="Current Curve Decomposition", showlegend=False)
    return _to_html(fig)


CHART_TABS = [
    {
        "key": "variance",
        "label": "Explained Variance",
        "description": (
            "This bar chart shows the percentage of total day-to-day yield curve "
            "variance that each principal component explains, from a PCA fit on "
            "daily changes across the six G-Sec tenors (3M, 6M, 1Y, 2Y, 5Y, 10Y). "
            "The three bars — Level, Slope, and Curvature — are ordered from most "
            "to least explanatory, so together their heights sum to the total "
            "variance captured by the 3-factor model. The y-axis is variance share "
            "in percent; each bar's color matches that component's color across "
            "all four charts in this module."
        ),
        "build": build_variance_html,
    },
    {
        "key": "loadings",
        "label": "Factor Loadings",
        "description": (
            "This chart plots each component's loading — its weight — against all "
            "six G-Sec tenors on the x-axis, in years. A loading vector describes "
            "how a one-unit move in that component's factor score translates into "
            "a yield change at each tenor: Level's line typically stays roughly "
            "flat and same-signed across tenors (a uniform shift), Slope typically "
            "moves monotonically from the short end to the long end, and Curvature "
            "typically bows in the middle relative to both ends. Line color matches "
            "the component's assigned color."
        ),
        "build": build_loadings_html,
    },
    {
        "key": "scores",
        "label": "Factor Scores",
        "description": (
            "This is a time series of each component's daily factor score — the "
            "value obtained by projecting that day's yield change onto the "
            "component's loading vector — plotted across the full historical "
            "sample used to fit the PCA. A score's magnitude reflects how "
            "strongly that component was expressed on a given day, and its sign "
            "reflects direction. All three components share the same date axis, "
            "so their timing can be compared directly against one another."
        ),
        "build": build_factor_scores_html,
    },
    {
        "key": "contribution",
        "label": "Current Decomposition",
        "description": (
            "This bar chart decomposes the difference between today's G-Sec "
            "curve and its historical mean curve into Level, Slope, and "
            "Curvature contributions, expressed in basis points. Each bar is "
            "computed by projecting that deviation onto the corresponding "
            "component's loading vector, so together the three bars account for "
            "how today's curve shape departs from its historical average, "
            "broken down by which factor drives each part of the departure."
        ),
        "build": build_contribution_html,
    },
]
