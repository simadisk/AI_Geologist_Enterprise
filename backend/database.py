from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Παίρνουμε το URL της βάσης από το περιβάλλον του Docker (το ορίσαμε στο docker-compose.yml)
# Αν δεν το βρει, βάζει ένα προεπιλεγμένο (χρήσιμο για τοπικές δοκιμές)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:secretpassword@db:5432/energy_db")

# Φτιάχνουμε τον "κινητήρα" που μιλάει στην PostgreSQL
engine = create_engine(DATABASE_URL)

# Φτιάχνουμε τη "συνεδρία" για να στέλνουμε/παίρνουμε δεδομένα
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Αυτή είναι η βάση πάνω στην οποία θα "χτίσουμε" τους πίνακές μας
Base = declarative_base()

# Συνάρτηση που ανοίγει και κλείνει με ασφάλεια τη σύνδεση κάθε φορά που τη χρειαζόμαστε
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()