from telegram.ext import (Updater, CommandHandler, MessageHandler,
        ConversationHandler, Filters, CallbackQueryHandler, Defaults, PicklePersistence)
from telegram import (ParseMode, InlineKeyboardButton,
        InlineKeyboardMarkup, InputMediaPhoto, PhotoSize,
        KeyboardButton, ReplyKeyboardMarkup)
from bot_token import TOKEN

from User import User
from database import Db
import updaters as u
import helpers as h
import coindata

from threading import Thread
from io import BytesIO
import logging
from datetime import datetime

from pprint import pprint as pp

def command_handler(update, context):
    if update.message:
        message = update.message.text
    else:
        message = '/' + update.callback_query.data

    user_id = update.effective_user.id
    user = update.effective_user

    print("\n", user_id, user['full_name'], ':')
    print(message)

    m = message.split()
    command, context.args = m[0][1:], m[1:]

    known_commands = ['start', 'stop', 'add', 'remove',
        'clear', 'show', 'info', 'list', 'delta', 'help', 'watchlist']

    if user_id not in users:
        start(update, context)

    if command not in known_commands:
        return -1

    if command == 'info':
        command = 'my'

    elif command == 'list':
        command = 'watchlist'

    elif command in ['add', 'remove', 'watchlist']:
        context.user_data.clear()

    elif command == 'start':
        return start(update, context)

    elif command == 'help':
        command = 'rules'

    return eval(f'{command}(update, context)')

def start(update, context):
    user_ = update.effective_user
    user_id = user_.id

    user = User.objects.get(user_id)
    if not user:
        user = User(user_id)
        print(' > > > > New User added:', user)

    user.id = user_id
    user.link_name = user_['name']
    user.full_name = user_['full_name']
    user.last_visit = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db.save(user)

    u.update_coins_in_use(users, coins_in_use, data)

    rules(update, context)

def rules(update, context):
    user_id = update.effective_user.id

    res = '/add btc - add btc to your list for manual price check\n'
    res += '\n'
    res += '/add btc =20000 - notification at price 20000\n'
    res += '\n'
    res += '/add btc +2000 - notification at price change +2000\n'
    res += '/add btc -2000 - notification at price change -2000\n'
    res += '/add btc 2000 - notification at price change +2000 or -2000\n'
    res += '\n'
    res += '/add btc +5% - notification at price change +5%\n'
    res += '/add btc -5% - notification at price change -5%\n'
    res += '/add btc 5% - notification at price change +5% or -5%\n'
    res += '\n'
    res += '/add btc 2000 once - notification will be shown once\n'
    res += '\n'
    res += '/remove - remove menu step by step\n'
    res += '/remove btc - fully removes token from the list\n'
    res += '/remove 1 3 - removes first and third rules from the list\n'
    res += '\n'
    res += '/list - show watched crypto and rules\n'
    res += '\n'
    res += '/info - show detailed info on watched crypto\n'
    res += '\n'
    res += '/clear - remove all tokens and all rules, clear the list\n'
    res += '\n'
    res += '/help - show this\n'
    res += '\n'
    res += '* try any token you wish to track instead of btc (e.g. eth, ltc, xmr, xrp)\n'

    context.bot.send_message(chat_id=user_id, text=res)

def show(update, context):
    user_id = update.effective_user.id
    user = users[user_id]

    print('user coins:', user.coins)

    if context.args:
        if 'strict' in context.user_data:
            user_data = h.get_data_by_stock_list_strict(context.args)
            context.user_data.clear()
        else:
            user_data = h.get_data_by_stock_list(context.args)
    else:
        user_data = h.get_data_user_coins(user_id)

    to_pretty = None
    if user_data:
        keys = {'rank':'Rank', 'name':'Name', 'code':'Code', 'current_price':'Price', '1h_change':'1h',
                '24h_change':'24h', '7d_change':'7d', '14d_change':'14d', '30d_change':'30d',
                '200d_change':'200d', '1y_change':'1y'}

        to_pretty = {coin: {name: data[key] for key, name in keys.items()} for coin, data in user_data.items()}

        to_pretty = coindata.prettify(to_pretty)
    update.message.reply_text(text=f'<pre>{to_pretty}</pre>', parse_mode='html')
    db.check_in(user)

def my(update, context):
    user_id = update.effective_user.id

    user_data = h.get_data_user_coins(user_id, context.args)

    if user_data:
        for coin in user_data.items():
            context.args = [coin]
            show_one(update, context)
    else:
        if context.args:
            if len(context.args) == 1:
                message = f"You don't track <code>{context.args[0]}</code>.\nInput /add <code>{context.args[0]}</code> to add it."
            else:
                message = f"You don't track any of these coins.\nUse /add command to add some."
        else:
            message = f"Your list is empty.\nAdd new coins with /add command."

        update.effective_message.reply_text(message, parse_mode='html')

def show_one(update, context):
    id, coin = context.args[0]
    img = coin['image'].replace('/large/','/small/')

    res = f"<b>{coin['name']}</b>:\n\n"
    res += '<pre>'
    res += f" Rank:  {coin['rank']:}\n"
    res += f"   ID:  {id}\n"
    res += f" Code:  {coin['code']}\n"
    res += f"Price:  {coin['current_price']}\n"
    res += f"   1h:  {coin['1h_change']}\n"
    res += f"  24h:  {coin['24h_change']}\n"
    res += f"   7d:  {coin['7d_change']}\n"
    res += f"  14d:  {coin['14d_change']}\n"
    res += f"  30d:  {coin['30d_change']}\n"
    res += f" 200d:  {coin['200d_change']}\n"
    res += f"   1y:  {coin['1y_change']}\n"
    res += f"  Max:  {coin['max_price']}\n"
    res += '</pre>'

    current_price = data[id]['current_price']
    img0 = coindata.graph(id, data[id]['sparkline'], current_price)
    bio = BytesIO()
    bio.name = 'image.png'
    img0.save(bio, 'PNG')
    img0.close()
    bio.seek(0)

    img1 = InputMediaPhoto(coin['image'], caption=res, parse_mode='html')
    img2 = InputMediaPhoto(bio)

    context.bot.send_media_group(
        chat_id=update.effective_chat.id,
        media=[img1, img2]
    )

def add(update, context):
    user_id = update.effective_user.id
    user = users[user_id]

    print('args:', context.args)

    if not context.args:
        if 'conv_add' not in context.user_data:
            update.message.reply_text(f'Usage: /add <code>coin</code> [rule]', parse_mode='html')
        return

    context.args = h.filter_similar(context.args)

    if len(context.args) == 3:
        if 'once' in context.args:
            if any([arg[0] in ['+', '-', '=', '.'] or arg[0].isdigit() for arg in context.args]):
                context.args.remove('once')
                context.args = ['once'] + context.args
                return delta(update, context)

    elif len(context.args) == 2:
        if context.args[1][0] in ['+', '-', '=', '.'] or context.args[1][0].isdigit():
            return delta(update, context)

    other_coins = context.args.copy()

    for coin in context.args:
        if not h.check_coin_limit(update, context):
            break

        other_coins.remove(coin)

        context.user_data['conv_add_other_coins'] = other_coins

        coin = coin.lower()

        coins_matched = h.get_coins_by_wide_name(coin)

        if len(coins_matched) == 1:
            if coins_matched[0] in user.coins:
                update.effective_message.reply_text(
                    text=f'You already have <code>{coins_matched[0]}</code>.',
                    parse_mode='html'
                )
                continue
            user.coins.append(coins_matched[0])
            user.coins = sorted(list(set(user.coins)))
            u.update_coins_in_use(users, coins_in_use, data)
            db.save(user)
            print('ADD:', f'{coin} added to list')
            update.effective_message.reply_text(
                f'<code>{h.get_coin_repr_name(coins_matched[0])}</code> added to your list.',
                parse_mode='html'
            )
            context.user_data['list_changed'] = True
        elif len(coins_matched) > 1:
            buttons = []
            for each in coins_matched:
                names = f'{h.get_coin_repr_name(each)} ({h.get_coin_code_name(each).upper()})'
                buttons.append([InlineKeyboardButton(names, callback_data=each)])
            context.user_data['conv_add'] = True
            context.user_data['conv_add_names'] = coins_matched

            legend = ''.join([f'{i + 1}.  <code>{coin}</code>\n' for i, coin in enumerate(coins_matched)])

            update.effective_message.reply_text(
                    text=f'Which <code>{coin}</code>?\n{legend}',
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode='html'
            )
            print('ADD return')
            return REPLY
        else:
            print(f'ADD: Nothing found for {coin}')
            update.effective_message.reply_text(f'Nothing found for <code>{coin}.</code>', parse_mode='html')

def remove(update, context):
    user_id = update.effective_user.id
    user = users[user_id]

    print('REMOVE:', context.user_data)
    print('context.args:', context.args)

    if not context.args:
        if 'conv_remove_which' not in context.user_data and 'conv_remove' not in context.user_data \
                and 'conv_remove_which_reply' not in context.user_data:
            user_coins = user.coins
            buttons = []
            for each in user_coins:
                names = f'{h.get_coin_repr_name(each)} ({h.get_coin_code_name(each).upper()})'
                buttons.append([InlineKeyboardButton(names, callback_data=each)])
            context.user_data['conv_remove_which'] = True
            context.user_data['conv_remove_names'] = user_coins
            context.user_data['conv_remove_other_names'] = []

            legend = ''.join([f'{i + 1}. <code>{coin}</code>\n' for i, coin in enumerate(user_coins)])

            update.effective_message.reply_text(
                text=f'Remove:\n{legend}',
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode='html'
            )
            print('REMOVE return')
            return REPLY

    context.args = h.filter_similar(context.args)
    other_names = context.args.copy()

    if context.args and all([arg.isdigit() for arg in context.args]):
        context.args = ['remove'] + context.args
        return watchlist(update, context)

    for name in context.args:
        other_names.remove(name)

        context.user_data['conv_remove_other_names'] = other_names

        name = name.lower()

        matched_coins = []
        for coin in user.coins:
            if name in [value.lower() for value in stock_coin_list[coin].values()]:
                matched_coins.append(coin)
        if len(matched_coins) == 0:
            print("REMOVE:", f"not found: {name}")
            continue
        elif len(matched_coins) == 1:
            coin = matched_coins[0]
            print("REMOVE:", coin)
            user.coins.remove(coin)
            for rule in user.watchlist.copy():
                if coin == rule[0]:
                    user.watchlist.remove(rule)
            if 'conv_remove_coins_removed' not in context.user_data:
                context.user_data['conv_remove_coins_removed'] = []
            context.user_data['conv_remove_coins_removed'].append(coin)
            u.update_coins_in_use(users, coins_in_use, data)
            db.save(user)
        else:
            buttons = []
            for each in matched_coins:
                button = f'{h.get_coin_repr_name(each)} ({h.get_coin_code_name(each).upper()})'
                buttons.append([InlineKeyboardButton(button, callback_data=each)])
            context.user_data['conv_remove'] = True
            context.user_data['conv_remove_names'] = matched_coins

            legend = ''.join([f'{i + 1}.  <code>{coin}</code>\n' for i, coin in enumerate(matched_coins)])

            update.effective_message.reply_text(
                    text=f'Which <code>{name}</code>?\n{legend}',
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode='html'
            )
            print('REMOVE return')
            return REPLY

    if 'conv_remove_coins_removed' in context.user_data:
        removed = context.user_data['conv_remove_coins_removed']
        print('removed:', removed)
        l = len(removed)
        if l == 1:
            message = f"<code>{h.get_coin_repr_name(removed[0])}</code> removed."
        else:
            message = f"Removed {l} coins."
        context.user_data.clear()
        context.user_data['list_changed'] = True
    elif 'conv_remove_rules_removed' in context.user_data:
        return watchlist(update, context)
    else:
        message = 'Nothing removed.'
    update.effective_message.reply_text(message, parse_mode='html')

def remove_which(update, context):
    user_id = update.effective_user.id
    user = users[user_id]

    print('REMOVE WHICH:')

    token = context.args[0]

    print('token:', token)

    token_rules = []
    if user.watchlist:
        for rule in user.watchlist:
            if rule[0] == token:
                token_rules.append(' '.join([rule[0], str(rule[2]), f'({rule[3]})']))

    if token_rules:
        names = [f'{token} and all its rules', f'all {token} rules'] + token_rules
        print('names:', names)

        buttons = []
        for each in names:
            button = f'{each}'
            buttons.append([InlineKeyboardButton(button, callback_data=each)])
        del context.user_data['conv_remove_which']
        context.user_data['conv_remove_which_reply'] = True
        context.user_data['conv_remove_names'] = names
        context.user_data['conv_token'] = token

        legend = ''.join([f'{i + 1}.  <code>{coin}</code>\n' for i, coin in enumerate(names)])

        update.effective_message.reply_text(
                text=f'Which <code>{token}</code>?\n{legend}',
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode='html'
        )
        print('REMOVE WHICH return REPLY')
        return REPLY

    else:
        print('REMOVE WHICH by strict')
        return remove_by_strict_name(update, context)

def clear(update, context):
    user_id = update.effective_user.id
    user = users[user_id]
    user.coins.clear()
    user.watchlist.clear()
    update.effective_message.reply_text('List cleared.')
    db.save(user)

def delta(update, context):
    user_id = update.effective_user.id
    user = users[user_id]

    print('args:', context.args)

    if not (len(context.args) == 2 or \
        (len(context.args) == 3 and context.args[0] == 'once')):
        update.effective_message.reply_text("Wrong input, syntax: /add [once] <coin> [+-]<value>[%]")
        return ConversationHandler.END

    if len(context.args) == 2:
        once = False
        coin = context.args[0]
        value = context.args[1]
    else:
        once = True
        coin = context.args[1]
        value = context.args[2]

    names = h.get_coins_by_wide_name(coin)
    print('DELTA:', coin, value, names)
    if len(names) == 0:
        update.effective_message.reply_text("No such coin.")
        context.user_data.clear()
        return ConversationHandler.END
    elif len(names) == 1:
        coin = h.get_strict_name(coin)
        context.args = [coin]
        if add_by_strict_name(update, context, muted=True) == 'overlimit':
            context.user_data.clear()
            return ConversationHandler.END
    elif 'conv_delta' in context.user_data and coin in context.user_data['conv_delta_names']:
        context.args = [coin]
        if add_by_strict_name(update, context, muted=True) == 'overlimit':
            context.user_data.clear()
            return ConversationHandler.END
    else:
        buttons = []
        for each in names:
            button = f'{h.get_coin_repr_name(each)} ({h.get_coin_code_name(each).upper()})'
            buttons.append([InlineKeyboardButton(button, callback_data=each)])
        context.user_data['conv_delta'] = True
        context.user_data['conv_delta_once'] = once
        context.user_data['conv_delta_value'] = value
        context.user_data['conv_delta_names'] = names

        legend = ''.join([f'{i + 1}.  <code>{coin}</code>\n' for i, coin in enumerate(names)])

        update.effective_message.reply_text(
                text=f'Which <code>{coin}</code>?\n{legend}',
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode='html'
        )

        return REPLY

    context.user_data.clear()

    if rule := h.delta_add_rule(user, coin, value, once=once):
        if rule == 'wrong_input':
            update.effective_message.reply_text('Wrong input: /add [once] coin [+-]value[%]')
        elif rule == 'small_value':
            update.effective_message.reply_text('Delta value is too small. Try bigger value.')
        else:
            print('rule:', rule)
            rule_value = rule[2]
            watch_value = rule[3]
            if rule_value[0] == '=':
                text = watch_value
            else:
                text = f'{rule_value}\n[{str(watch_value).strip("[]")}]'
            update.effective_message.reply_text(
                f'<code>{h.get_coin_repr_name(coin)}</code> {text}\nadded to your rules.',
                parse_mode='html'
            )
            context.user_data['list_changed'] = True
    else:
        update.effective_message.reply_text('delta_add_rule: Unknown error.')

def reply_by_text(update, context):
    context.user_data['conv_input'] = update.message.text
    return reply(update, context)

def reply_by_query(update, context):
    update.callback_query.answer()
    context.user_data['conv_input'] = update.callback_query.data
    return reply(update, context)

def reply(update, context):
    user_id = update.effective_user.id
    user = users[user_id]

    print('REPLY handler ::')
    print('User data:', context.user_data)

    message = context.user_data['conv_input'].lower()

    res = None

    if 'conv_add' in context.user_data:
        if message.isdigit() and \
                int(message) in range(1, len(context.user_data['conv_add_names']) + 1):
            message = context.user_data['conv_add_names'][int(message) - 1]
        if message in context.user_data['conv_add_names']:
            context.args = [message]
            add_by_strict_name(update, context)
        else:
            update.effective_message.reply_text(f'Not added. Try again.')
        print('OTHER COINS to ADD:', context.user_data['conv_add_other_coins'])
        context.args = context.user_data['conv_add_other_coins']
        if context.args:
            res = add(update, context)

    elif 'conv_remove' in context.user_data:
        if message.isdigit() and \
                int(message) in range(1, len(context.user_data['conv_remove_names']) + 1):
            message = context.user_data['conv_remove_names'][int(message) - 1]
        if message in context.user_data['conv_remove_names']:
            context.args = [message]
            coins_removed = remove_by_strict_name(update, context)
            if coins_removed:
                if 'conv_remove_coins_removed' not in context.user_data:
                    context.user_data['conv_remove_coins_removed'] = []
                context.user_data['conv_remove_coins_removed'].extend(coins_removed)
        else:
            update.effective_message.reply_text(f'Not removed. Try again.')
        print('OTHER COINS to REMOVE', context.user_data['conv_remove_other_names'])
        context.args = context.user_data['conv_remove_other_names']
        res = remove(update, context)

    elif 'conv_delta' in context.user_data:
        if message.isdigit() and \
                int(message) in range(1, len(context.user_data['conv_delta_names']) + 1):
            message = context.user_data['conv_delta_names'][int(message) - 1]
        context.args = [message, context.user_data['conv_delta_value']]
        if context.user_data['conv_delta_once']:
            context.args = ['once'] + context.args
        res = delta(update, context)

    elif 'conv_remove_which' in context.user_data:
        if message.isdigit() and \
                int(message) in range(1, len(context.user_data['conv_remove_names']) + 1):
            message = context.user_data['conv_remove_names'][int(message) - 1]
        if message in context.user_data['conv_remove_names']:
            context.args = [message]
            res = remove_which(update, context)
            if res == REPLY:
                return REPLY
            else:
                coins_removed = res
            print('coins removed:', coins_removed)
            if coins_removed:
                if 'conv_remove_coins_removed' not in context.user_data:
                    context.user_data['conv_remove_coins_removed'] = []
                context.user_data['conv_remove_coins_removed'].extend(coins_removed)
        else:
            update.effective_message.reply_text(f'Not removed. Try again.')
        print('OTHER COINS to REMOVE', context.user_data['conv_remove_other_names'])
        context.args = context.user_data['conv_remove_other_names']
        res = remove(update, context)

    elif 'conv_remove_which_reply' in context.user_data:
        if message.isdigit() and \
                int(message) in range(1, len(context.user_data['conv_remove_names']) + 1):
            message = context.user_data['conv_remove_names'][int(message) - 1]
        if message in context.user_data['conv_remove_names']:
            token = context.user_data['conv_token']
            print('names:', context.user_data['conv_remove_names'])
            pos = context.user_data['conv_remove_names'].index(message)
            if pos == 0:
                context.args = [token]
                res = remove_by_strict_name(update, context)
            elif pos == 1:
                removed = False
                for i, rule in enumerate(user.watchlist.copy()):
                    if rule[0] == token:
                        user.watchlist[i] = None
                        removed = True
                if removed:
                    user.watchlist = [rule for rule in user.watchlist if rule]
                    db.save(user)
                    context.user_data['conv_remove_rules_removed'] = True
            else:
                pos = pos - 2
                rules = []
                for rule in user.watchlist:
                    if rule[0] == token:
                        rules.append(rule)
                user.watchlist.remove(rules[pos])
                db.save(user)
                context.user_data['conv_remove_rules_removed'] = True

            if res:
                coins_removed = res
                if 'conv_removed_coins_removed' not in context.user_data:
                    context.user_data['conv_remove_coins_removed'] = []
                context.user_data['conv_remove_coins_removed'].extend(coins_removed)

            print('OTHER COINS to REMOVE', context.user_data['conv_remove_other_names'])
            context.args = context.user_data['conv_remove_other_names']
            res = remove(update, context)

    if res == REPLY:
        return res

    print("REPLY fully")

    # If list_changed matters
    # print(context.user_data)
    if 'list_changed' in context.user_data:
        # print('LIST PRINTING')
        pass

    print('- - - - - - - - - - -')
    context.user_data.clear()
    return ConversationHandler.END

def dummy_query_handler(update, context):
    update.callback_query.answer()

def add_by_strict_name(update, context, muted=False):
    user_id = update.effective_user.id
    user = users[user_id]

    context.args = h.filter_similar(context.args)

    changed = False
    for coin in context.args:
        coin = coin.lower()
        if coin in user.coins:
            if not muted:
                update.effective_message.reply_text(
                    f'You already have <code>{h.get_coin_repr_name(coin)}</code>.',
                    parse_mode='html'
                )
            continue
        if not h.check_coin_limit(update, context):
            return 'overlimit'
        if coin in stock_coin_list:
            user.coins.append(stock_coin_list[coin]['id'])
            changed = True
            print('ADD STRICT:', f'{coin} added to list')
            update.effective_message.reply_text(
                f'<code>{h.get_coin_repr_name(coin)}</code> added to your list.',
                parse_mode='html'
            )
            context.user_data['list_changed'] = True
        else:
            update.effective_message.reply_text(
                f'Nothing found for <code>{coin}<code>.',
                parse_mode='html'
            )

    if changed:
        users[user_id].coins = sorted(list(set(user.coins)))
        u.update_coins_in_use(users, coins_in_use, data)
        db.save(user)

def remove_by_strict_name(update, context):
    user_id = update.effective_user.id
    user = users[user_id]

    context.args = h.filter_similar(context.args)
    coins_removed = []

    print('REMOVE BY STRICT')
    for coin in context.args:
        coin = coin.lower()
        if coin in user.coins.copy():
            user.coins.remove(coin)
            for rule in user.watchlist.copy():
                if coin == rule[0]:
                    user.watchlist.remove(rule)
            coins_removed.append(coin)
    if coins_removed:
        db.save(user)
        u.update_coins_in_use(users, coins_in_use, data)

    return coins_removed

def watchlist(update, context):
    user_id = update.effective_user.id
    user = users[user_id]

    res = ''

    # /list [clear|remove]
    if context.args:
        if len(context.args) == 1 and context.args[0] == 'clear':
            user.watchlist.clear()
            db.save(user)
        elif context.args[0] == 'remove':
            removed = False
            for pos in context.args[1:]:
                if pos.isnumeric() and int(pos) - 1 in range(len(user.watchlist)):
                    user.watchlist[int(pos) - 1] = None
                    removed = True
            if removed:
                user.watchlist = [i for i in user.watchlist if i]
                db.save(user)
        else:
            update.message.reply_text('Usage:\n/list\n/list clear\n/list remove [num]')

    # /list

    not_watchlisted_tokens = h.get_not_watchlisted_tokens(user_id)

    if not_watchlisted_tokens or user.watchlist:
        res = 'List:\n'

    for not_watchlisted_token in not_watchlisted_tokens:
        current_value = h.get_current_value(not_watchlisted_token)
        token_code = h.get_coin_code_name(not_watchlisted_token)
        res += '\n'
        res += f'{not_watchlisted_token} ({token_code})'
        res += f' {current_value}'
        res += '\n'

    if user.watchlist:
        last_name = None

        for pos, rule in enumerate(user.watchlist):

            name, start_value, rule, watch_value, from_time, *once = rule

            current_value = h.get_current_value(name)
            token_code = h.get_coin_code_name(name)
            dtime = datetime.now() - datetime.strptime(from_time, '%Y-%m-%d %H:%M:%S')
            if dtime.days:
                dtime, suf = dtime.days, 'day'
            elif dtime.seconds // 3600:
                dtime, suf = dtime.seconds // 3600, 'hr'
            elif dtime.seconds // 60:
                dtime, suf = dtime.seconds // 60, 'min'
            else:
                dtime, suf = '', 'now'

            if dtime != 1 and suf == 'day':
                suf = 'days'

            if name != last_name:
                res += '\n'
                res += f'{name} ({token_code})'
                res += f' {current_value}:'
                res += '\n'
                last_name = name
            res += f'  {pos + 1}.'
            res += f'  {rule}'
            res += f' {once[0]}' if once else ''
            res += f' {watch_value}' if rule[0] != '=' else ''
            res += f'  {dtime} {suf}' if dtime else f'  {suf}'
            res += '\n'

    if not res:
        res = 'List is empty.'
    update.effective_message.reply_text(res)
    db.check_in(user)


def main():

    persistence = PicklePersistence('persistence')
    updater = Updater(token=TOKEN, persistence=persistence)
    dispatcher = updater.dispatcher

    u.update_coins_in_use(users, coins_in_use, data)

    t1 = Thread(target=u.update_data_daemon, args=(data, coins_in_use), daemon=True)
    t1.start()
    t2 = Thread(target=u.update_stock_coin_list_daemon, args=(stock_coin_list,), daemon=True)
    t2.start()
    t3 = Thread(target=u.check_watchlist_daemon, args=(updater.bot, users), daemon=True)
    t3.start()

    conv_handler = ConversationHandler(
        entry_points = [
                        MessageHandler(Filters.command & ~Filters.regex(r'/k'), command_handler),
                        ],
        states = {
            REPLY: [
                MessageHandler(Filters.text & ~Filters.command, reply_by_text),
                CallbackQueryHandler(reply_by_query)
            ],
        },
        fallbacks = []
    )

    dispatcher.add_handler(conv_handler, group=0)

    dispatcher.add_handler(MessageHandler(Filters.command, command_handler))

    dispatcher.add_handler(CallbackQueryHandler(dummy_query_handler), group=1)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    Defaults(run_async=True)
    db = Db()
    users = User.objects
    coins_in_use = []
    data = {}
    stock_coin_list = {}

    h.db = db
    u.db = db
    h.data = data
    h.users = users
    h.stock_coin_list = stock_coin_list

    REPLY = range(1)

    main()
