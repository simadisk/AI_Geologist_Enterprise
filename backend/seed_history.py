import os
import pandas as pd
import requests
from sqlalchemy.dialects.postgresql import insert
from database import SessionLocal
from models import WeatherRecord, EnergyRecord
from entsoe import EntsoePandasClient

def seed_weather(db):
    print("⏳ Κατέβασμα Ιστορικού Καιρού (2022 - Σήμερα)...")
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 55.6761,
        "longitude": 12.5683,
        "start_date": "2022-01-01",
        "end_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "hourly": ["temperature_2m", "wind_speed_10m"],
        "timezone": "Europe/Berlin"
    }
    res = requests.get(url, params=params)
    data = res.json()
    df = pd.DataFrame({
        "datetime": pd.to_datetime(data["hourly"]["time"]),
        "temperature_c": data["hourly"]["temperature_2m"],
        "wind_speed_kmh": data["hourly"]["wind_speed_10m"]
    })
    records = df.to_dict(orient="records")
    stmt = insert(WeatherRecord).values(records)
    on_conflict_stmt = stmt.on_conflict_do_nothing(index_elements=['datetime'])
    res_db = db.execute(on_conflict_stmt)
    db.commit()
    print(f"✅ Καιρός: Αποθηκεύτηκαν {res_db.rowcount} ιστορικές ώρες.")

def seed_energy(db):
    print("⏳ Κατέβασμα Ιστορικού Ενέργειας (2022 - Σήμερα)...")
    token = os.getenv("ENTSOE_TOKEN")
    client = EntsoePandasClient(api_key=token)
    
    years = [2022, 2023, 2024, 2025, 2026]
    total_saved = 0
    
    for year in years:
        print(f"   -> Άντληση έτους {year}...")
        start = pd.Timestamp(f"{year}-01-01", tz='Europe/Copenhagen')
        
        if year == 2026:
            end = pd.Timestamp.now(tz='Europe/Copenhagen')
        else:
            end = pd.Timestamp(f"{year}-12-31 23:59", tz='Europe/Copenhagen')
            
        try:
            ts = client.query_load("DK_2", start=start, end=end)
            
            # --- Η ΔΙΟΡΘΩΣΗ ΕΙΝΑΙ ΕΔΩ ---
            if isinstance(ts, pd.Series):
                df = ts.to_frame(name="load_mw")
            else:
                df = ts.copy()
                df.columns = ["load_mw"]
            # -----------------------------
            
            df.reset_index(inplace=True)
            df.rename(columns={"index": "datetime"}, inplace=True)
            
            df['datetime'] = df['datetime'].dt.tz_localize(None)
            
            records = df.to_dict(orient="records")
            stmt = insert(EnergyRecord).values(records)
            on_conflict_stmt = stmt.on_conflict_do_nothing(index_elements=['datetime'])
            res_db = db.execute(on_conflict_stmt)
            db.commit()
            
            total_saved += res_db.rowcount
        except Exception as e:
            print(f"❌ Σφάλμα στο έτος {year}: {e}")
            
    print(f"✅ Ενέργεια: Αποθηκεύτηκαν συνολικά {total_saved} ιστορικές ώρες.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_weather(db)
        seed_energy(db)
        print("🚀 Η μαζική εισαγωγή ιστορικού ολοκληρώθηκε με επιτυχία!")
    finally:
        db.close()