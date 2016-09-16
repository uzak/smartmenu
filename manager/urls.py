from django.conf.urls import url
from . import views

urlpatterns = [
    # AJAX stuff
    url(r"^menu/(?P<id>\d+)/category/ordering", views.set_category_ordering, name="set_category_ordering"),
    url(r"^category/(?P<id>\d+)/ordering", views.set_item_ordering, name="set_item_ordering"),
    url(r"^category/(?P<id>\d+)/view/(?P<view_id>\d+)", views.set_category_view, name="set_category_view"),

    # manager
    url(r"^$", views.index, name="index"),
    url(r"^restaurant/(?P<id>\d+)$", views.for_restaurant, name="for_restaurant"),
    url(r"^restaurant/create$", views.create_restaurant, name="create_restaurant"),
    url(r"^restaurant/(?P<id>\d+)/manage$", views.manage_restaurant, name="manage_restaurant"),
    url(r"^restaurant/(?P<id>\d+)/statistics$", views.statistics, name="statistics"),
    url(r"^restaurant/(?P<id>\d+)/delete", views.delete_restaurant, name="delete_restaurant"),
    url(r"^restaurant/(?P<id>\d+)/add_table$", views.add_table, name="add_table"),
    url(r"^restaurant/(?P<id>\d+)/tables$", views.table_index, name="table_index"),
    url(r"^table/(?P<id>\d+)/delete$", views.delete_table, name="delete_table"),
    url(r"^menu/(?P<id>\d+)/manage$", views.manage_menu, name="manage_menu"),
    url(r"^category/(?P<id>\d+)/manage", views.manage_category, name="manage_category"),
    url(r"^category/(?P<id>\d+)/delete", views.delete_category, name="delete_category"),
    url(r"^category/(?P<id>\d+)/rename", views.rename_category, name="rename_category"),
    url(r"^category/(?P<id>\d+)/add_item", views.add_item, name="add_item"),
    url(r"^menu/(?P<id>\d+)/category/add$", views.add_category, name="add_category"),
    url(r"^item/(?P<id>\d+)/manage$", views.manage_item, name="manage_item"),
    url(r"^item/(?P<id>\d+)/delete", views.delete_item, name="delete_item"),
    url(r"^menu/(?P<menu_id>\d+)/translation/add$", views.add_translation, name="add_translation"),
    url(r"^menu/(?P<menu_id>\d+)/translation/(?P<lang_id>\d+)/delete$", views.delete_translation,
        name="delete_translation"),
]
