from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from main.models import *
from main.forms import *
import json
import os
import qrcode


def index(request):
    # find out if the logged-in user is also manager or waiter
    manager_at = []
    waiter_at = []
    if request.user.is_authenticated():
        roles = UserRole.objects.filter(user=request.user)
        manager_at = filter(lambda x: x.role.name == UserRole.MANAGER, roles)
        waiter_at = filter(lambda x: x.role.name == UserRole.WAITER, roles)

    return render(request, "customer/index.html", {
        "hide_logo": True,
        "manager_at": manager_at,
        "waiter_at": waiter_at,
    })


def search(request):
    """search in a restaurant's name based on `q` parameter"""
    # XXX replace with a more robust search in case of many restaurants in the system

    result = []
    if "q" in request.GET:
        result = []
        q = request.GET["q"]
        # search the restaurant's name
        restaurants = Restaurant.objects.filter(name__icontains=q)
        for r in sorted(restaurants, lambda x, y: cmp(x.name, y.name)):
            result.append({
                "id": r.id,
                "name": r.name,
                "street": r.address.street,
                "street_no": r.address.street_no,
                "city": r.address.city,
                "zip_code": r.address.zip,
                "country": r.address.country.code,
            })
    return HttpResponse(json.dumps(result), content_type='application/json')


@login_required
def order_item(request, restaurant_id, item_id):
    """order an item for the logged-in user at a restaurant.
    """
    item = get_object_or_404(Item, id=item_id)
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    l = _get_menu_language(request, restaurant.menu)
    i18n = get_object_or_404(ItemI18n, language=l, item=item)

    # create order
    order = Order.for_user(request.user, restaurant)
    order.add_item(i18n)

    return redirect("customer:menu", restaurant.id)


@login_required
def check_in(request, restaurant_id):
    """check-in the logged-in user at restaurant
    """
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    # is an order already open?
    if Order.for_user(request.user, restaurant) is not None:
        return redirect("customer:menu", restaurant.id)

    _create_qr_code(request.user, restaurant)

    # wait for an signal, i.e. for an order to be opened (from waiter)
    return render(request, "customer/check-in.html", {
        "restaurant": restaurant})


@login_required
def check_for_open_order(request, id):
    """check if for given user and restaurant an order objects exists,
    i.e. a waiter has logged in the user"""
    restaurant = get_object_or_404(Restaurant, id=id)
    order = Order.for_user(request.user, restaurant, True)
    return HttpResponse("%s" % (order and order.id or ""))


def menu(request, id):
    """render a menu for a restaurant
    """
    restaurant = get_object_or_404(Restaurant, id=id)
    lang = _get_menu_language(request, restaurant.menu)
    order = Order.for_user(request.user, restaurant)
    prof = UserProfile.for_user(request.user)

    # store URL in case somebody wants to sign in and return back
    request.session["next"] = request.build_absolute_uri()

    # create a localized category tree with items and allergens.
    categories = []
    for c18n in restaurant.menu.categories_for_language(lang):
        cat_data = []
        for i18n in c18n.category.items_for_language(lang):
            allergens = []
            traces = []
            for itemallergen in i18n.item.itemallergen_set.all():
                a18n = get_object_or_404(AllergenI18n, language=lang, allergen=itemallergen.allergen)
                warn = prof and a18n.allergen in prof.allergens.all()
                if itemallergen.traces:
                    traces.append((a18n, warn))
                else:
                    allergens.append((a18n, warn))
            cat_data.append((i18n.item, i18n, allergens, traces))
        categories.append((c18n, cat_data))

    # available menu languages
    languages = [restaurant.menu.language]
    languages.extend(restaurant.menu.translations.all())

    return render(request, "customer/menu.html", {
        "language": lang,
        "menu_languages": languages,
        "categories": categories,
        "restaurant": restaurant,
        "order": order,
        "all_allergens": AllergenI18n.objects.filter(language=lang),
    })


def order(request, id):
    """render the summary page for an order
    """
    restaurant = get_object_or_404(Restaurant, id=id)
    order = Order.for_user(request.user, restaurant)
    lang = _get_menu_language(request, restaurant.menu)

    # guards
    if not order:
        raise Http404("Invalid order")

    # collect confirmed and not yet confirmed order items
    confirmed = []
    unconfirmed = []
    for oi in order.orderitem_set.all():
        oi18n = get_object_or_404(ItemI18n, language=lang, item=oi.item)
        if oi.confirmed:
            confirmed.append((oi, oi18n))
        else:
            unconfirmed.append((OrderItemForm(instance=oi), oi18n))

    return render(request, "customer/order.html", {
        "restaurant": restaurant,
        "order": order,
        "unconfirmed": unconfirmed,
        "confirmed": confirmed,
    })


@login_required
def confirm_orderitem(request, id):
    """confirm an item on the order
    """
    oi = get_object_or_404(OrderItem, id=id)

    # update order item
    form = OrderItemForm(request.POST, instance=oi)
    oi.confirmed = timezone.now()
    form.save()

    return redirect("customer:order", oi.order.table.restaurant.id)


@login_required
def remove_orderitem(request, id):
    """remove an item from the order
    """
    oi = get_object_or_404(OrderItem, id=id)
    oi.delete()
    return redirect("customer:order", oi.order.table.restaurant.id)


def _get_menu_language(request, menu):
    """return the actual menu language
    """
    result = menu.language

    # first obtain the language from URI
    lang = request.GET.get("l", None)
    if lang:
        result = Language.objects.filter(abbr=lang).first()
    else:
        # if not found, then obtain language form his browser's settings
        lang = Language.get_current()
        if lang in menu.translations.all():
            result = lang
            # print "get_menu_language for %s: %s" % (user, result)
    return result


@login_required
def checkout(request, id):
    """checkout the user. This closes the order and prompts the user to pay
    """
    order = get_object_or_404(Order, id=id)
    payment_methods = order.table.restaurant.payment_method.all()

    # if order is NOT empty
    if not order.total(confirmed_only=True):
        restaurant = order.table.restaurant
        order.checkout = timezone.now()
        order.save()
        return redirect("customer:menu", restaurant.id)

    return render(request, "customer/checkout.html", {
        "order": order,
        "restaurant": order.table.restaurant,
        "payment_methods": payment_methods,
    })


@login_required
def feedback(request, id):
    order = get_object_or_404(Order, id=id)

    # is there feedback posted?
    if request.POST:
        oi_id = request.POST.get("id")
        oi = get_object_or_404(OrderItem, id=oi_id)
        if Review.objects.filter(orderitem=oi).first():
            raise Http404("Review already exists for OrderItem (%d)" % oi.id)
        if oi.order.user != request.user:
            raise Http404("Requested OrderItem (%d) doesn't belong to you" % oi.id)
        rating = request.POST.get("rating")
        text = request.POST.get("text")
        # create review objects and save
        r = Review()
        r.text = text
        r.rating = rating
        r.orderitem = oi
        r.user = request.user
        r.save()

    # collect all unique items in the order
    orderitems = {}
    for oi in order.orderitem_set.all():
        orderitems[oi.item] = oi

    orderitems = sorted(orderitems.values(), lambda x, y: cmp(hasattr(x, "review"), hasattr(y, "review")))

    return render(request, "customer/feedback.html", {
        "order": order,
        "orderitems": orderitems,
        "restaurant": order.table.restaurant,
    })


@login_required
def pay(request, order_id, payment_method_id):
    order = get_object_or_404(Order, id=order_id)
    pm = get_object_or_404(PaymentMethod, id=payment_method_id)

    # checking for invalid logic
    payment = Payment.objects.filter(order=order).first()
    if payment:
        raise Http404("Order %d already paid for (Payment.id=%d)." % (order.id, payment.id))

    # do pay
    payment = Payment()
    payment.currency = order.table.restaurant.menu.currency
    payment.amount = order.total_confirmed()
    payment.order = order
    payment.method = pm
    payment.save()

    # XXX do the checkout. this is for demo only. in production this will be done by waiter after paying
    order.checkout = timezone.now()
    order.save()

    return render(request, "customer/paid.html", {
        "restaurant": order.table.restaurant,
        "order": order,
    })


def _get_logo_link(request):
    """return the link to be used in the logo (restaurant's name in the header)"""
    p = unicode(request.path)
    for pat in ("customer", "waiter", "manager"):
        if p.find("/%s" % pat) >= 0:
            return "%s:index" % pat
    assert 0


def _create_qr_code(user, restaurant):
    """create a QR code used for check-in by the waiter
    """
    code = "%d:%d" % (user.id, restaurant.id)
    img = qrcode.make(code)
    # save to file
    path = os.path.join(settings.MEDIA_ROOT, "qr")
    if not os.path.exists(path):
        os.mkdir(path)
    img_path = os.path.join(path, "%d.png" % user.id)
    img.save(img_path, "png")
