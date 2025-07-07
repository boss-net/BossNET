# src/models/student_performance_model.py

import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from typing import Tuple

def load_data(file_path: str) -> pd.DataFrame:
    return pd.read_csv(file_path)

def preprocess(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    df = df.dropna()
    X = df.drop(columns=["student_id", "performance_label"])
    y = df["performance_label"]
    return X.values, y.values

def train_model(X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print("📊 Classification Report:")
    print(classification_report(y_test, y_pred))

    # Track with MLflow
    mlflow.set_experiment("Student Performance Analysis")
    with mlflow.start_run():
        mlflow.log_param("model_type", "RandomForest")
        mlflow.log_metric("accuracy", acc)
        mlflow.sklearn.log_model(model, "model")

    return model

if __name__ == "__main__":
    df = load_data("processed_data/student_performance.csv")
    X, y = preprocess(df)
    train_model(X, y)
