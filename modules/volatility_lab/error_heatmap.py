import plotly.graph_objects as go
from modules.volatility_lab.heston_bridge import (
    HestonParams,
    MarketData,
    carr_madan_price,
    price_at_strikes,
    bs_call,
)

def build_error_heatmap_html(params: HestonParams, data: MarketData, expiry_idx: int = 0) -> str:
    T = data.expiries[expiry_idx]
    market_ivs = data.market_ivs[expiry_idx]
    atm_idx = len(data.strikes)//2
    atm_vol = market_ivs[atm_idx]

    strikes_fft, prices_fft = carr_madan_price(params, data.S, data.r, data.q, T)
    heston_prices = price_at_strikes(strikes_fft * data.S, prices_fft, data.strikes)

    bs_prices = bs_call(data.S, data.strikes, data.r, data.q, T, atm_vol)

    error_pct = (bs_prices - heston_prices) / heston_prices * 100
    moneyness = data.strikes / data.S

    fig = go.Figure(data=go.Heatmap(
        z=[error_pct],
        x=moneyness,
        y=[f"T={T:.4f}y"],
        colorscale="RdBu",
        zmid=0,
        colorbar=dict(title="Error (%)"),
    ))
    fig.update_layout(
        title="BS vs Heston Pricing Error by Moneyness",
        xaxis_title="Moneyness (K/S)",
        template="plotly_dark",
        paper_bgcolor="#0D0D0D",
        plot_bgcolor="#141414",
        font=dict(color="#E8E8E8"),
    )
    return fig.to_html(include_plotlyjs=True, full_html=True)