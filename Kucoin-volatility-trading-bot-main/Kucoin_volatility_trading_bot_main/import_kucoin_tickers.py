import os
import threading
import time
import requests
from kucoin_futures.client import Market
import yaml
from globals import user_data_path
from helpers.handle_creds import load_correct_creds
from helpers.parameters import load_config


DEFAULT_CREDS_FILE = user_data_path + "creds.yml"
parsed_creds = load_config(DEFAULT_CREDS_FILE)

access_key, secret_key, passphrase = load_correct_creds(parsed_creds)

kclient = Market(key=access_key, secret=secret_key, passphrase=passphrase, url='https://api-futures.kucoin.com')

# load yml file to dictionary
keys = yaml.safe_load(open(DEFAULT_CREDS_FILE))
TICKERS = "tickerlists/tickers_kucoin_USDT.txt"
TIME_TO_WAIT = 60


def get_kucoin():
    try:
        print("Get Kucoin")
        data = kclient.get_contracts_list()

        PAIRS_WITH = "USDT"
        li = []            
        for item in data:   
            if item["rootSymbol"] == PAIRS_WITH:
                li.append(item["symbol"])
        
        ignore = [
            "UP",
            "DOWN",
            "BEAR",
            "BULL",
            "USD",
            "BUSD",
            "EUR",
            "DAI",
            "TUSD",
            "GBP",
            "WBTC",
            "STETH",
            "CETH",
            "PAX",
        ]
        filtered = [x for x in li if not (x.endswith("USD") | x.startswith(tuple(ignore)))]

        # filtered = [sub[: -4] for sub in symbols]   # without USDT

        return filtered
    except Exception as e:
        return None


def get_cryptorank():
    print("Get Cryptorank")
    url = "https://api.cryptorank.io/v1/currencies"
    payload = {"api_key": keys["cryptorank"]["api_key"], "limit": 300}  # 148=100
    # 370=200
    req = requests.get(url, params=payload)
    dataj = req.json()["data"]
    li = [item.get("symbol") for item in dataj]
    ignore_usd = [x for x in li if not (x.endswith("USD") | x.startswith("USD"))]
    list1 = ["WBTC", "UST", "USDD", "DAI", "STETH", "CETH", "GBP", "PAX"]
    filtered = [x for x in ignore_usd if all(y not in x for y in list1)]
    filtered = [x + "USDT" for x in filtered]
    return filtered


def get_kucoin_tickerlist():
    ticker_list = list(set(get_kucoin()))
    ticker_list.sort()
    length = len(ticker_list)

    with open(f"{TICKERS}", "w") as output:
        for item in ticker_list:
            output.write(str(item) + "\n")
    return length


def do_work():
    print(os.getcwd())
    while True:
        try:
            print(os.getcwd())
            if not os.path.exists(TICKERS):
                with open(TICKERS, "w") as f:
                    f.write("")

            if not threading.main_thread().is_alive():
                exit()
            print("Importing kucoin tickerlist")
            print(
                f"Imported {TICKERS}: {get_kucoin_tickerlist()} coins. Waiting {TIME_TO_WAIT} minutes for next import."
            )

            time.sleep((TIME_TO_WAIT * 60))
        except Exception as e:
            print(f"Exception do_work() import kucoin tickerlist: {e}")
            continue
        except KeyboardInterrupt as ki:
            print(ki)
            exit()
