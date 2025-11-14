"""
Energy Forecasting Service
"""

import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class EnergyForecastingService:
    """Service for energy consumption forecasting - Singleton pattern"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, model_path: str = "energy_forecasting_model.pkl"):
        if cls._instance is None:
            cls._instance = super(EnergyForecastingService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, model_path: str = "energy_forecasting_model.pkl"):
        # Only initialize once
        if not self._initialized:
            self.model_data = None
            self.model = None
            self.feature_columns = None
            self.model_metrics = None
            self.stats = None
            self.model_path = model_path
            self._load_model()
            EnergyForecastingService._initialized = True
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the service"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _load_model(self):
        """Load the trained model and associated data"""
        try:
            # Try multiple locations for the model file
            possible_paths = [
                Path(self.model_path),  # Current directory
                Path(__file__).parent.parent / self.model_path,  # app directory
                Path(__file__).parent.parent.parent / self.model_path,  # project root
            ]
            
            model_file = None
            for path in possible_paths:
                if path.exists():
                    model_file = path
                    break
            
            if model_file is None:
                raise FileNotFoundError(f"Model file not found in any of these locations: {[str(p) for p in possible_paths]}")
            
            logger.info(f"Loading model from: {model_file}")
            self.model_data = joblib.load(model_file)
            
            self.model = self.model_data['model']
            self.feature_columns = self.model_data['feature_columns']
            self.model_metrics = self.model_data['model_metrics']
            
            # Load stats if available
            stats_file = model_file.parent / "model_stats.pkl"
            if stats_file.exists():
                self.stats = joblib.load(stats_file)
            else:
                # Try to find stats file in the same locations as model
                for path in possible_paths:
                    stats_path = path.parent / "model_stats.pkl"
                    if stats_path.exists():
                        self.stats = joblib.load(stats_path)
                        break
            
            logger.info(f"Model loaded successfully. R² score: {self.model_metrics.get('r2', 'N/A')}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def predict_single(self, cpu_utilization: float, memory_utilization: float) -> Dict[str, Any]:
        """
        Predict energy consumption for a single data point
        
        Args:
            cpu_utilization: CPU utilization percentage (0-100)
            memory_utilization: Memory utilization percentage (0-100)
            
        Returns:
            Dictionary with prediction and metadata
        """
        try:
            # Validate inputs
            if not (0 <= cpu_utilization <= 100):
                raise ValueError("CPU utilization must be between 0 and 100")
            if not (0 <= memory_utilization <= 100):
                raise ValueError("Memory utilization must be between 0 and 100")
            
            # Calculate derived features
            cpu_memory_ratio = cpu_utilization / (memory_utilization + 1e-8)
            
            # Create feature array with proper feature names
            import pandas as pd
            features_dict = {
                'cpu_utilization_percent': cpu_utilization,
                'memory_utilization_percent': memory_utilization,
                'cpu_memory_ratio': cpu_memory_ratio
            }
            features_df = pd.DataFrame([features_dict])
            
            # Make prediction
            prediction = self.model.predict(features_df)[0]
            
            # Calculate confidence based on how close inputs are to training data
            confidence = self._calculate_confidence(cpu_utilization, memory_utilization)
            
            return {
                'predicted_energy_watts': round(prediction, 4),
                'confidence': confidence,
                'inputs': {
                    'cpu_utilization_percent': cpu_utilization,
                    'memory_utilization_percent': memory_utilization,
                    'cpu_memory_ratio': round(cpu_memory_ratio, 4)
                },
                'model_info': {
                    'rmse': self.model_metrics.get('rmse'),
                    'r2_score': self.model_metrics.get('r2')
                }
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise
    
    def predict_timeseries(self, timeseries_data: List[Dict]) -> List[Dict]:
        """
        Predict energy consumption for a time series of data
        
        Args:
            timeseries_data: List of dictionaries with 'timestamp', 'cpu_utilization', 'memory_utilization'
            
        Returns:
            List of predictions with timestamps
        """
        try:
            predictions = []
            
            for data_point in timeseries_data:
                timestamp = data_point.get('timestamp')
                cpu_util = data_point.get('cpu_utilization', data_point.get('cpu_utilization_percent', 0))
                memory_util = data_point.get('memory_utilization', data_point.get('memory_utilization_percent', 0))
                
                # Make prediction
                prediction_result = self.predict_single(cpu_util, memory_util)
                
                # Add timestamp to result
                prediction_result['timestamp'] = timestamp
                predictions.append(prediction_result)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Time series prediction failed: {e}")
            raise
    
    def forecast_next_day(self, current_data: List[Dict], forecast_hours: int = 24) -> Dict[str, Any]:
        """
        Forecast energy consumption for the next day based on recent patterns
        
        Args:
            current_data: Recent data points (last few hours/days)
            forecast_hours: Number of hours to forecast (default 24)
            
        Returns:
            Dictionary with hourly forecasts and summary statistics
        """
        try:
            if not current_data:
                raise ValueError("Current data is required for forecasting")
            
            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(current_data)
            
            # Ensure we have the required columns
            required_cols = ['cpu_utilization_percent', 'memory_utilization_percent']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                # Try alternative column names
                if 'cpu_utilization' in df.columns:
                    df['cpu_utilization_percent'] = df['cpu_utilization']
                if 'memory_utilization' in df.columns:
                    df['memory_utilization_percent'] = df['memory_utilization']
            
            # Calculate recent patterns
            recent_cpu_mean = df['cpu_utilization_percent'].mean()
            recent_memory_mean = df['memory_utilization_percent'].mean()
            
            cpu_std = df['cpu_utilization_percent'].std()
            memory_std = df['memory_utilization_percent'].std()
            
            # Use small variation if std is very low
            cpu_std = max(cpu_std, 2.0) if not np.isnan(cpu_std) else 2.0
            memory_std = max(memory_std, 1.0) if not np.isnan(memory_std) else 1.0
            
            # Generate hourly forecasts
            forecasts = []
            base_time = datetime.now()
            
            for hour in range(forecast_hours):
                # Add some realistic variation based on time of day
                hour_of_day = (base_time + timedelta(hours=hour)).hour
                
                # Simple pattern: lower usage at night (22-6), higher during day (9-17)
                time_factor = self._get_time_factor(hour_of_day)
                
                # Generate forecast with some randomness
                cpu_forecast = max(0, min(100, 
                    recent_cpu_mean * time_factor + np.random.normal(0, cpu_std * 0.3)
                ))
                memory_forecast = max(0, min(100,
                    recent_memory_mean * time_factor + np.random.normal(0, memory_std * 0.3)
                ))
                
                # Make energy prediction
                prediction = self.predict_single(cpu_forecast, memory_forecast)
                
                forecast_point = {
                    'hour': hour + 1,
                    'timestamp': (base_time + timedelta(hours=hour)).isoformat(),
                    'forecasted_cpu_utilization': round(cpu_forecast, 2),
                    'forecasted_memory_utilization': round(memory_forecast, 2),
                    'forecasted_energy_watts': prediction['predicted_energy_watts'],
                    'confidence': prediction['confidence']
                }
                
                forecasts.append(forecast_point)
            
            # Calculate summary statistics
            energy_values = [f['forecasted_energy_watts'] for f in forecasts]
            
            summary = {
                'forecast_period_hours': forecast_hours,
                'total_forecasted_energy_kwh': round(sum(energy_values) / 1000, 4),  # Convert to kWh
                'average_hourly_energy_watts': round(np.mean(energy_values), 2),
                'peak_hourly_energy_watts': round(max(energy_values), 2),
                'min_hourly_energy_watts': round(min(energy_values), 2),
                'energy_range_watts': round(max(energy_values) - min(energy_values), 2),
                'base_patterns': {
                    'avg_cpu_utilization': round(recent_cpu_mean, 2),
                    'avg_memory_utilization': round(recent_memory_mean, 2)
                }
            }
            
            return {
                'hourly_forecasts': forecasts,
                'summary': summary,
                'model_info': self.model_metrics,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Day forecast failed: {e}")
            raise
    
    def _get_time_factor(self, hour: int) -> float:
        """Get a time-based adjustment factor (0.7 to 1.2)"""
        if 22 <= hour or hour <= 6:  # Night time
            return 0.7
        elif 9 <= hour <= 17:  # Business hours
            return 1.2
        else:  # Morning/evening
            return 1.0
    
    def _calculate_confidence(self, cpu_util: float, memory_util: float) -> str:
        """Calculate prediction confidence based on training data ranges"""
        if not self.stats:
            return "medium"
        
        cpu_mean = self.stats.get('cpu_utilization_mean', 50)
        cpu_std = self.stats.get('cpu_utilization_std', 10)
        memory_mean = self.stats.get('memory_utilization_mean', 15)
        memory_std = self.stats.get('memory_utilization_std', 5)
        
        # Check if inputs are within 2 standard deviations of training data
        cpu_in_range = abs(cpu_util - cpu_mean) <= 2 * cpu_std
        memory_in_range = abs(memory_util - memory_mean) <= 2 * memory_std
        
        if cpu_in_range and memory_in_range:
            return "high"
        elif cpu_in_range or memory_in_range:
            return "medium"
        else:
            return "low"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            'model_type': 'RandomForestRegressor',
            'features': self.feature_columns,
            'performance_metrics': self.model_metrics,
            'feature_importance': self.model_data.get('feature_importance', [])
        }