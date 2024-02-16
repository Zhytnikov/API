import sys
import json
import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

DATE_FORMAT = '%d.%m.%Y'
CURRENCY_RATE_SEARCH = ()
logging.basicConfig(format="%(message)s", level=logging.INFO)

class CustomHttpException(Exception):
    pass

async def custom_http_request(url: str):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    raise CustomHttpException(f"Error status: {response.status} for {url}")
        except (aiohttp.ClientConnectorError, aiohttp.InvalidURL) as error:
            raise CustomHttpException(f'Connection error: {url}', str(error))

def extract_data(day):
    daily_data = {}
    for currency_data in day['exchangeRate']:
        if currency_data['currency'] in CURRENCY_RATE_SEARCH:
            daily_data.update({
                currency_data['currency']: {
                    'sale': currency_data['saleRateNB'],
                    'purchase': currency_data['purchaseRateNB']
                }
            })
    return {day['date']: daily_data}

def save_results(data_result):
    with open('storage/data.json', 'w', encoding='utf-8') as file:
        json.dump(data_result, file, ensure_ascii=False, indent=4)

def parse_arguments(arguments: list):
    global CURRENCY_RATE_SEARCH
    CURRENCY_RATE_SEARCH = ('USD', 'EUR')
    days = 1
    if len(arguments) > 1:
        for index in range(len(arguments)):
            if index == 1:
                days = (arguments[index])
            if index > 1:
                CURRENCY_RATE_SEARCH += (arguments[index].strip(',').upper(),)
    return days

async def main_function(days):
    responses = []
    for day in range(days):
        date = (datetime.now() - timedelta(days=day)).date().strftime(DATE_FORMAT)
        responses.append(custom_http_request('https://api.privatbank.ua/p24api/exchange_rates?json&date=' + str(date)))
    try:
        event_loop = asyncio.get_running_loop()
        full_exchange_data = await asyncio.gather(*responses)

        with ThreadPoolExecutor() as executor:
            futures = [
                event_loop.run_in_executor(executor, extract_data, day) for day in full_exchange_data
            ]

        result = await asyncio.gather(*futures)
        save_results(result)
        return result
    except CustomHttpException as exception:
        return logging.error(f"{exception}")

if __name__ == '__main__':
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        days_input = int(parse_arguments(sys.argv))
        if days_input in range(10):
            logging.info(f"{asyncio.run(main_function(days_input))}")
    except (ValueError, TypeError, IndexError):
        logging.info(f'Incorrect value, days may be in range 1 - 10')
