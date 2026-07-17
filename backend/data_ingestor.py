import requests
import pandas as pd
import os
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from models import WeatherRecord, EnergyRecord
from entsoe import EntsoePandasClient
from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal
from data_ingestor import fetch_and_store_weather, fetch_and_store_energy
import contextlib



# 1. Φτιάχνουμε μια συνάρτηση "περιτύλιγμα" που θα τρέχει στο παρασκήνιο
def scheduled_data_ingestion():
    print("⏳ [CRON JOB] Ξεκινάει η αυτόματη λήψη δεδομένων...")
    
    # Ανοίγουμε χειροκίνητα μια σύνδεση με τη βάση (αφού δεν υπάρχει χρήστης να κάνει HTTP Request)
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
# Ρύθμιση για να τρέχει κάθε μέρα στις 00:05 το βράδυ (Ευρώπη/Κοπεγχάγη)
scheduler.add_job(scheduled_data_ingestion, 'cron', hour=0, minute=5)
scheduler.start()

# Προαιρετικά: Ρυθμίζουμε τον scheduler να κλείνει ομαλά όταν σταματάμε το FastAPI
@contextlib.asynccontextmanager
async def lifespan(app):
    yield
    scheduler.shutdown()



def fetch_and_store_weather(db: Session):
    # (Άφησε τον κώδικα του καιρού ακριβώς όπως τον είχαμε γράψει χθες)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 55.6761,
        "longitude": 12.5683,
        "hourly": ["temperature_2m", "wind_speed_10m"],
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "Europe/Berlin"
    }
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame({
        "datetime": pd.to_datetime(data["hourly"]["time"]),
        "temperature_c": data["hourly"]["temperature_2m"],
        "wind_speed_kmh": data["hourly"]["wind_speed_10m"]
    })
    records = df.to_dict(orient="records")
    stmt = insert(WeatherRecord).values(records)
    on_conflict_stmt = stmt.on_conflict_do_nothing(index_elements=['datetime'])
    result = db.execute(on_conflict_stmt)
    db.commit()
    return {"data": records, "new_saved": result.rowcount}


# <--- ΝΕΑ ΣΥΝΑΡΤΗΣΗ ΓΙΑ ΤΗΝ ΕΝΕΡΓΕΙΑ --->
def fetch_and_store_energy(db: Session):
    """Τραβάει το Πραγματικό Ενεργειακό Φορτίο (Actual Load) για τη ζώνη DK_2"""
    
    # Διαβάζει το κρυφό API Key από το docker-compose
    token = os.getenv("ENTSOE_TOKEN") 
    if not token:
        print("❌ Σφάλμα: Το ENTSOE_TOKEN δεν βρέθηκε!")
        return {"data": [], "new_saved": 0}

    client = EntsoePandasClient(api_key=token)
    
    # Ζητάμε τα δεδομένα των τελευταίων 24 ωρών
    end = pd.Timestamp.now(tz='Europe/Copenhagen')
    start = end - pd.Timedelta(days=1)
    
    try:
        # DK_2 είναι η ζώνη της Κοπεγχάγης
        ts = client.query_load("DK_2", start=start, end=end)
        
        # Το entsoe-py φέρνει μια "Λίστα" (Series). Την κάνουμε Πίνακα (DataFrame)
        df = ts.to_frame(name="load_mw")
        df.reset_index(inplace=True)
        df.rename(columns={"index": "datetime"}, inplace=True)
        
        # Καθαρίζουμε τη ζώνη ώρας για να ταιριάζει απόλυτα με τον καιρό
        df['datetime'] = df['datetime'].dt.tz_localize(None)
        
        records = df.to_dict(orient="records")
        
        # Bulk Upsert (ίδια λογική με τον καιρό)
        stmt = insert(EnergyRecord).values(records)
        on_conflict_stmt = stmt.on_conflict_do_nothing(index_elements=['datetime'])
        result = db.execute(on_conflict_stmt)
        db.commit()
        
        return {"data": records, "new_saved": result.rowcount}
        
    except Exception as e:
        print(f"❌ Σφάλμα με το API του ENTSO-E: {e}")
        return {"data": [], "new_saved": 0}