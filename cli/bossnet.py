# cli/bossnet.py

import typer
from src.data_processing.data_processor import run_etl
from src.models.student_performance_model import train_model

app = typer.Typer()

@app.command()
def etl(source: str = "banbeis"):
    """Run ETL pipeline for a data source"""
    run_etl(source)

@app.command()
def train(file: str = "processed_data/student_performance.csv"):
    """Train the student performance model"""
    import pandas as pd
    from src.models.student_performance_model import preprocess

    df = pd.read_csv(file)
    X, y = preprocess(df)
    train_model(X, y)

@app.command()
def dashboard():
    """Render the equity dashboard"""
    from src.visualization.edu_gap_dash import plot_equity_map
    plot_equity_map()

if __name__ == "__main__":
    app()
