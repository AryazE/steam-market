# Objective:
# - (done but already available with market_search) retrieve the lowest sell order for 'Booster Packs' & 'Sack of Gems',
# - (not yet done) retrieve the highest buy order for 'Booster Packs'.
#
# Caveat: I recommend using market_search.py instead, because:
# - regarding sell orders, the information is available with both market_search.py and market_listing.py,
# - I could not retrieve buy orders, which was the information missing from market_search.py in the first place,
# - due to rate limits, it is much more time efficient to download batches of 100 entries per page with market_search.py

import json
import time
from pathlib import Path

import requests

from market_search import load_all_listings
from personal_info import get_steam_cookie, get_cookie_dict
from utils import get_listing_details_output_file_name


def get_steam_market_listing_url(app_id=None, listing_hash=None):
    if app_id is None:
        app_id = 753

    if listing_hash is None:
        listing_hash = '511540-MoonQuest Booster Pack'

    market_listing_url = 'https://steamcommunity.com/market/listings/' + str(app_id) + '/' + listing_hash + '/render/'

    return market_listing_url


def get_listing_parameters():
    params = dict()

    params['currency'] = '3'

    return params


def get_steam_api_rate_limits_for_market_listing(has_secured_cookie=False):
    # Objective: return the rate limits of Steam API for the market.

    if has_secured_cookie:

        rate_limits = {
            'max_num_queries': 50,
            'cooldown': (1 * 60) + 10,  # 1 minute plus a cushion
        }

    else:

        rate_limits = {
            'max_num_queries': 25,
            'cooldown': (5 * 60) + 10,  # 5 minutes plus a cushion
        }

    return rate_limits


def get_listing_details(listing_hash=None, currency_symbol='€', cookie_value=None):
    listing_details = dict()

    url = get_steam_market_listing_url(listing_hash=listing_hash)
    req_data = get_listing_parameters()

    has_secured_cookie = bool(cookie_value is not None)

    if has_secured_cookie:
        cookie = get_cookie_dict(cookie_value)
        resp_data = requests.get(url, params=req_data, cookies=cookie)
    else:
        resp_data = requests.get(url, params=req_data)

    status_code = resp_data.status_code

    if status_code == 200:
        result = resp_data.json()

        html = result['results_html']

        tokens = html.split()

        price_headers = [l for (c, l) in enumerate(tokens[:-1]) if currency_symbol in tokens[c + 1]]
        price_values = [l for l in tokens if currency_symbol in l]

        if len(price_headers) > 0 and len(price_headers) != 3:
            print('Unexpected number of price headers = {}. Likely due to zero sell order.'.format(len(price_headers)))
            print(price_headers)

        try:
            chosen_index = 0
            chosen_price_header = price_headers[chosen_index]  # e.g. 'market_listing_price_with_fee">'
            chosen_price_value = price_values[chosen_index]  # e.g. '6,64€'

            listing_details[listing_hash] = dict()
            # listing_details[listing_hash]['price_header'] = chosen_price_header.strip('">')
            listing_details[listing_hash]['for_sale'] = float(chosen_price_value.strip('€').replace(',', '.'))
            listing_details[listing_hash]['buy_request'] = -1  # missing from the html code
        except IndexError:
            pass

    return listing_details, status_code


def get_listing_details_batch(listing_hashes):
    cookie_value = get_steam_cookie()
    has_secured_cookie = bool(cookie_value is not None)

    rate_limits = get_steam_api_rate_limits_for_market_listing(has_secured_cookie)

    all_listing_details = dict()
    num_listings = len(listing_hashes)

    query_count = 0

    for count, listing_hash in enumerate(listing_hashes):

        if count + 1 % 100 == 0:
            print('[{}/{}]'.format(count + 1, num_listings))

        listing_details, status_code = get_listing_details(listing_hash=listing_hash, cookie_value=cookie_value)

        if query_count >= rate_limits['max_num_queries']:
            cooldown_duration = rate_limits['cooldown']
            print('Number of queries {} reached. Cooldown: {} seconds'.format(query_count, cooldown_duration))
            time.sleep(cooldown_duration)
            query_count = 0

        query_count += 1

        if status_code != 200:
            print('Wrong status code for {} after {} queries.'.format(listing_hash, query_count))
            break

        all_listing_details.update(listing_details)

    return all_listing_details


def download_all_listing_details():
    listing_details__output_file_name = get_listing_details_output_file_name()

    if not Path(listing_details__output_file_name).exists():
        all_listings = load_all_listings()

        all_listing_details = get_listing_details_batch(all_listings.keys())

        with open(listing_details__output_file_name, 'w') as f:
            json.dump(all_listing_details, f)

    return True


def load_all_listing_details():
    with open(get_listing_details_output_file_name(), 'r') as f:
        all_listing_details = json.load(f)

    return all_listing_details


def get_sack_of_gems_price(currency_symbol='€', verbose=True):
    listing_hash = '753-Sack of Gems'
    num_gems = 1000

    listing_details, status_code = get_listing_details(listing_hash=listing_hash, currency_symbol=currency_symbol)

    if status_code == 200:
        sack_of_gems_price = listing_details[listing_hash]['for_sale']
    else:
        sack_of_gems_price = -1

    if verbose:
        print('A sack of {} gems can be bought for {} €.'.format(num_gems, sack_of_gems_price, currency_symbol))

    return sack_of_gems_price


if __name__ == '__main__':
    download_all_listing_details()
