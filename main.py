import requests
import json
import re
from tinydb import TinyDB, Query
from bs4 import BeautifulSoup
from jsondiff import diff
from pytablewriter import MarkdownTableWriter
from pytablewriter.style import Style
from datetime import datetime
from pytz import timezone

mainurl = "https://www.rosebikes.de"


def read_config_file():
    try:
        with open('bike_types.json', 'r') as bike_types:
            data = bike_types.read()
            return data
    except Exception as e:
        return {}


def build_url_list(bike_data):
    urllist = []
    jsonData = json.loads(bike_data)
    for item in jsonData:
        url = mainurl + "/" + item['type_url'] + "?" + "product_shape=" + \
            item['color'] + "&" + "article_size=" + item['size']
        urllist.append(url)
    return urllist


def check_stock_availability(urllist):
    name_data, ordernumber_data, color_data, price_data, availability_data, url_data = [], [], [], [], [], []

    for url in urllist:
        url_data.append(url)
        
        color = re.search('product_shape=(.+?)&article_size', url)
        if color:
            found = color.group(1)
            color_data.append(found)

        simple_url = url[:url.find("&article_size") ]

        response_simple= requests.get(simple_url)
        html_simple = BeautifulSoup(response_simple.text, 'html.parser')

        bike_name = html_simple.find("h1", class_="product-headline")
        bike_ordernumber = html_simple.find("span", itemprop="sku")

        if bike_ordernumber:
            for i in bike_ordernumber:
                ordernumber_data.append(i.strip("\n"))
        else:
            ordernumber_data.append("N/A")

        if bike_name:
            for i in bike_name:
                name_data.append(i)
        else:
            name_data.append("N/A")


        response_detailed = requests.get(url)
        html = BeautifulSoup(response_detailed.text, 'html.parser')
        
        stock_availability = html.find_all(
            'a', class_="bike-detail-availability__text")

        if stock_availability:
            for i in stock_availability: 
                availability_data.append(str(i.get_text()))
            price = html.find("span", itemprop="price")
            for i in price:
                price_data.append(i)
        else:
            availability_data.append("N/A")
            price_data.append("N/A")

    data = [{"bike_name": n, "sku": s, "color": c, "price": p, "stock_availability": a, "url": u} for n, s, c, p, a, u in zip(name_data, ordernumber_data, color_data, price_data, availability_data, url_data)]
    return data

def parse_availibility_data(bike_store_data):
    for item in bike_store_data:
        if item['stock_availability'] != "N/A":
            print(item)

def update_db(bike_store_data, db):
    change_list = []
    for item in bike_store_data:
        Bike = Query()
        if db.search(Bike.sku == item['sku']) :
            print("Product " + item['sku'] + " already exists.")
            db_item = db.search(Bike.sku == item['sku'])
            difference = check_for_update(item, db_item[0])
            has_difference = bool(difference)
            if has_difference:
                print("Updated item :" + item['sku'] + " - difference: " + str(difference))  
                db.update(item, Bike.sku == item['sku'])
                for key, value in difference.items():
                    change_structure = []
                    change_structure.append(item['bike_name'])
                    change_structure.append(item['sku'])
                    change_structure.append(key)
                    change_structure.append(db_item[0][key])
                    change_structure.append(item[key])
                    change_list.append(change_structure)
            else:
                print("Nothing to update on item: " + item['sku'])
        else:
            print("Product " + item['sku'] + " added.")
            data = item
            db.insert(data)
    if len(change_list) > 0:
        create_report_changes(change_list)
    
def check_for_update(query_item, db_item):
    difference = (diff(db_item, query_item))
    return difference

def create_report_changes(change_matrix):
    amsterdam = timezone('Europe/Amsterdam')
    dateTimeObj = datetime.now(amsterdam).strftime("%m-%d-%Y-%H-%M-%S")
    table_name = "bikes_changes_report_" + str(dateTimeObj)
    writer = MarkdownTableWriter(
        table_name=table_name ,
        headers=["Bike Name", "SKU", "Updated key", "Old value", "New Value"],
        value_matrix = change_matrix
    )
    f = open("report/" + table_name + ".md", "w")
    f.write(writer.dumps())
    f.close()

def create_report_main(db):
    Bike = Query()
    result = db.search(Bike.stock_availability != "N/A")
    if result:
        matrix_data = format_to_matrix(result)

        amsterdam = timezone('Europe/Amsterdam')
        dateTimeObj = datetime.now(amsterdam).strftime("%m-%d-%Y-%H-%M-%S")
        table_name = "bikes_available_report_" + str(dateTimeObj)
        writer = MarkdownTableWriter(
            table_name=table_name ,
            headers=["Bike Name", "SKU", "Color", "Price", "Lieferzeit", "URL"],
            value_matrix = matrix_data
        )
        f = open("report/" + table_name + ".md", "w")
        f.write(writer.dumps())
        f.close()

    result = db.search(Bike.stock_availability == "N/A")
    if result:
        matrix_data = format_to_matrix(result)
        
        amsterdam = timezone('Europe/Amsterdam')
        dateTimeObj = datetime.now(amsterdam).strftime("%m-%d-%Y-%H-%M-%S")
        table_name = "bikes_not_available_report_" + str(dateTimeObj)
        writer = MarkdownTableWriter(
            table_name= table_name,
            headers=["Bike Name", "SKU", "Color", "Price", "Lieferzeit", "URL"],
            value_matrix = matrix_data
        )
        f = open("report/" + table_name + ".md", "w")
        f.write(writer.dumps())
        f.close()
        

def format_to_matrix(data):
    n = 7
    list_main = []
        
    for item in data:
        list_sub = []
        list_sub.append(item['bike_name'])
        list_sub.append(item['sku'])
        list_sub.append(item['color'])
        list_sub.append(item['price'])
        list_sub.append(item['stock_availability'])
        list_sub.append(item['url'])
        list_main.append(list_sub)

    return list_main


if __name__ == "__main__":
    config = read_config_file()
    urllist = build_url_list(config)
    bike_store_data = check_stock_availability(urllist)
    
    db = TinyDB('db/db.json')
    update_db(bike_store_data, db)
    create_report_main(db)
