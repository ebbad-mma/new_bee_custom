import frappe
import keepa
import json
from frappe.model.document import Document

class ProductFinder(Document):
    accesskey = '4i9vbmksc3d9o67p6fd3s9aitdaaer17c604f3qrh93auu67fnh6pfucqvqltmjm'
    image_url = "https://images-na.ssl-images-amazon.com/images/I/"
    
    def validate(self):
        api = keepa.Keepa(ProductFinder.accesskey)
        product_params = {
            "sort": [
                [
                    "current_SALES",
                    "asc"
                ]
            ],
            "productType":
                0,
            "perPage": 50,
            "page": 0
        }
        
        if self.title:
            product_params['title'] = self.title
        if self.brand:
            product_params['brand'] = [self.brand]
        if self.color:
            product_params['color'] = [self.color]
        if self.size:
            product_params['size'] = [self.size]
        
        asins = api.product_finder(product_params, domain='IN')
        responses = []
        
        if asins:
            products = api.query(asins, domain='IN', stats=30)
            frappe.log_error("product_finder", f"Product params: \n {product_params}\n ASINs:\n {asins} \n Product details:\n{products}")
            
            for item in products:
                try:
                    image_url = ProductFinder.image_url + item['imagesCSV'].split(',')[0]
                    list_price = item.get('stats_parsed', {}).get('avg90', {}).get('LISTPRICE', 0)
                    new_current = item.get('stats_parsed', {}).get('current', {}).get('NEW', 0)
                    if list_price > 0:
                        discount_percentage = ((list_price - new_current) / list_price) * 100
                    else:
                        discount_percentage = 0

                    responses.append({
                        "asin_no": item['asin'],
                        'image': image_url,
                        'title': item['title'],
                        'categories_sub': ",".join([t['name'] for t in item['categoryTree']]),
                        'part_number': item['partNumber'],
                        'model': item['model'],
                        'color': item['color'],
                        'size': item['size'],
                        'mrp': list_price,
                        'online_price': new_current,
                        'discount': discount_percentage
                    })

                except Exception as e:
                    frappe.log_error(f"Error processing item: {item}", str(e))
                    pass
            
            # # Store the responses in the variable
            # self.product_finder_response = responses

            # Clear existing responses in the table
            self.set('product_finder_response', [])

            # Append new responses to the table
            for response in responses:
                self.append('product_finder_response', response)

            # Log the responses
            frappe.log_error("responses", responses)