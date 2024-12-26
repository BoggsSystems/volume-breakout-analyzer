import streamlit as st
import pandas as pd
import yfinance as yf

# Title of the app
st.title("Volume Breakout Analyzer")

# User Inputs
ticker = st.text_input("Enter Ticker Symbol (e.g., AAPL):")
start_date = st.date_input("Start Date")
end_date = st.date_input("End Date")
volume_threshold = st.number_input("Volume Breakout Threshold (%)", min_value=0.0, value=200.0)
price_change_threshold = st.number_input("Price Change Threshold (%)", min_value=0.0, value=2.0)
holding_period = st.number_input("Holding Period (Days)", min_value=1, value=10)

if st.button("Generate Report"):
    if not ticker:
        st.error("Please enter a valid ticker symbol.")
    else:
        # Fetch historical data
        try:
            data = yf.download(ticker, start=start_date, end=end_date)

            # Flatten column names if multi-level
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [col[0] for col in data.columns.values]

            st.write(f"Data for {ticker}", data)

            # Calculate average volume over the last 20 days
            data['AvgVolume'] = data['Volume'].rolling(window=20).mean()

            # Identify breakout days
            data['VolumeBreakout'] = data['Volume'] > (data['AvgVolume'] * (volume_threshold / 100))
            data['PriceChange'] = (data['Close'] - data['Close'].shift(1)) / data['Close'].shift(1) * 100
            data['PriceBreakout'] = data['PriceChange'] > price_change_threshold
            data['Breakout'] = data['VolumeBreakout'] & data['PriceBreakout']

            # Filter breakout days
            breakout_days = data[data['Breakout']]

            # Select specific columns for Breakout Days table
            columns_to_display = ['Close', 'High', 'Low', 'Open', 'Volume', 'PriceChange']
            breakout_days_limited = breakout_days[columns_to_display]

            st.write("Breakout Days", breakout_days_limited)

            # Calculate returns
            returns = []
            for index, row in breakout_days.iterrows():
                start_price = row['Close']
                end_index = index + pd.DateOffset(days=holding_period)

                if end_index in data.index:
                    end_price = data.loc[end_index, 'Close']
                    returns.append((end_price - start_price) / start_price * 100)
                else:
                    returns.append(None)

            breakout_days['Return'] = returns

            # Select specific columns for Breakout Days with Returns table
            columns_to_display_with_returns = ['Close', 'High', 'Low', 'Open', 'Volume', 'PriceChange', 'Return']
            breakout_days_with_returns_limited = breakout_days[columns_to_display_with_returns]

            # Format the Date column to remove the time portion
            breakout_days_with_returns_limited.reset_index(inplace=True)
            breakout_days_with_returns_limited['Date'] = breakout_days_with_returns_limited['Date'].dt.strftime('%Y-%m-%d')

            # Define a function for conditional formatting of the 'Return' column
            def color_returns(val):
                if pd.notnull(val):  # Check if the value is not NaN
                    color = "green" if val > 0 else "red"
                    return f"color: {color}"
                return ""

            # Use pandas Styler for formatting
            styled_df = breakout_days_with_returns_limited.style.format({
                'Close': "{:,.2f}",
                'High': "{:,.2f}",
                'Low': "{:,.2f}",
                'Open': "{:,.2f}",
                'Volume': "{:,.0f}",
                'PriceChange': "{:,.2f}",
                'Return': "{:,.2f}"
            }).applymap(color_returns, subset=['Return'])

            # Display the styled DataFrame
            st.write("Breakout Days with Returns")
            st.dataframe(styled_df)

            # Convert to CSV
            csv = breakout_days_with_returns_limited.to_csv(index=False)

            # Provide a download button
            st.download_button("Download Report", csv, file_name=f"{ticker}_breakout_report.csv", mime="text/csv")

        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {str(e)}")
