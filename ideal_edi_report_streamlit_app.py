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
            st.rerun()  # Automatically rerun the app after login.
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
# With the new "Order Status" column now supporting PENDING,
# we now read 10 columns.
df = conn.read(workshee='Sheet1', usecols=list(range(10)), ttl=5)
df = df.dropna(how="all")

# Define the expected columns including the new "Order Status"
expected_columns = [
    "PO number", "DateOrdered", "Net Total of order", "Branch name",
     "Description", "SupplierItemCode", "Unit price", "QtyOrdered", "DateExpected",
    "Order Status"
]
df.columns = expected_columns

# Verify that all expected columns exist.
for col in expected_columns:
    if col not in df.columns:
        st.error(f"Missing expected column in Google Sheet: {col}")
        st.stop()

# -------------------------------
# CONVERT DATEORDERED TO DATETIME FOR FILTERING & SORTING
# -------------------------------
df["DateOrdered_dt"] = pd.to_datetime(df["DateOrdered"], format="%Y-%m-%d", errors="coerce")

# -------------------------------
# DATE RANGE FILTER (Placed in the Sidebar)
# -------------------------------
today = datetime.date.today() + datetime.timedelta(days=1)
one_month_ago = today - datetime.timedelta(days=30)
selected_dates = st.sidebar.date_input(
    "Select Order Date Range (filters by DateOrdered)", 
    value=(one_month_ago, today)
)

if isinstance(selected_dates, (list, tuple)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
    mask = (df["DateOrdered_dt"].dt.date >= start_date) & (df["DateOrdered_dt"].dt.date <= end_date)
    filtered_df = df.loc[mask].copy()
else:
    selected_date = selected_dates
    mask = df["DateOrdered_dt"].dt.date == selected_date
    filtered_df = df.loc[mask].copy()

# -------------------------------
# BRANCH NAME FILTER (Placed Below the Date Range Filter in the Sidebar)
# -------------------------------
unique_branches = sorted(df["Branch name"].dropna().unique().tolist())
branch_options = ["All"] + unique_branches
branch_selection = st.sidebar.selectbox("Filter by Branch Name (searchable dropdown):", options=branch_options)

if branch_selection != "All":
    filtered_df = filtered_df[filtered_df["Branch name"] == branch_selection]

# -------------------------------
# ORDER STATUS FILTER (New Filter in the Sidebar)
# -------------------------------
order_status_options = ["All", "PASS", "FAIL", "PENDING"]
order_status_selection = st.sidebar.selectbox("Filter by Order Status (PASS/FAIL/PENDING):", options=order_status_options)

# -------------------------------
# ABOUT THIS REPORT (Placed Under the Filters in the Sidebar)
# -------------------------------
with st.sidebar.expander("About this report"):
    st.markdown(
        """
        EDI Report Portal – End-User Guide

        Overview:
        The EDI Report Portal is a secure, web-based application designed to help you view and analyze purchase orders from Ideal EDI ordering from a centralized location. 
        The app groups order details by PO number, making it easy to explore individual orders and their associated line items. 
        Additionally, you can filter orders by date, branch, and order status using built-in filters.

        How to Access the Report:
        1. Launch the application in your web browser.
        2. You will first encounter a login screen. Enter the following credentials:
           • Username: oepnz
           • Password: oepnz
        3. Click the "Login" button. If the credentials are correct, the app will automatically reload, and you will be granted access to the report.

        Features and How to Use Them:

        1. Login Screen:
           • Secure Entry: The app starts with a simple login form. Only users with the correct username and password can access the data.
           • Automatic Redirection: Once you log in successfully, the app automatically reloads to display the report.

        2. Date Range, Branch Name, and Order Status Filters:
           • The Date Range filter is pre-set with a default range from one month ago until today.
           • The Branch Name filter is provided as a searchable dropdown.
           • The Order Status filter enables you to display orders that are overall PASS, FAIL, or PENDING.
             (Note: If any line item in the order has a status of FAIL, the overall order is marked as FAIL. If no line item fails but at least one is PENDING, the order is flagged as PENDING. Otherwise, the order is marked as PASS.)
           • All filters work in conjunction (AND operation) to display only those orders that match the selected criteria.
           
        3. Order Grouping and Sorting:
           • Orders are grouped by their “PO number.”
           • The report sorts orders from the latest to the oldest based on the DateOrdered field, so the most recent purchase orders appear at the top.
           • If any line item within an order fails, the order banner shows a red indicator (EDI process: FAIL). Similarly, if at least one item is pending (but no failures) then the status indicator shows pending.
        
        4. Viewing Order Details:
           • Each order appears as an expandable section (an expander). The header shows key order-level details such as:
                - PO number
                - DateOrdered
                - Branch name
                - Net Total of order
                - Overall EDI process status (PASS, FAIL, or PENDING)
           • Click on an order header to expand it. Inside, you’ll see a table containing detailed order lines.
           • Each order line now also includes:
                - SupplierItemCode
                - Description
                - Unit price
                - QtyOrdered
                - DateExpected
                - Order Status

        Tips for Best Experience:
           • Always ensure the selected date range, branch, and order status are appropriate for your needs.
           • To review details of a specific order, simply click on its expander header to reveal the order lines.
           • Use the table’s built-in sorting functionality (by clicking the column headers) to further organize the data if needed.

        This app was built by Amrit Ramadugu. If you have any questions, comments or suggestions, please get in touch.
        """
    )

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
        # Format PO number to avoid commas and decimals.
        if isinstance(po, (float, int)):
            po_display = str(int(po))
        else:
            po_display = str(po)

        group_df = filtered_df[filtered_df["PO number"] == po]
        
        # Determine the aggregated order status:
        # If any line item fails, the order is marked as FAIL.
        # If no failures but any line is pending, the order is marked as PENDING.
        # Otherwise, it is marked as PASS.
        if group_df["Order Status"].str.upper().eq("FAIL").any():
            aggregated_status = "FAIL"
        elif group_df["Order Status"].str.upper().eq("PENDING").any():
            aggregated_status = "PENDING"
        else:
            aggregated_status = "PASS"
        
        # Set a status tag for the expander header.
        if aggregated_status == "FAIL":
            status_tag = " | EDI process: 🔴 FAIL"
        elif aggregated_status == "PENDING":
            status_tag = " | EDI process: ⏳ PENDING"
        else:
            status_tag = " | EDI process: ✅ PASS"
        
        # Apply the order status filter (if not "All", only display orders matching the selected status)
        if order_status_selection != "All" and aggregated_status != order_status_selection:
            continue
        
        order_level = group_df.iloc[0]
        order_date = order_level["DateOrdered_dt"].date() if pd.notnull(order_level["DateOrdered_dt"]) else order_level["DateOrdered"]
        net_total = order_level["Net Total of order"]
        branch = order_level["Branch name"]

        expander_label = f"PO: {po_display} | DateOrdered: {order_date} | Branch: {branch} | Net Total: {net_total}{status_tag}"
        with st.expander(expander_label, expanded=False):
            st.markdown("**Order Lines:**")
            # Specify the columns including the new "Order Status" field.
            columns_to_show = [
                "PO number", "DateOrdered", "Branch name",
                  "Description","SupplierItemCode", "Unit price", "QtyOrdered", "DateExpected", "Order Status"
            ]
            order_lines = group_df[columns_to_show].copy()
            order_lines["PO number"] = order_lines["PO number"].apply(
                lambda x: str(int(x)) if pd.notnull(x) and isinstance(x, (float, int)) else x
            )
            st.dataframe(order_lines, use_container_width=True)
else:
    st.info("No orders found for the selected date range, branch, and order status filter.")