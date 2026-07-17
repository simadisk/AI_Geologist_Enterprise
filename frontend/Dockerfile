
# 1. Παίρνουμε την Python
FROM python:3.10-slim

# 2. Φτιάχνουμε τον φάκελο /app
WORKDIR /app

# 3. Αντιγράφουμε και κάνουμε install τις βιβλιοθήκες
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Αντιγράφουμε τον κώδικα του Frontend
COPY . .

# 5. Ανοίγουμε την πόρτα 8501 (η προεπιλογή του Streamlit)
EXPOSE 8501

# 6. Τρέχουμε το Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# Δημιουργία και χρήση ενός non-root χρήστη για λόγους ασφαλείας
RUN useradd -m appuser
USER appuser