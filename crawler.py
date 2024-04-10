from datetime import datetime
import requests
import json
from urllib.parse import urlencode
from bs4 import BeautifulSoup

'''
Business data example:
[
    {
        "name": X,
        "rating": X,
        "reviews_count": X,
        "yelp_url": X,
        "website": X,
        "reviews": [
            {
                "reviewer_name": X,
                "reviewer_location": X,
                "review_date": X
            }
        ]
    }
]

'''



class YelpCrawler:
    def __init__(self, category, location, *args, **kwargs):
        self.category = category
        self.location = location
        self.data = []
        self.search = ""
        self.number_of_reviews = 5
        self.max_pages = 5
    
    def run(self):
        '''
        Initializes the search url and runs crawler
        '''
        search_params = {
            "find_desc": self.category,
            "find_loc": self.location,
        }
        self.search = f"https://www.yelp.com/search?{urlencode(search_params)}"
        self.data = self.get_objects_list()
        return self.data


    def get_objects_list(self):
        '''
        Gets all objects from search for all pages and retrieves their data
        '''
        error_text = f"We're sorry, the page of results you requested is unavailable."
        page = 0
        objects = []
        while True:
            offset = page * 10
            page += 1
            if self.max_pages is not None and page > self.max_pages:
                break
            response = requests.get(self.search, params={"start": offset})
            soup = BeautifulSoup(response.content, 'html.parser')
            error_tag = soup.find_all("h3", string=error_text)
            # if error message is present -> means that there are no more pages
            if error_tag:
                break
            
            business_cards = soup.select('div[data-testid="serp-ia-card"]:not(.ABP)')
            for card in business_cards:
                objects.append(self.get_object_data(card))
            
        return objects

    def sanitize_element_text(self, element, additional_symbols=[]):
        '''
        Sanitizes element text from unwanted symbols
        '''
        if not element:
            return None
        text = element.text.strip()
        for symbol in additional_symbols:
            text = text.replace(symbol, "")
        return text

    
    def get_object_data(self, card):
        '''
        Gets single object data: name, rating, reviews_count, yelp_url etc.
        '''
        name_element = card.select_one('[class*="businessName"] a')

        rating_element = card.select_one('div.css-volmcs + div.css-1jq1ouh > span:first-child')
        review_count_element = card.select_one('div.css-volmcs + div.css-1jq1ouh > span:last-child')
        
        object_data = {
            "name": self.sanitize_element_text(name_element),
            "rating": self.sanitize_element_text(rating_element),
            "reviews_count": self.sanitize_element_text(review_count_element, additional_symbols=["(", ")"]),
            "yelp_url": f"https://www.yelp.com{name_element.get('href')}" if name_element else None,
            "reviews": [],
        }

        
        if object_data['yelp_url']:
            object_data['reviews'], object_data['website'] = self.get_object_reviews(object_data['yelp_url'])

        # for debugging purposes
        if not name_element:
            with open('fix.html', 'w', encoding='utf-8') as f:
                f.write(card.prettify())

        return object_data


    
    def get_object_reviews(self, object_url):
        '''
        Gets first N reviews for single object, and business website url
        '''
        response = requests.get(object_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        website = None
        website_element = soup.find_all("p", string="Business website")
        if website_element:
            website_element = website_element[0].parent.find_all('p')[1]
            website = self.sanitize_element_text(website_element)

        reviews_list_block = soup.select_one('div#reviews ul[class="list__09f24__ynIEd"]')
        reviews_items = []
        if not reviews_list_block:
            return reviews_items, website
        
        reviews = reviews_list_block.find_all('li')
        for review in reviews:
            if len(reviews_items) >= self.number_of_reviews:
                break

            name_element = review.select_one('div.user-passport-info > span > a')
            location_element = review.select_one('div.user-passport-info > div > div > span')
            date_element = soup.select('li > div > div')[1]
            date_element = date_element.select_one('div > div[class*="arrange-unit-fill"] > span')
            reviewer_name = self.sanitize_element_text(name_element)
            reviewer_location = self.sanitize_element_text(location_element)
            review_date = self.sanitize_element_text(date_element)

            review_data = {
                'reviewer_name': reviewer_name,
                'reviewer_location': reviewer_location,
                'review_date': review_date
            }
            reviews_items.append(review_data)

        return reviews_items, website

    def write_output(self) -> None:
        '''
        Writes data to json file
        '''
        with open('business.json', 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)



if __name__ == "__main__":
    crawler = YelpCrawler(category="Restaurants", location="New York City")
    crawler.run()
    crawler.write_output()