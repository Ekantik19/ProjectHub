import pandas as pd
from fredapi import Fred
import os
from dotenv import load_dotenv
load_dotenv()

fred = Fred(api_key=os.getenv('FRED_API_KEY'))

tickers = {
    'DGS1MO': 1/12, 'DGS3MO': 0.25, 'DGS6MO': 0.5,
    'DGS1': 1.0, 'DGS2': 2.0, 'DGS3': 3.0, 
    'DGS5': 5.0, 'DGS7': 7.0, 'DGS10': 10.0, 
    'DGS20': 20.0, 'DGS30': 30.0
}

data = []
for ticker, maturity in tickers.items():
    series = fred.get_series(ticker)
    latest_yield = series.iloc[-1]  # Get the most recent value
    data.append({'maturity_years': maturity, 'yield': latest_yield})

df_raw = pd.DataFrame(data).dropna()
print(df_raw)

output_filename = "raw_yield_curve_data.csv"
df_raw.to_csv(output_filename, index=False)
