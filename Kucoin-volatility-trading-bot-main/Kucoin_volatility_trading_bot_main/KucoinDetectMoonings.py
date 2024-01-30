import os

# use if needed to pass args to external modules
import sys
from pathlib import Path

# used for math functions
import math

# used to create threads & dynamic loading of modules
import multiprocessing
import importlib

# used for directory handling
import glob

# discord needs import request
import requests
from colorama import init
from utilities.txcolors import txcolors

# needed for the binance API / websockets / Exception handling
from kucoin_futures.client import Market
from kucoin_futures.client import Trade
from kucoin_futures.client import User

from requests.exceptions import ReadTimeout, ConnectionError

# used for dates
from datetime import datetime, timedelta
import time

# used to store trades and sell assets
import json

# used to display holding coins in an ascii table
from prettytable import PrettyTable

# Load helper modules
from helpers.parameters import parse_args, load_config

# Load creds modules
from helpers.handle_creds import load_correct_creds

# my helper utils
from helpers.os_utils import rchop
from helpers.db_interface import *
import pandas as pd
from globals import user_data_path


init()
# for colourful logging to the console

old_out = sys.stdout

class Client:
    user = None
    market = None
    trade = None

class St_ampe_dOut:
    """Stamped stdout."""

    nl = True

    def write(self, x):
        """Write function overloaded."""
        if x == "\n":
            old_out.write(x)
            self.nl = True
        elif self.nl:
            old_out.write(
                f"{txcolors.DIM}[{str(datetime.now().replace(microsecond=0))}]{txcolors.DEFAULT} {x}"
            )
            self.nl = False
        else:
            old_out.write(x)

    def flush(self):
        pass


class KucoinVolatilityBot:
    client = Client
    # user_data_path = '../user_data/'
    # db_file_name = 'transactions.db'
    db_interface = None
    # tracks profit/loss each session
    profile_summary = {}
    profile_summary_file_path = ""
    profile_summary_py_file_path = ""
    UI_notify_file_path = ""
    session_profit_incfees_perc = 0
    session_profit_incfees_total = 0

    CLEAN_START = False

    SESSION_TAKE_PROFIT = None
    SESSION_STOP_LOSS = None
    SESSION_TPSL_OVERRIDE = False
    session_tpsl_override_msg = ""
    is_bot_running = True
    historic_profit_incfees_perc = 0
    historic_profit_incfees_total = 0
    trade_wins = 0
    trade_losses = 0
    sell_all_coins = False
    sell_specific_coin = False
    buy_all_coins = False
    buy_specific_coin = False
    bot_started_datetime = 0
    market_startprice = 0
    market_currprice = 0
    total_capital = 0
    historical_prices = []

    transactions_df = None
    transactions_df_columns = [
        "Order Id",
        "Buy Time",
        "Symbol",
        "Volume",
        "Bought At",
        "Now At",
        "TP %",
        "SL %",
        "Change %",
        "Profit $",
        "Time Held",
        "Closed",
        "Sold At",
        "sell_reason",
    ]

    # algo params
    # set to false at Start
    bot_paused = False
    DEFAULT_CONFIG_FILE = ""
    DEFAULT_CREDS_FILE = ""
    # Default no debugging
    DEBUG = False
    tickers = []
    hsp_head = None

    signalthreads = []
    signals_status_file_name = "signals_status.json"

    coins_bought = {}
    coins_short = {}
    last_history_log_date = None
    discord_msg_balance_data = ""
    last_msg_discord_balance_date = None
    coins_bought_file_path = ""
    coins_short_file_path = ""
    transactions_file_path = ""
    LOG_FILE = ""
    HISTORY_LOG_FILE = ""
    volatility_cooloff = {}
    SELL_ON_SIGNAL_ONLY = None
    USE_TRAILING_STOP_LOSS = None
    TRAILING_TAKE_PROFIT = None
    TRAILING_STOP_LOSS = None

    test_order_id = 0

    def __init__(self):     
        # Get the path of the current script
        script_path = os.path.abspath(__file__)

        # Set the current working directory to the directory of the script
        os.chdir(os.path.dirname(script_path))

        args = parse_args()
        self.mymodule = {}

        self.discord_msg_balance_data = ""
        self.last_msg_discord_balance_date = datetime.now()
        self.last_history_log_date = datetime.now()
        self.notimeout = args.notimeout

        self.DEFAULT_CREDS_FILE = user_data_path + "creds.yml"
        self.creds_file = args.creds if args.creds else self.DEFAULT_CREDS_FILE

        self.DEFAULT_CONFIG_FILE = user_data_path + "config.yml"
        config_file = args.config if args.config else self.DEFAULT_CONFIG_FILE

        parsed_config = load_config(config_file)
        self.parsed_config = parsed_config

        # Load system vars
        self.CLEAN_START = parsed_config["script_options"]["CLEAN_START"]
        self.TEST_MODE = parsed_config["script_options"]["TEST_MODE"]
        self.LOG_FILE = parsed_config["script_options"].get("LOG_FILE")
        self.HISTORY_LOG_FILE = "history.txt"
        self.DEBUG_SETTING = parsed_config["script_options"].get("DEBUG")
        self.AMERICAN_USER = parsed_config["script_options"].get("AMERICAN_USER")

        # Load trading vars
        self.LEVERAGE = parsed_config["trading_options"]["LEVERAGE"]
        self.PAIR_WITH = parsed_config["trading_options"]["PAIR_WITH"]
        self.TRADE_TOTAL = parsed_config["trading_options"]["TRADE_TOTAL"]
        self.TRADE_SLOTS = parsed_config["trading_options"]["TRADE_SLOTS"]
        self.FIATS = parsed_config["trading_options"]["FIATS"]

        self.TIME_DIFFERENCE = parsed_config["trading_options"]["TIME_DIFFERENCE"]
        self.RECHECK_INTERVAL = parsed_config["trading_options"]["RECHECK_INTERVAL"]

        self.CHANGE_IN_PRICE = parsed_config["trading_options"]["CHANGE_IN_PRICE"]
        self.STOP_LOSS = parsed_config["trading_options"]["STOP_LOSS"]
        self.TAKE_PROFIT = parsed_config["trading_options"]["TAKE_PROFIT"]

        # COOLOFF_PERIOD = parsed_config['trading_options']['COOLOFF_PERIOD']

        self.CUSTOM_LIST = parsed_config["trading_options"]["CUSTOM_LIST"]
        self.CUSTOM_LIST_AUTORELOAD = parsed_config["trading_options"][
            "CUSTOM_LIST_AUTORELOAD"
        ]
        self.TICKERS_LIST = parsed_config["trading_options"]["TICKERS_LIST"]

        self.USE_TRAILING_STOP_LOSS = parsed_config["trading_options"][
            "USE_TRAILING_STOP_LOSS"
        ]
        self.TRAILING_STOP_LOSS = parsed_config["trading_options"]["TRAILING_STOP_LOSS"]
        self.TRAILING_TAKE_PROFIT = parsed_config["trading_options"][
            "TRAILING_TAKE_PROFIT"
        ]

        # If TRUE, coin will only sell based on an external SELL signal
        self.SELL_ON_SIGNAL_ONLY = parsed_config["trading_options"][
            "SELL_ON_SIGNAL_ONLY"
        ]

        # Discord integration
        # Used to push alerts, messages etc to value discord channel
        self.MSG_DISCORD = parsed_config["trading_options"]["MSG_DISCORD"]
        self.REINVEST_PROFITS = parsed_config["trading_options"]["REINVEST_PROFITS"]

        # Trashcan settings
        # HODLMODE_ENABLED = parsed_config['trading_options']['HODLMODE_ENABLED']
        # HODLMODE_TIME_THRESHOLD = parsed_config['trading_options']['HODLMODE_TIME_THRESHOLD']

        self.TRADING_FEE = parsed_config["trading_options"]["TRADING_FEE"]
        self.SIGNALLING_MODULES = parsed_config["trading_options"]["SIGNALLING_MODULES"]

        # if self.TEST_MODE:
        #     file_prefix = 'test_'
        # else:
        #     file_prefix = 'live_'
        file_prefix = ""

        # initialise database connection
        DB_TRANSACTIONS_FILE_NAME = parsed_config["data_options"][
            "DB_TRANSACTIONS_FILE_NAME"
        ]
        self.db_interface = DbInterface(user_data_path + DB_TRANSACTIONS_FILE_NAME)

        # path to the saved coins_bought file
        self.coins_bought_file_path = user_data_path + file_prefix + "coins_bought.json"
        self.coins_short_file_path = user_data_path + file_prefix + "coins_short.json"
        # path to the saved transactions history
        self.transactions_file_path = user_data_path + file_prefix + "transactions.csv"
        # path to the saved profile summary
        self.profile_summary_file_path = (
            user_data_path + file_prefix + "profile_summary.json"
        )
        self.profile_summary_py_file_path = user_data_path + "profile_summary.py"
        self.UI_notify_file_path = "UI/update_UI.py"
        # The below mod was stolen and altered from GoGo's fork, value nice addition for keeping value historical
        # history of profit across multiple bot sessions. path to the saved bot_stats file
        self.bot_stats_file_path = user_data_path + file_prefix + "bot_stats.json"

        self.signals_status_file_name = (
            user_data_path + file_prefix + self.signals_status_file_name
        )
        # use separate files for testing and live trading
        self.LOG_FILE = user_data_path + file_prefix + self.LOG_FILE
        self.HISTORY_LOG_FILE = user_data_path + file_prefix + self.HISTORY_LOG_FILE

        # Use CUSTOM_LIST symbols if CUSTOM_LIST is set to True
        try:
            if self.CUSTOM_LIST:
                self.tickers = [line.strip() for line in open(self.TICKERS_LIST)]
        except:
            pass
        if self.DEBUG_SETTING or args.debug:
            self.DEBUG = True

        if self.DEBUG:
            print(f"Loaded config below\n{json.dumps(self.parsed_config, indent=4)}")
            # print(f'Your credentials have been loaded from {creds_file}')

        # initialise reporting data
        self.historic_profit_incfees_perc = 0  # or some other default value.

        self.historic_profit_incfees_total = 0  # or some other default value.

        self.trade_wins = 0  # or some other default value.
        self.trade_losses = 0  # or some other default value.

        self.bot_started_datetime = ""
        self.market_startprice = 0

        # print with timestamps
        self.old_out = sys.stdout

        # essam transactions
        self.transactions_df = pd.DataFrame(columns=self.transactions_df_columns)

    def is_fiat(self):
        # check if we are using value fiat as value base currency
        PAIR_WITH = self.parsed_config["trading_options"]["PAIR_WITH"]
        # list below is in the order that Binance displays them, apologies for not using ASC order
        fiats = [
            "USDT",
            "BUSD",
            "AUD",
            "BRL",
            "EUR",
            "GBP",
            "RUB",
            "TRY",
            "TUSD",
            "USDC",
            "PAX",
            "BIDR",
            "DAI",
            "IDRT",
            "UAH",
            "NGN",
            "VAI",
            "BVND",
        ]

        if PAIR_WITH in fiats:
            return True
        else:
            return False

    def decimals(self):
        # set number of decimals for reporting fractions
        if self.is_fiat():
            return 4
        else:
            return 8

    def print_table(self, table):
        print("")
        sys.stdout = self.old_out
        print(table)
        sys.stdout = St_ampe_dOut()

    def print_notimestamp(self, msg):
        sys.stdout = self.old_out
        print(msg, end=" ")
        sys.stdout = St_ampe_dOut()

    def get_price(self, add_to_historical=True):
        """Return the current price for all coins on kucoin"""
        # Short compatible
        initial_price = {}
        prices = self.client.market.get_contracts_list()

        for coin in prices:
            if coin["symbol"] == "XBTUSDTM":
                if self.market_startprice == 0:
                    self.market_startprice = float(coin["markPrice"])
                self.market_currprice = float(coin["markPrice"])

            if self.CUSTOM_LIST:
                if any(
                    item + self.PAIR_WITH == coin["symbol"] for item in self.tickers
                ) and all(item not in coin["symbol"] for item in self.FIATS):
                    initial_price[coin["symbol"]] = {
                        "price": coin["markPrice"],
                        "time": datetime.now(),
                    }
            else:
                if self.PAIR_WITH in coin["symbol"] and all(
                    item not in coin["symbol"] for item in self.FIATS
                ):
                    initial_price[coin["symbol"]] = {
                        "price": coin["markPrice"],
                        "time": datetime.now(),
                    }

        if add_to_historical:
            self.hsp_head += 1

            if self.hsp_head == self.RECHECK_INTERVAL:
                self.hsp_head = 0

            self.historical_prices[self.hsp_head] = initial_price

        return initial_price

    def wait_for_price(self):
        """calls the initial price and ensures the correct amount of time has passed
        before reading the current price again"""

        # Short compatible
        volatile_coins = {}
        externals = {}
        externals_sell  = {}
        coins_up = 0
        coins_down = 0
        coins_unchanged = 0

        self.pause_bot()

        # get first element from the dictionary
        firstcoin = next(iter(self.historical_prices[self.hsp_head]))

        if self.historical_prices[self.hsp_head][firstcoin]["time"] > datetime.now() - timedelta(minutes=float(self.TIME_DIFFERENCE / self.RECHECK_INTERVAL)):
            time.sleep((timedelta(minutes=float(self.TIME_DIFFERENCE / self.RECHECK_INTERVAL)) - (datetime.now() - self.historical_prices[self.hsp_head][firstcoin]["time"])).total_seconds())
        
        last_price = self.wrap_get_price()

        # calculate the difference in prices
        for coin in self.historical_prices[self.hsp_head]:
            threshold_check = 0
            # minimum and maximum prices over time period
            try:
                min_price = min(
                    self.historical_prices,
                    key=lambda x: float("inf")
                    if x is None
                    else float(x[coin]["price"]),
                )
                max_price = max(
                    self.historical_prices,
                    key=lambda x: -1 if x is None else float(x[coin]["price"]),
                )

                threshold_check = (
                    (-1.0 if min_price[coin]["time"] > max_price[coin]["time"] else 1.0)
                    * (
                        float(max_price[coin]["price"])
                        - float(min_price[coin]["price"])
                    )
                    / float(min_price[coin]["price"])
                    * 100
                )

                # if coin == "BTCUSDT" or coin == "ETHUSDT":
                # print(f"coin: {coin} min_price: {min_price[coin]['price']} max_price: {max_price[coin]['price']}")
            except KeyError:
                if self.DEBUG:
                    print(
                        f"wait_for_price(): Got value KeyError for {coin}"
                        f". If this coin was just added to your tickers file, no need to worry about this KeyError."
                    )
                pass

            # FOR NEGATIVE PRICE CHECKING
            # if threshold_check>0 and CHANGE_IN_PRICE<0: threshold_check=0

            # each coin with higher gains than our CHANGE_IN_PRICE is added to the volatile_coins dict if less than
            # TRADE_SLOTS is not reached. FOR NEGATIVE PRICE CHECKING if abs(threshold_check) > abs(CHANGE_IN_PRICE):
            if threshold_check > self.CHANGE_IN_PRICE:
                coins_up += 1

                if coin not in self.volatility_cooloff:
                    self.volatility_cooloff[coin] = datetime.now() - timedelta(
                        minutes=self.TIME_DIFFERENCE
                    )
                    # volatility_cooloff[coin] = datetime.now() - timedelta(minutes=COOLOFF_PERIOD)

                # only include coin as volatile if it hasn't been picked up in the last TIME_DIFFERENCE minutes already
                if datetime.now() >= self.volatility_cooloff[coin] + timedelta(
                    minutes=self.TIME_DIFFERENCE
                ):
                    # if datetime.now() >= volatility_cooloff[coin] + timedelta(minutes=COOLOFF_PERIOD):
                    self.volatility_cooloff[coin] = datetime.now()

                    if (
                        len(self.coins_bought) + len(self.coins_short) + len(volatile_coins) < self.TRADE_SLOTS
                        or self.TRADE_SLOTS == 0
                    ):
                        # volatile_coins[coin] = round(threshold_check, 3)
                        volatile_coins[coin] = {
                            "buy_signal": "volatility_gain",
                            "value": 1,
                            "gain": round(threshold_check, 3),
                        }
                        print(
                            f"{coin} has gained {volatile_coins[coin]['gain']}% within the last {self.TIME_DIFFERENCE} minutes, "
                            f"purchasing ${self.TRADE_TOTAL} {self.PAIR_WITH} of {coin}!"
                        )

                    else:
                        print(
                            f"{txcolors.WARNING}{coin} has gained "
                            f"{round(threshold_check, 3)}% within the last "
                            f"{self.TIME_DIFFERENCE} "
                            f"minutes, but you are using all available trade slots!{txcolors.DEFAULT}"
                        )
                # else: if len(coins_bought) == TRADE_SLOTS: print(f'{txcolors.WARNING}{coin} has gained {round(
                # threshold_check, 3)}% within the last {TIME_DIFFERENCE} minutes, but you are using all available
                # trade slots!{txcolors.DEFAULT}') else: print(f'{txcolors.WARNING}{coin} has gained {round(
                # threshold_check, 3)}% within the last {TIME_DIFFERENCE} minutes, but failed cool off period of {
                # COOLOFF_PERIOD} minutes! Curr COP is {volatility_cooloff[coin] + timedelta(
                # minutes=COOLOFF_PERIOD)}{txcolors.DEFAULT}')
            elif threshold_check < self.CHANGE_IN_PRICE:
                coins_down += 1

            else:
                coins_unchanged += 1

        # Disabled until fix
        # print(f'Up: {coins_up} Down: {coins_down} Unchanged: {coins_unchanged}')

        # Here goes new code for external signalling
        externals = self.buy_external_signals()
        # Short sales
        externals_sell = self.sell_external_signals()
        #self.remove_external_signals("sell")
        #self.remove_external_signals("buy")
        exnumber = 0

        for excoin in externals:
            if (
                excoin not in volatile_coins
                #and excoin not in self.coins_bought
                #and excoin not in self.coins_short
                and (len(self.coins_bought) + len(volatile_coins) + len(self.coins_short)) < self.TRADE_SLOTS
            ):
                # (len(coins_bought) + exnumber + len(volatile_coins)) < TRADE_SLOTS:
                volatile_coins[excoin] = {
                    "sell_signal": "",
                    "buy_signal": externals[excoin]["buy_signal"],
                    "value": 1,
                }
                if excoin == "BUSDUSDTM":
                    print("xx")
                exnumber += 1
                print(
                    f"External signal received on {excoin}, purchasing ${self.TRADE_TOTAL} {self.PAIR_WITH} "
                    f"value of {excoin}!"
                )

        for excoin in externals_sell:
            if (
                excoin not in volatile_coins
                and excoin not in self.coins_short
                and excoin in self.coins_bought
                or (len(self.coins_bought) + len(volatile_coins) + len(self.coins_short)) < self.TRADE_SLOTS
            ):
                # (len(coins_bought) + exnumber + len(volatile_coins)) < TRADE_SLOTS:
                volatile_coins[excoin] = {
                    "buy_signal": "",
                    "sell_signal": externals_sell[excoin]["sell_signal"],
                    "value": 1,
                }
                if excoin == "BUSDUSDTM":
                    print("xx")
                exnumber += 1
                print(
                    f"External signal received on {excoin}, shorting ${self.TRADE_TOTAL} {self.PAIR_WITH} "
                    f"value of {excoin}!"
                )

        self.balance_report(last_price)
        return (
            volatile_coins,
            len(volatile_coins),
            self.historical_prices[self.hsp_head],
        )

    def buy_external_signals(self):
        external_list = {}
        signals = {}

        # check directory and load pairs from files into external_list
        signals = glob.glob("signals/*.buy")
        for filename in signals:
            for line in open(filename):
                symbol = line.strip()
                if symbol == "BUSDUSDT":
                    print("xx")
                # external_list[symbol] = {symbol: symbol, 'buy_signal': filename.replace('signals','').replace('//','').replace('\\','').replace('.buy','')}
                external_list[symbol] = {
                    symbol: symbol,
                    "buy_signal": Path(filename).stem,
                }
            try:
                print("")
                #os.remove(filename)
            except:
                if self.DEBUG:
                    print(
                        f"{txcolors.WARNING}Could not remove external signalling file{txcolors.DEFAULT}"
                    )

        return external_list

    def sell_external_signals(self):
        external_list = {}
        signals = {}

        # check directory and load pairs from files into external_list
        signals = glob.glob("signals/*.sell")
        for filename in signals:
            for line in open(filename):
                symbol = line.strip()
                # external_list[symbol] = {symbol: symbol, 'sell_signal': filename.replace('signals','').replace(
                # '//','').replace('\\','').replace('.sell','')}
                external_list[symbol] = {
                    symbol: symbol,
                    "sell_signal": Path(filename).stem,
                }
                if self.DEBUG:
                    print(f"{symbol} added to sell_external_signals() list")
            try:
                print("")
            #    os.remove(filename)
            except:
                if self.DEBUG:
                    print(
                        f"{txcolors.WARNING}Could not remove external SELL signalling file{txcolors.DEFAULT}"
                    )

        return external_list

    def balance_report(self, last_price):
        unrealised_session_profit_incfees_perc = 0
        unrealised_session_profit_incfees_total = 0

        BUDGET = float(self.TRADE_SLOTS * self.TRADE_TOTAL)
        exposure_calcuated = 0

        for coin in list(self.coins_bought):            
            LastPrice = float(last_price[coin]["price"])
            sellFee = LastPrice * (self.TRADING_FEE / 100)

            BuyPrice = float(self.coins_bought[coin]["bought_at"])
            buyFee = BuyPrice * (self.TRADING_FEE / 100)

            exposure_calcuated = exposure_calcuated + round((float(self.coins_bought[coin]["bought_at"]) * float(self.coins_bought[coin]["multiplier"]))* float(self.coins_bought[coin]["volume"]), 0,)

            # PriceChangeIncFees_Total = float(((LastPrice+sellFee) - (BuyPrice+buyFee)) * coins_bought[coin]['volume'])
            PriceChangeIncFees_Total = float(((LastPrice - sellFee) - (BuyPrice + buyFee)) * float(self.coins_bought[coin]["multiplier"]) * self.coins_bought[coin]["volume"])
            # unrealised_session_profit_incfees_perc = float(unrealised_session_profit_incfees_perc +
            # PriceChangeIncFees_Perc)
            unrealised_session_profit_incfees_total = float(unrealised_session_profit_incfees_total + PriceChangeIncFees_Total)

        for coin in list(self.coins_short):
            
            LastPrice = float(last_price[coin]["price"])
            sellFee = LastPrice * (self.TRADING_FEE / 100)

            BuyPrice = float(self.coins_short[coin]["bought_at"])
            buyFee = BuyPrice * (self.TRADING_FEE / 100)

            exposure_calcuated = exposure_calcuated - round((float(self.coins_short[coin]["bought_at"]) * float(self.coins_short[coin]["multiplier"]))* float(self.coins_short[coin]["volume"]), 0,)

            # PriceChangeIncFees_Total = float(((LastPrice+sellFee) - (BuyPrice+buyFee)) * coins_bought[coin]['volume'])
            PriceChangeIncFees_Total = float(((LastPrice - sellFee) - (BuyPrice + buyFee)) * float(self.coins_short[coin]["multiplier"]) * self.coins_short[coin]["volume"])
            # unrealised_session_profit_incfees_perc = float(unrealised_session_profit_incfees_perc +
            # PriceChangeIncFees_Perc)
            unrealised_session_profit_incfees_total = float(unrealised_session_profit_incfees_total + PriceChangeIncFees_Total)

        unrealised_session_profit_incfees_perc = ((unrealised_session_profit_incfees_total / BUDGET) * 100)

        DECIMALS = int(self.decimals())
        # CURRENT_EXPOSURE = round((TRADE_TOTAL * len(coins_bought)), DECIMALS)
        CURRENT_EXPOSURE = round(exposure_calcuated, 0)
        INVESTMENT_TOTAL = round((self.TRADE_TOTAL * self.TRADE_SLOTS), DECIMALS)

        # truncating some of the above values to the correct decimal places before printing
        WIN_LOSS_PERCENT = 0
        if (self.trade_wins > 0) and (self.trade_losses > 0):
            WIN_LOSS_PERCENT = round(
                (self.trade_wins / (self.trade_wins + self.trade_losses)) * 100, 2
            )
        if (self.trade_wins > 0) and (self.trade_losses == 0):
            WIN_LOSS_PERCENT = 100

        self.profile_summary = {
            "Started": str(self.bot_started_datetime).split(".")[0],
            "Running for": str(datetime.now() - self.bot_started_datetime).split(".")[
                0
            ],
            "CURRENT HOLDS": f"{len(self.coins_bought) + len(self.coins_short)}/{self.TRADE_SLOTS} ({float(CURRENT_EXPOSURE)}/{float(INVESTMENT_TOTAL)} {self.PAIR_WITH})",
            "Buying Paused": self.bot_paused,
            "SESSION PROFIT (Inc Fees)": {
                "Realised": f"{self.session_profit_incfees_perc:.4f}% Est:${self.session_profit_incfees_total:.4f} {self.PAIR_WITH}",
                "Unrealised": f"{unrealised_session_profit_incfees_perc:.4f}% Est:${unrealised_session_profit_incfees_total:.4f} {self.PAIR_WITH}",
                "Total": f"{self.session_profit_incfees_perc + unrealised_session_profit_incfees_perc:.4f}% Est:${self.session_profit_incfees_total + unrealised_session_profit_incfees_total:.4f} {self.PAIR_WITH}{txcolors.DEFAULT}",
            },
            "ALL TIME DATA": {
                "Market Profit": f"{((self.market_currprice - self.market_startprice) / self.market_startprice) * 100:.4f}% (Since STARTED)",
                "Bot Profit": f"{self.historic_profit_incfees_perc: .4f} % Est:${self.historic_profit_incfees_total: .4f}{self.PAIR_WITH}",
                "Completed Trades": f"{self.trade_wins + self.trade_losses} (Wins:{self.trade_wins} Losses:{self.trade_losses})",
                "Win Ratio": f"{float(WIN_LOSS_PERCENT):g}%",
            },
        }

        # save the coins in value json file in the same directory
        # with open(self.profile_summary_file_path, 'w') as file:
        #     json.dump(self.profile_summary, file, indent=4)

        print(f"")
        print(f"--------")
        print(
            f"STARTED         : {str(self.bot_started_datetime).split('.')[0]} | Running for: {str(datetime.now() - self.bot_started_datetime).split('.')[0]}"
        )
        print(
            f"CURRENT HOLDS   : {len(self.coins_bought) + len(self.coins_short)}/{self.TRADE_SLOTS} ({float(CURRENT_EXPOSURE):g}/{float(INVESTMENT_TOTAL):g} {self.PAIR_WITH})"
        )
        if self.REINVEST_PROFITS:
            print(
                f"ADJ TRADE TOTAL : {self.TRADE_TOTAL:.2f} (Current TRADE TOTAL adjusted to reinvest profits)"
            )
        print(f"Buying Paused   : {self.bot_paused}")
        print(f"")
        print(f"SESSION PROFIT (Inc Fees)")
        print(
            f"Realised        : {txcolors.SELL_PROFIT if self.session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{self.session_profit_incfees_perc:.4f}% Est:${self.session_profit_incfees_total:.4f} {self.PAIR_WITH}{txcolors.DEFAULT}"
        )
        print(
            f"Unrealised      : {txcolors.SELL_PROFIT if unrealised_session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{unrealised_session_profit_incfees_perc:.4f}% Est:${unrealised_session_profit_incfees_total:.4f} {self.PAIR_WITH}{txcolors.DEFAULT}"
        )
        print(
            f"        Total   : {txcolors.SELL_PROFIT if (self.session_profit_incfees_perc + unrealised_session_profit_incfees_perc) > 0. else txcolors.SELL_LOSS}{self.session_profit_incfees_perc + unrealised_session_profit_incfees_perc:.4f}% Est:${self.session_profit_incfees_total + unrealised_session_profit_incfees_total:.4f} {self.PAIR_WITH}{txcolors.DEFAULT}"
        )
        print(f"")
        print(f"ALL TIME DATA   :")
        print(
            f"Market Profit   : {txcolors.SELL_PROFIT if self.historic_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{((self.market_currprice - self.market_startprice) / self.market_startprice) * 100:.4f}% (Since STARTED){txcolors.DEFAULT}"
        )
        print(
            f"Bot Profit      : {txcolors.SELL_PROFIT if self.historic_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{self.historic_profit_incfees_perc:.4f}% Est:${self.historic_profit_incfees_total:.4f} {self.PAIR_WITH}{txcolors.DEFAULT}"
        )
        print(
            f"Completed Trades: {self.trade_wins + self.trade_losses} (Wins:{self.trade_wins} Losses:{self.trade_losses})"
        )
        print(f"Win Ratio       : {float(WIN_LOSS_PERCENT):g}%")

        print(f"--------")
        print(f"")

        # msg1 = str(bot_started_datetime) + " | " + str(datetime.now() - bot_started_datetime)
        msg1 = str(datetime.now()).split(".")[0]
        msg2 = (
            " | "
            + str(len(self.coins_bought))
            + "/"
            + str(self.TRADE_SLOTS)
            + " | PBOT: "
            + str(self.bot_paused)
        )
        msg2 = (
            msg2
            + " SPR%: "
            + str(round(self.session_profit_incfees_perc, 2))
            + " SPR$: "
            + str(round(self.session_profit_incfees_total, 4))
        )
        msg2 = (
            msg2
            + " SPU%: "
            + str(round(unrealised_session_profit_incfees_perc, 2))
            + " SPU$: "
            + str(round(unrealised_session_profit_incfees_total, 4))
        )
        msg2 = (
            msg2
            + " SPT%: "
            + str(
                round(
                    self.session_profit_incfees_perc
                    + unrealised_session_profit_incfees_perc,
                    2,
                )
            )
            + " SPT$: "
            + str(
                round(
                    self.session_profit_incfees_total
                    + unrealised_session_profit_incfees_total,
                    4,
                )
            )
        )
        msg2 = (
            msg2
            + " ATP%: "
            + str(round(self.historic_profit_incfees_perc, 2))
            + " ATP$: "
            + str(round(self.historic_profit_incfees_total, 4))
        )
        msg2 = (
            msg2
            + " CTT: "
            + str(self.trade_wins + self.trade_losses)
            + " CTW: "
            + str(self.trade_wins)
            + " CTL: "
            + str(self.trade_losses)
            + " CTWR%: "
            + str(round(WIN_LOSS_PERCENT, 2))
        )

        self.msg_discord_balance(msg1, msg2)
        self.history_log(
            self.session_profit_incfees_perc,
            self.session_profit_incfees_total,
            unrealised_session_profit_incfees_perc,
            unrealised_session_profit_incfees_total,
            self.session_profit_incfees_perc + unrealised_session_profit_incfees_perc,
            self.session_profit_incfees_total + unrealised_session_profit_incfees_total,
            self.historic_profit_incfees_perc,
            self.historic_profit_incfees_total,
            self.trade_wins + self.trade_losses,
            self.trade_wins,
            self.trade_losses,
            WIN_LOSS_PERCENT,
        )

        return msg1 + msg2

    def history_log(
        self,
        sess_profit_perc,
        sess_profit,
        sess_profit_perc_unreal,
        sess_profit_unreal,
        sess_profit_perc_total,
        sess_profit_total,
        alltime_profit_perc,
        alltime_profit,
        total_trades,
        won_trades,
        lost_trades,
        winloss_ratio,
    ):

        time_between_insertion = datetime.now() - self.last_history_log_date

        # only log balance to log file once every 60 seconds
        if time_between_insertion.seconds > 60:
            self.last_history_log_date = datetime.now()
            timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")

            if not os.path.exists(self.HISTORY_LOG_FILE):
                with open(self.HISTORY_LOG_FILE, "a+") as f:
                    f.write(
                        "Datetime\tCoins Holding\tTrade Slots\tPausebot Active\tSession Profit %\tSession Profit $\tSession Profit Unrealised %\tSession Profit Unrealised $\tSession Profit Total %\tSession Profit Total $\tAll Time Profit %\tAll Time Profit $\tTotal Trades\tWon Trades\tLost Trades\tWin Loss Ratio\n"
                    )

            with open(self.HISTORY_LOG_FILE, "a+") as f:
                f.write(
                    f"{timestamp}\t{len(self.coins_bought) + len(self.coins_short)}\t{self.TRADE_SLOTS}\t{str(self.bot_paused)}\t{str(round(sess_profit_perc, 2))}\t{str(round(sess_profit, 4))}\t{str(round(sess_profit_perc_unreal, 2))}\t{str(round(sess_profit_unreal, 4))}\t{str(round(sess_profit_perc_total, 2))}\t{str(round(sess_profit_total, 4))}\t{str(round(alltime_profit_perc, 2))}\t{str(round(alltime_profit, 4))}\t{str(total_trades)}\t{str(won_trades)}\t{str(lost_trades)}\t{str(winloss_ratio)}\n"
                )

    def msg_discord_balance(self, msg1, msg2):

        time_between_insertion = datetime.now() - self.last_msg_discord_balance_date

        # only put the balance message to discord once every 60 seconds and if the balance information has changed since last times
        if time_between_insertion.seconds > 60:
            if msg2 != self.discord_msg_balance_data:
                self.msg_discord(msg1 + msg2)
                self.discord_msg_balance_data = msg2
            else:
                # ping msg to know the bot is still running
                self.msg_discord(".")

    def msg_discord(self, msg):

        message = msg + "\n\n"

        if self.MSG_DISCORD:
            # Webhook of my channel. Click on edit channel --> Webhooks --> Creates webhook
            mUrl = "https://discordapp.com/api/webhooks/" + self.DISCORD_WEBHOOK
            data = {"content": message}
            response = requests.post(mUrl, json=data)
            # BB
            # print(response.content)

    def pause_bot(self):
        """Pause the script when external indicators detect value bearish trend in the market"""

        # start counting for how long the bot has been paused
        start_time = time.perf_counter()

        while os.path.exists("signals/pausebot.pause"):

            # do NOT accept any external signals to buy while in pausebot mode
            self.remove_external_signals("buy")
            self.remove_external_signals("sell")

            if self.bot_paused == False:
                print(
                    f"{txcolors.WARNING}Buying paused due to negative market conditions, stop loss and take profit will continue to work...{txcolors.DEFAULT}"
                )

                msg = (
                    str(datetime.now())
                    + " | PAUSEBOT. Buying paused due to negative market conditions, stop loss and take profit will continue to work."
                )
                self.msg_discord(msg)

                self.bot_paused = True

            # reporting and health checks
            self.track_module_status()
            # Sell function needs to work even while paused
            coins_sold = self.sell_coins()
            self.remove_from_portfolio(coins_sold)
            last_price = self.get_price(True)
            self.report_profile_summary(last_price)
            # pausing here
            if self.hsp_head == 1:
                # print(f'Paused...Session profit: {self.session_profit_incfees_perc:.2f}% Est: ${session_profit_incfees_total:.{decimals()}f} {PAIR_WITH}')
                self.balance_report(last_price)

            time.sleep((self.TIME_DIFFERENCE * 60) / self.RECHECK_INTERVAL)

        else:
            # stop counting the pause time
            stop_time = time.perf_counter()
            time_elapsed = timedelta(seconds=int(stop_time - start_time))

            # resume the bot and set pause_bot to False
            if self.bot_paused:
                print(
                    f"{txcolors.WARNING}Resuming buying due to positive market conditions, total sleep time: {time_elapsed}{txcolors.DEFAULT}"
                )

                msg = (
                    str(datetime.now())
                    + " | PAUSEBOT. Resuming buying due to positive market conditions, total sleep time: "
                    + str(time_elapsed)
                )
                self.msg_discord(msg)

                self.bot_paused = False

        return

    def convert_volume(self):
        """Converts the volume given in TRADE_TOTAL from USDT to the each coin's volume"""
        # Short compatible
        volatile_coins, number_of_coins, last_price = self.wait_for_price()
        lot_size = {}
        volume = {}
        buy_signal = {}
        sell_signal = {}
        for coin in volatile_coins:

            # Find the correct step size for each coin
            # max accuracy for BTC for example is 6 decimal points
            # while XRP is only 1
            try:
                info = self.client.market.get_contract_detail(coin)
                lot_size[coin] = int(info["lotSize"])
                if lot_size[coin] < 0:
                    lot_size[coin] = 0

                multiplier = float(info["multiplier"])
                coin_value = float(info["markPrice"])
                available_funds = self.TRADE_TOTAL
                volume[coin] = int(available_funds / (lot_size[coin] * multiplier * coin_value))
            except:
                pass
            if volatile_coins[coin]["buy_signal"] == "":
                sell_signal[coin] = volatile_coins[coin]["sell_signal"]
            else:
                buy_signal[coin] = volatile_coins[coin]["buy_signal"]

            # define the volume with the correct step size
            if coin not in lot_size:
                # original code: volume[coin] = float('{:.1f}'.format(volume[coin]))
                volume[coin] = int(volume[coin])
            else:
                # if lot size has 0 decimal points, make the volume an integer
                if lot_size[coin] == 0:
                    volume[coin] = int(volume[coin])
                else:
                    volume[coin] = self.truncate(volume[coin], lot_size[coin])

        return volume, last_price, buy_signal, sell_signal

    def generate_test_order_id(self):
        self.test_order_id -= 1
        return self.test_order_id

    def buy(self):
        """Place order market orders for each volatile coin found"""
        #Short compatible
        volume, last_price, buy_signal, sell_signal = self.convert_volume()
        orders = {}
        for coin in volume:
            try:
                if buy_signal[coin] != "":
                    side = "BUY"
            except:
                side = "SELL"
            if coin not in self.coins_bought and coin not in self.coins_short and volume[coin] != 0:
                self.remove_external_signals("buy")
                self.remove_external_signals("sell")
                print(f"{txcolors.BUY}Preparing to {side} {volume[coin]} LOTs of {coin} @ ${last_price[coin]['price']}{txcolors.DEFAULT}")

                msg1 = (
                    "@everyone"
                    + str(datetime.now())
                    + f" | {side}: "
                    + coin
                    + ". V:"
                    + str(volume[coin])
                    + " P$:"
                    + str(last_price[coin]["price"])
                )
                self.msg_discord(msg1)

                try:
                    order_details = self.client.trade.create_market_order(symbol=coin, side=side, lever=self.LEVERAGE, size=volume[coin])
                # error handling here in case position cannot be placed
                except Exception as e:
                    print(f"buy() exception: {e}")

                orders[coin] = self.client.trade.get_fills_details(orderId=order_details["orderId"])
                # kucoin sometimes returns an empty list, the code will wait here until binance returns the order
                while len(orders[coin]["items"]) == 0:
                    try:
                        orders[coin] = self.client.trade.get_fills_details(orderId=order_details["orderId"])
                    except:
                        print("waiting for kucoin to return order")
                        print("Kucoin is being slow in returning the order, calling the API again...")

                    time.sleep(1)
                else:
                    print("Order returned, saving order to file")

                    orders[coin] = self.extract_order_data(orders[coin])
                    self.write_log(
                        f"\t{side}\t{coin}\t{orders[coin]['volume']}\t{orders[coin]['avgPrice']}\t{self.PAIR_WITH}"
                    )
                    if side == "BUY":
                        self.write_signallsell(rchop(coin, self.PAIR_WITH))
                    else:
                        self.write_signallbuy(rchop(coin, self.PAIR_WITH))

            else:
                print(
                    f"Signal detected, but there is already an active trade on {coin}"
                )
        # Add buy signal used to issue each order
        for coin in orders:
            try:
                orders[coin]["buy_signal"] = buy_signal[coin]
            except:
                pass
            try:
                orders[coin]["sell_signal"] = sell_signal[coin]
            except:
                pass
        return orders, last_price, volume

    def sell_coins(self, tpsl_override=False, specific_coin_to_sell="", specific_coin_to_buy=""):
        """sell coins that have reached the STOP LOSS or TAKE PROFIT threshold"""
        # global coin_order_id,

        externals = self.sell_external_signals()
        externals_buy = self.buy_external_signals()
        self.remove_external_signals("sell")
        self.remove_external_signals("buy")
        last_price = self.get_price(False)  # don't populate rolling window
        # last_price = get_price(add_to_historical=True) # don't populate rolling window
        coins_sold = {}
        coins_long = {}

        BUDGET = self.TRADE_TOTAL * self.TRADE_SLOTS

        # table stuff
        my_table = PrettyTable()
        my_table.field_names = [
            "Symbol",
            "Volume",
            "Bought At",
            "Now At",
            "TP %",
            "SL %",
            "Change %",
            "Profit $",
            "Time Held",
        ]
        my_table.align["Symbol"] = "l"
        my_table.align["Volume"] = "r"
        my_table.align["Bought At"] = "r"
        my_table.align["Now At"] = "r"
        my_table.align["TP %"] = "r"
        my_table.align["SL %"] = "r"
        my_table.align["Change %"] = "r"
        my_table.align["Profit $"] = "r"
        my_table.align["Time Held"] = "l"

        for coin in list(self.coins_bought):

            if self.sell_specific_coin and not specific_coin_to_sell == coin:
                continue
            time_held = timedelta(
                seconds=datetime.now().timestamp()
                - int(str(self.coins_bought[coin]["timestamp"])[:10])
            )

            LastPrice = float(last_price[coin]["price"])
            sellFee = self.coins_bought[coin]["buyFeeBNB"]
            LastPriceLessFees = LastPrice - sellFee

            BuyPrice = float(self.coins_bought[coin]["bought_at"])
            buyFee = self.coins_bought[coin]["buyFeeBNB"]

            BuyPricePlusFees = BuyPrice + buyFee
            ProfitAfterFees = LastPriceLessFees - BuyPricePlusFees

            PriceChange_Perc = float((LastPrice - BuyPrice) / BuyPrice * 100)

            PriceChangeIncFees_Perc = float(
                ((LastPrice - sellFee) - (BuyPrice + buyFee))
                / (BuyPrice + buyFee)
                * 100
            ) 
            PriceChangeIncFees_Perc = float((LastPrice - sellFee) - (BuyPrice + buyFee))

            # define stop loss and take profit
            TP = float(self.coins_bought[coin]["bought_at"]) + (
                (
                    float(self.coins_bought[coin]["bought_at"])
                    * (self.coins_bought[coin]["take_profit"])
                    / 100
                )
            )
            SL = float(self.coins_bought[coin]["bought_at"]) + (
                (
                    float(self.coins_bought[coin]["bought_at"])
                    * (self.coins_bought[coin]["stop_loss"])
                    / 100
                )
            )

            self.coins_bought[coin]["TTP_TSL"] = False

            # check that the price is below the stop loss or above take profit (if trailing stop loss not used) and sell if this is the case
            sellCoin = False
            sell_reason = ""
            if self.SELL_ON_SIGNAL_ONLY:
                # only sell if told to by external signal
                if coin in externals:
                    sellCoin = True
                    sell_reason = externals[coin][
                        "sell_signal"
                    ]  # 'External Sell Signal'
            else:
                # if LastPrice < SL:
                if LastPriceLessFees < SL:
                    sellCoin = True
                    sell_reason = "SL reached"
                    sell_reason = sell_reason
                    # if LastPrice > TP:
                if LastPriceLessFees > TP:
                    sellCoin = True
                    sell_reason = "TP reached"
                if coin in externals:
                    sellCoin = True
                    sell_reason = externals[coin][
                        "sell_signal"
                    ]  # 'External Sell Signal'

            if self.sell_all_coins:
                sellCoin = True
                sell_reason = "Sell All Coins"
            if self.sell_specific_coin:
                sellCoin = True
                sell_reason = "Sell Specific Coin"
            if tpsl_override:
                sellCoin = True
                sell_reason = self.session_tpsl_override_msg

            if sellCoin:
                print(
                    f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc <= 0. else txcolors.SELL_LOSS}Sell: {self.coins_bought[coin]['volume']} of {coin} | {sell_reason} | ${float(LastPrice):g} - ${float(BuyPrice):g} | Profit: {PriceChangeIncFees_Perc:.2f}% Est: {self.calc_profit(coin, PriceChangeIncFees_Perc):.{self.decimals()}f} {self.PAIR_WITH} (Inc Fees){txcolors.DEFAULT}"
                )

                msg1 = (
                    "@everyone"
                    + str(datetime.now())
                    + "| SELL: "
                    + coin
                    + ". R:"
                    + sell_reason
                    + " P%:"
                    + str(round(PriceChangeIncFees_Perc, 2))
                    + " P$:"
                    + str(
                        round(self.calc_profit(coin, PriceChangeIncFees_Perc),4,)
                    )
                )
                self.msg_discord(msg1)

                # try to create value real order
                try:
                    order_info = self.client.trade.create_market_order(symbol=coin, side="SELL", lever=self.LEVERAGE, size=self.coins_bought[coin]["volume"])
                    order_details = self.client.trade.get_fills_details(orderId=order_info["orderId"])
                    while len(order_details["items"]) == 0:
                        try:
                            order_details = self.client.trade.get_fills_details(orderId=order_info["orderId"])
                        except:
                            order_details = []
                            print("waiting for kucoin to return order")
                # error handling here in case position cannot be placed
                except Exception as e:
                    # if repr(e).upper() == "APIERROR(CODE=-1111): PRECISION IS OVER THE MAXIMUM DEFINED FOR THIS ASSET.":
                    print(
                        f"sell_coins() Exception occured on selling the coin! Coin: {coin}\nSell Volume coins_bought: {self.coins_bought[coin]['volume']}\nPrice:{LastPrice}\nException: {e}"
                    )

                # run the else block if coin has been sold and create value dict for each coin sold
                else:
                    coins_sold[coin] = self.extract_order_data(order_details)
                    LastPrice = float(coins_sold[coin]["avgPrice"])
                    sellFee = coins_sold[coin]["tradeFeeBNB"]
                    coins_sold[coin]["orderId"] = self.coins_bought[coin]["orderId"]
                    priceChange = float((LastPrice - BuyPrice) / BuyPrice * 100)

                    PriceChangeIncFees_Unit = float(
                            (LastPrice - sellFee) - (BuyPrice + buyFee)
                        )
                    # prevent system from buying this coin for the next TIME_DIFFERENCE minutes
                    self.volatility_cooloff[coin] = datetime.now()

                    if self.DEBUG:
                        print(
                            f"sell_coins() | Coin: {coin} | Sell Volume: {float(coins_sold[coin]['volume']) * float(coins_sold[coin]['multiplier'])} | Price:{LastPrice}"
                        )

                    # Log trade

                    profit_incfees_total = (coins_sold[coin]["volume"] * coins_sold[coin]["multiplier"]) * PriceChangeIncFees_Unit
                    self.write_log(
                        f"\tSell\t{coin}\t{float(coins_sold[coin]['volume']) * float(coins_sold[coin]['multiplier']) * LastPrice}\t{BuyPrice}\t{self.PAIR_WITH}\t{LastPrice}\t{profit_incfees_total:.{self.decimals()}f}\t{PriceChangeIncFees_Perc:.2f}\t{sell_reason}"
                    )
                    # reinvest profits
                    if self.REINVEST_PROFITS:
                        self.TRADE_TOTAL += profit_incfees_total / self.TRADE_SLOTS

                    # this is good
                    self.session_profit_incfees_total = (self.session_profit_incfees_total + profit_incfees_total)
                    self.session_profit_incfees_perc = (self.session_profit_incfees_perc + ((profit_incfees_total / BUDGET) * 100))

                    self.historic_profit_incfees_total = (self.historic_profit_incfees_total + profit_incfees_total)
                    self.historic_profit_incfees_perc = (self.historic_profit_incfees_perc + ((profit_incfees_total / BUDGET) * 100))

                    if (LastPrice - sellFee) >= (BuyPrice + buyFee):
                        self.trade_wins += 1
                    else:
                        self.trade_losses += 1

                    changes2 = {
                        "time_held": str(time_held).split(".")[0],
                        "tp_perc": self.coins_bought[coin]["take_profit"],
                        "now_at": LastPrice,
                        "sl_perc": self.coins_bought[coin]["stop_loss"],
                        "change_perc": PriceChangeIncFees_Perc,
                        "profit_dollars": profit_incfees_total,
                        "closed": 1,
                        "sold_at": float(LastPrice),
                        "sell_time": datetime.now(),
                        "sell_reason": sell_reason,
                    }

                    self.update_transaction_history_data(coin=coin, changes2=changes2)
                    self.update_bot_stats()
                    if not self.sell_all_coins and not self.sell_specific_coin:
                        # within sell_all_coins, it will print display to screen
                        self.balance_report(last_price)

                # sometimes get "rate limited" errors from Binance if we try to sell too many coins at once
                # so wait 1 second in between sells
                time.sleep(1)
                continue

            # no action; print once every TIME_DIFFERENCE
            if self.hsp_head == 1:
                if len(self.coins_bought) > 0:
                    # print(f"Holding: {coins_bought[coin]['volume']} of {coin} | {LastPrice} - {BuyPrice} | Profit: {txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.SELL_LOSS}{PriceChangeIncFees_Perc:.4f}% Est: ({((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_Perc)/100:.{decimals()}f} {PAIR_WITH}){txcolors.DEFAULT}")
                    my_table.add_row(
                        [
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{coin}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{self.coins_bought[coin]['volume']:.6f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{BuyPrice:.6f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{LastPrice:.6f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{self.coins_bought[coin]['take_profit']:.4f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{self.coins_bought[coin]['stop_loss']:.4f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{PriceChangeIncFees_Perc:.4f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{self.calc_profit(coin, PriceChangeIncFees_Perc):.6f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{str(time_held).split('.')[0]}{txcolors.DEFAULT}",
                        ]
                    )

            changes2 = {
                "time_held": str(time_held).split(".")[0],
                "tp_perc": self.coins_bought[coin]["take_profit"],
                "now_at": LastPrice,
                "sl_perc": self.coins_bought[coin]["stop_loss"],
                "profit_dollars": (
                    (float(self.coins_bought[coin]["volume"])
                      * float(self.coins_bought[coin]["bought_at"])
                        * float(self.coins_bought[coin]["multiplier"])
                     ) * PriceChangeIncFees_Perc ) / 100,
                "change_perc": PriceChangeIncFees_Perc,
            }

            self.update_transaction_history_data(coin=coin, changes2=changes2)
        
        for coin in list(self.coins_short):
            if self.buy_specific_coin and not specific_coin_to_buy == coin:
                continue
            time_held = timedelta(
                seconds=datetime.now().timestamp()
                - int(str(self.coins_short[coin]["timestamp"])[:10])
            )

            LastPrice = float(last_price[coin]["price"])
            sellFee = self.coins_short[coin]["buyFeeBNB"]
            LastPriceLessFees = LastPrice + sellFee

            BuyPrice = float(self.coins_short[coin]["bought_at"])
            buyFee = self.coins_short[coin]["buyFeeBNB"]
            BuyPricePlusFees = BuyPrice - buyFee

            ProfitAfterFees = -(LastPriceLessFees - BuyPricePlusFees)

            PriceChange_Perc = float((LastPrice - BuyPrice) / BuyPrice * 100)

            PriceChangeIncFees_Perc = -float(
                ((LastPrice + sellFee) - (BuyPrice - buyFee))
                / (BuyPrice - buyFee)
                * 100
            )
            PriceChangeIncFees_Unit = -float((LastPrice + sellFee) - (BuyPrice - buyFee))

            # define stop loss and take profit
            TP = -float(self.coins_short[coin]["bought_at"]) + ((float(self.coins_short[coin]["bought_at"]) * (self.coins_short[coin]["take_profit"]) / 100))
            SL = float(self.coins_short[coin]["bought_at"]) + ((float(self.coins_short[coin]["bought_at"]) * (self.coins_short[coin]["stop_loss"]) / 100))

            self.coins_short[coin]["TTP_TSL"] = False
            buyCoin = False
            buy_reason = ""
            if self.SELL_ON_SIGNAL_ONLY:
                # only sell if told to by external signal
                if coin in externals_buy:
                    buyCoin = True
                    buy_reason = externals_buy[coin][
                        "buy_signal"
                    ]  # 'External Sell Signal'
            else:
                if LastPriceLessFees > SL:
                    buyCoin = True
                    buy_reason = "SL reached"
                    buy_reason = buy_reason
                if LastPriceLessFees < TP:
                    buyCoin = True
                    buy_reason = "TP reached"
                if coin in externals_buy:
                    buyCoin = True
                    buy_reason = externals_buy[coin][
                        "buy_signal"
                    ]  # 'External Sell Signal'

            if self.buy_all_coins:
                buyCoin = True
                buy_reason = "Buy All Coins"
            if self.buy_specific_coin:
                buyCoin = True
                buy_reason = "Buy Specific Coin"
            if tpsl_override:
                buyCoin = True
                buy_reason = self.session_tpsl_override_msg

            if buyCoin:
                print(
                    f"{txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.SELL_LOSS}Buy: {self.coins_short[coin]['volume']} of {coin} | {buy_reason} | ${float(LastPrice):g} - ${float(BuyPrice):g} | Profit: {PriceChangeIncFees_Perc:.2f}% Est: {self.calc_profit(coin, PriceChangeIncFees_Perc, True):.{self.decimals()}f} {self.PAIR_WITH} (Inc Fees){txcolors.DEFAULT}"
                )

                msg1 = (
                    "@everyone"
                    + str(datetime.now())
                    + "| BUY: "
                    + coin
                    + ". R:"
                    + buy_reason
                    + " P%:"
                    + str(round(PriceChangeIncFees_Perc, 2))
                    + " P$:"
                    + str(
                        round(self.calc_profit(coin, PriceChangeIncFees_Perc, True),4,)
                    )
                )
                self.msg_discord(msg1)

                # try to create value real order
                try:
                    order_info = self.client.trade.create_market_order(symbol=coin, side="BUY", lever=self.LEVERAGE, size=self.coins_short[coin]['volume'])
                    order_details = self.client.trade.get_fills_details(orderId=order_info["orderId"])
                    while len(order_details["items"]) == 0:
                        try:
                            order_details = self.client.trade.get_fills_details(orderId=order_info["orderId"])
                        except:
                            order_details = []
                            print("waiting for kucoin to return order")
                # error handling here in case position cannot be placed
                except Exception as e:
                    # if repr(e).upper() == "APIERROR(CODE=-1111): PRECISION IS OVER THE MAXIMUM DEFINED FOR THIS ASSET.":
                    print(
                        f"sell_coins() Exception occured on selling the coin! Coin: {coin}\nBuy Volume coins_short: {self.coins_short[coin]['volume']}\nPrice:{LastPrice}\nException: {e}"
                    )

                # run the else block if coin has been sold and create value dict for each coin sold
                else:
                    coins_long[coin] = self.extract_order_data(order_details)
                    LastPrice = float(coins_long[coin]["avgPrice"])
                    sellFee = coins_long[coin]["tradeFeeBNB"]
                    coins_long[coin]["orderId"] = self.coins_short[coin]["orderId"]

                    PriceChangeIncFees_Unit = float(
                            (LastPrice + sellFee) - (BuyPrice - buyFee)
                        )

                    if self.DEBUG:
                        print(f"sell_coins() | Coin: {coin} | Buy Volume: {float(coins_long[coin]['volume'])} | Price:{LastPrice}")

                    # Log trade
                    profit_incfees_total = (float(coins_long[coin]['volume']) * float(coins_long[coin]['multiplier'])) * PriceChangeIncFees_Unit
                    self.write_log(
                        f"\tBuy\t{coin}\t{float(coins_long[coin]['volume']) * float(coins_long[coin]['multiplier']) * LastPrice}\t{BuyPrice}\t{self.PAIR_WITH}\t{LastPrice}\t{profit_incfees_total:.{self.decimals()}f}\t{PriceChangeIncFees_Perc:.2f}\t{buy_reason}"
                    )
                    # reinvest profits
                    if self.REINVEST_PROFITS:
                        self.TRADE_TOTAL += profit_incfees_total / self.TRADE_SLOTS

                    # this is good
                    self.session_profit_incfees_total = (self.session_profit_incfees_total + profit_incfees_total)
                    self.session_profit_incfees_perc = (self.session_profit_incfees_perc + ((profit_incfees_total / BUDGET) * 100))

                    self.historic_profit_incfees_total = (self.historic_profit_incfees_total + profit_incfees_total)
                    self.historic_profit_incfees_perc = (self.historic_profit_incfees_perc + ((profit_incfees_total / BUDGET) * 100))

                    # TRADE_TOTAL*PriceChangeIncFees_Perc)/100

                    # if (LastPrice+sellFee) >= (BuyPrice+buyFee):
                    if (LastPrice + sellFee) < (BuyPrice - buyFee):
                        self.trade_wins += 1
                    else:
                        self.trade_losses += 1

                    changes2 = {
                        "time_held": str(time_held).split(".")[0],
                        "tp_perc": self.coins_short[coin]["take_profit"],
                        "now_at": LastPrice,
                        "sl_perc": self.coins_short[coin]["stop_loss"],
                        "change_perc": PriceChangeIncFees_Perc,
                        "profit_dollars": profit_incfees_total,
                        "closed": 1,
                        "sold_at": float(LastPrice),
                        "sell_time": datetime.now(),
                        "sell_reason": buy_reason,
                    }

                    self.update_transaction_history_data(coin=coin, changes2=changes2)
                    self.update_bot_stats()
                    if not self.sell_all_coins and not self.sell_specific_coin:
                        # within sell_all_coins, it will print display to screen
                        self.balance_report(last_price)
                time.sleep(1)
                continue

            # no action; print once every TIME_DIFFERENCE
            if self.hsp_head == 1:
                if len(self.coins_short) > 0:
                    # print(f"Holding: {coins_bought[coin]['volume']} of {coin} | {LastPrice} - {BuyPrice} | Profit: {txcolors.SELL_PROFIT if PriceChangeIncFees_Perc >= 0. else txcolors.SELL_LOSS}{PriceChangeIncFees_Perc:.4f}% Est: ({((float(coins_bought[coin]['volume'])*float(coins_bought[coin]['bought_at']))*PriceChangeIncFees_Perc)/100:.{decimals()}f} {PAIR_WITH}){txcolors.DEFAULT}")
                    my_table.add_row(
                        [
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{coin}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{self.coins_short[coin]['volume']:.6f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{BuyPrice:.6f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{LastPrice:.6f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{self.coins_short[coin]['take_profit']:.4f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{self.coins_short[coin]['stop_loss']:.4f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{PriceChangeIncFees_Perc:.4f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{self.calc_profit(coin, PriceChangeIncFees_Perc, True):.6f}{txcolors.DEFAULT}",
                            f"{txcolors.SELL_PROFIT if ProfitAfterFees >= 0. else txcolors.SELL_LOSS}{str(time_held).split('.')[0]}{txcolors.DEFAULT}",
                        ]
                    )

            changes2 = {
                "time_held": str(time_held).split(".")[0],
                "tp_perc": self.coins_short[coin]["take_profit"],
                "now_at": LastPrice,
                "sl_perc": self.coins_short[coin]["stop_loss"],
                "profit_dollars": (
                        (
                            float(self.coins_short[coin]["volume"])
                            * float(self.coins_short[coin]["bought_at"])
                            * float(self.coins_short[coin]["multiplier"])
                        )
                        * PriceChangeIncFees_Perc
                    )
                    / 100,
                "change_perc": PriceChangeIncFees_Perc,
            }

            self.update_transaction_history_data(coin=coin, changes2=changes2)
        my_table.sortby = "Change %"
        # my_table.reversesort = True

        if len(self.coins_bought) + len(self.coins_short) == 0:
            if self.hsp_head == 1:
                print(f"No trade slots are currently in use")
        else:
            if len(my_table._rows) > 0:
                self.print_table(my_table)

        # if tpsl_override: is_bot_running = False

        return coins_sold, coins_long

    def extract_order_data(self, order_details):
        # global STOP_LOSS, TAKE_PROFIT
        pos_info = self.client.trade.get_position_details(order_details['items'][0]["symbol"])
        transactionInfo = {}
        FILLS_TOTAL = 0
        FILLS_QTY = 0
        FILLS_FEE = 0
        # loop through each 'fill':
        for fills in order_details['items']:
            FILL_PRICE = float(fills['price'])
            FILL_QTY = float(fills['size'])
            FILLS_FEE += float(fills['fee'])

            # quantity of fills * price
            FILLS_TOTAL += (FILL_PRICE * FILL_QTY)
            # add to running total of fills quantity
            FILLS_QTY += FILL_QTY

        # calculate average fill price:
        FILL_AVG = (FILLS_TOTAL / FILLS_QTY)

        # tradeFeeApprox = (float(FILLS_QTY) * float(FILL_AVG)) * (self.TRADING_FEE/100)
        # Olorin Sledge: I only want fee at the unit level, not the total level
        tradeFeeApprox = float(FILL_AVG) * (float(order_details['items'][0]["feeRate"]) / 100)

        try:
            stop_loss = ((float(pos_info["liquidationPrice"]) - FILL_AVG) / FILL_AVG) * 100
        except:
            stop_loss = 6

        # the volume size is sometimes outside of precision, correct it
        try:
            coin_info = self.client.market.get_contract_detail(order_details['items'][0]["symbol"])
            multiplier = float(coin_info["multiplier"])
        except Exception as e:
            print(f"extract_order_data(): Exception getting coin {order_details['items'][0]['symbol']} step size! Exception: {e}")

        # create object with received data from Binance
        transactionInfo = {
            'symbol': order_details['items'][0]['symbol'],
            'orderId': order_details['items'][0]['orderId'],
            'timestamp': order_details['items'][0]['tradeTime'],
            'avgPrice': float(FILL_AVG),
            'volume': float(FILLS_QTY),
            'tradeFeeBNB': float(FILLS_FEE),
            'tradeFeeUnit': tradeFeeApprox,
            'multiplier': multiplier,
            'stop_loss': stop_loss,
            'liquidationPrice': float(pos_info["liquidationPrice"]),
            'side': order_details['items'][0]['side']
        }
        return transactionInfo

    def update_portfolio(self, orders, last_price, volume):
        """add every coin bought to our portfolio for tracking/selling later"""

        #     print(orders)
        for coin in orders:
            try:
                coin_step_size = float(orders[coin]["step_size"])
            except Exception as ExStepSize:
                coin_step_size = 0.1

            temp = {
                "symbol": orders[coin]["symbol"],
                "orderId": orders[coin]["orderId"],
                "timestamp": orders[coin]["timestamp"],
                "bought_at": orders[coin]["avgPrice"],
                "volume": orders[coin]["volume"],
                "multiplier": orders[coin]["multiplier"],
                "volume_debug": volume[coin],
                "buyFeeBNB": orders[coin]["tradeFeeBNB"],
                "buyFee": orders[coin]["tradeFeeUnit"] * orders[coin]["volume"],
                "stop_loss": orders[coin]["stop_loss"],
                "take_profit": self.TAKE_PROFIT,
                "step_size": float(coin_step_size),
                "liquidationPrice": orders[coin]["liquidationPrice"],
                "side": orders[coin]["side"]
            }

            if orders[coin]["side"] != "buy":
                self.coins_short[coin] = temp
            else:
                self.coins_bought[coin] = temp
            print(
                f'Order for {orders[coin]["symbol"]} with ID {orders[coin]["orderId"]} placed and saved to file.'
            )
        
            try:
                self.coins_short[coin]["sell_signal"] = orders[coin]["sell_signal"]
                self.add_transaction2db(self.coins_short[coin])
            except Exception as e:
                print(f"update_portfolio() Sell Exception: {e}")
            try:
                self.coins_bought[coin]["buy_signal"] = orders[coin]["buy_signal"]
                self.add_transaction2db(self.coins_bought[coin])     
            except Exception as e:
                print(f"update_portfolio() Buy Exception: {e}")

            # save the coins in value json file in the same directory
            with open(self.coins_bought_file_path, "w") as file:
                json.dump(self.coins_bought, file, indent=4)
            with open(self.coins_short_file_path, "w") as file:
                json.dump(self.coins_short, file, indent=4)

    def remove_from_portfolio(self, coins_sold, coins_bought):
        """Remove coins sold due to SL or TP from portfolio"""
        for coin in coins_sold:
            self.coins_bought.pop(coin)

        with open(self.coins_bought_file_path, "w") as file:
            json.dump(self.coins_bought, file, indent=4)

        if os.path.exists("signalsell_tickers.txt"):
            os.remove("signalsell_tickers.txt")
            for coin in self.coins_bought:
                self.write_signallsell(rchop(coin, self.PAIR_WITH))

        for coin in coins_bought:
            self.coins_short.pop(coin)

        with open(self.coins_short_file_path, "w") as file:
            json.dump(self.coins_short, file, indent=4)

        if os.path.exists("signalbuy_tickers.txt"):
            os.remove("signalbuy_tickers.txt")
            for coin in self.coins_short:
                self.write_signallbuy(rchop(coin, self.PAIR_WITH))

    def update_bot_stats(self):
        bot_stats = {
            "total_capital": self.TRADE_SLOTS * self.TRADE_TOTAL,
            "botstart_datetime": str(self.bot_started_datetime),
            "historicProfitIncFees_Percent": self.historic_profit_incfees_perc,
            "historicProfitIncFees_Total": self.historic_profit_incfees_total,
            "tradeWins": self.trade_wins,
            "tradeLosses": self.trade_losses,
            "market_startprice": self.market_startprice,
        }

        # save session info for through session portability
        with open(self.bot_stats_file_path, "w") as file:
            json.dump(bot_stats, file, indent=4)

    def report_profile_summary(self, last_price):
        # unrealised_session_profit_incfees_perc = 0
        unrealised_session_profit_incfees_total = 0

        BUDGET = self.TRADE_SLOTS * self.TRADE_TOTAL
        exposure_calcuated = 0

        # last_price = self.get_price(False)

        for coin in list(self.coins_bought):
            LastPrice = float(last_price[coin]["price"])
            sellFee = self.coins_bought[coin]["buyFeeBNB"]

            BuyPrice = float(self.coins_bought[coin]["bought_at"])
            buyFee = self.coins_bought[coin]["buyFeeBNB"]
            allFee = sellFee + buyFee
            exposure_calcuated = exposure_calcuated + round(
                float(self.coins_bought[coin]["bought_at"]) * float(self.coins_bought[coin]["multiplier"])
                * float(self.coins_bought[coin]["volume"]),
                0,
            )

            # PriceChangeIncFees_Total = float(((LastPrice+sellFee) - (BuyPrice+buyFee)) * coins_bought[coin]['volume'])
            PriceChangeIncFees_Total = float(
                ((LastPrice - BuyPrice) - allFee) * (float(self.coins_bought[coin]["multiplier"]) * self.coins_bought[coin]["volume"])
            )

            # unrealised_session_profit_incfees_perc = float(unrealised_session_profit_incfees_perc + PriceChangeIncFees_Perc)
            unrealised_session_profit_incfees_total = float(
                unrealised_session_profit_incfees_total + PriceChangeIncFees_Total
            )

        for coin in list(self.coins_short):
            LastPrice = float(last_price[coin]["price"])
            sellFee = self.coins_short[coin]["buyFeeBNB"]

            BuyPrice = float(self.coins_short[coin]["bought_at"])
            buyFee = self.coins_short[coin]["buyFeeBNB"]
            allFee = sellFee + buyFee

            exposure_calcuated = exposure_calcuated + round(
                float(self.coins_short[coin]["bought_at"]) * float(self.coins_short[coin]["multiplier"])
                * float(self.coins_short[coin]["volume"]),
                0,
            )

            # PriceChangeIncFees_Total = float(((LastPrice+sellFee) - (BuyPrice+buyFee)) * coins_bought[coin]['volume'])
            PriceChangeIncFees_Total = float(
                ((LastPrice - BuyPrice) + allFee) * (float(self.coins_short[coin]["multiplier"]) * -self.coins_short[coin]["volume"])
            )

            # unrealised_session_profit_incfees_perc = float(unrealised_session_profit_incfees_perc + PriceChangeIncFees_Perc)
            unrealised_session_profit_incfees_total = float(
                unrealised_session_profit_incfees_total + PriceChangeIncFees_Total
            )

        unrealised_session_profit_incfees_perc = (
            unrealised_session_profit_incfees_total / BUDGET
        ) * 100

        DECIMALS = int(self.decimals())
        # CURRENT_EXPOSURE = round((TRADE_TOTAL * len(coins_bought)), DECIMALS)
        CURRENT_EXPOSURE = round(exposure_calcuated, 0)
        INVESTMENT_TOTAL = round((self.TRADE_TOTAL * self.TRADE_SLOTS), DECIMALS)

        # truncating some of the above values to the correct decimal places before printing
        WIN_LOSS_PERCENT = 0
        if (self.trade_wins > 0) and (self.trade_losses > 0):
            WIN_LOSS_PERCENT = round(
                (self.trade_wins / (self.trade_wins + self.trade_losses)) * 100, 2
            )
        if (self.trade_wins > 0) and (self.trade_losses == 0):
            WIN_LOSS_PERCENT = 100

        # market_next_check_seconds = (self.TIME_DIFFERENCE * 60) / self.RECHECK_INTERVAL
        # market_next_check_time = datetime.now() + timedelta(seconds=market_next_check_seconds)

        with open(self.profile_summary_file_path) as f:
            old_profile = json.load(f)

        curr_stats = {
            "bot_paused": self.bot_paused,
            "market_next_check_time": old_profile["market_next_check_time"],
            "started": str(self.bot_started_datetime).split(".")[0],
            "current_holds": len(self.coins_bought) + len(self.coins_short),
            "slots": self.TRADE_SLOTS,
            "current_exposure": float(CURRENT_EXPOSURE),
            "invstment_total": float(INVESTMENT_TOTAL),
            "pair_with": self.PAIR_WITH,
            "realised_session_profit_incfees_perc": round(
                self.session_profit_incfees_perc, 5
            ),
            "realised_session_profit_incfees_total": round(
                self.session_profit_incfees_total, 5
            ),
            "unrealised_session_profit_incfees_perc": round(
                unrealised_session_profit_incfees_perc, 5
            ),
            "unrealised_session_profit_incfees_total": round(
                unrealised_session_profit_incfees_total, 5
            ),
            "session_profit_incfees_total_perc": round(
                self.session_profit_incfees_perc
                + unrealised_session_profit_incfees_perc,
                5,
            ),
            "session_profit_incfees_total": round(
                self.session_profit_incfees_total
                + unrealised_session_profit_incfees_total,
                5,
            ),
            "all_time_market_profit": round(
                (
                    (self.market_currprice - self.market_startprice)
                    / self.market_startprice
                )
                * 100,
                5,
            ),
            "bot_profit_perc": round(self.historic_profit_incfees_perc, 5),
            "bot_profit": round(self.historic_profit_incfees_total, 5),
            "trade_wins": self.trade_wins,
            "trade_losses": self.trade_losses,
            "win_ratio": float(WIN_LOSS_PERCENT),
        }

        with open(self.profile_summary_file_path, "w") as file:
            json.dump(curr_stats, file, indent=4)

        self.notify_UI()

    def notify_UI(self, reset=False):
        """
        this function updates value python script monitored by UI. This triggers streamlit to update itself
        Args:
            reset:

        Returns:

        """
        try:
            if reset:
                update = 0
            else:
                try:
                    with open(self.UI_notify_file_path, "r") as fp:
                        update = int(fp.read().split("=")[1])
                except:
                    update = 0

            with open(self.UI_notify_file_path, "w") as fp:
                fp.write(f"update={update + 1}")
        except Exception as e:
            print(f"notify_UI() Exception: {e}")


    def add_transaction2db(self, order=None):
        """
        Adds value new buy order to the database
        Args:
            order:

        Returns:

        """
        try:
            if order["stop_loss"] > 0:
                signal = order["sell_signal"]
            else:
                signal = order["buy_signal"]
            db_transaction = {
                "order_id": order["orderId"],
                "buy_time": datetime.fromtimestamp(int(order["timestamp"] / 1e9)),
                "symbol": order["symbol"],
                "volume": order["volume"],
                "bought_at": order["bought_at"],
                "now_at": order["bought_at"],
                "tp_perc": order["take_profit"],
                "sl_perc": order["stop_loss"],
                "change_perc": 0,
                "profit_dollars": 0,
                "time_held": 0,
                "closed": 0,
                "buy_signal": signal,
            }
            self.db_interface.add_record(db_transaction)
            self.notify_UI()
        except Exception as e:
            print(f"add_transaction2db() Exception: {e}")

    def update_transaction_history_data(self, coin, changes2):
        """
        Updates an open trade with given changes
        Args:
            coin:
            changes2:

        Returns:

        """
        self.db_interface.update_transaction_record(symbol=coin, update_dict=changes2)
        self.notify_UI()

    def write_log(self, logline):
        timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")

        if not os.path.exists(self.LOG_FILE):
            with open(self.LOG_FILE, "a+") as f:
                f.write(
                    "Datetime\tType\tCoin\tVolume\tBuy Price\tCurrency\tSell Price\tProfit $\tProfit %\tSell Reason\n"
                )

        with open(self.LOG_FILE, "a+") as f:
            f.write(timestamp + " " + logline + "\n")

    def write_signallsell(self, symbol):
        with open("signalsell_tickers.txt", "a+") as f:
            f.write(f"{symbol}\n")

    def write_signallbuy(self, symbol):
        with open("signalbuy_tickers.txt", "a+") as f:
            f.write(f"{symbol}\n")

    def remove_external_signals(self, fileext):
        signals = glob.glob(f"signals/*.{fileext}")
        for filename in signals:
            # for line in open(filename):
            try:
                os.remove(filename)
            except:
                if self.DEBUG:
                    print(
                        f"{txcolors.WARNING}Could not remove external signalling file {filename}{txcolors.DEFAULT}"
                    )

    def sell_all(self, msgreason, session_tspl_ovr=False):

        self.msg_discord(f"{str(datetime.now())} | SELL ALL COINS: {msgreason}")

        # stop external signals so no buying/selling/pausing etc can occur
        self.stop_signal_threads()

        # sell all coins NOW!
        self.sell_all_coins = True
        self.buy_all_coins = True

        coins_sold, coins_buy = self.sell_coins(session_tspl_ovr)
        self.remove_from_portfolio(coins_sold, coins_buy)

        # display final info to screen
        # last_price = get_price()
        last_price = self.wrap_get_price()

        discordmsg = self.balance_report(last_price)
        self.msg_discord(discordmsg)

    def sell_a_specific_coin(self, coin):

        self.msg_discord(f"{str(datetime.now())} | SELL SPECIFIC COIN: {coin}")

        # sell all coins NOW!
        self.sell_specific_coin = True

        coins_sold, coins_buy = self.sell_coins(False, coin)
        self.remove_from_portfolio(coins_sold, coins_buy)

        self.sell_specific_coin = False

    def buy_a_specific_coin(self, coin):
        self.msg_discord(f"{str(datetime.now())} | BUY SPECIFIC COIN: {coin}")

        # sell all coins NOW!
        self.buy_specific_coin = True

        coins_sold, coins_buy = self.sell_coins(False, buy_specific_coin=coin)
        self.remove_from_portfolio(coins_sold, coins_buy)

        self.buy_specific_coin = False

    def stop_signal_threads(self):

        try:
            for signalthread in self.signalthreads:
                print(f"Terminating thread {str(signalthread.name)}")
                signalthread.terminate()
        except:
            pass

    def calc_profit(self, coin, PriceChangeIncFees_Perc, short = False):
        if short:
            return ((((float(self.coins_short[coin]["volume"]) * float(self.coins_short[coin]["bought_at"]) * float(self.coins_short[coin]["multiplier"])) * PriceChangeIncFees_Perc) / 100))
        else:
            return ((((float(self.coins_bought[coin]["volume"]) * float(self.coins_bought[coin]["bought_at"]) * float(self.coins_bought[coin]["multiplier"])) * PriceChangeIncFees_Perc) / 100))

    def truncate(self, number, decimals=0):
        """
        Returns value value truncated to value specific number of decimal places.
        Better than rounding
        """
        if not isinstance(decimals, int):
            raise TypeError("decimal places must be an integer.")
        elif decimals < 0:
            raise ValueError("decimal places has to be 0 or more.")
        elif decimals == 0:
            return math.trunc(number)

        factor = 10.0**decimals
        return math.trunc(number * factor) / factor

    def wrap_get_price(self):
        # Use CUSTOM_LIST symbols if CUSTOM_LIST is set to True
        if self.CUSTOM_LIST:
            if self.CUSTOM_LIST_AUTORELOAD:
                while True:
                    if not os.path.exists(self.TICKERS_LIST):
                        print(
                            f"Autoreload tickers cannot find {self.TICKERS_LIST} file. Will retry in 1 second."
                        )
                        time.sleep(1)
                    else:
                        break
                prevcoincount = len(self.tickers)

                self.tickers = list(set([line.strip() for line in open(self.TICKERS_LIST)] + [rchop(coin["symbol"], self.PAIR_WITH)for coin in self.coins_bought.values() + self.coins_short.values()]))

                if self.DEBUG:
                    print(
                        f"Reloaded tickers from {self.TICKERS_LIST} file. Prev coin count: {prevcoincount} | New coin count: {len(self.tickers)}"
                    )

        return self.get_price()

    def clear_profile_summary(self):
        curr_stats = {
            "bot_paused": False,
            "market_next_check_time": "",
            "started": "",
            "current_holds": 0,
            "slots": self.TRADE_SLOTS,
            "current_exposure": 0,
            "invstment_total": 0,
            "pair_with": self.PAIR_WITH,
            "realised_session_profit_incfees_perc": 0,
            "realised_session_profit_incfees_total": 0,
            "unrealised_session_profit_incfees_perc": 0,
            "unrealised_session_profit_incfees_total": 0,
            "session_profit_incfees_total_perc": 0,
            "session_profit_incfees_total": 0,
            "all_time_market_profit": 0,
            "bot_profit_perc": 0,
            "bot_profit": 0,
            "trade_wins": 0,
            "trade_losses": 0,
            "win_ratio": 0,
        }

        with open(self.profile_summary_file_path, "w") as file:
            json.dump(curr_stats, file, indent=4)

        self.notify_UI(reset=True)

    def clear_historical_records(self):
        self.db_interface.create_db()
        self.clear_profile_summary()

        # clear session info
        with open(self.bot_stats_file_path, "w") as file:
            file.write("")

        # try to clear all the coins bought by the bot if the file exists
        if os.path.isfile(self.coins_bought_file_path):
            with open(self.coins_bought_file_path, "w") as file:
                file.write("")

        if os.path.isfile(self.coins_short_file_path):
            with open(self.coins_short_file_path, "w") as file:
                file.write("")

        # if os.path.isfile(self.transactions_file_path):
        #     with open(self.transactions_file_path, 'w') as file:
        #         file.write(",".join(self.transactions_df_columns))

        if os.path.exists(self.HISTORY_LOG_FILE):
            with open(self.HISTORY_LOG_FILE, "w") as f:
                f.write("")

        if os.path.exists(self.LOG_FILE):
            with open(self.LOG_FILE, "w") as f:
                f.write("")

    def load_and_update_open_trades(self):
        if (os.path.isfile(self.coins_bought_file_path) and os.stat(self.coins_bought_file_path).st_size != 0):
            with open(self.coins_bought_file_path) as file:
                self.coins_bought = json.load(file)

            # UPDATE take_profit and stop_loss to the most recent parameters read from the config file
            if len(self.coins_bought) > 0:
                for k in self.coins_bought:
                    self.coins_bought[k]["TTP_TSL"] = False
                    if self.coins_bought[k]["TTP_TSL"] == False:
                        self.coins_bought[k]["stop_loss"] = -(self.coins_bought[k]["liquidationPrice"] - float(self.coins_bought[k]["bought_at"])) / float(self.coins_bought[k]["bought_at"]) * 100
                        self.coins_bought[k]["take_profit"] = self.TAKE_PROFIT

                        changes = {
                            "tp_perc": self.TAKE_PROFIT,
                            "sl_perc": self.STOP_LOSS,
                        }
                        self.db_interface.update_transaction_record(k, changes)

        if (os.path.isfile(self.coins_short_file_path) and os.stat(self.coins_short_file_path).st_size != 0):
            with open(self.coins_short_file_path) as file:
                self.coins_short = json.load(file)
            if len(self.coins_short) > 0:
                for k in self.coins_short:
                    self.coins_short[k]["TTP_TSL"] = False
                    if self.coins_short[k]["TTP_TSL"] == False:
                        self.coins_short[k]["stop_loss"] = (self.coins_short[k]["liquidationPrice"] - float(self.coins_short[k]["bought_at"])) / float(self.coins_short[k]["bought_at"]) * 100
                        self.coins_short[k]["take_profit"] = -self.TAKE_PROFIT

                        changes = {
                            "tp_perc": self.TAKE_PROFIT,
                            "sl_perc": self.STOP_LOSS,
                        }
                        self.db_interface.update_transaction_record(k, changes)

    def load_bot_stats(self):
        if (
            os.path.isfile(self.bot_stats_file_path)
            and os.stat(self.bot_stats_file_path).st_size != 0
        ):
            with open(self.bot_stats_file_path) as file:
                self.bot_stats = json.load(file)
                # load bot stats:
                try:
                    self.bot_started_datetime = datetime.strptime(
                        self.bot_stats["botstart_datetime"], "%Y-%m-%d %H:%M:%S.%f"
                    )
                except Exception as e:
                    print(
                        f"Exception on reading botstart_datetime from {self.bot_stats_file_path}. Exception: {e}"
                    )
                    self.bot_started_datetime = datetime.now()

                try:
                    self.total_capital = self.bot_stats["total_capital"]
                except Exception as e:
                    print(
                        f"Exception on reading total_capital from {self.bot_stats_file_path}. Exception: {e}"
                    )
                    self.total_capital = self.TRADE_SLOTS * self.TRADE_TOTAL

                self.historic_profit_incfees_perc = self.bot_stats[
                    "historicProfitIncFees_Percent"
                ]
                self.historic_profit_incfees_total = self.bot_stats[
                    "historicProfitIncFees_Total"
                ]
                self.trade_wins = self.bot_stats["tradeWins"]
                self.trade_losses = self.bot_stats["tradeLosses"]
                try:
                    self.market_startprice = self.bot_stats["market_startprice"]
                except:
                    pass

                if self.total_capital != self.total_capital_config:
                    self.historic_profit_incfees_perc = (
                        self.historic_profit_incfees_total / self.total_capital_config
                    ) * 100
        if self.REINVEST_PROFITS:
            if self.total_capital == 0:
                self.TRADE_TOTAL = self.total_capital_config / self.TRADE_SLOTS
            else:
                self.TRADE_TOTAL = self.total_capital / self.TRADE_SLOTS

    def track_module_status(self):
        """
        This module created by Essam to track modules run in other threads for errors
        This is important to keep track of any errors
        stackoverflow.com/questions/22125256/python-multiprocessing-watch-a-process-and-restart-it-when-fails
        """
        module_status = []
        module_status.append(
            {
                "signal": "KucoinDetectMoonings",
                "status": "active",
                "updated": str(datetime.now()).split(".")[0],
                "message": "working",
            }
        )

        for p in self.signalthreads:
            # if p.exitcode is None and not p.is_alive():  # Not finished and not running
            #     # Do your error handling and restarting here assigning the new process to processes[n]
            #     print(p.name, ' is gone as if never born!')
            if p.exitcode is not None:  # and p.exitcode < 0:
                module_status.append(
                    {
                        "signal": p.name,
                        "status": "not active",
                        "updated": str(datetime.now()).split(".")[0],
                        "message": f"Process {p.name} ended with an error or a terminate: {p.exitcode}",
                    }
                )
                print(
                    f"Process {p.name} ended with an error or a terminate: {p.exitcode}"
                )
                # Handle this either by restarting or delete the entry so it is removed from list as for else
            elif p.is_alive():
                module_status.append(
                    {
                        "signal": p.name,
                        "status": "active",
                        "updated": str(datetime.now()).split(".")[0],
                        "message": "working",
                    }
                )

                # print(a, 'finished')
                # p.join()  # Allow tidyup
                # del processes[n]  # Removed finished items from the dictionary

        # save the coins in value json file in the same directory
        with open(self.signals_status_file_name, "w") as file:
            json.dump(module_status, file, indent=4)

    def run(self):
        # clear all historical data and open trades
        if self.CLEAN_START:
            self.clear_historical_records()

        sys.stdout = St_ampe_dOut()

        # Load creds for correct environment
        parsed_creds = load_config(self.creds_file)
        access_key, secret_key, passphrase = load_correct_creds(parsed_creds)

        if self.MSG_DISCORD:
            self.DISCORD_WEBHOOK = parsed_creds['discord']['DISCORD_WEBHOOK']

        # Authenticate with the client, Ensure API key is good before continuing
        if self.AMERICAN_USER:
            self.client.user  = User(key=access_key, secret=secret_key, passphrase=passphrase, url='https://api-futures.kucoin.com')
            self.client.market = Market(key=access_key, secret=secret_key, passphrase=passphrase, url='https://api-futures.kucoin.com')
            self.client.trade = Trade(key=access_key, secret=secret_key, passphrase=passphrase, url='https://api-futures.kucoin.com')
        else:
            self.client.user  = User(key=access_key, secret=secret_key, passphrase=passphrase, url='https://api-futures.kucoin.com')
            self.client.market = Market(key=access_key, secret=secret_key, passphrase=passphrase, url='https://api-futures.kucoin.com')
            self.client.trade = Trade(key=access_key, secret=secret_key, passphrase=passphrase, url='https://api-futures.kucoin.com')
        # this will stop the script from starting, and display value helpful error.

        self.bot_started_datetime = datetime.now()
        self.total_capital_config = self.TRADE_SLOTS * self.TRADE_TOTAL

        self.load_bot_stats()
        # rolling window of prices; cyclical queue
        self.historical_prices = [None] * (self.TIME_DIFFERENCE * self.RECHECK_INTERVAL)
        self.hsp_head = -1

        # prevent including value coin in volatile_coins if it has already appeared there less than TIME_DIFFERENCE
        # minutes ago
        self.volatility_cooloff = {}

        # try to load all the coins bought by the bot if the file exists and is not empty
        # if saved coins_bought json file exists and it's not empty then load it
        self.load_and_update_open_trades()

        # if os.path.isfile(self.transactions_file_path) and os.stat(self.transactions_file_path).st_size != 0:
        #     self.transactions_df = pd.read_csv(self.transactions_file_path)

        print(f"{txcolors.WARNING}Press Ctrl-C for more options / to stop the bot{txcolors.DEFAULT}")

        if not self.TEST_MODE:
            if not self.notimeout:  # if notimeout skip this (fast for dev tests)
                print(
                    "WARNING: Test mode is disabled in the configuration, you are using _LIVE_ funds."
                )
                print(
                    "WARNING: Waiting 5 seconds before live trading as value security measure!"
                )
                time.sleep(5)

        self.remove_external_signals("buy")
        self.remove_external_signals("sell")
        self.remove_external_signals("pause")

        # load signalling modules
        self.signalthreads = []
        try:
            if len(self.SIGNALLING_MODULES) > 0:
                for module in self.SIGNALLING_MODULES:
                    print(f"Starting {module}")
                    self.mymodule[module] = importlib.import_module(module)
                    # t = threading.Thread(target=mymodule[module].do_work, args=())
                    t = multiprocessing.Process(
                        target=self.mymodule[module].do_work, args=()
                    )
                    t.name = module
                    t.daemon = True
                    t.start()

                    # add process to value list. This is so the thread can be terminated at value later time
                    self.signalthreads.append(t)

                    time.sleep(2)
            else:
                print(f"No modules to load {self.SIGNALLING_MODULES}")
        except Exception as e:
            if str(e) == "object of type 'NoneType' has no len()":
                print(f"No external signal modules running")
            else:
                print(f"Loading external signals exception: {e}")

        # seed initial prices
        # get_price()
        self.wrap_get_price()
        TIMEOUT_COUNT = 0
        READ_CONNECTERR_COUNT = 0

        while self.is_bot_running:
            try:
                orders, last_price, volume = self.buy()
                self.update_portfolio(orders, last_price, volume)

                coins_sold, coins_long = self.sell_coins()
                self.remove_from_portfolio(coins_sold, coins_long)
                self.sell_specific_coin = False

                # reporting and health checks
                self.track_module_status()
                self.update_bot_stats()
                self.report_profile_summary(last_price)

            except ReadTimeout as rt:
                TIMEOUT_COUNT += 1
                print(
                    f"We got value timeout error from Kucoin. Re-loop. Connection Timeouts so far: {TIMEOUT_COUNT}"
                )
            except ConnectionError as ce:
                READ_CONNECTERR_COUNT += 1
                print(
                    f"We got value connection error from Kucoin. Re-loop. Connection Errors so far: {READ_CONNECTERR_COUNT}"
                )
            except KeyboardInterrupt as ki:
                # stop external signal threads
                self.stop_signal_threads()

                # ask user if they want to sell all coins
                while True:
                    # print_notimestamp(f'{txcolors.WARNING}\n--|  Binance Bot Menu  |--{txcolors.DEFAULT}')
                    self.print_notimestamp(f"\n[1] Exit (default option)")
                    self.print_notimestamp(f"\n[2] Close All Coins")
                    self.print_notimestamp(f"\n[3] Close A Specific Coin")
                    self.print_notimestamp(f"\n[4] Resume Bot")
                    self.print_notimestamp(
                        f"\n{txcolors.WARNING}Please choose one of the above menu options ([1]. Exit):{txcolors.DEFAULT}"
                    )
                    menuoption = input()

                    if menuoption == "1" or menuoption == "":
                        self.print_notimestamp("\n")
                        sys.exit(0)
                    elif menuoption == "2":
                        self.print_notimestamp("\n")
                        self.sell_all("Sell All Coins menu option chosen!")
                        self.print_notimestamp("\n")
                    elif menuoption == "3":
                        while not menuoption.upper() == "N":
                            # setup table
                            my_table = PrettyTable()
                            my_table.field_names = [
                                "Symbol",
                                "Volume",
                                "Bought At",
                                "Now At",
                                "TP %",
                                "SL %",
                                "Change % (ex fees)",
                                "Profit $",
                                "Time Held",
                            ]
                            my_table.align["Symbol"] = "l"
                            my_table.align["Volume"] = "r"
                            my_table.align["Bought At"] = "r"
                            my_table.align["Now At"] = "r"
                            my_table.align["TP %"] = "r"
                            my_table.align["SL %"] = "r"
                            my_table.align["Change % (ex fees)"] = "r"
                            my_table.align["Profit $"] = "r"
                            my_table.align["Time Held"] = "l"

                            # get latest prices
                            last_price = self.wrap_get_price()

                            # display coins to sell
                            # print('\n')
                            for coin in self.coins_bought:
                                time_held = timedelta(
                                    seconds=datetime.now().timestamp()
                                    - int(
                                        str(self.coins_bought[coin]["timestamp"])[:10]
                                    )
                                )
                                change_perc = (
                                    (
                                        float(last_price[coin]["price"])
                                        - float(self.coins_bought[coin]["bought_at"])
                                    )
                                    / float(self.coins_bought[coin]["bought_at"])
                                    * 100
                                )
                                ProfitExFees = float(last_price[coin]["price"]) - float(
                                    self.coins_bought[coin]["bought_at"]
                                )
                                my_table.add_row(
                                    [
                                        f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{coin}{txcolors.DEFAULT}",
                                        f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(self.coins_bought[coin]['volume']):.6f}{txcolors.DEFAULT}",
                                        f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(self.coins_bought[coin]['bought_at']):.6f}{txcolors.DEFAULT}",
                                        f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(last_price[coin]['price']):.6f}{txcolors.DEFAULT}",
                                        f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(self.coins_bought[coin]['take_profit']):.4f}{txcolors.DEFAULT}",
                                        f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(self.coins_bought[coin]['stop_loss']):.4f}{txcolors.DEFAULT}",
                                        f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{change_perc:.4f}{txcolors.DEFAULT}",
                                        f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{self.calc_profit(coin, change_perc):.6f}{txcolors.DEFAULT}",
                                        f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{str(time_held).split('.')[0]}{txcolors.DEFAULT}",
                                    ]
                                )

                            my_table.sortby = "Change % (ex fees)"
                            if len(my_table._rows) > 0:
                                self.print_notimestamp(my_table)
                            else:
                                break

                            # ask for coin to sell
                            self.print_notimestamp(
                                f"{txcolors.WARNING}\nType in the Symbol you wish to sell, including pair (i.e. "
                                f"BTCUSDT) or type N to return to Menu (N)?{txcolors.DEFAULT}"
                            )
                            menuoption = input()
                            if menuoption == "":
                                break

                            self.sell_a_specific_coin(menuoption.upper())
                    elif menuoption == "4":
                        self.print_notimestamp(
                            f"{txcolors.WARNING}\nResuming the bot...\n\n{txcolors.DEFAULT}"
                        )
                        #self.start_signal_threads() need to add this
                        break

        if not self.is_bot_running:
            if self.SESSION_TPSL_OVERRIDE:
                print(f"")
                print(f"")
                print(
                    f"{txcolors.WARNING}{self.session_tpsl_override_msg}{txcolors.DEFAULT}"
                )

                self.sell_all(self.session_tpsl_override_msg, True)
                sys.exit(0)

            else:
                print(f"")
                print(f"")
                print(f"Bot terminated for some reason.")


if __name__ == "__main__":

    # Load arguments then parse settings
    bot = KucoinVolatilityBot()
    bot.run()
