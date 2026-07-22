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
		api = keepa.Keepa(ProductFinder.accesskey, timeout=60)
		product_params = {
			"sort": [
				[
					"current_SALES",
					"asc"
				]
			],
			"productType": [0],
			"perPage": 50,
			"page": 0
		}
		
		asins_found = False  # Flag to track if ASINs are found
		responses = []

		if self.title:  # If title is provided
			result = jumble_string_by_word_subsets(self.title)  # Generate title subsets
			result.insert(0,self.title)
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
		else:
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
					brand = item.get('brand', '')
					# Try new 'images' field first (list of image objects), fall back to deprecated 'imagesCSV'
					image_url = ''
					images = item.get('images')
					if images and len(images) > 0 and images[0]:
						img_filename = images[0].get('l') or images[0].get('m', '')
						if img_filename:
							image_url = 'https://m.media-amazon.com/images/I/' + img_filename
					if not image_url:
						images_csv = item.get('imagesCSV', '')
						if images_csv:
							image_url = 'https://m.media-amazon.com/images/I/' + images_csv.split(',')[0]
					if not image_url:
						# Fallback: use Amazon product image via ASIN
						asin = item.get('asin', '')
						if asin:
							image_url = f'https://images-na.ssl-images-amazon.com/images/P/{asin}.01._SCLZZZZZZZ_.jpg'
					list_price = item.get('stats_parsed', {}).get('avg90', {}).get('LISTPRICE', 0) or 0
					new_current = item.get('stats_parsed', {}).get('current', {}).get('NEW', 0) or 0
					if list_price > 0:
						discount_percentage = ((list_price - new_current) / list_price) * 100
					else:
						discount_percentage = 0

					category_tree = item.get('categoryTree', []) or []
					responses.append({
						"asin_no": item.get('asin', ''),
						'image': image_url,
						'title': item.get('title', ''),
						'categories_sub': ",".join([t['name'] for t in category_tree if 'name' in t]),
						'part_number': item.get('partNumber', '') or '',
						'model': item.get('model', '') or '',
						'color': item.get('color', '') or '',
						'size': item.get('size', '') or '',
						'mrp': list_price,
						'online_price': new_current,
						'discount': discount_percentage,
						'brand': brand
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
