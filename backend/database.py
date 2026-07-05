import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# ΕΔΩ ΕΙΝΑΙ ΤΟ ΜΥΣΤΙΚΟ: Διαβάζουμε το URL απευθείας από το docker-compose.yml!
# Αν δεν το βρει, βάζουμε το σωστό ως εναλλακτική.
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://admin:secretpassword@db:5432/geologist_db"
)

# Ενεργοποίηση της μηχανής SQLAlchemy
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =====================================================================
# ΤΟ ΣΧΕΔΙΟ ΤΟΥ ΠΙΝΑΚΑ (Database Schema)
# =====================================================================
class PredictionRecord(Base):
    __tablename__ = "predictions_history"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    analysis_date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="Success")
    
    dominant_rock_name = Column(String)
    dominant_rock_percentage = Column(Float)