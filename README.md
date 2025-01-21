This is a simple interface to quickly check key facts and historical data for a given security.

# Installation
Run the following in your python console to download the required libraries.
```
pip install streamlit
pip install pandas
pip install numpy
pip install altair
pip install yfinance
pip install streamlit_extras
```

Pull this project into your local environment.
From the home directory (hgv) run the following command:
```
streamlit run geni.py
```

# Usage
Start with the text box. Enter in any ticker and press Enter.
Alternatively, you can use the "Screener" tab to select from a pre-determined list.

Select a Start and End Date for the price data.

Toggle the graph between Price history and Earnings data.

Price History data includes benchmarks that show their relative performance since the specified Start Date.

Due to the free version of yfinance, we are not able to get any financials for anything beyond 12 months in the past. With this in mind, the financials do not adhere to the date filters, but they do control the price graph and relative benchmark data.