import asyncio
import streamlit as st
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.rest import REST, TimeFrame
from alpaca_trade_api.common import URL
import pandas as pd
import plotly.graph_objects as go
import time

# Alpaca API keys
API_KEY = ""
SECRET_KEY = ""
BASE_URL = "https://paper-api.alpaca.markets"

# Initialize Alpaca REST API
api = REST(API_KEY, SECRET_KEY, BASE_URL)

# Initialize Alpaca WebSocket Stream
stream = Stream(API_KEY, SECRET_KEY, base_url=URL(BASE_URL), data_feed='iex')  # Use 'iex' or 'sip'

# Global variables for live updates
live_prices = {}
positions = None


# Helper Functions
def get_positions():
    """Fetches current account positions."""
    global positions
    positions = api.list_positions()
    data = [
        {
            "Symbol": pos.symbol,
            "Quantity": pos.qty,
            "Market Value": pos.market_value,
            "Cost Basis": pos.cost_basis,
            "Unrealized P/L": pos.unrealized_pl,
        }
        for pos in positions
    ]
    return pd.DataFrame(data)


def get_portfolio_history():
    """Fetches portfolio growth data."""
    history = api.get_portfolio_history(period="1M", timeframe="1D").df
    history["time"] = pd.to_datetime(history.index, unit="s")
    return history


def place_order(symbol, qty, side, order_type="market"):
    """Places buy/sell orders."""
    return api.submit_order(
        symbol=symbol,
        qty=qty,
        side=side,
        type=order_type,
        time_in_force="gtc"
    )


def liquidate_all_positions():
    """Liquidates all open positions."""
    api.close_all_positions()


# WebSocket for Real-Time Prices
async def stream_prices(symbols):
    """Updates live prices for given symbols using WebSocket."""
    @stream.on_bar(symbols)
    async def on_bar(bar):
        live_prices[bar.symbol] = bar.close

    await stream.run()


# Streamlit UI
st.title("Real-Time Trading Dashboard")

# Section: Current Positions
st.header("Current Positions")
positions_df = get_positions()
if not positions_df.empty:
    st.dataframe(positions_df)
else:
    st.write("No active positions.")

# Section: Portfolio Growth
st.header("Portfolio Growth")
portfolio_history = get_portfolio_history()
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=portfolio_history["time"],
    y=portfolio_history["equity"],
    mode="lines",
    name="Portfolio Equity"
))
fig.update_layout(
    title="Portfolio Growth Over Time",
    xaxis_title="Date",
    yaxis_title="Equity ($)"
)
st.plotly_chart(fig)

# Section: Real-Time Prices
st.header("Real-Time Prices")
symbols = st.text_input("Enter comma-separated symbols (e.g., AAPL,MSFT):", "AAPL,MSFT")
symbol_list = [s.strip().upper() for s in symbols.split(",")]

if st.button("Start Price Stream"):
    asyncio.run(stream_prices(symbol_list))

if live_prices:
    st.subheader("Live Prices")
    st.write(pd.DataFrame.from_dict(live_prices, orient="index", columns=["Price"]))

# Section: Buy/Sell Orders
st.header("Buy/Sell Orders")
col1, col2 = st.columns(2)
with col1:
    order_symbol = st.text_input("Symbol (e.g., AAPL):")
with col2:
    qty = st.number_input("Quantity:", min_value=1, value=1)
side = st.radio("Order Side:", ["Buy", "Sell"])

if st.button("Place Order"):
    try:
        order = place_order(order_symbol, qty, side.lower())
        st.success(f"{side} order placed for {qty} shares of {order_symbol}. Order ID: {order.id}")
    except Exception as e:
        st.error(f"Error placing order: {e}")

# Section: Liquidate All
st.header("Liquidate All Positions")
if st.button("Liquidate All"):
    try:
        liquidate_all_positions()
        st.success("All positions liquidated.")
    except Exception as e:
        st.error(f"Error liquidating positions: {e}")

# Periodic Refresh for Positions and Portfolio Growth
if st.button("Refresh Data"):
    st.experimental_rerun()

#streamlit run d.py