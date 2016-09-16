from django.contrib import admin
# Register your models here.

from .models import *


class ItemAdmin(admin.ModelAdmin):
    list_filter = ['category']
    list_display = ("id", "category")
    readonly_fields = ("image_preview",)


class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "amount", "name", "price", "confirmed")


class ItemI18nAdmin(admin.ModelAdmin):
    list_filter = ['language']
    list_display = ("id", "name", "language")
    search_fields = ("id", "item__id", "name")


class CategoryAdmin(admin.ModelAdmin):
    list_filter = ['menu']
    list_display = ("id", "menu", "view")


class CategoryI18nAdmin(admin.ModelAdmin):
    list_filter = ['language', "category"]
    list_display = ("id", "name", "language")


class ItemAllergenAdmin(admin.ModelAdmin):
    list_filter = ['item', "allergen"]
    list_display = ('id', 'traces', 'allergen', 'item')


class AllergenI18nAdmin(admin.ModelAdmin):
    list_display = ("allergen", "language", "name")
    list_filter = ("language", "allergen")


class UserProfileAdmin(admin.ModelAdmin):
    filter_horizontal = ('allergens',)


class RestaurantAdmin(admin.ModelAdmin):
    filter_horizontal = ('payment_method',)


class MenuAdmin(admin.ModelAdmin):
    filter_horizontal = ("translations",)


admin.site.register(Menu, MenuAdmin)
admin.site.register(Language)
admin.site.register(Currency)
admin.site.register(Category, CategoryAdmin)
admin.site.register(CategoryI18n, CategoryI18nAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(ItemI18n, ItemI18nAdmin)
admin.site.register(Allergen)
admin.site.register(AllergenI18n, AllergenI18nAdmin)
admin.site.register(Order)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Payment)
admin.site.register(PaymentMethod)
admin.site.register(Review)
admin.site.register(Restaurant, RestaurantAdmin)
admin.site.register(Table)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Role)
admin.site.register(UserRole)
admin.site.register(Address)
admin.site.register(ItemAllergen, ItemAllergenAdmin)
admin.site.register(CategoryView)
