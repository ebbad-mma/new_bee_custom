"""The category structure Ashish specified, and how the existing catalogue maps onto it.

STRUCTURE is his document verbatim - 12 main categories, 74 subcategories. The
names must match character-for-character in three places at once: this file, the
ERPNext Item Group, and the WooCommerce product category. The connector matches
on the name alone, so a stray accent or plural silently creates a duplicate
category on the storefront instead of failing.

The catalogue was never classified this way. item_group held 29 values, 4,617
items in "All Groups" and 2,260 in "Kitchen"; the real classification lived in
custom_category (125 values) and custom_sub_category (1,099 free-text values),
an older and coarser vocabulary. DIRECT maps the values that have exactly one
home in the new structure.

SPLIT covers the three that do not. Drinkware, Serveware and Kitchen Tools are
47% of the catalogue between them and the new structure divides each of them
three ways, so they can only be resolved from the sub-category text - which is
free-text and inconsistent ("bottle" and "bottles", "mug", "mugs" and "mug set",
"peeler" and "peelers"). Longest keyword match wins, so "bottles - insulated"
resolves before the bare "bottle" can claim it.

Together these place 92% of the catalogue. The rest is genuinely ambiguous and
went to Ashish as a list rather than being guessed at.
"""

STRUCTURE = {
 "Kitchen & Dining": ["Bakeware","Cookware","Bottles & Sippers","Mugs, Cups & Tea Sets",
   "Glassware & Bar","Everyday Plates & Bowls","Dinner Sets & Formal Serveware",
   "Festive & Bar Serveware","Kitchen Organisation & Storage","Cutting & Peeling Tools",
   "Measuring & Cooking Prep","Serving & Cooking Tools","Bar & Drink Prep Tools","Cutlery"],
 "Home Essentials": ["Bathroom Organisation","Storage Boxes & Baskets",
   "Closet & Garment Organisation","Furniture & Laundry Organisation",
   "Racks, Shelves & Wall Organisation","Home Cleaning","Home Hardware & Tools",
   "Home Security","Pest Control & Plumbing","Gardening Tools"],
 "Home Furnishing": ["Bed Linen","Bath Linen","Kitchen Linen","Floor Linen",
   "Appliances Linen","Curtains & Accessories","Spiritual & Festive"],
 "Toys & Games": ["Ball Games & Outdoor Play","Ride-On & Wheeled Toys",
   "Pretend Play & Dress Up","Board & Card Games","Building & Puzzle Toys",
   "Learning & Educational Toys","Electronic & Remote Toys","Soft Toys & Stacking Games",
   "Vehicle & Action Toys"],
 "Personal Care": ["Hair & Beard Care","Health Care & Wellness","Oral Care & Hygiene",
   "Perfumes","Personal Care Appliances","Personal Care & Skin Care Tools"],
 "Home Decor & Lighting": ["Home Decor","Table & Wall Decor","Indoor Lighting",
   "Outdoor & Solar Lighting","Plants & Planters"],
 "Appliances": ["Home Appliances","Cooking Appliances","Food Prep Appliances",
   "Breakfast & Snack Appliances","Appliances Parts & Accessories"],
 "Electronics & Accessories": ["Mobile Accessories","Computer Accessories",
   "Gaming Accessories","Car Accessories","Bike Accessories"],
 "Sports & Fitness": ["Gym & Yoga","Cricket","Badminton","Football","Other Sports"],
 "Fashion, Bags & Travel": ["Footwear","Apparel & Baby","Bags & Wallets",
   "Hand Bags & Backpacks","Travel Bags & Luggage"],
 "Stationary": ["Office & Desk Organisation","Books & Writing Material"],
 "Food & Beverages": ["Beverages"],
}


# custom_category (lowercased) -> doc subcategory. 1:1 where the doc has one home.
DIRECT = {
 "cookware":"Cookware", "bakeware":"Bakeware", "cutlery":"Cutlery",
 "kitchen storage":"Kitchen Organisation & Storage",
 "kitchen organisation":"Kitchen Organisation & Storage",
 "kitchen appliances":"Cooking Appliances",
 "boxes, baskets & bins":"Storage Boxes & Baskets",
 "closet organisation":"Closet & Garment Organisation",
 "bathroom organisation":"Bathroom Organisation",
 "laundry organisation":"Furniture & Laundry Organisation",
 "storage furniture":"Furniture & Laundry Organisation",
 "outdoor furniture":"Furniture & Laundry Organisation",
 "wall organisation":"Racks, Shelves & Wall Organisation",
 "racks, shelves & drawers":"Racks, Shelves & Wall Organisation",
 "organisation":"Storage Boxes & Baskets",
 "shoe organisation":"Closet & Garment Organisation",
 "home cleaning":"Home Cleaning",
 "tools":"Home Hardware & Tools", "home tools":"Home Hardware & Tools",
 "home hardware":"Home Hardware & Tools",
 "plumbing hardware":"Pest Control & Plumbing",
 "insect & animal control":"Pest Control & Plumbing",
 "home security":"Home Security",
 "gardening tools":"Gardening Tools", "fertilizer & soil":"Gardening Tools",
 "bed linen":"Bed Linen", "bath linen":"Bath Linen", "kitchen linen":"Kitchen Linen",
 "floor linen":"Floor Linen", "appliances linen":"Appliances Linen",
 "slipcovers":"Appliances Linen",
 "curtains":"Curtains & Accessories", "spiritual":"Spiritual & Festive",
 "home décor":"Home Decor", "home decor":"Home Decor",
 "wall décor":"Table & Wall Decor", "table décor":"Table & Wall Decor",
 "lighting":"Indoor Lighting", "plants & planters":"Plants & Planters",
 "home appliances":"Home Appliances", "appliances":"Home Appliances",
 "appliances parts & accessories":"Appliances Parts & Accessories",
 "personal care appliances":"Personal Care Appliances",
 "personal care tools":"Personal Care & Skin Care Tools",
 "skin care":"Personal Care & Skin Care Tools", "facial":"Personal Care & Skin Care Tools",
 "hair care":"Hair & Beard Care", "beard care":"Hair & Beard Care",
 "oral care":"Oral Care & Hygiene", "hygeine":"Oral Care & Hygiene",
 "bath & shower":"Oral Care & Hygiene",
 "perfumes":"Perfumes",
 "health care":"Health Care & Wellness", "health care devices":"Health Care & Wellness",
 "mobile accessories":"Mobile Accessories", "tablets":"Mobile Accessories",
 "computer accessories":"Computer Accessories",
 "video game":"Gaming Accessories", "video gaming":"Gaming Accessories",
 "car  accessories":"Car Accessories", "car accessories":"Car Accessories",
 "automotive safety":"Car Accessories",
 "bike accessories":"Bike Accessories", "cycling":"Bike Accessories",
 "gym & yoga":"Gym & Yoga", "exercise & fitness":"Gym & Yoga",
 "cricket":"Cricket", "badminton":"Badminton", "football":"Football",
 "tennis":"Other Sports", "volleyball":"Other Sports", "boxing":"Other Sports",
 "skating":"Other Sports", "running":"Other Sports", "camping & hiking":"Other Sports",
 "ball games":"Ball Games & Outdoor Play", "ball set & games":"Ball Games & Outdoor Play",
 "bikes, trikes & ride-ons":"Ride-On & Wheeled Toys", "tricycle":"Ride-On & Wheeled Toys",
 "dress up & pretend play":"Pretend Play & Dress Up",
 "board games":"Board & Card Games", "board & table games":"Board & Card Games",
 "building  block toys":"Building & Puzzle Toys",
 "learning & education":"Learning & Educational Toys",
 "arts & crafts":"Learning & Educational Toys",
 "electronic toys":"Electronic & Remote Toys", "sound toys":"Electronic & Remote Toys",
 "music games":"Electronic & Remote Toys",
 "soft toys":"Soft Toys & Stacking Games", "stacking games":"Soft Toys & Stacking Games",
 "vehicle":"Vehicle & Action Toys", "vehicles":"Vehicle & Action Toys",
 "guns":"Vehicle & Action Toys", "blasters & toy guns":"Vehicle & Action Toys",
 "hand bags":"Hand Bags & Backpacks", "handbags":"Hand Bags & Backpacks",
 "women handbags":"Hand Bags & Backpacks", "bags & backpacks":"Hand Bags & Backpacks",
 "travel luggage":"Travel Bags & Luggage", "travel organisation":"Travel Bags & Luggage",
 "travel accessories":"Travel Bags & Luggage",
 "mens shoes":"Footwear", "baby clothing":"Apparel & Baby",
 "mens accessories":"Bags & Wallets", "mens lifestyle":"Bags & Wallets",
 "office organisation":"Office & Desk Organisation",
 "writing material":"Books & Writing Material",
 "reading material":"Books & Writing Material",
 "beverages":"Beverages",
}

# The three the document splits three ways. Resolved on custom_sub_category
# keywords - longest match wins, so "bottles - insulated" beats "bottle".
SPLIT = {
 "drinkware": [
   ("Glassware & Bar",        ["glass set","wine glass","wine glasses","glass","tumbler",
                               "lemon set","bar set","decanter","shot"]),
   ("Mugs, Cups & Tea Sets",  ["cup & saucer","cup set","tea set","teapot","kettle set",
                               "mug set","mugs","mug","cup","cups","saucer"]),
   ("Bottles & Sippers",      ["bottles - insulated","flask - insulated","bottle","bottles",
                               "sipper","sippers","flask","jug","jugs","thermos","casserole"]),
 ],
 "serveware": [
   ("Dinner Sets & Formal Serveware", ["dinner set","porcelain crockery","soup set",
                                       "pudding set","crockery","dinnerware"]),
   ("Festive & Bar Serveware",        ["serving casserole","serving handi","platter","tray",
                                       "trays","snack set","handi","casserole",
                                       "ice bucket","ice buckets","wine chiller"]),
   ("Everyday Plates & Bowls",        ["bowl set","serving plate","serving plates","bowls",
                                       "bowl","plate","plates","thali","serving set","dish"]),
   # Items filed under Serveware whose real home is elsewhere in the structure.
   # A target does not have to sit under the same main category - the connector
   # matches on the leaf name, and a spoon set is Cutlery wherever it was filed.
   ("Cutlery",                        ["spoon set","fork set","cutlery","knife set",
                                       "teaspoon","dessert spoon","spoon & fork"]),
   ("Mugs, Cups & Tea Sets",          ["mug set","mugs","mug","cup set","cup & saucer",
                                       "tea set","cups"]),
   ("Bottles & Sippers",              ["bottle","bottles","flask","sipper"]),
   ("Serving & Cooking Tools",        ["serving spoon","serving fork","ladle","laddle",
                                       "server","tong","tongs","skimmer"]),
 ],
 "kitchen tools": [
   ("Cutting & Peeling Tools", ["chopping board","kitchen knife","knife","knives","peeler",
                                "peelers","chopper","choppers","scissor","scissors","slicer",
                                "slicers & grater","grater","cutter"]),
   ("Measuring & Cooking Prep",["food strainer","strainer","strainers","masher","measuring",
                                "whisk","sieve","rolling","press","squeezer"]),
   ("Serving & Cooking Tools", ["skimmer","laddle","ladle","turner","tong","tongs","spatula",
                                "net cover","lighter","opener","server"]),
 ],
}


def resolve(custom_category, custom_sub_category):
	"""Return the subcategory an item belongs in, or None if it cannot be decided."""
	cat = (custom_category or "").strip().lower()
	sub = (custom_sub_category or "").strip().lower()

	if cat in SPLIT:
		best = None
		for target, keywords in SPLIT[cat]:
			for kw in keywords:
				# Longest match wins - "bottles - insulated" must beat "bottle".
				if kw in sub and (best is None or len(kw) > best[1]):
					best = (target, len(kw))
		return best[0] if best else None

	return DIRECT.get(cat)


def all_names():
	"""Every category name, mains first - the order they must be created in."""
	return list(STRUCTURE) + [s for subs in STRUCTURE.values() for s in subs]


# Where an item goes when it cannot be classified. A real, named group rather
# than "All Groups": unclassified stock should be visible as a queue to work
# through, not silently mixed into the root of the tree. It also has no
# WooCommerce counterpart, so these items simply do not publish - which is the
# right outcome for a product nobody has categorised yet.
HOLDING_GROUP = "Uncategorised"


def group_for(custom_category, custom_sub_category):
	"""The Item Group an item belongs in, or the holding group."""
	return resolve(custom_category, custom_sub_category) or HOLDING_GROUP
