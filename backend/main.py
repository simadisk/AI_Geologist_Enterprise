from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
import os
import requests
import holidays
from prometheus_fastapi_instrumentator import Instrumentator

# --- Imports για το "ξυπνητήρι" (Cron Job) ---
from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal
from data_ingestor import fetch_and_store_weather, fetch_and_store_energy
import contextlib

# 1. Η συνάρτηση που θα τρέχει στο παρασκήνιο τα μεσάνυχτα
def scheduled_data_ingestion():
    print("⏳ [CRON JOB] Ξεκινάει η αυτόματη λήψη δεδομένων...")
    db = SessionLocal()
    try:
        weather_res = fetch_and_store_weather(db)
        energy_res = fetch_and_store_energy(db)
        print(f"✅ [CRON JOB] Ολοκληρώθηκε! Νέες εγγραφές - Καιρός: {weather_res.get('new_saved')}, Ενέργεια: {energy_res.get('new_saved')}")
    except Exception as e:
        print(f"❌ [CRON JOB] Σφάλμα κατά την αυτόματη λήψη: {e}")
    finally:
        db.close()

# 2. Ξεκινάμε το ρομπότ (Scheduler)
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_data_ingestion, 'cron', hour=0, minute=5)
scheduler.start()

# 3. Ρυθμίζουμε το FastAPI να κλείνει το ρομπότ όταν κλείνουμε τον server
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    scheduler.shutdown()

# 4. ΕΔΩ ΟΡΙΖΟΥΜΕ ΤΟ APP (ΜΟΝΟ ΜΙΑ ΦΟΡΑ ΜΑΖΙ ΜΕ ΤΟ LIFESPAN!)
app = FastAPI(title="Energy Forecasting API v2.0", lifespan=lifespan)

# --- Prometheus Instrumentation ---
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# --- Σύνδεση με τη Βάση ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:secretpassword@db:5432/energy_db")
engine = create_engine(DATABASE_URL)

# --- Ημερολόγιο Δανίας ---
dk_holidays = holidays.DK()

# --- Φόρτωση των Μοντέλων από τον φάκελο "model_files" ---
MODEL_DIR = os.path.join(os.path.dirname(__file__), "model_files")

try:
    print("Φόρτωση ΝΕΩΝ Μοντέλων ML v2.0...")
    lr_model = joblib.load(os.path.join(MODEL_DIR, "final_linear_regression.joblib"))
    rf_model = joblib.load(os.path.join(MODEL_DIR, "final_random_forest.joblib"))
    xgb_model = joblib.load(os.path.join(MODEL_DIR, "final_xgboost.joblib"))
    print("Τα μοντέλα φορτώθηκαν επιτυχώς!")
except Exception as e:
    print(f"Σφάλμα φόρτωσης μοντέλων: {e}")
    lr_model, rf_model, xgb_model = None, None, None

# --- Pydantic Schema για χειροκίνητα δεδομένα στο /api/predict ---
class PredictionInput(BaseModel):
    temperature_c: float
    apparent_temp_c: float
    wind_speed_kmh: float
    solar_radiation: float
    hour: int
    month: int
    day_of_week: int
    is_holiday: int
    load_lag_24h: float
    load_lag_168h: float
@app.get("/")
def read_root():
    return {"status": "ML Backend v2.0 is running"}

@app.post("/api/predict")
def predict_single(data: PredictionInput):
    """ΝΕΟ ENDPOINT: Δέχεται χειροκίνητα δεδομένα και επιστρέφει άμεση πρόβλεψη"""
    if not xgb_model:
        raise HTTPException(status_code=500, detail="Το μοντέλο XGBoost δεν έχει φορτωθεί.")
        
    # Μετατροπή των ωρών/μηνών σε κυκλικά features
    hour_sin = np.sin(2 * np.pi * data.hour / 24)
    hour_cos = np.cos(2 * np.pi * data.hour / 24)
    month_sin = np.sin(2 * np.pi * data.month / 12)
    month_cos = np.cos(2 * np.pi * data.month / 12)
    is_weekend = 1 if data.day_of_week >= 5 else 0
    
    # Δημιουργία DataFrame με τη σειρά που εκπαιδεύτηκε το μοντέλο
    df_input = pd.DataFrame([{
        'temperature_c': data.temperature_c,
        'apparent_temp_c': data.apparent_temp_c,
        'wind_speed_kmh': data.wind_speed_kmh,
        'solar_radiation': data.solar_radiation,
        'hour_sin': hour_sin,
        'hour_cos': hour_cos,
        'month_sin': month_sin,
        'month_cos': month_cos,
        'is_weekend': is_weekend,
        'is_holiday': data.is_holiday,
        'load_lag_24h': data.load_lag_24h,
        'load_lag_168h': data.load_lag_168h
    }])
    
    # Ζωντανή Πρόβλεψη
    pred_xgb = xgb_model.predict(df_input)[0]
    
    return {
        "prediction_mw": float(pred_xgb),
        "model_used": "XGBoost Tuned"
    }

@app.get("/api/forecast")
def get_forecast(start_date: str, end_date: str):
    """ΙΣΤΟΡΙΚΗ ΠΡΟΒΛΕΨΗ (BACKTESTING) - V2.0"""
    if not all([lr_model, rf_model, xgb_model]):
        raise HTTPException(status_code=500, detail="Τα μοντέλα δεν έχουν φορτωθεί.")

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        fetch_start = start_dt - timedelta(days=7)
        
        # 1. Φορτίο από τη Βάση
        query = text("""
            SELECT datetime, load_mw FROM energy_history
            WHERE datetime >= :start AND datetime <= :end ORDER BY datetime ASC
        """)
        with engine.connect() as conn:
            df_load = pd.read_sql(query, conn, params={"start": fetch_start, "end": end_dt})
        
        if df_load.empty:
            return {"error": "Δεν βρέθηκαν ιστορικά δεδομένα φορτίου για αυτή την περίοδο."}
        df_load.set_index('datetime', inplace=True)
        
        # 2. Καιρός V2.0 από το Archive API
        weather_url = f"https://archive-api.open-meteo.com/v1/archive?latitude=55.6761&longitude=12.5683&start_date={fetch_start.strftime('%Y-%m-%d')}&end_date={end_dt.strftime('%Y-%m-%d')}&hourly=temperature_2m,apparent_temperature,wind_speed_10m,shortwave_radiation"
        res = requests.get(weather_url).json()
        
        if "error" in res:
             return {"error": "Αδυναμία άντλησης ιστορικού καιρού από το Open-Meteo."}
             
        df_weather = pd.DataFrame({
            'datetime': pd.to_datetime(res['hourly']['time']),
            'temperature_c': res['hourly']['temperature_2m'],
            'apparent_temp_c': res['hourly']['apparent_temperature'],
            'wind_speed_kmh': res['hourly']['wind_speed_10m'],
            'solar_radiation': res['hourly']['shortwave_radiation']
        })
        df_weather.set_index('datetime', inplace=True)
        
        # 3. Ένωση και Feature Engineering
        df = df_load.join(df_weather, how='inner')
        df['load_lag_24h'] = df['load_mw'].shift(24)
        df['load_lag_168h'] = df['load_mw'].shift(168)
        
        df_target = df.loc[start_date:end_date].copy()
        df_target.dropna(inplace=True)
        
        if df_target.empty:
            return {"error": "Δεν επαρκούν τα δεδομένα (Lags) για πρόβλεψη."}

        # Κυκλικός Χρόνος & Ημερολόγιο
        df_target['hour'] = df_target.index.hour
        df_target['month'] = df_target.index.month
        df_target['hour_sin'] = np.sin(2 * np.pi * df_target['hour'] / 24)
        df_target['hour_cos'] = np.cos(2 * np.pi * df_target['hour'] / 24)
        df_target['month_sin'] = np.sin(2 * np.pi * df_target['month'] / 12)
        df_target['month_cos'] = np.cos(2 * np.pi * df_target['month'] / 12)
        df_target['is_weekend'] = df_target.index.dayofweek.map(lambda x: 1 if x >= 5 else 0)
        df_target['is_holiday'] = df_target.index.map(lambda x: 1 if x.date() in dk_holidays else 0)

        # 4. Πρόβλεψη
        features = ['temperature_c', 'apparent_temp_c', 'wind_speed_kmh', 'solar_radiation', 'hour_sin', 'hour_cos', 'month_sin', 'month_cos', 'is_weekend', 'is_holiday', 'load_lag_24h', 'load_lag_168h']
        X = df_target[features]
        
        df_target['pred_lr'] = lr_model.predict(X)
        df_target['pred_rf'] = rf_model.predict(X)
        df_target['pred_xgb'] = xgb_model.predict(X)
        df_target['pred_ensemble'] = (df_target['pred_lr'] + df_target['pred_rf'] + df_target['pred_xgb']) / 3
        
        df_target.reset_index(inplace=True)
        return df_target.to_dict(orient="records")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/api/live_forecast")
def live_forecast(start_date: str, end_date: str):
    """LIVE ΠΡΟΒΛΕΨΗ ΜΕΛΛΟΝΤΟΣ - V2.0"""
    try:
        # 1. Καιρός V2.0 από το Forecast API
        url = f"https://api.open-meteo.com/v1/forecast?latitude=55.6761&longitude=12.5683&hourly=temperature_2m,apparent_temperature,wind_speed_10m,shortwave_radiation&start_date={start_date}&end_date={end_date}"
        weather_res = requests.get(url).json()
        
        if "error" in weather_res:
            return {"error": "Αδυναμία άντλησης καιρού από το Open-Meteo."}
            
        times = weather_res['hourly']['time']
        temps = weather_res['hourly']['temperature_2m']
        apparent_temps = weather_res['hourly']['apparent_temperature']
        winds = weather_res['hourly']['wind_speed_10m']
        radiations = weather_res['hourly']['shortwave_radiation']
        
        # 2. Lags από τη Βάση
        query = text("SELECT load_mw FROM energy_history ORDER BY datetime DESC LIMIT 168;")
        with engine.connect() as conn:
            recent_loads = [row[0] for row in conn.execute(query).fetchall()]
            recent_loads.reverse()
            
        results = []
        for i in range(len(times)):
            dt = datetime.fromisoformat(times[i])
            
            # Υπολογισμός Lags
            lag_24_index = -(24 - (i % 24))
            lag_24 = recent_loads[lag_24_index] if abs(lag_24_index) <= len(recent_loads) else recent_loads[-1]
            lag_168 = recent_loads[i % 168] if i < 168 else recent_loads[-1]
            
            # Δημιουργία των 12 Features
            X_live = pd.DataFrame([{
                'temperature_c': temps[i], 
                'apparent_temp_c': apparent_temps[i], 
                'wind_speed_kmh': winds[i], 
                'solar_radiation': radiations[i],
                'hour_sin': np.sin(2 * np.pi * dt.hour / 24), 
                'hour_cos': np.cos(2 * np.pi * dt.hour / 24), 
                'month_sin': np.sin(2 * np.pi * dt.month / 12), 
                'month_cos': np.cos(2 * np.pi * dt.month / 12),
                'is_weekend': 1 if dt.weekday() >= 5 else 0, 
                'is_holiday': 1 if dt.date() in dk_holidays else 0, 
                'load_lag_24h': lag_24, 
                'load_lag_168h': lag_168
            }])
            
            # Πρόβλεψη V2.0
            pred_lr = lr_model.predict(X_live)[0]
            pred_rf = rf_model.predict(X_live)[0]
            pred_xgb = xgb_model.predict(X_live)[0]
            pred_ensemble = (pred_lr + pred_rf + pred_xgb) / 3
            
            results.append({
                "datetime": dt.isoformat(),
                "temperature_c": temps[i],
                "apparent_temp_c": apparent_temps[i], 
                "wind_speed_kmh": winds[i],
                "solar_radiation": radiations[i],     
                "pred_ensemble": pred_ensemble
            })
            
        return results
    except Exception as e:
        return {"error": str(e)}