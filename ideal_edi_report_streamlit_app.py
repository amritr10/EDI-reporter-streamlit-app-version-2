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
            st.rerun()  # Rerun the app after login.
        else:
            st.error("Invalid username or password.")

if not st.session_state["logged_in"]:
    login()
    st.stop()

# -------------------------------
# MAIN REPORT PORTAL
# -------------------------------
st.title("EDI Report Portal")

# Add a refresh button at the top.
if st.button("Refresh Data"):
    st.rerun()

# -------------------------------
# ESTABLISH GOOGLE SHEET CONNECTION
# -------------------------------
# Using st.connection with the GSheetsConnection type.
conn = st.connection("gsheets", type=GSheetsConnection)

# -------------------------------
# READ DATA FROM GOOGLE SHEET
# -------------------------------
# We read 12 columns (including our two new manual fix columns).
df = conn.read(worksheet="Sheet1", usecols=list(range(12)), ttl=5)
df = df.dropna(how="all")

# Define the expected columns (make sure the sheet header includes these names).
expected_columns = [
    "PO number", "DateOrdered", "Net Total of order", "Branch name",
    "Description", "SupplierItemCode", "Unit price", "QtyOrdered", "DateExpected",
    "Order Status", "Manual Fix By", "Manual Fix Comment"
]
if len(df.columns) < len(expected_columns):
    st.error("The Google Sheet does not have enough columns. Please update the sheet to include the required columns.")
    st.stop()
df.columns = expected_columns

# Convert DateOrdered column for filtering & sorting.
df["DateOrdered_dt"] = pd.to_datetime(df["DateOrdered"], format="%Y-%m-%d", errors="coerce")

# -------------------------------
# SIDEBAR FILTERS: DATE RANGE, BRANCH, ORDER STATUS
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

unique_branches = sorted(df["Branch name"].dropna().unique().tolist())
branch_options = ["All"] + unique_branches
branch_selection = st.sidebar.selectbox("Filter by Branch Name (searchable dropdown):", options=branch_options)
if branch_selection != "All":
    filtered_df = filtered_df[filtered_df["Branch name"] == branch_selection]

# Include "MANUAL FIX" as an option.
order_status_options = ["All", "PASS", "FAIL", "PENDING", "MANUAL FIX"]
order_status_selection = st.sidebar.selectbox("Filter by Order Status:", options=order_status_options)

# -------------------------------
# ABOUT THIS REPORT (Sidebar)
# -------------------------------
with st.sidebar.expander("About this report"):
    st.markdown(
        """
        EDI Report Portal – End-User Guide

        Overview:
        This portal displays purchase order details grouped by PO number. You may filter by order date, branch, and order status.
        Additionally, when an order is flagged as FAIL, you can enter who manually fixed the order and add any comments regarding the fix.
        Once marked, the order status will update to “MANUAL FIX” in both the Google Sheet and the report display.

        How to Use:
         1. Login with your credentials (username: oepnz, password: oepnz).
         2. Use the sidebar filters to view orders as needed.
         3. For any order with status “FAIL,” expand the order and provide “Fixed By” and “Fix Comments.”
         4. Click “Mark as Manually Fixed” to update the sheet.
         5. Refresh the report to see the updated status.

        This app was built by Amrit Ramadugu.
        """
    )

# -------------------------------
# FUNCTION TO UPDATE THE GOOGLE SHEET USING conn.update
# -------------------------------
def update_order_manual_fix(po_number, fixed_by, fix_comment):
    """
    Update all rows in the Google Sheet that have the given PO number:
      - Set "Order Status" to "MANUAL FIX"
      - Set "Manual Fix By" to the provided fixed_by value
      - Set "Manual Fix Comment" to the provided fix_comment value
    The update is done using the gsheetsconnection's conn.update method.
    """
    # Read the full sheet again as a dataframe.
    df_update = conn.read(worksheet="Sheet1", usecols=list(range(12)))
    df_update = df_update.dropna(how="all")
    df_update.columns = expected_columns

    # Locate rows matching the PO number (using string comparison).
    mask = df_update["PO number"].astype(str).str.strip() == str(po_number).strip()
    df_update.loc[mask, "Order Status"] = "MANUAL FIX"
    df_update.loc[mask, "Manual Fix By"] = fixed_by
    df_update.loc[mask, "Manual Fix Comment"] = fix_comment

    # Write the updated dataframe back to the Google Sheet.
    conn.update(worksheet="Sheet1", data=df_update)

# -------------------------------
# GROUPING, SORTING, & DISPLAY OF ORDERS
# -------------------------------
filtered_df = filtered_df.sort_values(by="DateOrdered_dt", ascending=False)
unique_po = filtered_df["PO number"].drop_duplicates().tolist()

st.markdown("### Orders (Grouped by PO number)")
if unique_po:
    for po in unique_po:
        # Format the PO number for display.
        if isinstance(po, (float, int)):
            po_display = str(int(po))
        else:
            po_display = str(po)

        group_df = filtered_df[filtered_df["PO number"] == po]
        # Determine aggregated order status using a hierarchy:
        statuses = group_df["Order Status"].str.upper().unique().tolist()
        if "FAIL" in statuses:
            aggregated_status = "FAIL"
        elif "PENDING" in statuses:
            aggregated_status = "PENDING"
        elif "MANUAL FIX" in statuses:
            aggregated_status = "MANUAL FIX"
        else:
            aggregated_status = "PASS"

        # Prepare a tag for the order header.
        if aggregated_status == "FAIL":
            status_tag = " | EDI process: 🔴 FAIL"
        elif aggregated_status == "PENDING":
            status_tag = " | EDI process: ⏳ PENDING"
        elif aggregated_status == "MANUAL FIX":
            status_tag = " | EDI process: 🛠️ MANUAL FIX"
        else:
            status_tag = " | EDI process: ✅ PASS"

        # Apply the order status filter if it is not "All".
        if order_status_selection != "All" and aggregated_status != order_status_selection:
            continue

        order_level = group_df.iloc[0]
        order_date = order_level["DateOrdered_dt"].date() if pd.notnull(order_level["DateOrdered_dt"]) else order_level["DateOrdered"]
        net_total = order_level["Net Total of order"]
        branch = order_level["Branch name"]

        expander_label = f"PO: {po_display} | DateOrdered: {order_date} | Branch: {branch} | Net Total: {net_total}{status_tag}"
        with st.expander(expander_label, expanded=False):
            st.markdown("**Order Lines:**")
            columns_to_show = [
                "PO number", "DateOrdered", "Branch name",
                "Description", "SupplierItemCode", "Unit price", "QtyOrdered", "DateExpected",
                "Order Status", "Manual Fix By", "Manual Fix Comment"
            ]
            order_lines = group_df[columns_to_show].copy()
            order_lines["PO number"] = order_lines["PO number"].apply(
                lambda x: str(int(x)) if pd.notnull(x) and isinstance(x, (float, int)) else x
            )
            st.dataframe(order_lines, use_container_width=True)

            # If the order is flagged as FAIL, allow user input to mark it as manually fixed.
            if aggregated_status == "FAIL":
                st.markdown("### Manual Order Fix")
                fixed_by = st.text_input("Fixed By", key=f"fix_by_{po_display}")
                fix_comment = st.text_area("Fix Comments", key=f"fix_comment_{po_display}")
                if st.button("Mark as Manually Fixed", key=f"manual_fix_button_{po_display}"):
                    if not fixed_by:
                        st.error("Please enter the name of the user who fixed the order.")
                    else:
                        update_order_manual_fix(po, fixed_by, fix_comment)
                        st.success("Order updated as MANUAL FIX. Refreshing...")
                        st.rerun()
            elif aggregated_status == "MANUAL FIX":
                # Optionally display the fix details
                fix_by_info = order_level.get("Manual Fix By", "")
                fix_comment_info = order_level.get("Manual Fix Comment", "")
                st.info(f"This order was manually fixed by: {fix_by_info}\n\nComments: {fix_comment_info}")
else:
    st.info("No orders found for the selected filters.")