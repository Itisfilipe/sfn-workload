import os
import tempfile
import time
from datetime import datetime

import boto3
import pandas as pd
import requests
from flatten_dict import flatten
from requests import HTTPError

__doc__ = """
This is a script to grab and format data from an ebay like website called mercadolibre.
The code needs refactoring/testing and it was made for personal usage.
USE AT YOUR OWN RISK
"""


# TODO: turns it into a whitelist
ATTRIBUTE_BLACKLIST = [
    "accepts_mercadopago",
    "address/city_id",
    "address/state_id",
    "buying_mode",
    "catalog_listing",
    "catalog_product_id",
    "category_id",
    "currency_id",
    "differential_pricing/id",
    "id",
    "installments/amount",
    "installments/currency_id",
    "installments/quantity",
    "installments/rate",
    "official_store_id",
    "original_price",
    "seller/car_dealer",
    "seller/id",
    "seller/real_estate_agency",
    "seller/tags",
    "seller_address/address_line",
    "seller_address/city/id",
    "seller_address/comment",
    "seller_address/country/id",
    "seller_address/country/name",
    "seller_address/id",
    "seller_address/latitude",
    "seller_address/longitude",
    "seller_address/state/id",
    "seller_address/zip_code",
    "shipping/logistic_type",
    "shipping/mode",
    "shipping/store_pick_up",
    "shipping/tags",
    "site_id",
    "stop_time",
    "tags",
    "thumbnail",
    "seller_address/city/name",
    "seller_address/state/name",
    "seller/eshop/eshop_id",
    "seller/eshop/seller",
    "seller/eshop/nick_name",
    "seller/eshop/eshop_status_id",
    "seller/eshop/site_id",
    "seller/eshop/eshop_logo_url",
    "seller/eshop/eshop_rubro",
    "seller/eshop/eshop_locations",
    "seller/eshop/eshop_experience",
    "installments",
]


LANGUAGE_ATTR_MAPPING = {
    "address/city_name": "Cidade",
    "address/state_name": "Estado",
    "attributes": "Atributos",
    "available_quantity": "Quantidade Disponível",
    "condition": "Condição",
    "listing_type_id": "Listagem",
    "permalink": "Link do Produto",
    "price": "Preço",
    "seller/permalink": "Link do Vendedor",
    "seller/power_seller_status": "Mercado Líder",
    "shipping/free_shipping": "Frete Grátis",
    "sold_quantity": "Quantidade Vendida",
    "title": "Título",
}

LANGUAGE_VALUE_MAPPING = {
    "new": "Novo",
    False: "Não",
    True: "Sim",
}

s3_client = boto3.client("s3")

BUCKET_NAME = os.environ["BUCKET_NAME"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]


def access_token():
    # TODO: reset and pass credentials with env vars
    AUTH_URL = f"https://api.mercadolibre.com/oauth/token?grant_type=client_credentials&\
                client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}"
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    r = requests.post(AUTH_URL, headers=headers)
    r.raise_for_status()
    return r.json()["access_token"]


def make_request(query, offset=0):
    token = access_token()
    QUERY_URL = f"https://api.mercadolibre.com/sites/MLB/search?q={query}&offset={offset}\
                &access_token={token}"
    r = requests.get(QUERY_URL)
    r.raise_for_status()
    return r.json()


def retryable_request(query, offset=0):
    try:
        return make_request(query, offset)
    except HTTPError:  # sophisticated retry =P
        try:
            time.sleep(2)
            return make_request(query, offset)
        except HTTPError:
            try:
                time.sleep(3)
                return make_request(query, offset)
            except HTTPError:
                pass


def retryable_results_request(query_string, offset=0):
    data = retryable_request(query_string, offset)
    if data is None:
        print("!!!Request Error!!!")
        print(f"offset {offset}; querystring: {query_string}")
        print("!!!Request Error!!!")
        # TODO: either return a error and treat it on step functions or just bypass this case somehow
        return {}
    # sophisticated retry, again =P
    if len(data["results"]) == 0:
        time.sleep(2)
        data = retryable_request(query_string, offset)
        if data is None:
            return None
        if len(data["results"]) == 0:
            time.sleep(3)
            data = retryable_request(query_string, offset)
            if data is None:
                return None

    return data["results"]


def parse_results(results):
    parsed_results = []
    for result in results:
        # make it flat 8-)
        result = flatten(result, reducer="path")
        # remove blacklisted attrs (don't forget to change this to whitelist)
        for attr in ATTRIBUTE_BLACKLIST:
            if attr in result:
                del result[attr]
        # make attributes readable
        if "attributes" in result:
            result["attributes"] = " | ".join(
                [
                    f"{attr['name']}: {attr['value_name']}"
                    for attr in result["attributes"]
                ]
            )
        # Translate attributes to Portuguese
        for attr_en, attr_pt in LANGUAGE_ATTR_MAPPING.items():
            # and also values lol
            # "not isinstance(result[attr_en], int)" is a hack to not translate numbers
            if (
                not isinstance(result[attr_en], int)
                and result[attr_en] in LANGUAGE_VALUE_MAPPING
            ):
                result[attr_en] = LANGUAGE_VALUE_MAPPING[result[attr_en]]
            result[attr_pt] = result[attr_en]
            del result[attr_en]

        parsed_results.append(result)

    return parsed_results


def extract_results(query_string):
    data = retryable_request(query_string)
    if data is None:
        print("!!!Request Error!!!")
        print(f"offset 0; querystring: {query_string}")
        print("!!!Request Error!!!")
        # TODO: return a error and treat it on step functions or just bypass this case
        return {}
    total_results = (
        data["paging"]["total"] if data["paging"]["total"] < 5000 else 5000
    )  # 5000 max, more than that will take toooo mutch time
    all_results = parse_results(data["results"])
    for offset in range(50, total_results, 50):
        results = retryable_results_request(query_string, offset)
        if results is None:
            print("!!!Request Error!!!")
            print(f"offset 0; querystring: {query_string}")
            print("!!!Request Error!!!")
            continue
        all_results.extend(parse_results(results))
    return all_results


def handler(event, context):
    start = time.time()
    # aways take the first item, it will be removed by the end of the stepFunctions
    keywords = event["ClientData"][0]["Keywords"]
    pages = {}
    for keyword in keywords:
        pages[keyword] = extract_results(keyword)

    tmp_file = tempfile.NamedTemporaryFile(suffix=".xlsx").name
    with pd.ExcelWriter(tmp_file) as writter:
        for page, items in pages.items():
            df = pd.DataFrame.from_dict(items)
            df.to_excel(writter, sheet_name=page, engine="xlsxwriter")

    current_year = f"{datetime.now():%Y%z}"
    current_month = f"{datetime.now():%m%z}"
    current_day = f"{datetime.now():%d%z}"
    current_time = f"{datetime.now():%H:%M:%S%z}"
    file_name = (
        f"{current_year}/{current_month}/{current_day}/{current_time}-report.xlsx"
    )
    s3_client.upload_file(tmp_file, BUCKET_NAME, file_name)

    print(f"Took {time.time() - start} seconds")
    event.update({"FileName": file_name})
    return event


if __name__ == "__main__":
    # for testing
    handler(None, None)
