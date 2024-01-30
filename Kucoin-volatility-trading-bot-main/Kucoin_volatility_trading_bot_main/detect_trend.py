from binance.client import Client
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

def importdata(symbol, interval, limit):
    client = Client("","")
    df = pd.DataFrame(client.get_klines(symbol=symbol, interval=interval, limit=limit)).astype(float)
    df = df.iloc[:, :6]
    df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

def tr(data):
    data["previous_close"] = data["close"].shift(1)
    data["high-low"] = abs(data["high"] - data["low"])
    data["high-pc"] = abs(data["high"] - data["previous_close"])
    data["low-pc"] = abs(data["low"] - data["previous_close"])

    tr = data[["high-low", "high-pc", "low-pc"]].max(axis=1)

    return tr

def atr(data, period):
    data["tr"] = tr(data)
    atr = data["tr"].rolling(period).mean()

    return atr

def supertrend(df, period=7, atr_multiplier=3):
    hl2 = (df["high"] + df["low"]) / 2
    df["atr"] = atr(df, period)
    df["upperband"] = hl2 + (atr_multiplier * df["atr"])
    df["lowerband"] = hl2 - (atr_multiplier * df["atr"])
    df["in_uptrend"] = True
    for current in range(1, len(df.index)):
        previous = current - 1

        if df["close"][current] > df["upperband"][previous]:
            df["in_uptrend"][current] = True
        elif df["close"][current] < df["lowerband"][previous]:
            df["in_uptrend"][current] = False
        else:
            df["in_uptrend"][current] = df["in_uptrend"][previous]

            if df["in_uptrend"][current] and df["lowerband"][current] < df["lowerband"][previous]:
                df["lowerband"][current] = df["lowerband"][previous]

            if not df["in_uptrend"][current] and df["upperband"][current] > df["upperband"][previous]:
                df["upperband"][current] = df["upperband"][previous]
    return df
def show_chart(df):
    # Generate some data
    x = df["timestamp"]
    y = df["close"]
    y1 = df["upperband"]
    y2 = df["lowerband"]

    # Create the plot and add the line collection
    fig, ax = plt.subplots()

    ax.plot(x, y, label="close")
    ax.plot(x, y1, label="Upper")
    ax.plot(x, y2, label="Lower")

    y_up, x_up, y_down, x_down, y_sell, x_sell, y_buy, x_buy = [],[],[],[],[],[],[],[]

    for current in range(1, len(df.index)):
        previous = current - 1
        if df["in_uptrend"][current]:
            x_up.append(df["timestamp"][previous])
            y_up.append(df["close"][previous])
        else:
            x_down.append(df["timestamp"][previous])
            y_down.append(df["close"][previous])

        if df["buy"][current]:
            x_buy.append(df["timestamp"][current])
            y_buy.append(df["close"][current])
        
        if df["sell"][current]:
            x_sell.append(df["timestamp"][current])
            y_sell.append(df["close"][current])

    ax.scatter(x_up, y_up, s=30, facecolors='none', edgecolors='g')
    ax.scatter(x_down, y_down, s=30, facecolors='none', edgecolors='r')
    ax.scatter(x_buy, y_buy, s=30, facecolors='g', edgecolors='g')
    ax.scatter(x_sell, y_sell, s=30, facecolors='r', edgecolors='r')

    ax.set_xlabel('Timestamp')
    ax.set_ylabel('Close')
    ax.set_title('Plot title')

    # Customize appearance
    ax.grid(True)

    # Display the plot
    plt.show()

def is_uptrend(symbol):
    interval = "1h"
    limit = 100
    period = 4
    multi = 1
    df = importdata(symbol, interval, limit)
    df = supertrend(df, period=period, atr_multiplier=multi)
    print(f'{symbol} is in uptrend: {df["in_uptrend"][len(df.index)-1]}')
    return df["in_uptrend"][len(df.index)-1]

if __name__ == "__main__":
    symbol = "SOL" + "USDT"
    interval = "ih"
    limit = 500
    df = importdata(symbol, interval, limit)
    while True:
        #period = int(input("Period:"))
        #multi = int(input("Multi:"))
        period = 4
        multi = 1
        holding = False
        trade = {"slot" : 100,
                 "profit" : 0,
                 "amount" : 0,
                 "bought_at" : 0,
                 "sold_at" : 0
                 }
        trades = []

        df = supertrend(df, period=period, atr_multiplier=multi)
        df["buy"] = False
        df["sell"] = False
        for current in range(1, len(df.index)):
            if df["in_uptrend"][current - 1] != df["in_uptrend"][current]:
                if not holding:
                    holding = True
                    df["buy"][current] = True
                else:
                    holding = False
                    df["sell"][current] = True
                    trade["sold_at"] = df["close"][current]
                    trade["profit"] = trade["amount"] * trade["sold_at"] - trade["slot"]
                    trades.append(trade)
        print(trade["profit"])
        show_chart(df)