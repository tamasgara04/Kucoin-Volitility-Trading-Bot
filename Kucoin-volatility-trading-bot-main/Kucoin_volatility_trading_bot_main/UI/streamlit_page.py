import json
from types import SimpleNamespace

from load_css import local_css
from datetime import datetime
import pandas as pd
from web_layout.utils import *
from web_layout.data import *
from sqlalchemy import create_engine
from dateutil.parser import parse
from update_UI import update

import pathlib
import os

current_directory = os.path.dirname(os.path.abspath(__file__))
signals_directory = os.path.join(current_directory, '..', 'signals')

user_data_path = str(pathlib.Path(__file__).parent.parent.parent.as_posix())

#@st.cache_resource(allow_output_mutation=True)
def get_db_connection():
    database = "transactions.db"
    try:
        return create_engine(f'sqlite:///../../user_data/{database}')
    except (Exception) as error:
        st.error((f"Error while connecting to {database}: ", error))
        print(f"Error while connecting to {database}: ", error)
        return None

def sell(coin):
    file_name = 'sell_specific_coin.sell'
    file_path = os.path.join(signals_directory, file_name)
    with open(file_path, "w") as file:
        file.write(f"{coin}\n")

# path to the saved transactions history
profile_summary_file = user_data_path +"/user_data/"+ "profile_summary.json"

with open(profile_summary_file) as f:
    profile_summary = json.load(f, object_hook=lambda d: SimpleNamespace(**d))

st.set_page_config(
    page_title = f'{profile_summary.unrealised_session_profit_incfees_total}$ Wavetrend',
    page_icon = '💎',
    layout = 'wide',
)


local_css("css/style.css")

st.markdown("<h1 style='text-align: center; color: Green;'>Tamas Kucoin Trading Bot 💰</h1>", unsafe_allow_html=True)

with st.sidebar:
    coin_to_sell = st.text_input("Sell coin:")
    pwd = st.text_input("Password", type="password")
    if st.button("Sell"):
        if pwd == "tamastamas":
            sell(coin_to_sell)
            st.success("Login successful!")
        else:
            st.error("Invalid password")
     

st.markdown("### Current Session")
kpi21, kpi23 = st.columns(2)
with kpi21:
    try:
        started = profile_summary.started
        start_date = datetime.fromisoformat(profile_summary.started)
        run_for = str(datetime.now() - start_date).split('.')[0]
    except:
        started = "NA"
        run_for = "NA"
    st.markdown(
        f"<h4 style='text-align: left; margin-left: 30px;'> Started: {started.split('.')[0]} | Running for: {run_for}</h4>",
        unsafe_allow_html=True)

    market_perf_color = 'red' if profile_summary.all_time_market_profit <= 0 else 'green'
    market_link = f'<value style="color: {market_perf_color}; text-decoration: none;" target="_blank" href="https://www.binance.com/en/trade/BTCUSDT">' +  str(profile_summary.all_time_market_profit) + '</value>'
    st.markdown(
        f"<h4 style='text-align: left; margin-left: 30px;'> Market Performance: <span style='text-align: center; color: {market_perf_color};'>{market_link}% </span> <span> (Since STARTED)</span></h3>",
        unsafe_allow_html=True)
    st.markdown(
        f"<h4 style='text-align: left;  margin-left: 30px;'>Current Trades: {profile_summary.current_holds}/{profile_summary.slots} "
        f"({profile_summary.current_exposure}/{profile_summary.invstment_total} {profile_summary.pair_with})</h4>",
        unsafe_allow_html=True)

with kpi23:
    realised_color = money_color(profile_summary.realised_session_profit_incfees_perc)

    st.markdown(
        f"<h4 style='text-align: left;  margin-left: 30px;'> Realised: &nbsp&nbsp&nbsp <span style='text-align: center; color: {realised_color};'>{profile_summary.realised_session_profit_incfees_perc:.5f}% Est: ${profile_summary.realised_session_profit_incfees_total} {profile_summary.pair_with}</span></h3>",
        unsafe_allow_html=True)


    unrealised_color = money_color(profile_summary.unrealised_session_profit_incfees_perc)
    st.markdown(f"<h4 style='text-align: left;  margin-left: 30px;'> Unrealised: <span style='text-align: center; color: {unrealised_color};'>{profile_summary.unrealised_session_profit_incfees_perc:.5f}% Est: ${profile_summary.unrealised_session_profit_incfees_total} {profile_summary.pair_with}</span></h3>", unsafe_allow_html=True)

    total_color = money_color(profile_summary.session_profit_incfees_total_perc)
    st.markdown(f"<h4 style='text-align: left;  margin-left: 30px;'> Total: &nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp <span style='text-align: center; color: {total_color};'>{profile_summary.session_profit_incfees_total_perc:.5f}% Est: ${profile_summary.session_profit_incfees_total} {profile_summary.pair_with}</span></h3>", unsafe_allow_html=True)

st.markdown("### All Time Data")
kpi11, kpi12 = st.columns(2)
with kpi11:
    bot_perf_color = 'red' if profile_summary.bot_profit_perc < 0 else 'green'
    st.markdown(f"<h4 style='text-align: left; margin-left: 30px;'> Bot Performance: <span style='text-align: center; color: {bot_perf_color};'>{profile_summary.bot_profit_perc}%</span> <span> Est: </span><span style='color: {bot_perf_color}';>${profile_summary.bot_profit} {profile_summary.pair_with}</span></h3>", unsafe_allow_html=True)

with kpi12:
    st.markdown(
        f"<h4 style='text-align: left;  margin-left: 30px; padding-right: 0px'> Completed Trades: {profile_summary.trade_wins + profile_summary.trade_losses} (Wins: <span style='color:green'>{profile_summary.trade_wins}</span>, Losses: <span style='color:red'>{profile_summary.trade_losses} </span>) | Win Ratio: {profile_summary.win_ratio}%</h4>",
        unsafe_allow_html=True)

st.markdown("<hr/>",unsafe_allow_html=True)


try:
	transactions_df = pd.read_sql_query('select * from transactions', get_db_connection())
	transactions_df ['time_held'] =  pd.to_timedelta(transactions_df['time_held']).dt.floor(freq='s').astype('string')
	transactions_df['buy_time'] = pd.to_datetime(transactions_df['buy_time'])
	transactions_df['sell_time'] = pd.to_datetime(transactions_df['sell_time'])

	open_columns = ["id", "symbol", "change_perc", "profit_dollars", "bought_at", "now_at", "volume",  "buy_time", "time_held", "tp_perc", "sl_perc", "buy_signal"]
	open_trades = transactions_df.loc[transactions_df['closed'] == 0, open_columns]


	closed_trades_columns = ["id", "symbol", "change_perc", "profit_dollars", "bought_at", "sold_at", "volume", "buy_time", "sell_time", "time_held", "tp_perc", "sl_perc", "buy_signal", "sell_reason"]
	closed_trades = transactions_df.loc[transactions_df['closed'] == 1, closed_trades_columns]

	st.markdown(f"### Open Trades (Winning: <span style='color:green;'>{open_trades[open_trades.change_perc > 0].change_perc.count()}</span> | Losing: <span style='color:red;'>{open_trades[open_trades.change_perc <= 0].change_perc.count()}</span>) ",
			unsafe_allow_html=True)
	report_open_trades(open_trades)
	st.markdown("### **Closed Trades**")
	report_closed_trades(closed_trades)
except Exception as e:
	pass
