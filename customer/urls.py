from django.conf.urls import url
from . import views

urlpatterns = [
    url(r"^$", views.index, name="index"),
    url(r"^restaurant/(\d+)/order$", views.order, name="order"),
    url(r"^orderitem/(\d+)/confirm$", views.confirm_orderitem, name="confirm_orderitem"),
    url(r"^orderitem/(\d+)/remove", views.remove_orderitem, name="remove_orderitem"),
    url(r"^order/(\d+)/checkout$", views.checkout, name="checkout"),
    url(r"^order/(?P<order_id>\d+)/pay/(?P<payment_method_id>\d+)$", views.pay, name="pay"),
    url(r"^order/(\d+)/feedback$", views.feedback, name="feedback"),
    url(r"^restaurant/(?P<restaurant_id>\d+)/check-in$", views.check_in, name="check_in"),
    url(r"^restaurant/(?P<restaurant_id>\d+)/order/(?P<item_id>\d+)$", views.order_item, name="order_item"),
    url(r"^restaurant/(\d+)/menu$", views.menu, name="menu"),

    # AJAX handlers
    url(r"^restaurant/(?P<id>\d+)/check-for-order$", views.check_for_open_order, name="check_for_open_order"),
    url(r"^restaurant/search$", views.search, name="restaurant_search"),

]
