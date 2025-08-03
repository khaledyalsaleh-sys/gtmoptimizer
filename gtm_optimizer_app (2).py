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
c = [0, 0, 0, 0, 0]  # AE Comm, AE Ent, AMs, BDR Comm, BDR Ent
A_eq = [
    [comm_quota, 0, 0, 0, 0],
    [0, ent_quota, 0, 0, 0],
    [0, 0, am_quota, 0, 0]
]
b_eq = [comm_new_arr, ent_new_arr, expansion_arr]

A_ub = [
    [1, 1, 0, 0, 0],
    [0, 0, 0, 1, 1]
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

    df = pd.DataFrame({
        "Metric": [
            "Comm AEs", "Ent AEs", "AMs",
            "Comm BDRs", "Ent BDRs",
            "Expansion ARR", "Comm New ARR", "Ent New ARR",
            "Comm Pipeline ($)", "Ent Pipeline ($)",
            "Total Meetings Required"
        ],
        "Value": [
            round(ae_comm), round(ae_ent), round(ams),
            round(bdr_comm), round(bdr_ent),
            round(expansion_arr), round(comm_new_arr), round(ent_new_arr),
            round(comm_pipeline), round(ent_pipeline),
            round(total_meetings_needed)
        ]
    }).set_index("Metric")

    st.subheader("📊 Summary Table")
    st.dataframe(df)

    st.subheader("📉 Scenario Risk Sensitivity")
    sensitivity = pd.DataFrame({
        "Variable": ["Comm Win Rate -10%", "Ent Win Rate -10%", "ASP +5% (Comm)", "ASP +5% (Ent)"],
        "Impact on Pipeline ($)": [
            round(comm_new_arr / (comm_win_rate * 0.9)),
            round(ent_new_arr / (ent_win_rate * 0.9)),
            round(comm_new_arr * 0.95 / comm_win_rate),
            round(ent_new_arr * 0.95 / ent_win_rate)
        ]
    })
    st.dataframe(sensitivity)

    st.subheader("📈 Pipeline Breakdown")
    chart_df = pd.DataFrame({
        "Segment": ["Commercial", "Enterprise"],
        "Pipeline ($)": [comm_pipeline, ent_pipeline]
    })
    st.bar_chart(chart_df.set_index("Segment"))

else:
    st.error("Optimization failed. Try adjusting constraints.")
