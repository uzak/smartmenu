from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Max
from django.http.response import Http404
from django.utils import translation
from django_countries.fields import CountryField

RUBAXA_SORTABLE_SEP = ","


def ids(alist):
    return map(lambda x: x.id, alist)


def ordered(items, order_str, sep="|"):
    """return all items, ordered by integers in 'order_str'.
    If 'order_str' is not set, use default order"""
    # print "order_str", order_str
    if not order_str:
        return items
    # obtain ordering instructinos
    order = map(int, order_str.split(sep))
    # build a dict with IDs as keys
    tmp = {}
    for e in items:
        tmp[e.id] = e
    # make a list ordered by 'order'
    result = []
    for o in order:
        if o in tmp:
            result.append(tmp[o])
    # add omitted elements (not found in 'order_str')
    for k, v in tmp.items():
        if k not in order:
            result.insert(0, v)
    return result


def _ordering_str(data, sep=RUBAXA_SORTABLE_SEP):
    result = []
    for i in data:
        if i.ordering:
            result.append(i.ordering)
    return sep.join(map(str, result))


# Icons took from http://www.allergenchecker.co.uk/allergens.php
class Allergen(models.Model):
    no = models.PositiveSmallIntegerField()

    def __unicode__(self):
        return "Allergen (no=%d)" % self.no

    def image_uri(self):
        return "/media/allergens/%d.png" % self.no


class AllergenI18n(models.Model):
    allergen = models.ForeignKey(Allergen)
    language = models.ForeignKey("Language")
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return "%d (%s)" % (self.allergen.no, self.name)

    @staticmethod
    def for_item(item, language):
        # obtains allergens as tuples: (ItemAllergen, AllergenI18n)
        allergens = AllergenI18n.objects.filter(language=language)
        allergens = [(ItemAllergen.objects.filter(item=item, allergen=a18n.allergen).first(), a18n) for a18n in
                     allergens]
        return allergens


class Currency(models.Model):
    abbr = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name_plural = "Currencies"

    def __unicode__(self):
        return self.abbr


class Language(models.Model):
    abbr = models.CharField(max_length=16, unique=True)
    # name is in local language (i.e. deutsch, english, slovensky)
    name = models.CharField(max_length=255)

    @staticmethod
    def get_current():
        ui_lang = translation.get_language()
        return Language.objects.filter(abbr=ui_lang).first()

    def __unicode__(self):
        return "%s (%s)" % (self.abbr, self.name)

    @staticmethod
    def order(languages, order_str=None):
        """return all languages, ordered by 'language_order'.
        If 'language_order' is not set, use default order"""
        return ordered(languages, order_str)


class Menu(models.Model):
    currency = models.ForeignKey(Currency)
    language = models.ForeignKey(Language)
    restaurant = models.OneToOneField("Restaurant")
    translations = models.ManyToManyField(Language, related_name="menu_translations")
    show_numbers = models.BooleanField(default=True)

    def all_languages(self):
        result = [self.language]
        for tr in self.translations.all():
            result.append(tr)
        return result

    class Meta:
        verbose_name_plural = "Menues"

    def __unicode__(self):
        return "Menu (id=%d) for restaurant %d" % (self.id, self.restaurant.id)

    def categories_for_language(self, language):
        """return all the categories of this menu in given language, if categories in given
        language cannot be found, default to primary menu language"""
        if language not in self.all_languages():
            raise Http404("Not supported language")
        result = []
        for c in self.category_set.all():
            cat = CategoryI18n.objects.filter(language=language, category=c).first()
            if not cat:  # try default category
                cat = CategoryI18n.objects.filter(language=self.language, category=c).first()
            if not cat:  # not found for given language, not found for master language
                # print "lang", language
                # print "default lang", self.language
                # print "all category languages:", CategoryI18n.objects.filter(category = c).all()
                raise Http404("Category (%d) with no I18N" % c.id)
            result.append(cat)
        result = sorted(result, lambda x, y: cmp(x.category.ordering, y.category.ordering))
        return result

    def category_ordering_str(self, sep=RUBAXA_SORTABLE_SEP):
        return _ordering_str(self.category_set.all(), sep=sep)


class Category(models.Model):
    """Category of a menu card"""

    menu = models.ForeignKey(Menu)
    ordering = models.SmallIntegerField(blank=True, null=True)
    view = models.ForeignKey("CategoryView")

    class Meta:
        verbose_name_plural = "Categories"

    def __unicode__(self):
        return "Category: (id=%d)" % self.id

    def item_ordering_str(self, sep=RUBAXA_SORTABLE_SEP):
        return _ordering_str(self.item_set.all(), sep=sep)

    def items_for_language(self, language):
        """return all the items of this category in given language, if items in given
        language cannot be found, default to primary menu language"""
        if language not in self.menu.all_languages():
            raise Http404("Not supported language")
        result = []
        for i in self.item_set.all():
            item = ItemI18n.objects.filter(language=language, item=i).first()
            if not item:  # try default language
                item = ItemI18n.objects.filter(language=self.menu.language, item=i).first()
            if not item:  # not found for given language, not found for master language
                raise Http404("Item (%d) with no I18N" % i.id)
            result.append(item)
        result = sorted(result, lambda x, y: cmp(x.item.ordering, y.item.ordering))
        return result


class CategoryI18n(models.Model):
    category = models.ForeignKey(Category)
    language = models.ForeignKey(Language)
    name = models.CharField(max_length=255)

    def __init__(self, *args, **kw):
        super(CategoryI18n, self).__init__(*args, **kw)
        # In case a category hasn't been translated yet, master's language category is used. In this
        # case we mark the object as not translated.
        self.translated = True

    @staticmethod
    def get_for_language(language, cat):
        """try to obtain the CategoryI18n for given 'language'.
        If language is not found, try master language. Otherwise fail
        """
        for lang in (language, cat.menu.language):
            cat18n = CategoryI18n.objects.filter(language=lang, category=cat).first()
            if cat18n:
                return cat18n
        raise Http404("ItemI18N not found for language (%s) and Item (%d)" % (language.abbr, cat.id))

    def __unicode__(self):
        return "%s (Cat: %d, lang: %s)" % (self.name, self.category.id, self.language.abbr)


class Item(models.Model):
    """a MenuItem"""
    no = models.PositiveSmallIntegerField(null=True, blank=True)
    price = models.FloatField()
    category = models.ForeignKey(Category)
    ordering = models.SmallIntegerField(blank=True, null=True)
    image = models.ImageField(upload_to="items/")

    # used in the admin (preview of the image)
    def image_preview(self):
        return '<img src="%s" />' % (self.url())

    image_preview.allow_tags = True

    @staticmethod
    def next_free_no(menu):
        result = Item.objects.filter(category__menu=menu).aggregate(Max("no"))["no__max"]
        if result:
            return result + 1
        return 1

    def currency(self):
        return self.category.menu.currency

    def __unicode__(self):
        return "Item (id=%d)" % self.id


# http://stackoverflow.com/questions/5372934/how-do-i-get-django-admin-to-delete-files-when-i-remove-an-object-from-the-datab
# Receive the pre_delete signal and delete the file associated with the model instance.
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver
import os


@receiver(pre_delete, sender=Item)
def mymodel_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.image.delete(False)


@receiver(models.signals.pre_save, sender=Item)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """Deletes image from filesystem
    when corresponding `Item` object is changed.
    """
    if not instance.pk:
        return False

    try:
        old_file = Item.objects.get(pk=instance.pk).image
    except Item.DoesNotExist:
        return False

    new_file = instance.image
    if not old_file == new_file:
        try:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)
        except Exception:
            return False


class ItemI18n(models.Model):
    item = models.ForeignKey(Item)
    language = models.ForeignKey(Language)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __init__(self, *args, **kw):
        super(ItemI18n, self).__init__(*args, **kw)
        # In case an item hasn't been translated yet, master's language item is used. In this
        # case we mark the object as not translated in views.py.
        self.translated = True

    @staticmethod
    def get_for_language(language, item):
        """try to obtain the ItemI18N for given 'language'.
        If language is not found, try master language. Otherwise fail"""
        for lang in (language, item.category.menu.language):
            i18n = ItemI18n.objects.filter(language=lang, item=item).first()
            if i18n:
                i18n.translated = (i18n.language == language)
                return i18n
        raise Http404("ItemI18N not found for language (%s) and Item (%d)" % (language.abbr, item.id))

    def __unicode__(self):
        return "%s (Item.id: %d, lang: %s)" % (self.name, self.item.id, self.language.abbr)


class ItemAllergen(models.Model):
    """Relationship Item__contains__Allergen"""

    item = models.ForeignKey(Item)
    allergen = models.ForeignKey(Allergen)
    traces = models.BooleanField(default=False)  # contains just traces

    def __unicode__(self):
        result = "item=%d, allergen.no=%d, traces=%d" % (self.item.id, self.allergen.no, self.traces)
        return result


class Address(models.Model):
    class Meta:
        verbose_name_plural = "Addresses"

    street = models.CharField(max_length=255)
    street_no = models.CharField(max_length=255)
    zip = models.PositiveSmallIntegerField()
    city = models.CharField(max_length=255)
    country = CountryField()
    restaurant = models.OneToOneField("Restaurant")

    def __unicode__(self):
        return "%s %s; %d %s; %s" % (self.street, self.street_no, self.zip, self.city, self.country)

    def as_json(self):
        return dict(
            street=self.street,
            street_no=self.street_no,
            zip_code=self.zip,
            city=self.city,
            country=self.country.code,
        )


class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    website = models.CharField(max_length=255, blank=True)
    facebook = models.CharField(max_length=255, blank=True)
    # logo = models.ImageField(upload_to="restaurant")
    payment_method = models.ManyToManyField("PaymentMethod")

    def __unicode__(self):
        return self.name

    def as_json(self):
        return dict(
            id=self.id,
            name=self.name,
            address=self.address.as_json(),
        )


class Role(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    role = models.ForeignKey(Role)
    restaurant = models.ForeignKey(Restaurant)

    MANAGER = "manager"
    WAITER = "waiter"

    @staticmethod
    def add(user, restaurant, rolestr):
        role = UserRole()
        role.user = user
        role.role = Role.objects.filter(name=rolestr).first()
        role.restaurant = restaurant
        role.save()

    def __unicode__(self):
        return "%s / %s @ %s" % (self.user, self.role, self.restaurant)


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    allergens = models.ManyToManyField(Allergen, blank=True)

    @staticmethod
    def for_user(user):
        if user.is_authenticated():
            return UserProfile.objects.get_or_create(user=user)[0]

    def __unicode__(self):
        return "UserProfile for %s" % self.user


class Table(models.Model):
    no = models.PositiveSmallIntegerField()
    description = models.TextField(blank=True)
    restaurant = models.ForeignKey(Restaurant)

    def __unicode__(self):
        return "%d (%s)" % (self.no, self.restaurant.name)

    def occuppied(self):
        orders = Order.objects.filter(table=self, checkout__isnull=True)
        return not not orders


class Order(models.Model):
    checkin = models.DateTimeField()
    table = models.ForeignKey(Table)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    checkout = models.DateTimeField(null=True, blank=True)

    # XXX support change of tables in the restaurant?
    # XXX add check-in-by-$USERNAME to see who did the check-in?

    def is_closed(self):
        return not not self.checkout

    def currency(self):
        return self.table.restaurant.menu.currency

    def total(self, confirmed_only=False):
        result = 0
        for oi in self.orderitem_set.all():
            if confirmed_only and not oi.confirmed:
                continue
            result += (oi.amount * oi.item.price)
        return result

    def total_confirmed(self):
        return self.total(True)

    def add_item(self, i18n, amount=1):
        # check if the item already exists in the order and update the amount
        exists = False
        orderitem = None
        for oi in self.orderitem_set.all():
            # but don't update amount on confirmed items
            if oi.item == i18n.item and not oi.confirmed:
                orderitem = oi
                orderitem.amount += amount
                exists = True
                break
        # item doesn't exist so create it
        if not exists:
            orderitem = OrderItem()
            orderitem.amount = amount
            orderitem.order = self
            orderitem.item = i18n.item
        orderitem.name = i18n.name
        orderitem.price = i18n.item.price
        orderitem.currency = self.table.restaurant.menu.currency
        orderitem.save()
        return orderitem

    @staticmethod
    def for_user(user, restaurant, empty=False):
        """return first empty not-closed Order for the 'user' at the
        'restaurant'"""
        if not user.is_authenticated():
            return None
        kw = dict(table__in=ids(restaurant.table_set.all()), user=user, checkout__isnull=True)
        if empty:
            kw["orderitem__isnull"] = True
        return Order.objects.filter(**kw).first()

    def __unicode__(self):
        return "Order (id=%d)" % self.id


class OrderItem(models.Model):
    """A MenuItem on an Order"""

    created = models.DateTimeField(auto_now_add=True)
    item = models.ForeignKey(Item)
    order = models.ForeignKey(Order)

    comment = models.TextField(blank=True)
    confirmed = models.DateTimeField(blank=True, null=True)
    amount = models.PositiveSmallIntegerField()
    # copy of price, currency, name  because they can change in time
    # XXX add item.no. and master_menu.item.name too?
    price = models.FloatField()
    currency = models.ForeignKey(Currency)
    # from localised menu (the user saw at the time of ordering)
    name = models.CharField(max_length=255)

    def subtotal(self):
        return self.item.price * self.amount

    def __unicode__(self):
        return "%dx (item.id=%d)" % (self.amount, self.item.id)


class Review(models.Model):
    rating = models.PositiveSmallIntegerField(validators=(
        MinValueValidator(1),
        MaxValueValidator(5)
    ))
    text = models.TextField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    date = models.DateTimeField(auto_now_add=True)
    orderitem = models.OneToOneField(OrderItem)

    def __unicode__(self):
        return "Review: %d" % self.id


# return "Review for item.id=%s, from user=%s" % (self.item.id, self.user)


class PaymentMethod(models.Model):
    # e.g. visa, cash, ...
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return self.name


class Payment(models.Model):
    datetime = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey(Order)
    amount = models.FloatField()
    currency = models.ForeignKey(Currency)
    method = models.ForeignKey(PaymentMethod)

    def __unicode__(self):
        return "Payment: Order.id=%d, %.2f %s, %s" % (self.order.id, self.amount, self.currency.abbr, self.datetime)


class CategoryView(models.Model):
    """The type of view used for a category"""

    IMAGE = "image_view (one big image)"
    DETAIL = "detailled_view (one small image and detailled text)"
    TEXT = "text_view (no image)"

    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    def __unicode__(self):
        return "%s" % self.name
