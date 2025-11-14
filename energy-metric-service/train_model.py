#!/usr/bin/env python3
"""
Script to train and save the energy forecasting model
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import os


def train_energy_model():
    """Train the energy forecasting model and save it"""
    
    # Load data
    print("Loading data...")
    df = pd.read_csv('node_metrics_export.csv')
    
    # Data preprocessing
    print("Preprocessing data...")
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # Drop unnecessary columns
    columns_to_drop = ['created_at', 'memory_utilization_bytes', 'memory_assigned_bytes', 'machine_memory_total_bytes']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])
    
    # Create derived features
    df['cpu_memory_ratio'] = df['cpu_utilization_percent'] / (df['memory_utilization_percent'] + 1e-8)
    
    # Sort by timestamp
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Select features
    feature_columns = [
        'cpu_utilization_percent',
        'memory_utilization_percent',
        'cpu_memory_ratio'
    ]
    
    X = df[feature_columns].copy()
    y = df['energy_watts'].copy()
    
    print(f"Dataset shape: {df.shape}")
    print(f"Features: {feature_columns}")
    
    # Split data (time-based split for time series)
    split_idx = int(0.8 * len(X))
    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]
    
    print(f"Training set: {X_train.shape}")
    print(f"Test set: {X_test.shape}")
    
    # Train model
    print("Training Random Forest model...")
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate model
    print("Evaluating model...")
    y_pred = model.predict(X_test)
    
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    print(f"Model Performance:")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  R²: {r2:.4f}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(f"\nFeature Importance:")
    for _, row in feature_importance.iterrows():
        print(f"  {row['feature']}: {row['importance']:.4f}")
    
    # Save model and metadata
    print("Saving model...")
    
    model_data = {
        'model': model,
        'feature_columns': feature_columns,
        'model_metrics': {
            'rmse': rmse,
            'r2': r2
        },
        'feature_importance': feature_importance.to_dict('records')
    }
    
    joblib.dump(model_data, 'energy_forecasting_model.pkl')
    
    # Save sample data statistics for validation
    stats = {
        'cpu_utilization_mean': df['cpu_utilization_percent'].mean(),
        'cpu_utilization_std': df['cpu_utilization_percent'].std(),
        'memory_utilization_mean': df['memory_utilization_percent'].mean(),
        'memory_utilization_std': df['memory_utilization_percent'].std(),
        'energy_mean': df['energy_watts'].mean(),
        'energy_std': df['energy_watts'].std(),
    }
    
    joblib.dump(stats, 'model_stats.pkl')
    
    print("Model saved successfully!")
    print(f"Files created:")
    print(f"  - energy_forecasting_model.pkl")
    print(f"  - model_stats.pkl")
    
    return model_data


if __name__ == "__main__":
    train_energy_model()