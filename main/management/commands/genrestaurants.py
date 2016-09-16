# vim: set fileencoding=utf-8

from django.core.management.base import BaseCommand
from main.models import Restaurant, Category, CategoryI18n, Item, ItemI18n, Address, Menu, Currency, \
    Allergen, AllergenI18n, Table, ItemAllergen, CategoryView, Role, UserRole
from django.core.files.base import ContentFile
from common import gen_unique_name, create_payment_methods, create_languanges, get_or_create_objects
import django_countries
import requests
import random


def create_currencies():
    data = [("EUR", "Euro"),
            ("USD", "Dollar"),
            ("CZK", "Czech Koruna")
            ]
    result = []
    for abbr, name in data:
        c = Currency.objects.get_or_create(abbr=abbr, name=name)
        c = c[0]
        c.save()
        result.append(c)
    return result


def create_allergens(language):
    result = []
    data = (
        "cereals with gluten",
        "crustacean (shellfish)",
        "egg",
        "fish",
        "peanuts",
        "soy",
        "milk",
        "tree nuts",
        "celery",
        "mustard",
        "sesame",
        "sulphur dioxide and sulfites",
        "lupin",
        "molluscan shellfish",
    )
    for i in range(1, len(data) + 1):
        a = Allergen.objects.get_or_create(no=i)[0]
        a.save()
        # generate name, don't append (language.abbr) for english
        if language.abbr == "en":
            name = data[i - 1]
        else:
            name = "%s (%s)" % (data[i - 1], language.abbr)
        a18n = AllergenI18n.objects.get_or_create(language=language, allergen=a, name=name)[0]
        a18n.save()
        result.append(a18n)
    return result


def get_pictures():
    print "Obtaining pictures for menu items"
    url = "http://lorempixel.com/400/400/food/%d/"
    result = []
    for i in range(1, 11):
        u = url % i
        r = requests.get(u)
        f = ContentFile(r.content)
        result.append(f)
        print "Got %s" % u
    return result


_pictures = get_pictures()
_languages = create_languanges()
_currencies = create_currencies()
for lang in _languages:
    _allergens = create_allergens(lang)  # english is last
_countries = dict(django_countries.countries).keys()
_payment_methods = create_payment_methods()
_views = get_or_create_objects(CategoryView, (CategoryView.TEXT, CategoryView.IMAGE, CategoryView.DETAIL))
_roles = get_or_create_objects(Role, (UserRole.MANAGER, UserRole.WAITER))


class Command(BaseCommand):
    help = 'Generate test restaurant data in the db'

    def add_arguments(self, parser):
        parser.add_argument('count', type=int)

    def handle(self, *args, **options):
        restaurant_count = options["count"]

        # keep track of used names, streets etc. in the variables below,
        # so we can prevent duplicates
        names = []
        streets = []
        cities = []
        # XXX factorize into smaller functions
        for item in range(restaurant_count):
            print "generate restaurant %d" % (item + 1)
            r = Restaurant()
            r.name = gen_unique_name(names, restaurant_names)
            r.save()
            print "generate address"
            a = Address(country=random.choice(_countries))
            a.street = gen_unique_name(streets, street_names)
            a.street_no = random.randint(1, 100)
            a.zip = random.randint(1000, 100000)
            a.city = gen_unique_name(cities, city_names)
            a.restaurant = r
            a.save()
            count = random.randint(5, 25)
            print "generate %d tables" % count
            for i in range(1, 1 + count):
                t = Table()
                t.restaurant = r
                t.no = i
                t.save()
            print "add supported payment methods"
            for _ in range(2, len(_payment_methods)):
                method = random.choice(_payment_methods)
                if method not in r.payment_method.all():
                    r.payment_method.add(method)
            r.save()
            print "generate menu"
            m = Menu()
            m.currency = random.choice(_currencies)
            m.language = _languages[2]
            m.restaurant = r
            m.save()
            m.translations.add(_languages[0])
            m.translations.add(_languages[1])
            m.save()

            items = []
            _cat_names = []
            count = random.randint(3, 12)
            itemid = 1
            print "generate %d categories" % count
            for j in range(1, 1 + count):
                c = Category()
                c.menu = m
                c.ordering = j
                c.view = random.choice(_views)
                c.save()
                count = random.randint(4, 20)
                # i18n stuff
                name = gen_unique_name(_cat_names, category_names)

                for lang in _languages:
                    c18n = CategoryI18n()
                    c18n.category = c
                    c18n.language = lang
                    c18n.name = name
                    if lang.abbr != "en":
                        c18n.name += "(%s)" % lang.abbr
                    c18n.save()
                print "generate %d items" % count
                for _ in range(1, count):
                    item = Item()
                    item.no = itemid
                    itemid += 1
                    item.category = c
                    item.price = "%.2f" % random.uniform(1, 110)  # 2 decimal points
                    item.save()
                    item.image.save("item%d.jpg" % item.id, random.choice(_pictures), save=True)
                    count = random.randint(0, 8)
                    # "assign %d allergens" % count
                    for k in range(count):
                        a = random.choice(_allergens).allergen
                        if a in ItemAllergen.objects.filter(item=item, allergen=a):
                            continue
                        traces = bool(random.randint(0, 1))
                        ItemAllergen.objects.get_or_create(item=item, allergen=a, traces=traces)[0].save()
                    item.save()
                    # i18n stuff
                    name = gen_unique_name(items, food_names)
                    for lang in _languages:
                        i18n = ItemI18n()
                        i18n.item = item
                        i18n.language = lang
                        i18n.name = name
                        if lang.abbr != "en":
                            i18n.name += "(%s)" % lang.abbr
                        i18n.description = "Very delicious %s. It is made with love and all the care it is needed to make a great %s." % (
                            name, name)
                        i18n.save()

            print

        self.stdout.write('Successfully added %d restaurants' % restaurant_count)


restaurant_names = """The Noodle Chef
The Modern Chicken
The Bengal Monkey
The Tropical Clam
The New Heart
Shazam
Revelations
The Lotus
The Momument
Cinnamon
Auslander Restaurant
Anthony's Italian Restaurant
Mario's Pizza & Ristorante
Carriage Court Pizza
Empress Of China
Kneaders Bakery Cafe
Daily Grind Cafe & Dessertery
Cafe Venus
Sunny Han's Wok & Grill
Ruam Mit Thai
Haven
Booby's Charcoal Rib
Matisse Cafe Restaurant
Francesca's By The River
Manny Hattan's New York Deli
Bocelli 2 Restaurant
Tommy Bahama Restaurant
Capri Steak House
Zuni
LA Margarita Restaurante
Burg's Lounge
Branded Steer
Cathay Kitchen Chinese Rstrnt
El Siboney Restaurant
Golden Pancake Restaurant
Slope's Bbq Of Roswell
Deep Blue Bar & Grill
Flyers Pizza & Subs
Union Street Restaurant
Banshee
Freedom Cafe & Pub
Old Town Pizza
Pie Town
Chris Ruth's Steak House
Ol' Mexico Restaurante
Weber Grill Restaurant
Ricardo's Italian Cafe
Hailback Enterprises
Divots At Edgewood
Sanducci's Restaurant
Dining In-Personal Chef Svc
Komegashi Japanese Restaurant
Bar Abilene
Blue Crab Coffee CO
Amerigo Restaurant
Upstairs On The Square
Town House Drive-In Restaurant
Sal's Angus Grill
A Fish Called Avalon
Brady's Landing
Newbury Street Jewelry
Tully's II Food & Spirits
Wheat Fields Restaurant
Bims Taverns Inc
Linkspass
Snow White
Tom Can Cook
Pacific Software Publishing
India Garden Inc
Microspecialists Corporation
Orland Meat Market & Deli
Dau And Company
Reid Paxson
Mark Smith
Fort Wayne Museum Of Art
G. & W Corporate Aviation Inc.
Ingersoll Dinner Theater
Aztec Cafe
Zinfandel
Malay Satay Hut
34th Street Cafe & Catering
Mineola Steak House
Hitt Communications
Terry Barlow
Mjr Accounting & Business Solutions
MANGAN
Duck-In & Gazebo
Screaming Maries Italian Market
Cafe Estela's
Hooters Of Hollywd
Jonathan Friedman
Pittsburgh Leadership Foundation
Odette's
Family Resource Mall
Dilaras Cafe
Link Core
Miss Lily's Cafe Florist
Master Griller Catering
Primanti Brothers Restaurant
Catholic Family Life Insurance
Pacific Chinese Deli
La Place At The Plaza
District 7 Grill
Planas
40th Street Cafe
Dairy Queen Brazier
El Parador Restaurant
Caliente Grille
Bravo Pizza
Hopsfrog Tavern
Rasdi Restaurant Banquet
Favazza's Inc
Matthews House Catering
Carrollwood Deli
On Safari Foods
Napa Valley Caterers
Firebonz All American Bar-B-Q
St Clements Reception Ctr
Fair Winds Fine Catering
Mansion Catering By Angelo
Capt'n John's Clambakes
Swift & CO
Private Affairs Catering Ltd
Armons
Catering CO
Hugh's Catering FL
Island Chateau
Bause-Landry Catering Inc
Dobb's International Svc Inc
Barristers Deli Restaurant
Your The Boss Inc
Kathleen's Creative Catering
Just Great Food
Roosevelt Ballroom Featuring
California Tortilla Group Inc
Colorful Palate
Edible Indulgence Llc
Common Plea Restaurant
Villa Di Roma Restaurant
Special Affairs Caterers
Atrium Country Club
Old Gin Special Event Ctr
Heaven's Peak Restaurant
Diana's Fine Catering
Gumby's Speciality Catering
Custom Catering Inc
A Touch Of Class
Casa-Di-Pizza
J R's Festival Lakes
Creative Edge Parties
Nazareth Hall
Grandview Catering
Sicola's Catering & Pvt Dining
Affinity Enterprises
Soup To Nuts Caterers
Hachi Hachi Japanese Exp Inc
Catering By John
R & R Catering
Savoir Fare Ltd
L'Italiano Catering Inc
Ace Coffee Bar Inc
Off Campus Dining Network
N American Distributors Co
Java Distribution
Goldberg Family
Unofficial
New England Envelope
Silverado Ranch Parties
Only Perfect Parties Inc
Success Personnel Services
Fun Services
J&r Electronics
Mintco
Strange Fruit Music Inc
Your Pleasure
American Express Company
Aaaa All In One Entrtn
Sirness Vending Svc Inc
Bon Soir Caterers Inc
Ponies & Pals
Sno-Mobile Of Louisiana
Plover Systems Co
V & F Coffee Inc
Shaklee
Berres Brothers Coffee
Mailcntr.com
Jen-Gil Management Svc
Coffee Plus Inc
Florida Datacore Services
G5japan
Marc Beckman
Egelman Enterprises
Lloyd's Auto Service Inc.
Devereux Books
Creative Celebrations
Cvs Svc Equipment Distrs
Coffee Millers
Pat Kelly
Fundora Party Rentals
Basch Subscriptions
Campbells Jumping For Fun
Sage Dining Svc Inc
Cool Kids Jump & Bounce
Happy Times Farm-Traveling
Trading Post Coffee Svc
First Class Travel - Phoenix
Dallas Party Rentals
Brandon Computer Services
Dino Jump
Arizona Air Bounce""".splitlines()

street_names = """Buttonwood Drive
Cambridge Court
Harrison Street
Glenwood Drive
Forest Street
Jefferson Street
8th Street
Laurel Street
Franklin Street
Hawthorne Avenue
Route 11
William Street
Aspen Drive
Valley Road
6th Street North
Augusta Drive
2nd Street East
Amherst Street
Evergreen Lane
Heather Lane
Cottage Street
Catherine Street
Hilltop Road
Route 20
Myrtle Street
York Road
Cypress Court
Lexington Court
Lake Street
Marshall Street
West Avenue
Devon Court
8th Street West
Main Street South
Dogwood Lane
Hickory Street
Depot Street
Route 9
Holly Drive
Spruce Street
Valley View Road
Church Street South
Front Street North
East Avenue
Sunset Avenue
Washington Avenue
Route 17
Colonial Avenue
Henry Street
High Street
Park Place
Rose Street
Brookside Drive
8th Street South
Cobblestone Court
Route 44
6th Avenue
7th Street
Howard Street
Magnolia Court
Oxford Road
Grand Avenue
Shady Lane
Mulberry Street
Evergreen Drive
Orchard Lane
Pin Oak Drive
Sherman Street
Cemetery Road
Heritage Drive
Rosewood Drive
Virginia Street
Center Street
Deerfield Drive
Railroad Street
Locust Lane
Cleveland Avenue
Bank Street
Elmwood Avenue
Warren Avenue
Fawn Court
Edgewood Drive
Hamilton Street
Eagle Street
James Street
John Street
Orchard Avenue
5th Avenue
Valley View Drive
Cherry Lane
Edgewood Road
Prospect Street
River Street
Route 41
Route 6
Arch Street
Grant Avenue
Beech Street
2nd Street West
Heather Court
Lafayette Street
7th Avenue
Queen Street
Forest Drive
Union Street
York Street
Main Street North
Lexington Drive
Church Road
Route 64
Beechwood Drive
Willow Lane
Orchard Street
14th Street
Locust Street
Vine Street
Lafayette Avenue
Arlington Avenue
Canterbury Road
Myrtle Avenue
State Street East
4th Avenue
White Street
Church Street North
Chestnut Avenue
Sherwood Drive
6th Street
Garden Street
Windsor Drive
Prospect Avenue
Olive Street
Woodland Avenue
Elm Street
Willow Street
River Road
Walnut Street
Country Club Drive
School Street
Woodland Drive
Hillside Avenue
Strawberry Lane
Laurel Lane
Fulton Street
Bridle Lane
10th Street
Devonshire Drive
12th Street East
Canal Street
Mill Street
Linden Avenue
Warren Street
5th Street South
2nd Street North
King Street
Carriage Drive
Bridle Court
Somerset Drive
Country Lane
Essex Court
Spring Street
Winding Way
Sheffield Drive
Sunset Drive
Briarwood Drive
Monroe Street
3rd Street West
North Avenue
Route 70
Cleveland Street
Sycamore Street
Magnolia Avenue
Schoolhouse Lane
Cambridge Drive
Valley Drive
Academy Street
Grove Avenue
Route 29
4th Street North
Maple Avenue
Crescent Street
Homestead Drive
Willow Avenue
Main Street East
Summer Street
Canterbury Court
George Street
Victoria Court
Street Road
Lantern Lane
Lilac Lane
Harrison Avenue
Park Street
West Street
9th Street
Cross Street
4th Street
Pearl Street
Route 7
Creekside Drive
Atlantic Avenue
Linden Street
Wood Street
2nd Street
Ashley Court
Liberty Street
Walnut Avenue
Route 30
1st Street
Belmont Avenue
Brandywine Drive
Pine Street
North Street
Delaware Avenue
Ivy Lane
South Street
Maple Lane
Charles Street
Lakeview Drive
Church Street
Hudson Street
Jackson Street
Wall Street
Briarwood Court
Front Street South
Riverside Drive
Pennsylvania Avenue
Jefferson Court
11th Street
Mill Road
Poplar Street
Primrose Lane
Ridge Road
Windsor Court
Route 5
Central Avenue
Madison Street
Smith Street
Oak Lane
Hillcrest Drive
Spruce Avenue
Hamilton Road
5th Street West
Manor Drive
Hartford Road
Bay Street
Lawrence Street
Cooper Street
New Street
Grant Street
Circle Drive
Route 202
5th Street East
Highland Avenue
Madison Court
Jackson Avenue
9th Street West
East Street
Holly Court
Orange Street
Hillside Drive
Lake Avenue
Lincoln Street
Linda Lane
5th Street North
Virginia Avenue
Glenwood Avenue
Devon Road
Aspen Court
Clinton Street
8th Avenue
Highland Drive
Cedar Avenue
Jones Street
Mulberry Lane
Washington Street
Meadow Lane
Parker Street
Creek Road
Hill Street
13th Street
Cedar Lane
Race Street
Franklin Avenue
Surrey Lane
Canterbury Drive
Chapel Street
3rd Street East
Durham Court
Roosevelt Avenue
Cherry Street
Country Club Road
Overlook Circle
Cedar Court
Durham Road
Andover Court
Westminster Drive
Broad Street
Broadway
Main Street West
Oxford Courti""".splitlines()

city_names = """Tielen
Doberburg
Plossig
Wenninghausen
Heuscheune
Auingen
Wurlitz
Kleingiersdorf
Wenings
Rhene
Ruschwedel
Engelsholt
Mittelurbach
Gramming
Steinfurth
Leichsenhof
Schonau
Wolpertshausen
Brautlach
Wietzenbruch
Ammeln
Paarsch
Deisendorf
Pfennigstedterfeld
Donnerstedt
Wollershausen
Jerchel
Fischern
Muderpolz
Kirchenkirnberg
Unterwangen
Prinzenmoor
Dlugi
Geyern
Reppenhagen
Bispingen
Kleinalsleben
Endham
Niederodenspiel
Vehlow
Salingen
Meinefeld
Seglohe
Boslar
Oberfrauenwald
Neckartenzlingen
Sollern
Wustendorf
Scheckwitz
Suderburg""".splitlines()

category_names = """Soups
Curries
Pasta
Roasts
Desserts
Appetisers
Stews
Cakes
Vegetables
Sauces
Pizza
Salad
Drinks
Antipasti
Sandwiches
BBQ food""".splitlines()

food_names = """Apple Pie
Sweet & Sour Chicken
Breakfast Sandwich
Tuna Casserole 
Bagels
Salmon
Sweet Potato Pie
Hot Dogs
Beef & Potato W/ Cheese Soup
Pop Tarts
Strawberry Syrup
Cheddar Biscuits From Red Lobster
Red Velvet cake/cupcakes
Strawberry Jam
Any Muffin That Doesn't Have Nuts In It
Cookie Dough Ice Cream
Toast
Almost Cereal
Bacon
Buffalo Wings
Hash Browns
Lobster
Bread Rolls
Brownies
Steak
Reuben Sandwiches
Lemon Squares
Burgers
The McGriddle
Strawberry Shortcake
Steak Fajitas 
Fruit Cocktail 
Pancakes
Subs
Chocolate Chip Cookies
Pear
BBQ Chicken
Green Beans
Eggs of any sort including Omelet's
Fruit Salad
Not a "food" but I'm obsessed with Orange Juice
Cantaloupe 
Doughnuts
Mac & Cheese
Superman Ice Cream
Fried Chicken
Grapes
BBQ Ribs
Cinnamon Rolls""".splitlines()
