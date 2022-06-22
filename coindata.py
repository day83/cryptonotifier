from pycoingecko import CoinGeckoAPI
import datetime
import dateutil.relativedelta
from pprint import pprint as pp
from prettytable import PrettyTable
import time
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageFont, ImageDraw


cg = CoinGeckoAPI()

def get_coins_list():
    return cg.get_coins_list()

def dataframe(coins):
    request = cg.get_coins_markets(ids=','.join(coins),
                    vs_currency='usd', sparkline=True,
                    price_change_percentage='1h,24h,7d,14d,30d,200d,1y')
    data = {}

    for coin in request:
        i = coin['id']
        data[i] = {}
        data[i]['rank'] = coin['market_cap_rank']
        data[i]['image'] = coin['image']
        data[i]['name'] = coin['name']
        data[i]['code'] = coin['symbol']
        data[i]['current_price'] = coin['current_price']
        data[i]['1h_change'] = coin['price_change_percentage_1h_in_currency']
        data[i]['24h_change'] = coin['price_change_percentage_24h_in_currency']
        data[i]['7d_change'] = coin['price_change_percentage_7d_in_currency']
        data[i]['14d_change'] = coin['price_change_percentage_14d_in_currency']
        data[i]['30d_change'] = coin['price_change_percentage_30d_in_currency']
        data[i]['200d_change'] = coin['price_change_percentage_200d_in_currency']
        data[i]['1y_change'] = coin['price_change_percentage_1y_in_currency']
        data[i]['low_24h'] = coin['low_24h']
        data[i]['high_24h'] = coin['high_24h']
        data[i]['min_price'] = coin['atl']
        data[i]['max_price'] = coin['ath']
        data[i]['total_supply'] = coin['total_supply']
        data[i]['max_supply'] = coin['max_supply']
        data[i]['total_volume'] = coin['total_volume']
        data[i]['market_cap'] = coin['market_cap']
        data[i]['sparkline'] = coin['sparkline_in_7d']['price']

    to_percents = ['1h_change', '24h_change', '7d_change',
            '14d_change', '30d_change', '200d_change', '1y_change']
    for id, coin in data.items():
        for k, v in coin.items():
            if isinstance(v, float) and k in to_percents:
                data[id][k] = '{:.2f}%'.format(v)
                if data[id][k][0] != '-':
                    data[id][k] = '+' + data[id][k]
    return data

def prettify(data):
    table = PrettyTable()
    table.field_names = list(data.values())[0].keys()
    for k, coin in data.items():
        table.add_row(coin.values())
    return table

def graph(id, sparkline, current_price):
        y = sparkline
        if not y:
            pil_image = Image.new('RGB', (640, 480), (32, 36, 51))
            draw = ImageDraw.Draw(pil_image)
            font = ImageFont.truetype('DejaVuSans.ttf', 48)
            draw.text((80, 80), "No data", font=font, fill=(255, 16, 16))
            return pil_image

        x = list(range(len(y)))

        plt.figure(facecolor='#202433')
        ax = plt.axes()
        ax.set_facecolor('#202433')
        ax.tick_params(axis='x', colors='#c0c0c0')
        ax.tick_params(axis='y', colors='#c0c0c0')
        ax.spines['bottom'].set_color('#303443')
        ax.spines['top'].set_color('#303443')
        ax.spines['left'].set_color('#303443')
        ax.spines['right'].set_color('#303443')
        plt.plot(x, y, color='#f22', linewidth=2)

        plt.ylim(min(y), max(y))
        plt.xlim(min(x), max(x))
        plt.title(f'{id} {datetime.datetime.now()}', color='#c0c0c0')
        # plt.xlabel('time', color="#808080")
        # plt.ylabel('price', color="#808080")
        plt.grid(color='#303443', linestyle='-.', linewidth=0.5)
        # plt.show()

        canvas = plt.get_current_fig_manager().canvas
        canvas.draw()

        pil_image = Image.frombytes('RGB', canvas.get_width_height(), canvas.tostring_rgb())

        plt.close()
        return pil_image
