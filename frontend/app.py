import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="AI Energy Forecast", page_icon="⚡", layout="wide")
st.title("⚡ AI Energy Forecast Dashboard")

st.sidebar.header("📅 Ρυθμίσεις Πρόβλεψης")

# Παίρνουμε τη σημερινή ημερομηνία από το σύστημα
today = datetime.now().date()

# 1. Ημερομηνίες
start_date = st.sidebar.date_input("Από (Ημερομηνία)", datetime(2024, 2, 5))
end_date = st.sidebar.date_input("Έως (Ημερομηνία)", start_date + timedelta(days=1))

# 2. Ο ΑΠΟΛΥΤΟΣ ΚΟΦΤΗΣ
is_error = end_date < start_date

if is_error:
    st.sidebar.error("⛔ Σφάλμα: Η λήξη δεν μπορεί να προηγείται της έναρξης!")
    is_live = False
else:
    # 3. Δυναμική Ετικέτα
    if end_date < today:
        st.sidebar.warning("🧪 Κατάσταση: ΤΕΣΤ (Ιστορικά Δεδομένα)")
        is_live = False
    else:
        st.sidebar.success("🟢 Κατάσταση: ΚΑΝΟΝΙΚΗ ΠΡΟΒΛΕΨΗ")
        is_live = True

# 4. Κουμπί εκτέλεσης
if st.sidebar.button("🚀 Εκτέλεση Πρόβλεψης", use_container_width=True, disabled=is_error):
    with st.spinner("Άντληση δεδομένων & εκτέλεση μοντέλων..."):
        
        params = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }
        
        if not is_live:
            url = "http://backend:8000/api/forecast"
        else:
            url = "http://backend:8000/api/live_forecast"
            
        try:
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if "error" in data:
                    st.error(f"Σφάλμα από το Backend: {data['error']}")
                else:
                    df = pd.DataFrame(data)
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    
                    st.subheader("📊 Σύγκριση Πραγματικού Φορτίου vs Πρόβλεψης")
                    fig = go.Figure()
                    
                    if not is_live and 'load_mw' in df.columns:
                        fig.add_trace(go.Scatter(x=df['datetime'], y=df['load_mw'], mode='lines', 
                                                 name='Πραγματικό Φορτίο', line=dict(color='#1f77b4', width=2)))
                                                 
                    fig.add_trace(go.Scatter(x=df['datetime'], y=df['pred_ensemble'], mode='lines', 
                                             name='AI Πρόβλεψη', line=dict(color='#00ff00', width=3, dash='dot' if not is_live else 'solid')))
                    
                    fig.update_layout(xaxis_title="Ώρα", yaxis_title="Megawatts (MW)", 
                                      template="plotly_white", hovermode="x unified", height=500)
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # --- Πίνακας Δεδομένων ---
                    st.subheader("📋 Αναλυτικά Δεδομένα & Καιρός")
                    
                    # Προσθέσαμε την Αισθητή Θερμοκρασία και την Ακτινοβολία στις στήλες!
                    if not is_live:
                        display_cols = ['datetime', 'load_mw', 'pred_ensemble', 'temperature_c', 'apparent_temp_c', 'wind_speed_kmh', 'solar_radiation']
                        col_names = ['Ημερομηνία/Ώρα', 'Πραγματικό (MW)', 'Ensemble (MW)', 'Θερμ. (°C)', 'Αισθ. Θερμ. (°C)', 'Αέρας (km/h)', 'Ακτινοβολία (W/m²)']
                    else:
                        display_cols = ['datetime', 'pred_ensemble', 'temperature_c', 'apparent_temp_c', 'wind_speed_kmh', 'solar_radiation']
                        col_names = ['Ημερομηνία/Ώρα', 'Ensemble (MW)', 'Θερμ. (°C)', 'Αισθ. Θερμ. (°C)', 'Αέρας (km/h)', 'Ακτινοβολία (W/m²)']
                        
                    display_df = df[display_cols].copy()
                    display_df.columns = col_names
                    display_df['Ημερομηνία/Ώρα'] = display_df['Ημερομηνία/Ώρα'].dt.strftime('%Y-%m-%d %H:00')
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
            else:
                st.error("Σφάλμα διακομιστή")
                
        except requests.exceptions.ConnectionError:
            st.error("Αδυναμία σύνδεσης στο Backend. Βεβαιώσου ότι το container 'backend' τρέχει.")