import os
import time
import json
import redis
import pandas as pd
import streamlit as st
import plotly.express as px

# =========================
# CONFIGURAÇÕES
# =========================

REDIS_HOST = os.getenv("REDIS_HOST", "192.168.121.189")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_KEY  = os.getenv("REDIS_OUTPUT_KEY", "luizcouto-proj3-output")
UPDATE_INTERVAL = 3  # segundos
MAX_RECORDS = 100

# =========================
# CONEXÃO REDIS
# =========================

@st.cache_resource
def get_redis_client():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

redis_client = get_redis_client()

# =========================
# ESTADO
# =========================

if "cpu_min" not in st.session_state:
    st.session_state.cpu_min = []

if "cpu_hour" not in st.session_state:
    st.session_state.cpu_hour = []

if "mem" not in st.session_state:
    st.session_state.mem = []

# =========================
# FUNÇÕES
# =========================

def fetch_data():
    raw = redis_client.get(REDIS_KEY)
    if not raw:
        return None
    return json.loads(raw)

def update_records(data):
    cpu_min = [v for k, v in data.items() if "cpu" in k and "last_minute" in k]
    cpu_hour = [v for k, v in data.items() if "cpu" in k and "last_hour" in k]
    mem = data.get("mvg_avg_memory_last_min")

    if cpu_min:
        st.session_state.cpu_min.append(cpu_min)
    if cpu_hour:
        st.session_state.cpu_hour.append(cpu_hour)
    if mem is not None:
        st.session_state.mem.append(mem)

    st.session_state.cpu_min = st.session_state.cpu_min[-MAX_RECORDS:]
    st.session_state.cpu_hour = st.session_state.cpu_hour[-MAX_RECORDS:]
    st.session_state.mem = st.session_state.mem[-MAX_RECORDS:]

def plot_cpu(data, title):
    df = pd.DataFrame(data)
    fig = px.line(df, title=title)
    st.plotly_chart(fig, use_container_width=True)

# =========================
# INTERFACE
# =========================

st.set_page_config(layout="wide")
st.title("Serverless Monitoring Dashboard")

while True:
    data = fetch_data()

    if not data:
        st.warning("Aguardando dados no Redis...")
    else:
        update_records(data)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("CPU - Média por Minuto")
            plot_cpu(st.session_state.cpu_min, "CPU - Last Minute")

        with col2:
            st.subheader("CPU - Média por Hora")
            plot_cpu(st.session_state.cpu_hour, "CPU - Last Hour")

        st.subheader("Uso de Memória (Média por Minuto)")
        plot_cpu(pd.DataFrame(st.session_state.mem, columns=["mem"]), "Memory")

    time.sleep(UPDATE_INTERVAL)
    st.rerun()
