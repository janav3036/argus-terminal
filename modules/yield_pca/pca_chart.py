import plotly.graph_objects as go
from plotly.subplots import make_subplots

from modules.yield_pca.pca_worker import PCAResult

COMPONENT_COLORS = {
    "Level": "#2B5EA7",
    "Slope": "#2ECC71",
    "Curvature": "#E74C3C",
}

def build_pca_html(result: PCAResult) -> str:
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Explained Variance", "Factor Loadings by Tenor",
            "Historical Factor Scores", "Current Curve Decomposition",
        ),
    )

    fig.add_trace(
        go.Bar(
            x=result.component_labels,
            y=result.explained_variance_ratio * 100,
            marker_color=[COMPONENT_COLORS[c] for c in result.component_labels],
            showlegend=False,
        ),
        row=1, col=1,
    )

    for i, label in enumerate(result.component_labels):
        fig.add_trace(
            go.Scatter(
                x=result.tenors, y=result.loadings[i],
                mode="lines+markers", name=label,
                line=dict(color=COMPONENT_COLORS[label], width=2),
            ),
            row=1, col=2,
        )

    for i, label in enumerate(result.component_labels):
        fig.add_trace(
            go.Scatter(
                x=result.dates, y=result.factor_scores[:, i],
                mode="lines", name=label, showlegend=False,
                line=dict(color=COMPONENT_COLORS[label], width=1.5),
            ),
            row=2, col=1,
        )

    fig.add_trace(
        go.Bar(
            x=result.component_labels,
            y=result.current_contributions * 10000,
            marker_color=[COMPONENT_COLORS[c] for c in result.component_labels],
            showlegend=False,
        ),
        row=2, col=2,
    )

    fig.update_yaxes(title_text="% of variance", row=1, col=1)
    fig.update_yaxes(title_text="Loading", row=1, col=2)
    fig.update_xaxes(title_text="Tenor (years)", row=1, col=2)
    fig.update_yaxes(title_text="bps", row=2, col=2)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0D0D0D",
        plot_bgcolor="#141414",
        font=dict(color="#E8E8E8"),
        height=700,
        showlegend=True,
    )

    return fig.to_html(include_plotlyjs=True, full_html=True)