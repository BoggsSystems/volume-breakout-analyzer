import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

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

            # Plot candlestick chart with breakout markers
            fig = go.Figure()

            # Add candlestick chart
            fig.add_trace(go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name='Candlestick'
            ))

            # Add breakout markers
            fig.add_trace(go.Scatter(
                x=breakout_days.index,
                y=breakout_days['Close'],
                mode='markers',
                name='Breakout Days',
                marker=dict(color='red', size=8, symbol='cross')
            ))

            # Add volume bar chart
            fig.add_trace(go.Bar(
                x=data.index,
                y=data['Volume'],
                name='Volume',
                marker=dict(color='blue'),
                yaxis='y2'  # Secondary y-axis for volume
            ))

            # Layout settings
            fig.update_layout(
                title=f"{ticker} Price and Volume Breakout Chart",
                xaxis_title="Date",
                yaxis_title="Price",
                yaxis2=dict(
                    title="Volume",
                    overlaying="y",
                    side="right"
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            # Display the chart
            st.plotly_chart(fig)

            # Format the Date column to remove the time portion
            breakout_days_with_returns_limited.reset_index(inplace=True)
            breakout_days_with_returns_limited['Date'] = breakout_days_with_returns_limited['Date'].dt.strftime('%Y-%m-%d')

            # Display Breakout Days with Returns
            st.write("Breakout Days with Returns", breakout_days_with_returns_limited)

            # Convert to CSV
            csv = breakout_days_with_returns_limited.to_csv(index=False)

            # Provide a download button
            st.download_button("Download Report", csv, file_name=f"{ticker}_breakout_report.csv", mime="text/csv")

        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {str(e)}")
