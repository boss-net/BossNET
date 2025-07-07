# src/visualization/edu_gap_dash.py

import plotly.express as px
import pandas as pd

def plot_equity_map(data_path="processed_data/equity_by_district.csv"):
    df = pd.read_csv(data_path)
    fig = px.choropleth(
        df,
        geojson="geo_data/bd_districts.geojson",
        locations="district",
        featureidkey="properties.district",
        color="gender_gap_score",
        title="📍 Gender Gap in Education by District"
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.show()
