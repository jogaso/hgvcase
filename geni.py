import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import yfinance as yf
from datetime import datetime
from streamlit_extras.stylable_container import stylable_container

st.set_page_config(layout="wide")

# Function to clean the income statement data
def yf_clean_incomeStmt(i, qtrOrAnnual):
    # Quarterly and Annual data have different row names
    if qtrOrAnnual == 'Quarterly':
        i = i.loc[['Total Revenue', 'Cost Of Revenue', 'Gross Profit', 'Operating Expense', 'Operating Income', 'EBITDA']]
    else:
        i = i.loc[['TotalRevenue', 'CostOfRevenue', 'GrossProfit', 'OperatingExpense', 'OperatingIncome', 'EBITDA']]
    new_row_names = {
        'TotalRevenue': 'Total Revenue',
        'CostOfRevenue': 'Cost of Revenue',
        'GrossProfit': 'Gross Profit',
        'OperatingExpense': 'Operating Expense',
        'OperatingIncome': 'Operating Income'
    }
    if qtrOrAnnual == 'Annual':
        i = i.rename(index=new_row_names)
    neg_rows = ['Cost Of Revenue', 'Operating Expense']
    i.loc[neg_rows] = i.loc[neg_rows] * -1
    i = i * 0.001
    i.columns = pd.to_datetime(i.columns).date
    i.dropna(how='all', axis=1, inplace=True)
    return i

def clear_textbox():
    return st.text_input('Ticker', value='', key=0)

def copy_to_textbox():
    newinput = st.session_state.ticker
    return st.text_input('Ticker', value=newinput, key=0)

# Function to add emojis (not implemented)
def add_emoji(value, previous_value):
    if value > previous_value:
        return f"⇧ {value}"
    elif value < previous_value:
        return f"⇩ {value}"
    else:
        return f"{value}"

# Read screener security data        
column_names = ["Ticker"]
df = pd.read_csv('files/tickers.csv', names=column_names) 

# Sidebar for security input from user
with st.sidebar:
    tickerTxtTab, tickerBoxTab = st.tabs(["Ticker", "Screener"])
    with tickerTxtTab:
        txtticker = st.text_input('Ticker', placeholder = 'Enter a symbol')
        txtticker = txtticker.upper()
        st.session_state.ticker = txtticker
    with tickerBoxTab:
        if st.session_state.ticker == '':
            st.session_state.ticker = st.selectbox('Select a symbol:', df)
        else:
            chk_inScreener = df['Ticker'].isin([st.session_state.ticker]).any()
            if chk_inScreener:
                boxTickerIdx = df[df['Ticker'] == st.session_state.ticker].index[0]
                st.session_state.ticker = st.selectbox('Select a symbol:', df, index=int(boxTickerIdx))
            else:
                st.selectbox('Select a symbol:', df)
        ticker = st.session_state.ticker
    
    # Set ticker
    ticker = st.session_state.ticker

    # Fetch data for a specific ticker
    dat = yf.Ticker(ticker)
    
    # Adding date range filter in the sidebar
    start_date = st.date_input('Start date', datetime(2024, 1, 1))
    end_date = st.date_input('End date', datetime.today())

# Add security name as title
st.title(dat.info['shortName'] + " " + "(" + ticker + ")")

# Get benchmark prices and error handle for date range
if start_date < end_date:
    px_data = yf.download([ticker, 'SPY', 'COMP'], start=start_date, end=end_date)
else:
    st.error('Error: End date must fall after start date.')


# Clean up the price data
keepCol = [('Close', ticker), ('Close', 'SPY'), ('Close', 'COMP')]
px_data = px_data[px_data.columns.intersection(keepCol)]
px_data.columns = px_data.columns.droplevel()

# Calculations for benchmark relative price data
start_px = px_data[ticker].values[0]

px_data['SPYPctChg'] = (px_data['SPY'].pct_change().fillna(0) + 1).cumprod()
px_data['SPY_1'] = start_px * (px_data['SPYPctChg'])
px_data.drop(['SPY', 'SPYPctChg'], axis=1, inplace=True)
px_data.rename(columns={ticker: ticker, 'SPY_1': 'SPY'}, inplace=True)

px_data['COMPPctChg'] = (px_data['COMP'].pct_change().fillna(0) + 1).cumprod()
px_data['COMP_1'] = start_px * (px_data['COMPPctChg'])
px_data.drop(['COMP', 'COMPPctChg'], axis=1, inplace=True)
px_data.rename(columns={ticker: ticker, 'COMP_1': 'COMP'}, inplace=True)

px_data.index = px_data.index.date.astype(str)


fig_col1, fig_col2, fig_col3 = st.columns([10.9, 0.2, 10.9])

with fig_col1:
    fcol1, fcol2 = st.columns(2)
    # Get income statement data
    fig = dat.quarterly_income_stmt
    with fcol1:
        st.markdown("Fact Sheet")
        i = dat.info
        cf = round(i['operatingCashflow'] * 0.001, 0)
        factsdf = pd.DataFrame([['Beta', i['beta']], ['P/E Ratio', i['forwardPE']], ['Avg Vol (90D)', i['averageVolume']]], columns=['Category', 'Value'])
        factsdf['Value'] = factsdf['Value'].round(2)
        factsdf.loc[len(factsdf)] = ['Cash Flow TTM (thousands $)', cf]
        factsdf.set_index('Category', inplace=True)
        factsdf.index.name = None
        # Display fact sheet
        with stylable_container(
            key="factsdf",
            css_styles="""
            dataframe{
                float: right;
            }
            """
        ): factsdf = st.dataframe(factsdf, use_container_width=True)
        st.divider()
        
        # Get balance sheet data
        q_bs = dat.quarterly_balance_sheet
        q_bs = q_bs * 0.001
        q_bs_Date = q_bs.columns[0].date()
        specific_rows = q_bs.loc[['Total Debt', 'Net Debt', 'Stockholders Equity', 'Total Capitalization']]
        capdf = specific_rows.iloc[:, [0]].copy()
        capdf.rename(columns={capdf.columns[0]: 'thousands ($)'}, inplace=True)
        
        # display capital data
        st.dataframe(data=capdf, use_container_width=True)
        st.caption("_Data as of " + q_bs_Date.strftime("%Y-%m-%d") + "_")
    
    with fcol2:
        # Display income data
        st.markdown("Quick Income")
        rev_out = yf_clean_incomeStmt(fig, 'Quarterly')
        rev_unpiv = rev_out.loc[['Total Revenue', 'Gross Profit', 'Operating Income']].unstack().reset_index(name='value')
        rev_unpiv = rev_unpiv.rename(columns={'level_0': 'Date', 'level_1': 'Category', 'value': 'Value'})
        # sample SQL code to replicate the coding of rev_unpiv
#        DECLARE @lastmonth datetime
#        SELECT @lastmonth = EOMONTH(GETDATE(), -1)
#        CREATE TABLE #tmpDates (EndDate datetime)
#
#        WHILE @count < 12
#        BEGIN
#           INSERT  INTO #tmpDates (EndDate)
#           SELECT  @lastmonth
#           SELECT @lastmonth = EOMONTH(DATEADD('m', -1 , @lastmonth))
#           SELECT @count = @count + 1
#        END
#        DECLARE	@stCols VARCHAR(MAX)
#
#        SELECT	@stCols = STUFF((
#        SELECT	', '+QUOTENAME(d.EndDate)
#        FROM	#tmpDates d
#        ORDER BY d.EndDate
#        FOR	XML PATH('')), 1, 2, '')
#
#        SELECT	@stSQL = '
#        SELECT Date, Category, Value
#        FROM
#        (
#        SELECT 
#            ' + @stCols + ', 
#            Category, 
#        FROM rev_out
#        ) r
#        UNPIVOT
#        (
#        value
#        for Date in (' + @stCols + ')
#        ) unpiv;
#        '
#
#        EXEC (@stSQL)
        # end of sample SQL code

        # Code to add icons to indicate change in the period (not implemented)
        tr = rev_unpiv.loc[rev_unpiv['Category'] == 'Total Revenue'].copy()
        rev_prev = tr['Value'].shift(-1)
        tr['prev'] = rev_prev.fillna(tr['Value'])
        tr['Value'] = tr.apply(lambda x: add_emoji(x['Value'], x['prev']), axis=1)
        tr = tr.pivot(index='Category', columns='Date', values='Value')
        tr = tr.sort_index(axis=0, ascending=False)

        revout = st.dataframe(rev_out, use_container_width=True)
        st.area_chart(rev_unpiv, x='Date', y='Value', color='Category', x_label='Date', y_label='thousands ($)', use_container_width=True)

# Add vertical divider for readability    
with fig_col2:
    st.html(
        '''
            <div class="divider-vertical-line"></div>
            <style>
                .divider-vertical-line {
                    border-left: 2px solid rgba(49, 51, 63, 0.2);
                    height: 700px;
                    margin: auto;
                }
            </style>
        '''
    )

with fig_col3:
    tab1, tab2 = st.tabs(["Price", "Earnings"])
    ccy = i['financialCurrency']
    ylbl = "Price (" + ccy + ")"
    
    # Display price data with benchmark change
    with tab1:
        #unpivot data for plotting
        px_data_unpiv = px_data.unstack().reset_index(name='Price')
        px_data_unpiv = px_data_unpiv.rename(columns={'Ticker': 'Ticker', 'level_1': 'Date', 'Price': ylbl})
        # Setting some custom y axis limits
        px_max = px_data_unpiv[ylbl].max()
        px_min = px_data_unpiv[ylbl].min()
        y_max = px_max + 0.1*(px_max - px_min)
        y_min = px_min - 0.1*(px_max - px_min)
        order= [ticker, 'SPY', 'COMP']
        # using altair chart for date handling
        chart = alt.Chart(px_data_unpiv).mark_line().encode(
            x=alt.X('Date'),
            y=alt.Y(ylbl, scale=alt.Scale(domain=[y_min, y_max])),
            color=alt.Color('Ticker', sort=order),
            order=alt.Order('color_ticker_sort_index:Q')
        ).properties(
            height=700
        ).interactive()
        st.altair_chart(chart, theme="streamlit", use_container_width=True)
        
    # display earnings history
    with tab2:
        eps_data = fig.loc['Diluted EPS'].copy()
        eps_data = eps_data.replace(to_replace='None', value=np.nan).dropna()
        # Calculate TTM eps data
        TTM = eps_data[::-1].rolling(4).sum()[::-1]
        eps_data = pd.concat([eps_data, TTM], axis=1)
        eps_data.columns = ['Qtrly EPS', 'TTM']
        eps_data.index.name = 'Quarter End'
        eps_data['Date'] = eps_data.index
        base = alt.Chart(eps_data).encode(x=alt.X('Date:T', axis = alt.Axis(title='Date', format = ("%b %Y")))).interactive()

        bar = base.mark_bar(size=80).encode(y='Qtrly EPS:Q')

        line =  base.mark_line(color='#ffc0b8').encode(y='TTM:Q')
        # overlay the two charts
        c = (bar + line).properties(width=600)
        st.altair_chart(c, theme="streamlit", use_container_width=True)
        


# make csv's available:
csv = dat.quarterly_balance_sheet.to_csv().encode('utf-8')
csv.capitalize()
st.download_button(
    label="Balance Sheet",
    data=csv,
    file_name=f'{ticker}_quarterly_balance_sheet.csv',
    mime='text/csv',
)

csv = dat.quarterly_income_stmt.to_csv().encode('utf-8')
csv.capitalize()
st.download_button(
    label="Income Stmt",
    data=csv,
    file_name=f'{ticker}_quarterly_income_stmt.csv',
    mime='text/csv',
)

csv = dat.quarterly_cashflow.to_csv().encode('utf-8')
csv.capitalize()
st.download_button(
    label="Cash Flow",
    data=csv,
    file_name=f'{ticker}_quarterly_cash_flow.csv',
    mime='text/csv',
)

