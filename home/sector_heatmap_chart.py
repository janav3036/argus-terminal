import plotly.graph_objects as go

_FILL_HTML_STYLE = (
    "<style>html, body { margin: 0; padding: 0; height: 100%; "
    "background: #0D0D0D; }</style></head>"
)

# Negative -> Argus's muted red, neutral -> panel-border grey (reads as part
# of the terminal chrome rather than a bright midpoint), positive -> muted
# green. Matches the candlestick up/down colors and the QSS palette instead
# of Plotly's default RdYlGn.
_HEATMAP_COLORSCALE = [
    [0.0, "#E74C3C"],
    [0.5, "#2A2A2A"],
    [1.0, "#2ECC71"],
]

def build_heatmap_html(sector_data: dict) -> str:
    labels = list(sector_data.keys())
    values = [sector_data[label]["weight"] for label in labels]
    pct_changes = [sector_data[label]["pct_change"] for label in labels]
    text = [f"{label}<br>{pct:+.2f}%" for label, pct in zip(labels, pct_changes)]

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=[""] * len(labels),
        values=values,
        text=text,
        textinfo="text",
        textfont=dict(size=16),
        pathbar=dict(visible=False),
        tiling=dict(pad=3),
        marker=dict(
            colors=pct_changes,
            colorscale=_HEATMAP_COLORSCALE,
            cmid=0,
            line=dict(width=1, color="#0D0D0D"),
            showscale=True,
            colorbar=dict(
                title=dict(text="% Chg", font=dict(color="#888888", size=11)),
                tickfont=dict(color="#888888", size=10),
                outlinewidth=0,
                tickcolor="#3A3A3A",
                bgcolor="rgba(0,0,0,0)",
                thickness=12,
                len=0.9,
            ),
        ),
    ))
    fig.update_layout(
        margin=dict(t=4, l=4, r=48, b=4),
        template="plotly_dark",
        paper_bgcolor="#0D0D0D",
        font=dict(color="#E8E8E8"),
    )
    html = fig.to_html(
        include_plotlyjs=True,
        full_html=True,
        config={"responsive": True, "displayModeBar": False},
    )
    return html.replace("</head>", _FILL_HTML_STYLE, 1)