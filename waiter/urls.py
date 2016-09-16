from django.conf.urls import url
from . import views

urlpatterns = [
    url(r"^$", views.index, name="waiter"),
    url(r"^restaurant/(?P<id>\d+)$", views.for_restaurant, name="for_restaurant"),
    url(r"^restaurant/(?P<id>\d+)/qr/read$", views.read_qr, name="read_qr"),
    url(r"^checkin/(?P<table_id>\d+)/(?P<user_id>\d+)$", views.checkin_customer, name="checkin_customer"),
    url(r"^table/choose", views.choose_table, name="choose_table"),
    url(r"^checkout/(?P<id>\d+)", views.checkout, name="checkout"),
]
