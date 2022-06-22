import coindata
import logging
from math import modf, log10, floor

from pprint import pprint as pp

from helpers import (get_current_value, get_time_delta, get_coin_repr_name,
        delta_add_rule)

import time

def update_data_daemon(data, coins_in_use):
    time.sleep(60)
    while True:
        update_data(data, coins_in_use)
        time.sleep(60)

def update_data(data, coins_in_use):
    logging.info('update_data:')
    try:
        new_data = coindata.dataframe(coins_in_use)
        data.clear()
        data.update(new_data)
        logging.info(f'\t{coins_in_use}')
    except Exception as e:
        logging.exception('update_data')

def update_coins_in_use(users, coins_in_use, data):
    control = coins_in_use.copy()
    new_coins_in_use = []
    for user_coins in [user.coins for user in users.values()]:
        for coin in user_coins:
            new_coins_in_use.append(coin)
    coins_in_use.clear()
    coins_in_use.extend(sorted(set(new_coins_in_use)))
    if (set(coins_in_use) | set(control)) != set(control):
        update_data(data, coins_in_use)

def update_stock_coin_list_daemon(stock_coin_list):
    while True:
        try:
            new_stock_coin_list = coindata.get_coins_list()
            stock_coin_list.clear()
            stock_coin_list.update({coin['id']:coin for coin in new_stock_coin_list})
        except Exception:
            logging.exception("update_stock_coin_list_daemon")
        finally:
            time.sleep(60*60*6)

def check_watchlist_daemon(bot, users):
    time.sleep(10)
    while True:
        for user in users.values():
            user_id = user.id
            if user.watchlist:
                for record in user.watchlist.copy():
                    rule_done = False
                    if record[-1] == 'once':
                        once = True
                        coin, start_value, rule, watch_value, from_time = record[:-1]
                    else:
                        once = False
                        coin, start_value, rule, watch_value, from_time = record

                    if coin not in user.coins:
                        continue

                    current_value = get_current_value(coin)

                    # Estimate rule type
                    ar = ['⬆','⬇']
                    if type(watch_value) == list:
                        if current_value <= watch_value[0]:
                            arrow = ar[1]
                            rule_done = True
                        elif current_value >= watch_value[1]:
                            arrow = ar[0]
                            rule_done = True

                    else:
                        if rule[0] == '-' and current_value <= watch_value:
                            arrow = ar[1]
                            rule_done = True

                        elif rule[0] == '+' and current_value >= watch_value:
                            arrow = ar[0]
                            rule_done = True

                        elif rule[0] == '=':
                            if (current_value <= watch_value and watch_value <= start_value):
                                arrow = ar[1]
                                rule_done = True
                            elif (current_value >= watch_value and watch_value >= start_value):
                                arrow = ar[0]
                                rule_done = True

                    if rule_done:

                        # Add from_time notice
                        if rule[-1] == '%' or rule[0] == '=':
                            dvalue = ((current_value - start_value) / start_value) * 100
                            if dvalue >= 10:
                                dvalue = round(dvalue)
                            else:
                                print('%', current_value, start_value, dvalue)
                                dvalue = round(dvalue, 1-int(floor(log10(abs(dvalue)))))
                                if dvalue == int(dvalue):
                                    dvalue = int(dvalue)
                            dvalue = '{0:+}%'.format(dvalue)
                        else:
                            dvalue = current_value - start_value
                            if dvalue >= 10:
                                dvalue = round(dvalue)
                            else:
                                print('d', current_value, start_value, dvalue)
                                dvalue = round(dvalue, 1-int(floor(log10(abs(dvalue)))))
                                if dvalue == int(dvalue):
                                    dvalue = int(dvalue)
                            dvalue = '{0:+}'.format(dvalue)

                        dtime = get_time_delta(from_time)

                        name = get_coin_repr_name(coin)
                        message = f'{name}: {arrow}{current_value}'
                        message += f'\n{dvalue} in {dtime}\n({start_value} {rule})'
                        bot.send_message(chat_id=user_id, text=message, parse_mode='html')
                        user.watchlist.remove(record)
                        if not once:
                            delta_add_rule(user, coin, rule)
                        else:
                            db.save(user)

        time.sleep(60)
