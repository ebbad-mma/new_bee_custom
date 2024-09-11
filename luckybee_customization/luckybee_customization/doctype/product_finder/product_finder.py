import frappe
import keepa
import json
from frappe.model.document import Document
import random
from itertools import combinations


def jumble_string_by_word_subsets(input_string):
	# Split the input string into a list of words
	words = input_string.split()
	
	# Create a set to store unique jumbled sequences
	jumbled_list = set()
	
	# Define the subset sizes you want (2, 3, or 4 words)
	subset_sizes = [2, 3, 4]
	
	# Generate unique jumbled sequences from subsets of the defined sizes
	for size in subset_sizes:
		if len(words) >= size:
			subsets = list(combinations(words, size))
			for subset in subsets:
				temp_list = list(subset)
				random.shuffle(temp_list)
				jumbled_list.add(' '.join(temp_list))
	
	# Convert set to list and ensure we return exactly 5 unique items
	return list(jumbled_list)[:5]

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
			"productType": 0,
			"perPage": 50,
			"page": 0
		}
		
		asins_found = False  # Flag to track if ASINs are found
		responses = []

		if self.title:  # If title is provided
			result = jumble_string_by_word_subsets(self.title)  # Generate title subsets
			frappe.log_error("result", result)
			for title in result:
				frappe.log_error("title", title)
				product_params['title'] = title  # Set the current title from result
				
				# Add other search fields
				if self.brand:
					product_params['brand'] = [self.brand]
				if self.color:
					product_params['color'] = [self.color]
				if self.size:
					product_params['size'] = [self.size]
				
				asins = api.product_finder(product_params, domain='IN')
				if asins:
					self.title=title
					frappe.log_error("re", asins)
					asins_found = True  # Set flag to True when ASINs are found
					break  # Exit the loop if ASINs are found
		else:  # If title is not provided
			# Use only other search fields
			if self.brand:
				product_params['brand'] = [self.brand]
			if self.color:
				product_params['color'] = [self.color]
			if self.size:
				product_params['size'] = [self.size]

			# Perform search with other fields
			asins = api.product_finder(product_params, domain='IN')
			if asins:
				frappe.log_error("re", asins)
				asins_found = True

		# Process the results if ASINs are found
		if asins_found:
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
			
			# Clear existing responses in the table
			self.set('product_finder_response', [])

			
			# Append new responses to the table
			for response in responses:
				self.append('product_finder_response', response)

			# Log the responses
			frappe.log_error("responses", responses)
		else:
			frappe.log_error("No ASINs found", "No products matched the search criteria.")
