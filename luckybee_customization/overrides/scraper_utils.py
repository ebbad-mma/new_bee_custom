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
	# frappe.log_error("runnig",soup)
	# general = soup.find_all('div', class_='GNDEQ-')[0]
	# frappe.log_error("General Div Content", str(general))
	title = soup.find('span', class_='VU-ZEz').text    
	
	categories = [div.text for div in soup.find_all('div',class_='r2CdBx')[1:-1]]

	rating = soup.find('div', class_='XQDdHH').text
	price = soup.find('div', class_='Nx9bqj CxhGGd').text
	seller = soup.find('div', class_='yeLeBC').text
	seller_rating = soup.find('div', class_='XQDdHH uuhqql').text
	main_image_div = soup.find('div', class_='_4WELSP _6lpKCl')
	if not main_image_div:
		main_image_div = soup.find('div', class_='gqcSqV YGE0gZ')
	
	main_image = None
	if main_image_div:
		main_image = main_image_div.img['src']
	
	image_div = soup.find_all('div',class_= 'Pz+aTd')
	image_src = []
	for image in image_div:
		image_src.append(image.img['src'])
	
	# print("Title: " , title)
	# print("rating: ", rating)
	# print("Price" , price)
	# print("Seller: ", seller)
	# print("Image url: ", main_image)
	
	
	# print("\nSpecifications:\n")
	specs = soup.find_all('div', class_='GNDEQ-')
	 # Loop through each 'div' in specs and find elements with class '_4BJ2V+'
	for spec in specs:
		elements = spec.find_all('div', class_='_4BJ2V+')
		for element in elements:
			element['style'] = 'font-weight: bold; font-size: larger;'
	modified_html = str(specs)
	specs_dict = {}
	for spec in specs:
		spec_title = spec.find('div', class_='_4BJ2V+').text
		specs_dict[spec_title] = {}
		# print('\t',spec_title)
		table = spec.find('table')
		for row in table.find_all('tr'):
			columns = row.find_all('td')
			if len(columns) == 2:
				col1 = columns[0].text.strip()
				col2 = columns[1].text.strip()
				# print(f"\t{col1} - {col2}")
				specs_dict[spec_title][col1] = col2
		# print()    

	main_div=soup.find('div', class_='sBVJqn')
	product_details_dict = {}
	# print("Product Details")
	if main_div:
		for row_div in main_div.find_all('div', class_='row'):
			# Extract data from columns
			columns = row_div.find_all('div')
			if len(columns) == 2:
				column1_data = columns[0].text.strip()
				column2_data = columns[1].text.strip()
				# print(f"\t{column1_data} : {column2_data}")
				product_details_dict[column1_data] = column2_data
		
	# Extract ratings and reviews
	ratings_reviews = soup.find('span', class_='Wphh3N')
	ratings_reviews_text = ratings_reviews.text if ratings_reviews else ""
	
	ratings, reviews = "0 Ratings", "0 Reviews"
	if ratings_reviews_text:
		ratings = ratings_reviews_text.split('Ratings')[0].strip()
		reviews = ratings_reviews_text.split('&')[1].strip()

	#extract discount
	discount = None
	discount_div = soup.find('div', class_='UkUFwK WW8yVX')
	if discount_div:
		discount = discount_div.find('span').text.strip()
		discount=extract_discount(discount)

		
	data = {
		"title" : title,
		'categories': categories,
		"rating" : rating,
		"price" : price,
		"seller" : seller,
		"image_url":  main_image,
		"multiple_images" : image_src,
		'product_details': product_details_dict,
		'specifications' : specs_dict,
		'ratings':ratings,
		'reviews':reviews,
		'discount':discount

	}
	data['general']=modified_html
	# data['general']=specs
	data['description'] = ""
	# description = soup.find('div', class_='_4gvKMe').text
	# data['description'] = description
	data['highlights'] = []
	try:
		# print("Highlights")
		highlights = soup.find('div', class_='xFVion')        
		for item in highlights:
			for i in item:
				data['highlights'].append[i.text]
				# print('\t',i.text)       
	except:        
		frappe.log_error("Flipkart scraper", "some values not fetched")
		# pass
	frappe.log_error("data",data)
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