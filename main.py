import requests
import json
from bs4 import BeautifulSoup

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
    name_data, price_data, availability_data, url_data = [], [], [], []

    for url in urllist:
        url_data.append(url)

        response = requests.get(url)
        html = BeautifulSoup(response.text, 'html.parser')
        
        stock_availability = html.find_all(
            'a', class_="bike-detail-availability__text")

        bike_name = html.find("h1", class_="product-headline")

        if bike_name:
            for i in bike_name:
                name_data.append(i)
        else:
            name_data.append("N/A")

        if stock_availability:
            for i in stock_availability: 
                availability_data.append(str(i.get_text()))
            price = html.find("span", itemprop="N/A")
            for i in price:
                price_data.append(i)
        else:
            availability_data.append("N/A")
            price_data.append("N/A")

    data = [{"bike_name": n, "price": p, "stock_availability": a, "url": u} for n, p, a, u in zip(name_data, price_data, availability_data, url_data)]
    print(json.dumps(data))


if __name__ == "__main__":
    config = read_config_file()
    urllist = build_url_list(config)
    check_stock_availability(urllist)
