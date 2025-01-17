import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import yfinance as yf
from datetime import datetime

st.set_page_config(layout="wide")

# Function to clean the income statement data
def yf_clean_incomeStmt(i):
    i = i.loc[['TotalRevenue', 'CostOfRevenue', 'GrossProfit', 'OperatingExpense', 'OperatingIncome']]
    neg_rows = ['CostOfRevenue', 'OperatingExpense']
    i.loc[neg_rows] = i.loc[neg_rows] * -1
    i = i * 0.001
    i.columns = pd.to_datetime(i.columns).date
    new_row_names = {
        'TotalRevenue': 'Total Revenue',
        'CostOfRevenue': 'Cost of Revenue',
        'GrossProfit': 'Gross Profit',
        'OperatingExpense': 'Operating Expense',
        'OperatingIncome': 'Operating Income'
    }
    i = i.rename(index=new_row_names)
    return i

# Function to get displayName for a given symbol
def get_display_name(symbol, result):
    for quote in result['quotes']:
        if quote['symbol'] == symbol:
            return quote.get('displayName', 'Unknown')
    return 'Unknown'



screener = yf.Screener()
screener.set_predefined_body('aggressive_small_caps')
result = screener.response
symbols = [quote['symbol'] for quote in result['quotes']]

# Move selectbox to the sidebar
with st.sidebar:
    st.write("Symbols from the screener:")
    ticker = st.selectbox(
        'Select a symbol from the screener:',
        symbols
        + ['PENN', 'BYD', 'FAF', 'R', 'DRVN', 'CZR', 'PLYA']
    )
    st.write(get_display_name(ticker, result))
    # Adding date range filter in the sidebar
    start_date = st.date_input('Start date', datetime(2024, 1, 10))
    end_date = st.date_input('End date', datetime.today())

if start_date < end_date:
    px_data = yf.download([ticker, 'SPY', 'COMP'], start=start_date, end=end_date)
else:
    st.error('Error: End date must fall after start date.')

#print(px_data.head(n=10).to_string(index=False))
#row_labels = px_data.index
#print(row_labels)

keepCol = [('Close', ticker), ('Close', 'SPY'), ('Close', 'COMP')]
px_data = px_data[px_data.columns.intersection(keepCol)]
#px_data = px_data['Close'].copy(deep=True)
#px_data.drop(['High', 'Low', 'Open', 'Volume'], axis=1, inplace=True)
px_data.columns = px_data.columns.droplevel()
#column_labels_list = px_data.columns.tolist()
#print(column_labels_list)

start_px = px_data.iloc[0, 0]
px_data['SPYPctChg'] = (px_data['SPY'].pct_change().fillna(0) + 1).cumprod()
px_data['SPY_1'] = start_px * (px_data['SPYPctChg'])
px_data.drop(['SPY', 'SPYPctChg'], axis=1, inplace=True)
px_data.rename(columns={ticker: ticker, 'SPY_1': 'SPY'}, inplace=True)

px_data['COMPPctChg'] = (px_data['COMP'].pct_change().fillna(0) + 1).cumprod()
px_data['COMP_1'] = start_px * (px_data['COMPPctChg'])
px_data.drop(['COMP', 'COMPPctChg'], axis=1, inplace=True)
px_data.rename(columns={ticker: ticker, 'COMP_1': 'COMP'}, inplace=True)

px_data.index = px_data.index.date.astype(str)




fig_col1, fig_col2 = st.columns(2)

with fig_col1:
    st.markdown("Fact Sheet")
    dat = yf.Ticker(ticker)
    #fig = dat.quarterly_income_stmt
    fig = dat.get_income_stmt()
    tbl_out = yf_clean_incomeStmt(fig)
    #st.write(tbl_out)
    
    i = dat.info
    #st.write(i)
    factsdf = pd.DataFrame([['Beta', i['beta']], ['P/E Ratio', i['forwardPE']], ['Avg Vol (90D)', i['averageVolume']]], columns=['Category', 'Value'])
    factsdf.set_index('Category', inplace=True)

    #factsdf.drop(['Category'], axis=1, inplace=True)
    st.write(factsdf)

    # Export income statement to CSV
    csv = fig.to_csv().encode('utf-8')
    csv.capitalize()
    st.download_button(
        label="csv",
        data=csv,
        file_name=f'{ticker}_quarterly_income_stmt.csv',
        mime='text/csv',
    )
    tbl_unpiv = tbl_out.unstack().reset_index(name='value')
    tbl_unpiv = tbl_unpiv.rename(columns={'level_0': 'Date', 'level_1': 'Category', 'value': 'Value'})
    
    st.area_chart(tbl_unpiv, x='Date', y='Value', color='Category', height=400, use_container_width=False)
    #st.write(i)
    #facts = [['Beta', i['beta']]]
    #factsdf = pd.DataFrame(facts, columns=['Value'])
    #st.write(factsdf)

with fig_col2:
#    if not px_btn and not eps_btn:
#        px_btn = True
#    ccy = i['financialCurrency']
#    if px_btn:
#        st.markdown("Chart")
#        st.write(f"Close Price for {ticker}:")
#        ylbl = "Price (" + ccy + ")"
#        st.line_chart(px_data, width=0, height=700, use_container_width=True, x_label='Date', y_label=ylbl)
#    elif eps_btn:
#        st.markdown("Chart")
#        st.write(f"EPS for {ticker}:")
    tab1, tab2 = st.tabs(["Price", "Earnings"])
    ccy = i['financialCurrency']
    ylbl = "Price (" + ccy + ")"
    with tab1:
        px_data_unpiv = px_data.unstack().reset_index(name='Price')
        px_data_unpiv = px_data_unpiv.rename(columns={'Ticker': 'Ticker', 'level_1': 'Date', 'Price': ylbl})
        px_max = px_data_unpiv[ylbl].max()
        px_min = px_data_unpiv[ylbl].min()
        y_max = px_max + 0.1*(px_max - px_min)
        y_min = px_min - 0.1*(px_max - px_min)
        chart = alt.Chart(px_data_unpiv).mark_line().encode(
            x=alt.X('Date'),
            y=alt.Y(ylbl, scale=alt.Scale(domain=[y_min, y_max])),
            color='Ticker'
        ).properties(
            height=700
        ).interactive()
        st.altair_chart(chart, theme="streamlit", use_container_width=True)
        #st.markdown("Price Chart w Benchmark")        
        #st.line_chart(px_data, width=0, height=700, use_container_width=True, x_label='Date', y_label=ylbl)
    with tab2:
        st.line_chart(px_data, width=0, height=700, use_container_width=True, x_label='Date', y_label=ylbl)



#st.write(t.get_shares_full())
#st.write(t.get_income_stmt())
#st.write(t.get_balance_sheet())
#st.write(t.get_earnings_history())
#st.write(t.get_cashflow())
#st.write(t.basic_info())