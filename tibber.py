import json

import requests


class Tibber:
    url = 'https://api.tibber.com/v1-beta/gql'
    access_token = None
    headers = {
        'Content-Type': 'application/json',
    }
    DEMO_TOKEN = "5K4MVS-OjfWhK_4yrjOlFe1F6kJXPVf7eQYggo8ebAE"

    cheapest_hours = None
    most_expensive_hours = None
    percentage_difference_cheapest = None
    percentage_difference_expensive = None
    average_price = None

    def __init__(self):
        self.load_access_token("config.json")
        self.set_header()

    def run(self):
        data = self.get_prices()
        self.calculate_prices_and_hours(data)
        self.send_push_notification()

    def load_access_token(self, filename):
        with open(filename, "r") as f:
            config = json.load(f)
            self.access_token = config.get("access_token", self.DEMO_TOKEN)

    def set_header(self):
        self.headers['Authorization'] = 'Bearer ' + self.access_token

    def get_prices(self):
        query = '''
        {
          viewer {
            homes {
              currentSubscription{
                priceInfo{
                  current{
                    total
                    startsAt
                  }
                  today {
                    total
                    startsAt
                  }
                  tomorrow {
                    total
                    startsAt
                  }
                }
              }
            }
          }
        }
        '''
        response = requests.post(self.url, headers=self.headers, json={'query': query})
        response.raise_for_status()

        return response.json()

    def calculate_prices_and_hours(self, data):
        prices = data['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['today']
        average_price = sum(price['total'] for price in prices) / len(prices)

        # Find the cheapest and most expensive price, also calculate the percentage differences
        cheapest_price = min(prices, key=lambda price: price['total'])
        most_expensive_price = max(prices, key=lambda price: price['total'])
        percentage_difference_cheapest = ((average_price - cheapest_price['total']) / average_price) * 100
        percentage_difference_expensive = ((most_expensive_price['total'] - average_price) / average_price) * 100

        # Round the percentage to 2 decimal places
        percentage_difference_cheapest = round(percentage_difference_cheapest, 2)
        percentage_difference_expensive = round(percentage_difference_expensive, 2)

        # sort the prices
        prices = sorted(prices, key=lambda price: price['total'])

        # extract the cheapeast three hours
        cheapest_hours = [(price['total'], price["startsAt"][11:11 + 2]) for price in prices[:3]]

        # extract the most expensive hours
        most_expensive_hours = [(price['total'], price["startsAt"][11:11 + 2]) for price in prices[-3:]]

        self.cheapest_hours = cheapest_hours
        self.most_expensive_hours = most_expensive_hours
        self.percentage_difference_cheapest = percentage_difference_cheapest
        self.percentage_difference_expensive = percentage_difference_expensive
        self.average_price = average_price

    def send_push_notification(self):

        query_push = '''
        mutation{
          sendPushNotification(input: {
            title: custom_title,
            message: "\\n🕑👍: {hours} Uhr\\n💶👍: {prices} Cent/kWh\\n\\n∅: {avg_price} Cent/kWh\\n\\n🕒🔥: {expensive_hours} Uhr\\n💶🔥: {expensive_prices} Cent/kWh",
            screenToOpen: CONSUMPTION
          }){
            successful
            pushedToNumberOfDevices
          }
        }
        '''

        query_push = query_push.replace("custom_title", '"Deine Strompreisempfehlung für heute!"')
        query_push = query_push.replace("{hours}", ", ".join([x[1] for x in self.cheapest_hours]))
        query_push = query_push.replace("{prices}", ", ".join(
            [str(round(price * 100, 2)) for price, _ in self.cheapest_hours]))
        query_push = query_push.replace("{expensive_hours}", ", ".join([x[1] for x in self.most_expensive_hours]))
        query_push = query_push.replace("{expensive_prices}", ", ".join(
            [str(round(price * 100, 2)) for price, _ in self.most_expensive_hours]))
        query_push = query_push.replace("{avg_price}", str(round(self.average_price * 100, 2)).replace('.', ','))
        response = requests.post(self.url, headers=self.headers, json={'query': query_push})
        response.raise_for_status()
        print("Push successful")


t = Tibber()
t.run()
