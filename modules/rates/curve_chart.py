import plotly.graph_objects as go

from modules.rates.curve_worker import CurveResult


def build_curve_html(result: CurveResult) -> str:
    tenors = result.tenors

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=tenors, y=result.market_yields * 100,
        mode="markers", name="Market (G-Sec)",
        marker=dict(color="#E8E8E8", size=9, symbol="diamond"),
    ))
    fig.add_trace(go.Scatter(
        x=tenors, y=result.vas_yields * 100,
        mode="lines", name=f"Vasicek (RMSE={result.vas_rmse_bps:.1f} bps)",
        line=dict(color="#2B5EA7", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=tenors, y=result.cir_yields * 100,
        mode="lines", name=f"CIR (RMSE={result.cir_rmse_bps:.1f} bps)",
        line=dict(color="#3CA55C", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=tenors, y=result.hw_yields * 100,
        mode="lines", name=f"Hull-White (RMSE={result.hw_rmse_bps:.1f} bps)",
        line=dict(color="#E74C3C", width=2),
    ))
    fig.update_layout(
        title="Model Yield Curves vs Market (Indian G-Sec)",
        xaxis_title="Tenor (years)",
        yaxis_title="Yield (%)",
        template="plotly_dark",
        paper_bgcolor="#0D0D0D",
        plot_bgcolor="#141414",
        font=dict(color="#E8E8E8"),
    )
    return fig.to_html(include_plotlyjs=True, full_html=True)