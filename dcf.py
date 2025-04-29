import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

# --- Streamlit Config ---
st.set_page_config(page_title="DCF Valuation Analysis — Finance Modeling", layout="wide")

# --- Custom CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    html, body, [class*="css"] {
        background-color: #050915;
        color: #E1E6ED;
        font-family: 'Segoe UI', sans-serif;
    }
    .stApp {
        background-color: #050915;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stSidebar {
        background-color: #0a3d62;
    }
    .stSidebar h1, .stSidebar h2, .stSidebar h3, .stSidebar h4, .stSidebar p, .stSidebar label, .stSidebar span {
        color: white !important;
    }
    h1 {
        font-size: 28px !important;
        color: #F0F4F8;
    }
    h4 {
        font-size: 20px !important;
        color: #F0F4F8;
    }
 .metric-box {
    background-color: #1e2a38; /* Ganti warna box di sini */
    padding: 1.2rem;
    border-radius: 14px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    font-size: 18px;
    margin-bottom: 1rem;
    box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.4); /* Tambah shadow supaya lebih modern */
    transition: 0.3s ease-in-out;
}
.metric-box:hover {
    background-color: #2b3a50; /* Sedikit lighten saat hover */
}

    .info-box {
        background-color: #2f3640;
        padding: 1rem;
        border-radius: 10px;
        font-size: 14px;
        color: #f1c40f;
        margin-top: 1rem;
    }
    section[data-testid="stSidebar"] .stButton button {
        width: 100% !important;
        margin-top: 10px !important;
        background-color: #d35400 !important;
        color: white !important;
        padding: 10px 0 !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 5px !important;
        cursor: pointer !important;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background-color: #ba4a00 !important;
    }
    .footer-text {
        margin: 3rem auto 1rem;
        text-align: center;
        font-size: 17px;
        font-weight: bold;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.image("logo.png", use_container_width=True)
st.sidebar.header("🧮 Input Parameters")

ticker = st.sidebar.text_input("Stock Ticker", value="INDF.JK")
risk_free_rate = st.sidebar.number_input("Risk-Free Rate (%)", value=5.50, step=0.01)
country = st.sidebar.selectbox("Country", ["Indonesia"])

submit = st.sidebar.button("Submit")

# --- Main Program ---
if submit:
    with st.spinner("Processing DCF Valuation..."):
        stock = yf.Ticker(ticker)
        market_price = stock.history(period="1d")["Close"].iloc[-1]
        cashflow = stock.cashflow.fillna(0)
        income_stmt = stock.financials.fillna(0)
        balance_sheet = stock.balance_sheet.fillna(0)

        def safe_get(df, label, default=0):
            return df.loc[label].values[0] if label in df.index else default

        # Free Cash Flow Forecast
        fcf_line = 'Free Cash Flow'
        if fcf_line in cashflow.index:
            fcf_raw = cashflow.loc[fcf_line].head(4)[::-1]
            years = [col.year for col in fcf_raw.index]
            base_value = np.mean(fcf_raw.values)
            forecast_years = [years[-1] + i for i in range(1, 6)]
            growth_rate = 0.17
            fcf_forecast = [base_value * (1 + growth_rate) ** i for i in range(1, 6)]
            terminal_value = fcf_forecast[-1] * 1.03
        else:
            fcf_forecast = [0] * 5
            terminal_value = 0

        # CAGR Calculation
        fcf_cagr = ((fcf_forecast[-1] / fcf_raw.values[0]) ** (1/9)) - 1 if fcf_raw.values[0] else 0

        # Capital Structure
        total_equity = safe_get(balance_sheet, 'Total Equity Gross Minority Interest')
        total_debt = safe_get(balance_sheet, 'Total Debt')
        cash = safe_get(balance_sheet, 'Cash And Cash Equivalents')
        net_debt = total_debt - cash
        shares_outstanding = safe_get(balance_sheet, 'Ordinary Shares Number')

        # Cost of Debt
        interest_expense = safe_get(income_stmt, 'Interest Expense')
        tax_rate = safe_get(income_stmt, 'Tax Rate For Calcs', default=0.241)
        pretax_cod = (interest_expense / total_debt * 100) if interest_expense and total_debt else 5
        after_tax_cod = pretax_cod * (1 - tax_rate)

        # Cost of Equity
        equity_risk_premium = 2.9 / 100
        country_risk_premium = 2.5 / 100
        cost_of_equity = (risk_free_rate/100) + equity_risk_premium + country_risk_premium

        # WACC
        total_capital = total_equity + total_debt
        equity_weight = total_equity / total_capital if total_capital else 0
        debt_weight = total_debt / total_capital if total_capital else 0
        wacc = (equity_weight * cost_of_equity) + (debt_weight * after_tax_cod / 100) if total_capital else 0.1

        # DCF Valuation
        discount_factors = [(1 + wacc) ** i for i in range(1, 6)]
        discounted_fcfs = np.array(fcf_forecast) / discount_factors
        discounted_terminal = terminal_value / ((1 + wacc) ** 5)
        enterprise_value = np.sum(discounted_fcfs) + discounted_terminal
        equity_value = enterprise_value - net_debt
        intrinsic_value = equity_value / shares_outstanding if shares_outstanding else 0
        upside = ((intrinsic_value - market_price) / market_price) * 100

        # --- TITLE ---
        st.title("📊 DCF Valuation Analysis")
        st.markdown("<hr style='margin-top:0; margin-bottom:2.5rem; border:1px solid #34495e;'>", unsafe_allow_html=True)

        # --- METRIC BOXES ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-box'>📈 Market Price<br>{market_price:,.2f}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-box'>📊 CAGR FCF<br>{fcf_cagr*100:.2f}%</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-box'>🏦 WACC<br>{wacc*100:.2f}%</div>", unsafe_allow_html=True)

        # --- INFO BOX BELOW THE METRIC BOXES ---
        st.markdown(f"""
        <div class='info-box'>💡 The Discounted Cash Flow (DCF) model is best suited for companies with stable growth and consistent free cash flow. It provides the most accurate intrinsic value for such firms. For companies like banks, which have fluctuating cash flows and dividend-based valuation, the Dividend Discount Model (DDM) is more appropriate. Stay tuned for the DDM model (coming soon).</div>
        """, unsafe_allow_html=True)

        # --- STOCK PERFORMANCE CHART ---
        st.markdown("<hr style='border:1px solid #34495e;'>", unsafe_allow_html=True)
        st.subheader("📈 Stock Performance (Last 5 Years)")
        hist = stock.history(period="5y")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='Close Price'))
        fig.update_layout(
            plot_bgcolor='#050915', 
            paper_bgcolor='#050915', 
            font=dict(color='white'),
            xaxis_title='Date',
            yaxis_title='Price',
            hovermode='x unified',
            margin=dict(l=30, r=30, t=50, b=30)
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- FCF FORECASTING CHART ---
        st.markdown("<hr style='border:1px solid #34495e;'>", unsafe_allow_html=True)
        st.subheader("📈 FCF Forecasting")

        fig2 = go.Figure()

        fig2.add_trace(go.Bar(
            x=years,
            y=fcf_raw.values,
            name='Historical FCF',
            marker_color='#f39c12'
        ))

        fig2.add_trace(go.Bar(
            x=forecast_years,
            y=fcf_forecast,
            name='Forecasted FCF',
            marker_color='#3498db'
        ))

        fig2.add_trace(go.Scatter(
            x=[forecast_years[-1]+1],
            y=[terminal_value],
            mode='markers+text',
            name='Terminal Value',
            marker=dict(size=12, color='#fab1a0'),
            text=['Terminal'],
            textposition='top center'
        ))

        fig2.update_layout(
            barmode='group',
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.12,
                xanchor="center",
                x=0.5,
                font=dict(size=14)
            ),
            plot_bgcolor='#050915',
            paper_bgcolor='#050915',
            font=dict(color='white'),
            xaxis_title='Year',
            yaxis_title='FCF Value',
            hovermode='x unified'
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.markdown(f"<div class='info-box'>📊 Historical free cash flow, after deducting capital expenditures from operations, is forecasted using machine learning, utilizing Random Forest models.</div>", unsafe_allow_html=True)

        # --- WACC AND CAPITAL STRUCTURE ---
        st.markdown("<hr style='border:1px solid #34495e;'>", unsafe_allow_html=True)
        st.subheader("📊 Capital Structure")

        fig_pie = go.Figure(data=[go.Pie(
            labels=['Equity', 'Debt'],
            values=[total_equity, total_debt],
            hole=0.4,
            textinfo='percent',
            insidetextorientation='horizontal'
        )])
        fig_pie.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            width=350,
            height=350,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.1,
                xanchor="center",
                x=0.5,
                font=dict(size=14)
            ),
            plot_bgcolor='#050915',
            paper_bgcolor='#050915',
            font=dict(color='white')
        )

        col1, col2 = st.columns([1, 1.2])
        with col1:
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
        with col2:
            st.markdown("#### Capital Structure Summary")
            df_structure = pd.DataFrame({
                'Component': ['Equity', 'Debt', 'Assets'],
                'Amount': [total_equity, total_debt, total_capital]
            })
            df_structure['Amount'] = df_structure['Amount'].apply(lambda x: f"{x:,.0f}")
            st.dataframe(df_structure, use_container_width=True)

        # --- COST OF EQUITY TABLE ---
        st.subheader("🧮 Cost of Equity")
        coe_data = pd.DataFrame({
            "Component": ["Risk-Free Rate", "Equity Risk Premium", "Country Risk Premium", "Final Cost of Equity"],
            "Value": [f"{risk_free_rate:.2f}%", "2.90%", "2.50%", f"{cost_of_equity*100:.2f}%"]
        })
        st.dataframe(coe_data, use_container_width=True)

        # --- COST OF DEBT TABLE ---
        st.subheader("🏦 Cost of Debt")
        cod_data = pd.DataFrame({
            "Component": ["Interest Expense", "Pretax Cost of Debt", "Effective Tax Rate", "After-Tax Cost of Debt"],
            "Value": [f"{interest_expense:,.0f}", f"{pretax_cod:.2f}%", f"{tax_rate*100:.2f}%", f"{after_tax_cod:.2f}%"]
        })
        st.dataframe(cod_data, use_container_width=True)

        st.markdown(f"""
        <div class='info-box'>
        📚 The cost of equity and the country risk premium figures are sourced from NYU Stern's financial market database curated by Professor Aswath Damodaran. 
        The after-tax cost of debt is computed by adjusting the pretax cost of debt based on the effective tax rate to accurately reflect the true cost of borrowing.
        </div>
        """, unsafe_allow_html=True)

        # --- VALUATION TABLE ---
        st.markdown("<hr style='border:1px solid #34495e;'>", unsafe_allow_html=True)
        st.subheader("📈 Final DCF Valuation Result")
        valuation_df = pd.DataFrame({
            "Metric": [
                "Discounted FCF (5 Years)",
                "Discounted Terminal Value",
                "Enterprise Value",
                "Net Debt",
                "Equity Value",
                "Shares Outstanding",
                "Intrinsic Value per Share"
            ],
            "Value": [
                np.sum(discounted_fcfs),
                discounted_terminal,
                enterprise_value,
                net_debt,
                equity_value,
                shares_outstanding,
                intrinsic_value
            ]
        })
        valuation_df['Value'] = valuation_df['Value'].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else x)
        st.dataframe(valuation_df, use_container_width=True)

        # --- FINAL UPSIDE/DOWNSIDE METRIC BOXES ---
        st.markdown("<hr style='border:1px solid #34495e;'>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-box'>📈 Market Price<br>{market_price:,.2f}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-box'>🎯 Intrinsic Value<br>{intrinsic_value:,.2f}</div>", unsafe_allow_html=True)
        with col3:
            if upside >= 0:
                st.markdown(f"<div class='metric-box'>📈 Upside Potential<br>+{upside:.2f}%</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='metric-box'>📉 Downside Risk<br>{upside:.2f}%</div>", unsafe_allow_html=True)

        # --- DISCLAIMER AND FOOTER ---
        st.markdown("<hr style='border:1px solid #34495e;'>", unsafe_allow_html=True)
        st.markdown(f"<div class='info-box'>⚠️ This tool is for educational purposes only. Please perform your own analysis or consult a financial advisor before making investment decisions.</div>", unsafe_allow_html=True)
        st.markdown("<div class='footer-text'>Created by Abida Massi</div>", unsafe_allow_html=True)

else:
    st.info("Please input parameters and click Submit to generate DCF Valuation.")
