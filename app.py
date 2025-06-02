import streamlit as st
import pdfplumber
import re
import pandas as pd
import altair as alt
from datetime import datetime

def extract_transactions(pdf_path, password):
    transactions = []
    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                matches = re.findall(
                    r'(?P<date>\d{1,2}/\d{1,2}/2025).*?(?P<type>Receive from Wallet|PayDirect Payment|DUITNOW_RECEI).*?(?P<name>[A-Z\s\/]+)?\s+.*?RM(?P<amount>\d+\.\d{2})\s+RM(?P<balance>\d+\.\d{2})',
                    text,
                    flags=re.DOTALL
                )
                for match in matches:
                    transactions.append({
                        "date": match[0],
                        "type": match[1].strip(),
                        "name": match[2].strip() if match[2] else "",
                        "amount": float(match[3]),
                        "balance": float(match[4])
                    })
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
    return transactions

def preprocess_transactions(txns):
    df = pd.DataFrame(txns)
    if df.empty:
        return df
    df['date'] = pd.to_datetime(df['date'], format="%d/%m/%Y")
    df['amount_signed'] = df.apply(
        lambda r: r['amount'] if r['type'] in ['Receive from Wallet', 'DUITNOW_RECEI'] else -r['amount'],
        axis=1
    )
    return df


def main():
    st.title("TNG E-wallet Transactions Analyzer - Advanced")

    pdf_file = st.file_uploader("Upload your password-protected PDF", type=["pdf"])
    password = st.text_input("Enter PDF password", type="password")

    if pdf_file and password:
        with open("temp_tng.pdf", "wb") as f:
            f.write(pdf_file.getbuffer())

        st.info("Extracting transactions...")
        transactions = extract_transactions("temp_tng.pdf", password)

        if not transactions:
            st.warning("No transactions found or incorrect password.")
            return

        df = preprocess_transactions(transactions)
        if df.empty:
            st.warning("No transaction data to display.")
            return

        # --- Advanced Filters ---
        st.sidebar.header("Filter Transactions")

        # Date range filter
        min_date = df['date'].min()
        max_date = df['date'].max()
        date_range = st.sidebar.date_input("Date range", [min_date, max_date], min_value=min_date, max_value=max_date)
        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df['date'] >= pd.Timestamp(start_date)) & (df['date'] <= pd.Timestamp(end_date))]

        # Transaction type filter
        all_types = df['type'].unique()
        selected_types = st.sidebar.multiselect("Transaction Type", options=all_types, default=list(all_types))
        if selected_types:
            df = df[df['type'].isin(selected_types)]

        # Amount range filter
        min_amount = float(df['amount_signed'].min())
        max_amount = float(df['amount_signed'].max())
        amount_range = st.sidebar.slider("Amount range (signed)", min_amount, max_amount, (min_amount, max_amount))
        df = df[(df['amount_signed'] >= amount_range[0]) & (df['amount_signed'] <= amount_range[1])]

        # Search by name filter
        search_name = st.text_input("🔍 Search by name:")
        if search_name:
            filtered_df = df[df['name'].str.contains(search_name, case=False, na=False)]
            st.write(f"Found {len(filtered_df)} transactions.")
            if not filtered_df.empty:
                st.dataframe(filtered_df)
            else:
                st.warning("No matching transactions found.")


        # --- Show Data ---
        st.dataframe(df[['date', 'type', 'name', 'amount_signed', 'balance']].sort_values('date'))

        # --- KPIs ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Received (RM)", f"{df[df['amount_signed'] > 0]['amount_signed'].sum():.2f}")
        col2.metric("Total Paid (RM)", f"{-df[df['amount_signed'] < 0]['amount_signed'].sum():.2f}")
        col3.metric("Last Balance (RM)", f"{df.iloc[-1]['balance']:.2f}")

        # --- Visualizations ---

        st.subheader("Cumulative Net Amount Over Time")
        cum_df = df.groupby('date')['amount_signed'].sum().cumsum().reset_index()

        line_chart = alt.Chart(cum_df).mark_line(point=True).encode(
            x='date:T',
            y=alt.Y('amount_signed:Q', title='Cumulative Amount (RM)'),
            tooltip=[alt.Tooltip('date:T', title='Date'), alt.Tooltip('amount_signed:Q', title='Cumulative RM')]
        ).properties(width=700, height=300).interactive()

        st.altair_chart(line_chart)

        st.subheader("Transaction Type Distribution")
        type_counts = df['type'].value_counts().reset_index()
        type_counts.columns = ['type', 'count']

        pie_chart = alt.Chart(type_counts).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="count", type="quantitative"),
            color=alt.Color(field="type", type="nominal", legend=alt.Legend(title="Transaction Type")),
            tooltip=['type', 'count']
        ).properties(width=400, height=400)

        st.altair_chart(pie_chart)

        st.subheader("Transaction Amount Distribution")
        hist = alt.Chart(df).mark_bar().encode(
            alt.X('amount_signed', bin=alt.Bin(maxbins=30), title='Amount (signed RM)'),
            y='count()',
            tooltip=['count()']
        ).properties(width=700, height=300)

        st.altair_chart(hist)

if __name__ == "__main__":
    main()
