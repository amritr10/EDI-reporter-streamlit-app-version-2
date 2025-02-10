# # example/st_app_gsheets_using_service_account.py

# import streamlit as st
# from streamlit_gsheets import GSheetsConnection
# import pandas as pd

# # Display Title and Description
# st.title("Vendor Management Portal")
# st.markdown("Enter the details of the new vendor below.")
# # Establishing a Google Sheets connection
# conn = st.connection("gsheets", type=GSheetsConnection)

# # Fetch existin vendors data
# existing_data = conn.read(workshee='Sheet1', usecols=list(range(8)),ttl=5)
# existing_data = existing_data.dropna(how="all")

# st.dataframe(existing_data)

#!/usr/bin/env python
import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

# -------------------------------
# LOGIN SECTION
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

def login():
    st.title("Login to EDI Report Portal")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if username == "oepnz" and password == "oepnz":
            st.session_state["logged_in"] = True
            st.success("Login successful! Redirecting to report...")
            st.rerun()  # Automatically rerun the app to load the report.
        else:
            st.error("Invalid username or password.")

if not st.session_state["logged_in"]:
    login()
    st.stop()

# -------------------------------
# MAIN REPORT PORTAL (Accessible After Login)
# -------------------------------
st.title("EDI Report Portal")
conn = st.connection("gsheets", type=GSheetsConnection)

# -------------------------------
# READ DATA FROM GOOGLE SHEET
# -------------------------------
df = conn.read(workshee='Sheet1', usecols=list(range(8)), ttl=5)
df = df.dropna(how="all")

# Define expected columns
expected_columns = [
    "PO number", "DateOrdered", "Net Total of order", "Branch name",
    "SupplierItemCode", "Unit price", "QtyOrdered", "DateExpected"
]
df.columns = expected_columns

# Verify that all expected columns exist
for col in expected_columns:
    if col not in df.columns:
        st.error(f"Missing expected column in Google Sheet: {col}")
        st.stop()

# -------------------------------
# CONVERT DATEORDERED TO DATETIME FOR FILTERING & SORTING
# -------------------------------
df["DateOrdered_dt"] = pd.to_datetime(df["DateOrdered"], format="%Y-%m-%d", errors="coerce")

# -------------------------------
# DATE RANGE FILTER
# -------------------------------
today = datetime.date.today()
one_month_ago = today - datetime.timedelta(days=30)
selected_dates = st.date_input("Select Order Date Range", value=(one_month_ago, today))

if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
    mask = (df["DateOrdered_dt"].dt.date >= start_date) & (df["DateOrdered_dt"].dt.date <= end_date)
    filtered_df = df.loc[mask].copy()
else:
    selected_date = selected_dates
    mask = df["DateOrdered_dt"].dt.date == selected_date
    filtered_df = df.loc[mask].copy()

# -------------------------------
# GROUPING AND SORTING THE ORDERS
# -------------------------------
filtered_df = filtered_df.sort_values(by="DateOrdered_dt", ascending=False)
unique_po = filtered_df["PO number"].drop_duplicates().tolist()

# -------------------------------
# DISPLAY THE GROUPED ORDERS WITH NESTED ORDER LINES
# -------------------------------
st.markdown("### Orders (Grouped by PO number)")
if unique_po:
    for po in unique_po:
        group_df = filtered_df[filtered_df["PO number"] == po]
        order_level = group_df.iloc[0]
        order_date = order_level["DateOrdered_dt"].date() if pd.notnull(order_level["DateOrdered_dt"]) else order_level["DateOrdered"]
        net_total = order_level["Net Total of order"]
        branch = order_level["Branch name"]

        expander_label = f"PO: {po} | DateOrdered: {order_date} | Branch: {branch} | Net Total: {net_total}"
        with st.expander(expander_label, expanded=False):
            st.markdown("**Order Lines:**")
            # Now include additional columns in the order lines: PO number, DateOrdered, and Branch name
            columns_to_show = [
                "PO number", "DateOrdered", "Branch name",
                "SupplierItemCode", "Unit price", "QtyOrdered", "DateExpected"
            ]
            order_lines = group_df[columns_to_show]
            st.dataframe(order_lines, use_container_width=True)
else:
    st.info("No orders found for the selected date range.")

# -------------------------------
# ABOUT THE REPORT
# -------------------------------
with st.expander("About this report"):
    st.markdown(
        """
        This report groups purchase order line items by PO number.
        
        For each order:
         • The header shows:
             - PO number 
             - DateOrdered 
             - Branch name 
             - Net Total of order
         • Expanding the order reveals its associated order lines:
             - PO number
             - DateOrdered 
             - Branch name 
             - SupplierItemCode
             - Unit price
             - QtyOrdered
             - DateExpected
        
        Use the date range picker to filter orders by the DateOrdered field.  
        The default selection is from one month ago to today.
        Click on the table headers within an order for additional sorting options.

        This app was built by Amrit Ramadugu. If you have any questions, comments or suggestions please get in touch with me.
        """
    )