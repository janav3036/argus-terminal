import plotly.graph_objects as go
from modules.options_pricer.pricing_worker import PricingResult

def build_convergence_html(result: PricingResult) -> str:
    ns = result.checkpoint_ns
    prices = result.checkpoint_prices
    ses = result.checkpoint_ses
    lower = prices - 1.96 * ses
    upper = prices + 1.96 * ses

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(ns) + list(ns[::-1]),
        y=list(upper) + list(lower[::-1]),
        fill="toself", fillcolor="rgba(43, 94, 167, 0.2)",
        line=dict(color="rgba(0,0,0,0)"),
        name="95% CI", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=ns, y=prices,
        mode="lines+markers", name="Price estimate",
        line=dict(color="#2B5EA7", width=2),
    ))
    fig.add_hline(y=result.price, line=dict(color="#E8E8E8", width=1, dash="dot"))
    fig.update_layout(
        title=f"Convergence (final price = {result.price:.4f} ± {result.stderr:.4f})",
        xaxis_title="N paths",
        yaxis_title="Price",
        template="plotly_dark",
        paper_bgcolor="#0D0D0D",
        plot_bgcolor="#141414",
        font=dict(color="#E8E8E8"),
    )
    return fig.to_html(include_plotlyjs=True, full_html=True)