import plotly.graph_objects as go
from plotly.subplots import make_subplots

REGIME_COLORS = {
    "Low Vol": "#2ECC71",
    "Elevated Vol": "#F5A623",
    "High Vol": "#E74C3C",
    "Crisis": "#8B0000",
}

def _regime_segments(dates, labels):
    segments = []
    start = 0
    n = len(labels)
    for i in range(1, n+1):
        if i==n or labels[i] != labels[start]:
            segments.append((dates[start], dates[i-1], labels[start]))
            start = i
    return segments

def build_regime_html(result):
    fig = make_subplots(
        rows=2,
        cols=1,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.12,
        subplot_titles=("NIFTY Price with Volatility Regimes", "Realized Vol Distribution by Regime"),
    )

    for start, end, label in _regime_segments(result.dates, result.state_labels):
        fig.add_vrect(
            x0=start, x1=end,
            fillcolor=REGIME_COLORS.get(label, "#888888"),
            opacity=0.25, line_width=0,
            row=1, col=1
        )
    fig.add_trace(
    go.Scatter(x=result.dates, y=result.price, mode="lines",
               line=dict(color="#E8E8E8", width=1.5), name="NIFTY"),
    row=1, col=1,
    )

    for label in result.label_order:
        mask = result.state_labels == label
        fig.add_trace(
            go.Histogram(x=result.vol[mask], name=label,
                        marker_color=REGIME_COLORS.get(label, "#888888"),
                        opacity=0.7, nbinsx=40),
            row=2, col=1,
        )

    fig.update_layout(
        barmode="overlay",
        template="plotly_dark",
        paper_bgcolor="#0D0D0D",
        plot_bgcolor="#0D0D0D",
        font=dict(color="#E8E8E8"),
        showlegend=True,
        height=700,
    )

    return fig.to_html(include_plotlyjs=True, full_html=True)