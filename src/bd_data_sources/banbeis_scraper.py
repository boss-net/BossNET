# src/bd_data_sources/banbeis_scraper.py

import pandas as pd
import requests
from io import StringIO

BANBEIS_URL = "https://example.banbeis.gov.bd/data.csv"  # Replace with real URL

def extract_banbeis_data() -> pd.DataFrame:
    try:
        response = requests.get(BANBEIS_URL, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        print(f"✅ Fetched {len(df)} rows from BANBEIS.")
        return df
    except Exception as e:
        print(f"❌ Error fetching BANBEIS data: {e}")
        return pd.DataFrame()
