import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# Title of the app
st.title("Enhanced Volume Breakout Analyzer")

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

            # Calculate additional parameters
            # Moving Averages
            data['MA50'] = data['Close'].rolling(window=50).mean()
            data['MA200'] = data['Close'].rolling(window=200).mean()

            # Relative Strength Index (RSI)
            delta = data['Close'].diff(1)
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            data['RSI'] = 100 - (100 / (1 + rs))

            # Bollinger Bands
            data['BB_Mid'] = data['Close'].rolling(window=20).mean()
            data['BB_Upper'] = data['BB_Mid'] + 2 * data['Close'].rolling(window=20).std()
            data['BB_Lower'] = data['BB_Mid'] - 2 * data['Close'].rolling(window=20).std()

            # Identify breakout days
            data['AvgVolume'] = data['Volume'].rolling(window=20).mean()
            data['VolumeBreakout'] = data['Volume'] > (data['AvgVolume'] * (volume_threshold / 100))
            data['PriceChange'] = (data['Close'] - data['Close'].shift(1)) / data['Close'].shift(1) * 100
            data['PriceBreakout'] = data['PriceChange'] > price_change_threshold
            data['Breakout'] = data['VolumeBreakout'] & data['PriceBreakout']

            # Filter breakout days
            breakout_days = data[data['Breakout']]

            # Select specific columns for Breakout Days table
            columns_to_display = ['Close', 'High', 'Low', 'Open', 'Volume', 'PriceChange', 'RSI', 'MA50', 'MA200']
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
            columns_to_display_with_returns = ['Close', 'High', 'Low', 'Open', 'Volume', 'PriceChange', 'Return', 'RSI', 'MA50', 'MA200']
            breakout_days_with_returns_limited = breakout_days[columns_to_display_with_returns]

            # Display Breakout Days with Returns table
            st.write("Breakout Days with Returns", breakout_days_with_returns_limited)

            # Plot candlestick chart with breakout markers and moving averages
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

            # Add moving averages
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MA50'],
                mode='lines',
                name='50-Day MA',
                line=dict(color='blue', dash='dot')
            ))
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['MA200'],
                mode='lines',
                name='200-Day MA',
                line=dict(color='green', dash='dot')
            ))

            # Add Bollinger Bands
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['BB_Upper'],
                name='Bollinger Upper',
                line=dict(color='orange', width=1),
                opacity=0.4
            ))
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['BB_Lower'],
                name='Bollinger Lower',
                line=dict(color='orange', width=1),
                opacity=0.4
            ))

            # Layout settings
            fig.update_layout(
                title=f"{ticker} Price and Volume Breakout Chart with Indicators",
                xaxis_title="Date",
                yaxis_title="Price",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            # Display the chart
            st.plotly_chart(fig)

            # Create a separate formatted DataFrame for CSV export
            export_df = breakout_days_with_returns_limited.copy()
            export_df['Close'] = export_df['Close'].apply(lambda x: f"{x:,.2f}")
            export_df['High'] = export_df['High'].apply(lambda x: f"{x:,.2f}")
            export_df['Low'] = export_df['Low'].apply(lambda x: f"{x:,.2f}")
            export_df['Open'] = export_df['Open'].apply(lambda x: f"{x:,.2f}")
            export_df['Volume'] = export_df['Volume'].apply(lambda x: f"{x:,.0f}")
            export_df['PriceChange'] = export_df['PriceChange'].apply(lambda x: f"{x:,.2f}")
            export_df['Return'] = export_df['Return'].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")

            # Convert to CSV
            csv = export_df.to_csv(index=False)

            # Provide a download button
            st.download_button("Download Report", csv, file_name=f"{ticker}_enhanced_breakout_report.csv", mime="text/csv")

        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {str(e)}")
