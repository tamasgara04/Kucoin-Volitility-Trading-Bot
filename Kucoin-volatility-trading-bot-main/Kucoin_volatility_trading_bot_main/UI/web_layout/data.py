from st_aggrid import GridOptionsBuilder, JsCode, AgGrid

cellsytle_jscode = JsCode("""
function(params) {
    if (params.value <= 0) {
        return {
            'color': 'white',
            'background-color': '#f44336'
        }
    } else {
        return {
            'color': 'white',
            'background-color': '#4caf50'
        }
    }
};
""")

coin_page_link = JsCode('''
    function(params){
        var test = '<a target="_blank" href="https://www.tradingview.com/chart/?symbol=BINANCE:' + params.value + '">' + params.value + '</a>';
        test = params.value;
        return test;
        }
    ''')
#return '<a target="_blank" href="https://www.tradingview.com/chart/?symbol=BINANCE:' + params.value + '">' + params.value + '</a>'
datetime_width = 125
reason_width = 125
symbol_width = 95
volume_width = 100
price_width  =100
dollar_width = 90
change_width = 95
tpsl_width = 65

def report_open_trades(open_trades):
    open_trades['id'] = list(range(1, len(open_trades) + 1))

    gb = GridOptionsBuilder.from_dataframe(open_trades)

    gb.configure_column("change_perc", cellStyle=cellsytle_jscode)
    gb.configure_column("profit_dollars", cellStyle=cellsytle_jscode)
    gb.configure_column("change_perc", type=["numericColumn","numberColumnFilter","customNumericFormat"], precision=2)
    # gb.configure_column("buy_time", type=["dateColumnFilter"], precision=0)
    gb.configure_column("tp_perc", type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=2)
    gb.configure_column("sl_perc", type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=2)
    gb.configure_column("volume", type=["numericColumn","numberColumnFilter","customNumericFormat"], precision=6)
    gb.configure_column("bought_at", type=["numericColumn","numberColumnFilter","customNumericFormat"], precision=6)
    gb.configure_column("now_at", type=["numericColumn","numberColumnFilter","customNumericFormat"], precision=6)
    gb.configure_column("profit_dollars", type=["numericColumn","numberColumnFilter","customNumericFormat"], precision=6)

    gb.configure_column("symbol", cellRenderer = coin_page_link)


    gb.configure_column("id", header_name="Id", width=40)
    gb.configure_column("change_perc", header_name="Change %", width=change_width)
    gb.configure_column("buy_time", header_name="Buy Time", width=datetime_width)
    gb.configure_column("symbol", header_name="Symbol", width=symbol_width)
    gb.configure_column("volume", header_name="Volume", width=volume_width)
    gb.configure_column("bought_at", header_name="Bought at", width=price_width)
    gb.configure_column("now_at", header_name="Now at", width=price_width)
    gb.configure_column("symbol", header_name="Symbol")
    gb.configure_column("profit_dollars", header_name="Profit $", aggFunc='sum', width=dollar_width)
    gb.configure_column("time_held", header_name="Time held", width=datetime_width)
    gb.configure_column("tp_perc", header_name="TP %", width=tpsl_width)
    gb.configure_column("sl_perc", header_name="SL %", width=tpsl_width)
    gb.configure_column("buy_signal", header_name="Buy Signal", width=datetime_width)

    # customize gridOptions
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum')

    gb.configure_pagination()
    gridOptions = gb.build()
    grid_return = AgGrid(open_trades, fit_columns_on_grid_load=False, gridOptions=gridOptions, allow_unsafe_jscode=True, reload_data=False, height=400)
    # open_trades = grid_return['data']

def report_closed_trades(closed_trades):
    closed_trades['id'] = list(range(1, len(closed_trades)+1))
    gb = GridOptionsBuilder.from_dataframe(closed_trades)
    gb.configure_column("change_perc", type=["numericColumn","numberColumnFilter","customNumericFormat"], precision=2)
    gb.configure_column("change_perc", cellStyle=cellsytle_jscode)
    gb.configure_column("tp_perc", type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=2)
    gb.configure_column("sl_perc", type=["numericColumn", "numberColumnFilter", "customNumericFormat"], precision=2)
    gb.configure_column("volume", type=["numericColumn","numberColumnFilter","customNumericFormat"], precision=6)
    gb.configure_column("bought_at", type=["numericColumn","numberColumnFilter","customNumericFormat"], precision=6)
    gb.configure_column("profit_dollars", type=["numericColumn","numberColumnFilter","customNumericFormat"], precision=6)
    gb.configure_column("profit_dollars", cellStyle=cellsytle_jscode)

    gb.configure_column("symbol", cellRenderer=coin_page_link)

    gb.configure_column("id", header_name="Id", width =40)
    gb.configure_column("change_perc", header_name="Profit %", width = change_width)
    gb.configure_column("buy_time", header_name="Buy Time", width =datetime_width)
    gb.configure_column("sell_time", header_name="Sell Time", width =datetime_width)

    gb.configure_column("symbol", header_name="Symbol", groupable=True, width = symbol_width)
    gb.configure_column("volume", header_name="Volume",width = volume_width)
    gb.configure_column("bought_at", header_name="Bought at", width = price_width)
    gb.configure_column("sold_at", header_name="Sold at", width = price_width)
    gb.configure_column("symbol", header_name="Symbol")
    gb.configure_column("profit_dollars", header_name="Profit $", width=dollar_width)
    gb.configure_column("time_held", header_name="Time held", width=datetime_width)
    gb.configure_column("tp_perc", header_name="TP %", width = tpsl_width)
    gb.configure_column("sl_perc", header_name="SL %", width = tpsl_width)
    gb.configure_column("buy_signal", header_name="Buy Signal", width=reason_width)
    gb.configure_column("sell_reason", header_name="Sell Reason", width=reason_width)

    gb.configure_pagination()

    gridOptions = gb.build()
    grid_return = AgGrid(closed_trades, fit_columns_on_grid_load=False, gridOptions=gridOptions, allow_unsafe_jscode=True, reload_data=False, height=400)
    # open_trades = grid_return['data']
