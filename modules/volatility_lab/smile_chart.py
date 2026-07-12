import plotly.graph_objects as go
from modules.volatility_lab.heston_bridge import (
    HestonParams,
    MarketData,
    carr_madan_price,
    price_at_strikes,
    implied_vol,
)

def build_smile_html(params: HestonParams, data: MarketData, expiry_idx: int = 0) -> str:
    T = data.expiries[expiry_idx]
    market_ivs = data.market_ivs[expiry_idx]

    strikes_fft, prices_fft = carr_madan_price(params, data.S, data.r, data.q, T)
    model_prices = price_at_strikes(strikes_fft * data.S, prices_fft, data.strikes)
    model_ivs = implied_vol(model_prices, data.S, data.strikes, data.r, data.q, T)

    moneyness = data.strikes / data.S

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=moneyness, y=market_ivs * 100,
        mode="markers", name="Market",
        marker=dict(color="#2B5EA7", size=9),
    ))
    fig.add_trace(go.Scatter(
        x=moneyness, y=model_ivs * 100,
        mode="lines", name="Heston",
        line=dict(color="#E74C3C", width=2),
    ))
    fig.update_layout(
        title=f"Vol Smile — T = {T:.4f}y",
        xaxis_title="Moneyness (K/S)",
        yaxis_title="Implied Volatility (%)",
        template="plotly_dark",
        paper_bgcolor="#0D0D0D",
        plot_bgcolor="#141414",
        font=dict(color="#E8E8E8"),
    )
    return fig.to_html(include_plotlyjs=True, full_html=True)