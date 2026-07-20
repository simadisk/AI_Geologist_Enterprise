# 🌍 Smart Energy Predictor & Monitor at Copenhagen,Denmark

## 💡 What is this project?
This project is a smart system that monitors how much electricity is being used and predicts how much will be needed in the future based on the weather. 

Think of it as a weather application, but instead of just telling you if it will rain, it tells you how the weather will affect the city's energy consumption.

---

## 🧩 How it works (The 4 Main Parts)

This system is made of four pieces that work together automatically:

### 1. 🤖 The Collector (Data Ingestion)
Every day at midnight, an automatic "robot" wakes up. It connects to the internet and downloads the latest weather data (from Open-Meteo) and energy consumption data (from ENTSO-E). 

### 2. 🗄️ The Memory (Database)
Once the Collector gets the new data, it saves it in a safe digital vault called **PostgreSQL**. This database holds all the history from 2022 up to today.

### 3. 🧠 The Brain (Machine Learning Model)
We have trained a smart algorithm (XGBoost) using years of historical data. The Brain looks at the Database, studies the patterns (like "people use more energy on cold Mondays"), and can predict future energy needs.

### 4. 📺 The Screens (User Interfaces)
We have two different screens where you can see the results:
* **The Predictor (Streamlit):** A simple website where you can ask the Brain to make future predictions.
* **The Live Monitor (Grafana):** A dashboard with beautiful graphs that shows the real-time energy and weather data from our Database.

---

## 🚀 How to start the system

You don't need to start each part separately. We use **Docker**, which is like a magic button that turns everything on at once.

### Step 1: Add your keys
Before starting, the system needs your secret passwords to work. Create a file named `.env` in the main folder and add your details like this:
```text
DB_USER=admin
DB_PASSWORD=your_secret_password_here
DB_NAME=postgres
ENTSOE_API_KEY=your_api_key_here


### Step 2: Turn it on
Open your terminal (Command Prompt), go to the project folder, and run this single command:
Bash
docker-compose up -d


Step 3: Open the screens
Now that the system is running, open your web browser and click on these links:
🔮 To make predictions (Streamlit): http://localhost:8501
📊 To see live graphs (Grafana): http://localhost:3000
⚙️ To see the background code (FastAPI): http://localhost:8000/docs


🛑 How to stop the system
When you are done and want to turn off the system, just run this command in your terminal:
Bash
docker-compose down
