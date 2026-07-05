from fastapi.testclient import TestClient
from main import app

# Φτιάχνουμε έναν "εικονικό πελάτη" που μιλάει στο API μας
client = TestClient(app)

def test_home_endpoint():
    """Τεστ: Ελέγχει αν η αρχική σελίδα του API λειτουργεί σωστά."""
    response = client.get("/")
    
    # 1. Ελέγχουμε αν η απάντηση είναι επιτυχής (Κωδικός 200 OK)
    assert response.status_code == 200
    
    # 2. Ελέγχουμε αν επιστρέφει το σωστό μήνυμα κατάστασης
    assert response.json()["status"] == "Online"