from sqlalchemy import Column, Integer, Float, DateTime
from database import Base

class WeatherRecord(Base):
    __tablename__ = "weather_history"
    id = Column(Integer, primary_key=True, index=True) 
    datetime = Column(DateTime, unique=True, index=True)
    temperature_c = Column(Float)
    wind_speed_kmh = Column(Float)

# <--- ΝΕΑ ΠΡΟΣΘΗΚΗ: Ο πίνακας της Ενέργειας --->
class EnergyRecord(Base):
    __tablename__ = "energy_history"
    id = Column(Integer, primary_key=True, index=True) 
    datetime = Column(DateTime, unique=True, index=True)
    load_mw = Column(Float) # Εδώ θα μπαίνει η κατανάλωση σε Megawatts