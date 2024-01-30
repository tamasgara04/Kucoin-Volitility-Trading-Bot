# Kucoin Volitility Trading Bot

## Description
This project orginally comes from https://github.com/returnsomeday2/Binance-volatility-trading-bot
I wanted to create also short sales and use leverage, but can not use futures trading in germany on Binance, so recreated it for Kucoin.
This Kucoin trading bot analyses the changes in price across all coins on Kucoin and place trades on the most volatile ones. 
In addition to that, this Kucoin trading algorithm will also keep track of all the coins bought and sell them according to your specified Stop Loss and Take Profit.

The bot will listen to changes in price accross all coins on Kucoin. By default, we're only picking USDT pairs. We're excluding Margin (like BTCDOWNUSDT) and Fiat pairs

> Information below is an example and is all configurable

- The bot checks if the any coin has gone up by more than 3% in the last 5 minutes (or  create a custom signal)
- The bot will buy/sell 100 USDT of the most volatile coins on Kucoin
- The bot will sell at 6% profit or 3% stop loss (or sell/buy is triggered by custom signal)


## READ BEFORE USE
Use at your own risk.

## Usage
- Get all api keys and enter it in the creds.yml file
- Install all requirements from the requirements.txt files
- Configure your settings in the config.creds.yml file (rename afterwards to creds.yml!)
- You need to first start the UI: streamlit run UI/streamlit_page.py then the KucoinDetectMoonings.py

## 💥 Disclaimer

All investment strategies and investments involve risk of loss. 
**Nothing contained in this program, scripts, code or repository should be construed as investment advice.**
Any reference to an investment's past or potential performance is not, 
and should not be construed as, a recommendation or as a guarantee of 
any specific outcome or profit.
By using this program you accept all liabilities, and that no claims can be made against the developers or others connected with the program.
