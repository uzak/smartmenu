from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from main.models import *
from dateutil.relativedelta import relativedelta
from main.views import get_role
from django.contrib.auth import get_user_model


def index(request):
    roles = UserRole.objects.filter(user=request.user, role__name__icontains=UserRole.WAITER)
    if not roles:
        raise Http404("You are not registered as a waiter")
    elif len(roles) > 1:
        return render(request, "waiter/select-restaurant.html", {
            "roles": roles,
        })
    return for_restaurant(request, roles[0].restaurant.id)


def for_restaurant(request, id):
    role = get_role(request.user, id, UserRole.WAITER)
    restaurant = role.restaurant

    # display orders for the last two days.
    # XXX bulgarian constant 2
    start = timezone.now() - relativedelta(days=2)
    orders = Order.objects.filter(table__restaurant=restaurant, checkin__gt=start)
    orders = orders.order_by("-checkin")

    return render(request, "waiter/index.html", {
        "restaurant": restaurant,
        "orders": orders
    })


def read_qr(request, id):
    return render(request, "waiter/check-in.html", {
        "restaurant_id": id
    })


def checkin_customer(request, table_id, user_id):
    table = get_object_or_404(Table, id=table_id)
    user = get_object_or_404(get_user_model(), id=user_id)

    # check if similar open order already exists
    open_orders = Order.for_user(user, table.restaurant, empty=True)
    if open_orders:
        raise Http404("User already checked-in: %s" % open_orders)

    order = Order()
    order.table = table
    order.user = user
    order.checkin = timezone.now()
    order.save()

    # print "checkin the customer: ", order

    return redirect("waiter:for_restaurant", table.restaurant.id)


def choose_table(request):
    data = request.GET.get("data")
    if not data:
        raise Http404("Data not specified")
    user_id, restaurant_id = data.split(":")

    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    get_role(request.user, restaurant.id, UserRole.WAITER)  # just a guard

    # choose table
    tables = Table.objects.filter(restaurant_id=restaurant.id)
    return render(request, "waiter/choose-table.html", {
        "tables": tables,
        "user_id": user_id,
        "restaurant_id": restaurant.id,
    })


def checkout(request, id):
    order = get_object_or_404(Order, id=id)
    if order.checkout:
        raise Http404("Order (%d) already checked out", order.id)
    restaurant_id = order.table.restaurant.id
    get_role(request.user, restaurant_id, UserRole.WAITER)  # guard

    # do the checkout
    order.checkout = timezone.now()
    order.save()

    return redirect("waiter:for_restaurant", restaurant_id)
