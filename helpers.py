import json
import numpy as np
from math import modf, log10, floor
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re

from pprint import pprint as pp


def delta_add_rule(user, coin, value, once=False):
    current_value = get_current_value(coin)
    # Single watchvalues:
    # bitcoin =50000
    if v := re.fullmatch(r'=(\d+(?:\.\d+)?)', value):
        rule_value = v[0]
        watch_value = float(v[0][1:])
        once = True
    # bitcoin +1000
    elif v := re.fullmatch(r'([-+]\d+(?:\.\d+)?)', value):
        rule_value = v[0]
        watch_value = current_value + float(v[0])
    # bitcoin +20%
    elif v := re.fullmatch(r'([-+])(\d+(?:\.\d+)?)%', value):
        rule_value = v[0]
        watch_value = current_value * (100 + float(v[0][:-1])) / 100
    # Double watchvalues:
    # bitcoin +-1000
    elif v := re.fullmatch(r'(?:((?:\+\-)|(?:\-\+)|(?:±))?\d+(?:\.\d+)?)', value):
        rule_value = v[0]
        rule_value = '±' + rule_value.lstrip('+-±')
        watch_value = [None] * 2
        watch_value[0] = current_value - float(rule_value[1:])
        watch_value[1] = current_value + float(rule_value[1:])
    # bitcoin +-5%
    elif v := re.fullmatch(r'(?:((?:\+\-)|(?:\-\+)|(?:±))?\d+(?:\.\d+)?)%', value):
        rule_value = v[0]
        rule_value = '±' + rule_value.lstrip('+-±')
        watch_value = [None] * 2
        watch_value[0] = current_value * (100 - float(rule_value[1:-1])) / 100
        watch_value[1] = current_value * (100 + float(rule_value[1:-1])) / 100
    else:
        return 'wrong_input'

    if type(watch_value) == list:
        for i, value in enumerate(watch_value):
            if value < 0:
                watch_value[i] = 0
            else:
                watch_value[i] = format_v(value, current_value)
        for value in watch_value:
            if value == current_value:
                return 'small_value'

    else:
        watch_value = format_v(watch_value, current_value)
        if watch_value == current_value:
            return 'small_value'

    from_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    record = [coin, current_value, rule_value, watch_value, from_time]
    if once:
        record.append('once')

    user.watchlist.append(record)
    user.watchlist.sort()

    db.save(user)

    return record

def format_v(num, to_current=False):
    dec_part, int_part = modf(num)
    l = len(str(abs(int_part))[:-2]) if int_part != 0 else 0
    dec_part = round(dec_part, 15 - l)
    if dec_part == 0:
        value = int(int_part)
    else:
        value = int_part + dec_part
        if to_current:
            dec_part, int_part = modf(to_current)
            l0 = len(str(abs(int_part))[:-2]) if int_part != 0 else 0
            l = len(np.format_float_positional(round(dec_part, 15 - l0))[2:])
            value = round(value, 2 + l)
    return value

def get_data_by_stock_list(coins):
    res = []
    for coin in coins:
        coin = coin.lower()
        for names in stock_coin_list.values():
            if coin in [name.lower() for name in names.values()]:
                res.append(names['id'])
    if res:
        try:
            res = coindata.dataframe(res)
        except Exception as e:
            raise
        finally:
            return res

def get_data_by_stock_list_strict(coins):
    res = []
    coins = [coin.lower() for coin in coins]
    for coin in coins:
        if coin in stock_coin_list:
            res.append(stock_coin_list[coin])
    if res:
        res = coindata.dataframe(res)
        return res

def get_data_user_coins(user_id, names=None):
    res = {}
    if names:
        for name in names:
            name = name.lower()
            coins = get_coins_by_wide_name(name, user_id)
            for coin in coins:
                res[coin] = data[coin]
    else:
        for coin in users[user_id].coins:
            res[coin] = data[coin]
    return res

def get_strict_name(coin):
    for coin_listed in stock_coin_list.values():
        for name in coin_listed.values():
            if coin == name.lower():
                return coin_listed['id']

def get_coins_by_wide_name(name, user_id=False):
    res = []
    name = name.lower()
    if not user_id:
        for stock_names in stock_coin_list.values():
            if name in [stock_name.lower() for stock_name in stock_names.values()]:
                res.append(stock_names['id'])
    else:
        for coin in users[user_id].coins:
            if name in [coin, data[coin]['name'].lower(), data[coin]['code'].lower()]:
                res.append(coin)
    print(f'{name}:', res)
    return res

def get_coin_repr_name(coin):
    return stock_coin_list[coin]['name']

def get_coin_code_name(coin):
    return stock_coin_list[coin]['symbol']

def to_digit(value):
    value = float(value)
    return int(value) if int(value) == value else value

def get_current_value(coin):
    value = data[coin]['current_price']
    return to_digit(value)

def get_not_watchlisted_tokens(user_id):
    res = []
    user_coins = users[user_id].coins
    user_watchlist = users[user_id].watchlist
    watchlisted_tokens = set([rule[0] for rule in user_watchlist])
    for user_coin in user_coins:
        if user_coin not in watchlisted_tokens:
            res.append(user_coin)
    res.sort()
    return res

def check_coin_limit(update, context):
    user_id = update.effective_user.id
    if len(users[user_id].coins) >= 20:
        update.effective_message.reply_text("Sorry!\nBot allows to add up to maximum 20 coins currently.")
        print('Coin limit exceeded!')
        return False
    return True

def get_time_delta(time):
    res = ''
    dtime = relativedelta(datetime.now(), datetime.strptime(time, '%Y-%m-%d %H:%M:%S'))
    timeframes = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
    for i, timeframe in enumerate(timeframes):
        if val := eval(f'dtime.{timeframe}'):
            res += f'{val} {timeframe}'
            if val == 1:
                res = res[:-1]
            if len(timeframes) - 1 > i:
                if val := eval(f'dtime.{timeframes[i + 1]}'):
                    res += f' {val} {timeframes[i + 1]}'
                    if val == 1:
                        res = res[:-1]
            return res

def is_json(expression):
    try:
        json.loads(expression)
    except ValueError:
        return False
    return True

def filter_similar(l):
    l = l[::-1]
    [l.remove(i) for i in l[:] if l.count(i) != 1]
    return l[::-1]
