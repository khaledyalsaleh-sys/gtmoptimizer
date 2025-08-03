import streamlit as st
from scipy.optimize import linprog
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="GTM Planner Optimizer", layout="wide")
st.title("📊 GTM Optimization Planner")

st.markdown("""
This app calculates the optimal number of AEs, AMs, and BDRs based on your revenue targets, quotas, and constraints.
Use the controls below to adjust assumptions and hiring constraints.
""")

# --- Scenario Selection ---
scenario = st.selectbox("Choose Scenario", ["Base", "Optimistic", "Conservative"])

# --- Inputs ---
st.sidebar.header(f"{scenario} Assumptions")
target_arr = st.sidebar.number_input("Target ARR ($)", value=28000000)
starting_arr = st.sidebar.number_input("Starting ARR ($)", value=12700000)
ndr_percent = st.sidebar.slider("Net Dollar Retention (%)", 100, 200, 145)

comm_asp = st.sidebar.number_input("Commercial ASP ($)", value=15000)
ent_asp = st.sidebar.number_input("Enterprise ASP ($)", value=100000)
comm_win_rate = st.sidebar.slider("Comm Win Rate", 0.3, 1.0, 0.55)
ent_win_rate = st.sidebar.slider("Ent Win Rate", 0.3, 1.0, 0.40)
mtg_to_sqo = st.sidebar.slider("Meeting to SQO Conversion", 0.1, 1.0, 0.33)

comm_quota = st.sidebar.number_input("Comm AE Quota", value=600000)
ent_quota = st.sidebar.number_input("Ent AE Quota", value=600000)
am_quota = st.sidebar.number_input("AM Quota", value=750000)

# --- Constraints ---
st.sidebar.header("Constraints")
min_comm_ae = st.sidebar.number_input("Min Comm AEs", value=2)
min_ent_ae = st.sidebar.number_input("Min Ent AEs", value=1)
max_total_ae = st.sidebar.number_input("Max Total AEs", value=20)

bdr_meetings_comm = st.sidebar.number_input("Comm BDR Meetings/mo", value=25)
bdr_meetings_ent = st.sidebar.number_input("Ent BDR Meetings/mo", value=15)
bdr_budget = st.sidebar.number_input("Total BDR Budget", value=8)

# --- Calculations ---
expansion_arr = starting_arr * (ndr_percent / 100 - 1)
new_logo_arr_needed = target_arr - starting_arr - expansion_arr
comm_new_arr = new_logo_arr_needed * 0.6
ent_new_arr = new_logo_arr_needed * 0.4

comm_pipeline = comm_new_arr / comm_win_rate
ent_pipeline = ent_new_arr / ent_win_rate
comm_meetings_needed = comm_pipeline / mtg_to_sqo
ent_meetings_needed = ent_pipeline / mtg_to_sqo

total_meetings_needed = comm_meetings_needed + ent_meetings_needed

# --- Solver Formulation ---
st.subheader("📌 Optimal Headcount Suggestion")
c = [0, 0, 0, 0, 0]  # AE Comm, AE Ent, AMs, BDR Comm, BDR Ent
A_eq = [
    [comm_quota, 0, 0, 0, 0],  # Comm AE contribution
    [0, ent_quota, 0, 0, 0],   # Ent AE contribution
    [0, 0, am_quota, 0, 0]     # AM contribution
]
b_eq = [comm_new_arr, ent_new_arr, expansion_arr]

A_ub = [
    [1, 1, 0, 0, 0],  # total AEs <= max
    [0, 0, 0, 1, 1]   # total BDRs <= budget
]
b_ub = [max_total_ae, bdr_budget]

bounds = [
    (min_comm_ae, None),
    (min_ent_ae, None),
    (0, None),
    (0, None),
    (0, None)
]

res = linprog(c=c, A_eq=A_eq, b_eq=b_eq, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

if res.success:
    ae_comm, ae_ent, ams, bdr_comm, bdr_ent = res.x
    total_bdr_meetings = bdr_comm * bdr_meetings_comm * 12 + bdr_ent * bdr_meetings_ent * 12
    self_gen_meetings = total_meetings_needed - total_bdr_meetings

    df = pd.DataFrame({
        "Role": ["Comm AEs", "Ent AEs", "AMs", "Comm BDRs", "Ent BDRs", "BDR Mtgs/year", "Total Meetings Needed", "AE Self-Gen Mtgs"],
        scenario: [round(ae_comm), round(ae_ent), round(ams), round(bdr_comm), round(bdr_ent), round(total_bdr_meetings), round(total_meetings_needed), round(self_gen_meetings)]
    }).set_index("Role")

    st.dataframe(df)

    st.subheader("📈 Visualizations")
    st.bar_chart(df)

else:
    st.error("Optimization failed. Try adjusting constraints.")
