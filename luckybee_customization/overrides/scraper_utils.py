import frappe
import requests
from bs4 import BeautifulSoup as bs
import re
def extract_discount(discount_text):
	# Extract the numeric part of the discount
	discount_percentage = re.search(r'\d+', discount_text)
	if discount_percentage:
		return discount_percentage.group()
	return None


def scrape(fsn):
	url = f"https://www.flipkart.com/product/p/itme?pid={fsn}"

	page = requests.get(url)
	soup = bs(page.content, 'html.parser')

	# Initialize data dictionary
	data = {}

	# Scrape the title
	try:
		title = soup.find('span', class_='VU-ZEz').text
		frappe.log_error("Title", title)
	except AttributeError as e:
		frappe.log_error(f"Error scraping title: {str(e)}", "Flipkart Scraper Error")
		title = ""
	data["title"] = title

	# Scrape the price
	try:
		price = soup.find('div', class_='Nx9bqj CxhGGd').text
		frappe.log_error("Price", price)
	except AttributeError as e:
		frappe.log_error(f"Error scraping price: {str(e)}", "Flipkart Scraper Error")
		price = 0
	data["price"] = price

	# Scrape categories
	try:
		categories = [div.text for div in soup.find_all('div', class_='r2CdBx')[1:-1]]
		frappe.log_error("Categories", categories)
	except AttributeError as e:
		frappe.log_error(f"Error scraping categories: {str(e)}", "Flipkart Scraper Error")
		categories = []
	data["categories"] = categories

    # Scrape the rating
	try:
		rating = soup.find('div', class_='XQDdHH').text
		frappe.log_error("Rating", rating)
	except AttributeError as e:
		frappe.log_error(f"Error scraping rating: {str(e)}", "Flipkart Scraper Error")
		rating = ""
	data["rating"] = rating

	# Scrape the seller information
	try:
		seller = soup.find('div', class_='yeLeBC').text
		frappe.log_error("Seller", seller)
	except AttributeError as e:
		frappe.log_error(f"Error scraping seller: {str(e)}", "Flipkart Scraper Error")
		seller = ""
	data["seller"] = seller

	# Scrape the seller rating
	try:
		seller_rating = soup.find('div', class_='XQDdHH uuhqql').text
		frappe.log_error("Seller Rating", seller_rating)
	except AttributeError as e:
		frappe.log_error(f"Error scraping seller rating: {str(e)}", "Flipkart Scraper Error")
		seller_rating = ""
	data["seller_rating"] = seller_rating

	# Scrape the main image
	try:
		main_image_div = soup.find('div', class_='_4WELSP _6lpKCl')
		if not main_image_div:
			main_image_div = soup.find('div', class_='gqcSqV YGE0gZ')
		main_image = main_image_div.img['src'] if main_image_div else ""
	except AttributeError as e:
		frappe.log_error(f"Error scraping main image: {str(e)}", "Flipkart Scraper Error")
		main_image = ""
	data["image_url"] = main_image

	# Scrape multiple images
	try:
		image_src = [img.img['src'] for img in soup.find_all('div', class_='Pz+aTd')]
	except AttributeError as e:
		frappe.log_error(f"Error scraping multiple images: {str(e)}", "Flipkart Scraper Error")
		image_src = []
	data["multiple_images"] = image_src

	# Scrape specifications
	try:
		specs_dict = {}
		specs = soup.find_all('div', class_='GNDEQ-')
		# General specifications as modified HTML
		data["general"] = str(specs)
		for spec in specs:
			spec_title = spec.find('div', class_='_4BJ2V+').text
			specs_dict[spec_title] = {}
			table = spec.find('table')
			for row in table.find_all('tr'):
				columns = row.find_all('td')
				if len(columns) == 2:
					col1 = columns[0].text.strip()
					col2 = columns[1].text.strip()
					specs_dict[spec_title][col1] = col2
	except AttributeError as e:
		frappe.log_error(f"Error scraping specifications: {str(e)}", "Flipkart Scraper Error")
		specs_dict = {}
	data["specifications"] = specs_dict

	 # Scrape product details
	try:
		product_details_dict = {}
		main_div = soup.find('div', class_='sBVJqn')
		if main_div:
			for row_div in main_div.find_all('div', class_='row'):
				columns = row_div.find_all('div')
				if len(columns) == 2:
					column1_data = columns[0].text.strip()
					column2_data = columns[1].text.strip()
					product_details_dict[column1_data] = column2_data
	except AttributeError as e:
		frappe.log_error(f"Error scraping product details: {str(e)}", "Flipkart Scraper Error")
		product_details_dict = {}
	data["product_details"] = product_details_dict

	# Scrape ratings and reviews
	# try:
	# 	ratings_reviews = soup.find('span', class_='Wphh3N')
	# 	ratings_reviews_text = ratings_reviews.text if ratings_reviews else ""
	# 	li=ratings_reviews_text.split(" ")
	# 	if "&" in li:
	# 		li = li.replace("&", " ")
	# 	frappe.throw(f"{li}")
	# 	ratings, reviews = "0 Ratings", "0 Reviews"
	# 	frappe.throw(f"{li}")
	# 	if ratings_reviews_text:
	# 		ratings =li[0]
	# 		reviews = li[3]
	# 		frappe.throw(f"{reviews}")
	# except AttributeError as e:
	# 	frappe.log_error(f"Error scraping ratings and reviews: {str(e)}", "Flipkart Scraper Error")
	ratings, reviews = "0 Ratings", "0 Reviews"
	data["ratings"] =ratings
	data["reviews"] = reviews

	# Scrape discount
	try:
		discount_div = soup.find('div', class_='UkUFwK WW8yVX')
		discount = discount_div.find('span').text.strip() if discount_div else None
		discount = extract_discount(str(discount))
	except AttributeError as e:
		frappe.log_error(f"Error scraping discount: {str(e)}", "Flipkart Scraper Error")
		discount = None
	data["discount"] = discount

	

	# Scrape highlights
	try:
		data["highlights"] = []
		highlights = soup.find('div', class_='xFVion')
		if highlights!=None:
			for item in highlights:
				for i in item:
					data["highlights"].append(i.text)
	except AttributeError as e:
		frappe.log_error(f"Error scraping highlights: {str(e)}", "Flipkart Scraper Error")
		data["highlights"] = []

	# Description placeholder
	data["description"] = ""

	return data





def set_images(doc,image_list):    
	n_images = min(len(image_list), 6)    
	if n_images == 1:
		doc.custom_image1 = image_list[0]
	if n_images == 2:
		doc.custom_image1 = image_list[0]
		doc.custom_image2 = image_list[1]
	if n_images == 3:
		doc.custom_image1 = image_list[0]
		doc.custom_image2 = image_list[1]
		doc.custom_image3 = image_list[2]
	if n_images == 4:
		doc.custom_image1 = image_list[0]
		doc.custom_image2 = image_list[1]
		doc.custom_image3 = image_list[2]
		doc.custom_image4 = image_list[3]
	if n_images == 5:
		doc.custom_image1 = image_list[0]
		doc.custom_image2 = image_list[1]
		doc.custom_image3 = image_list[2]
		doc.custom_image4 = image_list[3]
		doc.custom_image5 = image_list[4]
	if n_images == 6:
		doc.custom_image1 = image_list[0]
		doc.custom_image2 = image_list[1]
		doc.custom_image3 = image_list[2]
		doc.custom_image4 = image_list[3]
		doc.custom_image5 = image_list[4]
		doc.custom_image6 = image_list[5]

def extract_pid_with_regex(url):
	pattern = r'pid=([^&]+)'
	match = re.search(pattern, url)
	if match:
		return match.group(1)
	else:
		return None