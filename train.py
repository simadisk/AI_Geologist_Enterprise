import mlflow
import mlflow.xgboost
import mlflow.sklearn
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV
from sqlalchemy import create_engine
import joblib
import os
import holidays

# 1. Ρυθμίσεις - ΕΠΙΒΟΛΗ Τοπικής Καταγραφής με SQLite (Σύγχρονη μέθοδος)
mlflow.set_tracking_uri("sqlite:///mlflow.db")
mlflow.set_experiment("Energy_Forecasting_Tuning")

DB_URL = "postgresql+psycopg2://admin:secretpassword@127.0.0.1:5433/energy_db"
MODEL_DIR = "backend/model_files"
os.makedirs(MODEL_DIR, exist_ok=True)

# 2. Φόρτωση Δεδομένων
print("📥 Φόρτωση δεδομένων από τη βάση...")
engine = create_engine(DB_URL)
df = pd.read_sql("SELECT * FROM energy_history ORDER BY datetime ASC", engine)
df.set_index('datetime', inplace=True)

# 2.5 Feature Engineering (Δημιουργία των στηλών που έλειπαν)
print("⚙️ Δημιουργία Features (Lags, Ώρες, Αργίες)...")
df['load_lag_24h'] = df['load_mw'].shift(24)
df['load_lag_168h'] = df['load_mw'].shift(168)
df.dropna(inplace=True)

df['hour'] = df.index.hour
df['month'] = df.index.month
df['day_of_week'] = df.index.dayofweek
df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)

df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

dk_holidays = holidays.DK()
df['is_holiday'] = [1 if x.date() in dk_holidays else 0 for x in df.index]

# Ορισμός των στηλών για το μοντέλο
features = ['temperature_c', 'apparent_temp_c', 'wind_speed_kmh', 'solar_radiation', 
            'hour_sin', 'hour_cos', 'month_sin', 'month_cos', 
            'is_weekend', 'is_holiday', 'load_lag_24h', 'load_lag_168h']
X = df[features]
y = df['load_mw']

# 3. Εκπαίδευση & Tuning με MLflow Autologging
print("🚀 Ξεκινάει το Hyperparameter Tuning...")

# --- XGBoost Tuning ---
mlflow.xgboost.autolog()
with mlflow.start_run(run_name="XGBoost_Tuned"):
    xgb_model = xgb.XGBRegressor()
    params = {
        'n_estimators': [100, 200],
        'max_depth': [3, 6, 10],
        'learning_rate': [0.01, 0.1]
    }
    search = RandomizedSearchCV(xgb_model, params, n_iter=5, cv=3, verbose=2)
    search.fit(X, y)
    
    # Αποθήκευση καλύτερου μοντέλου
    joblib.dump(search.best_estimator_, os.path.join(MODEL_DIR, "final_xgboost.joblib"))
    print("✅ XGBoost έτοιμο!")

# --- Random Forest Tuning ---
mlflow.sklearn.autolog()
with mlflow.start_run(run_name="RandomForest_Tuned"):
    rf_model = RandomForestRegressor()
    params = {
        'n_estimators': [100, 200],
        'max_depth': [10, 20, None]
    }
    search = RandomizedSearchCV(rf_model, params, n_iter=5, cv=3, verbose=2)
    search.fit(X, y)
    
    # Αποθήκευση καλύτερου μοντέλου
    joblib.dump(search.best_estimator_, os.path.join(MODEL_DIR, "final_random_forest.joblib"))
    print("✅ Random Forest έτοιμο!")

print("🎉 Όλα ολοκληρώθηκαν!")