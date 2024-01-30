from datetime import datetime
import time
from kucoin_futures.client import Market
from kucoin_futures.client import Trade
from kucoin_futures.client import User
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

class Client:
    client = None
    user = None
    market = None
    trade = None

access_key = "65a1ccb58228970001b778da"
secret_key = "d048330f-598d-47b3-a046-9537fcf589c8"
passphrase = "Tamas123!"
client = Client

client.user  = User(key=access_key, secret=secret_key, passphrase=passphrase, url='https://api-futures.kucoin.com')
client.market = Market(key=access_key, secret=secret_key, passphrase=passphrase, url='https://api-futures.kucoin.com')
client.trade = Trade(key=access_key, secret=secret_key, passphrase=passphrase, url='https://api-futures.kucoin.com')

def calculate_supertrend(df, factor=1, period=4):
    """
    Calculates Supertrend signals based on the provided DataFrame and factors.
    
    Args:
    - df: DataFrame containing OHLCV data with columns 'High', 'Low', 'Close'.
    - factor: Multiplier for ATR (default is 1).
    - period: Period for ATR calculation (default is 4).

    Returns:
    - DataFrame with Supertrend signals.
    """
    atr = df['High'].combine(df['Low'], max) - df['Close'].shift(1)
    atr = atr.rolling(window=period).mean()

    df['UpperBand'] = df['High'] - factor * atr
    df['LowerBand'] = df['Low'] + factor * atr

    df['UpTrend'] = True
    df.loc[df['Close'] > df['UpperBand'], 'UpTrend'] = False

    df['DownTrend'] = True
    df.loc[df['Close'] < df['LowerBand'], 'DownTrend'] = False

    df['Signal'] = ''
    df.loc[df['UpTrend'], 'Signal'] = 'Buy'
    df.loc[df['DownTrend'], 'Signal'] = 'Sell'

    return df

def generate_signal_files(df, factor=1, period=4):
    """
    Generates 'supertrend.buy' or 'supertrend.sell' files based on Supertrend signals.
    
    Args:
    - df: DataFrame with Supertrend signals.
    - factor: Multiplier for ATR (default is 1).
    - period: Period for ATR calculation (default is 4).

    Returns:
    - None
    """
    df = calculate_supertrend(df, factor, period)

    buy_signal = df[df['Signal'] == 'Buy']
    sell_signal = df[df['Signal'] == 'Sell']

    if not buy_signal.empty:
        with open('supertrend.buy', 'w') as buy_file:
            buy_file.write(f"Symbol: {symbol}")

    if not sell_signal.empty:
        with open('supertrend.sell', 'w') as sell_file:
            sell_file.write(f"Symbol: {symbol}")

symbol = 'SOLUSDTM'
interval = 3 
data = client.market.get_kline_data(symbol, granularity=interval)
df = pd.DataFrame(data, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
generate_signal_files(df, factor=1, period=4)