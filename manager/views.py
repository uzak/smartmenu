from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from main import util
from main.forms import *
from main.views import get_role


@login_required
def index(request):
    roles = UserRole.objects.filter(user=request.user, role__name__icontains=UserRole.MANAGER)
    if not roles:
        return render(request, "manager/no-restaurant.html")
    if len(roles) > 1:
        return render(request, "manager/select-restaurant.html", {
            "roles": roles,
        })
    return redirect("manager:for_restaurant", roles[0].restaurant.id)


@login_required
def for_restaurant(request, id):
    role = get_role(request.user, id, UserRole.MANAGER)
    restaurant = role.restaurant

    roles = UserRole.objects.filter(user=request.user, role__name__icontains=UserRole.MANAGER)

    return render(request, "manager/index.html", {
        "restaurant": restaurant,
        "show_change_restaurant": len(roles) > 1,
    })


@login_required
def create_restaurant(request):
    restaurant_form = RestaurantForm()
    address_form = AddressForm()
    menu_form = MenuForm()

    if request.POST:
        restaurant_form = RestaurantForm(request.POST)
        address_form = AddressForm(request.POST)
        menu_form = MenuForm(request.POST)
        if restaurant_form.is_valid() and address_form.is_valid() and menu_form.is_valid():
            # save objects from the UI
            restaurant = restaurant_form.save()
            address = address_form.save(commit=False)
            address.restaurant = restaurant
            address.save()
            # add a manager's and waiter's role
            UserRole.add(request.user, restaurant, UserRole.MANAGER)
            UserRole.add(request.user, restaurant, UserRole.WAITER)
            # add a menu
            menu = menu_form.save(commit=False)
            menu.restaurant = restaurant
            menu.save()
            return redirect("manager:index")

    return render(request, "manager/create-restaurant.html", {
        "restaurant_form": restaurant_form,
        "address_form": address_form,
        "menu_form": menu_form,
    })


@login_required
def manage_restaurant(request, id):
    restaurant = get_object_or_404(Restaurant, id=id)
    get_role(request.user, id, UserRole.MANAGER)

    if request.POST:
        restaurant_form = RestaurantForm(request.POST, instance=restaurant)
        address_form = AddressForm(request.POST, instance=restaurant.address)
        if restaurant_form.is_valid():
            restaurant_form.save()
        if address_form.is_valid():
            address_form.save()
        return redirect("manager:for_restaurant", restaurant.id)
    else:
        restaurant_form = RestaurantForm(instance=restaurant)
        address_form = AddressForm(instance=restaurant.address)

    return render(request, "manager/manage-restaurant.html", {
        "restaurant": restaurant,
        "restaurant_form": restaurant_form,
        "address_form": address_form,
    })


@login_required
def manage_menu(request, id):
    menu = get_object_or_404(Menu, id=id)
    get_role(request.user, menu.restaurant.id, UserRole.MANAGER)

    if request.POST:
        menu_form = MenuForm(request.POST, instance=menu)
        if menu_form.is_valid():
            menu_form.save()
    else:
        menu_form = MenuForm(instance=menu)
    categories = CategoryI18n.objects.filter(category__menu=menu, language=menu.language)
    categories = categories.order_by("category__ordering")

    return render(request, "manager/manage-menu.html", {
        "restaurant": menu.restaurant,  # needed for displaying restaurant's name in the header
        "form": menu_form,
        "menu": menu_form.instance,
        "categories": categories,
        "ordering": menu.category_ordering_str(),
        "add_cat_form": AddCategoryForm(),
        "add_translation_form": AddTranslationForm(menu),
    })


@login_required
def manage_category(request, id):
    cat = get_object_or_404(Category, id=id)
    get_role(request.user, cat.menu.restaurant.id, UserRole.MANAGER)

    language = request.GET.get("l")
    if language:
        language = Language.objects.filter(abbr=language).first()
    if not language:
        language = cat.menu.language

    cat18n = CategoryI18n.objects.filter(category=cat, language=language).first()
    # XXX if there is no translation? get master language translation
    if cat18n is None:
        cat18n = CategoryI18n.objects.filter(category=cat, language=cat.menu.language).first()
        cat18n.translated = False

    items = cat.items_for_language(language)

    # languages (language, is_current_language, has_translation)
    languages = []
    for lang in cat.menu.all_languages():
        languages.append((lang, lang == language, CategoryI18n.objects.filter(language=lang, category=cat).first(),))

    # view
    change_view_form = ChangeViewForm(cat)

    # set next in case of renaming category
    request.session["next"] = request.build_absolute_uri()

    # XXX use a form here with the ability to change the view
    return render(request, "manager/manage-category.html", {
        "cat": cat,
        "restaurant": cat.menu.restaurant,  # needed for displaying restaurant's name in the header
        "language": language,
        "languages": languages,
        "cat18n": cat18n,
        "items": items,
        "change_view_form": change_view_form,
        "ordering": cat.item_ordering_str(),
    })


@login_required
def manage_item(request, id):
    item = get_object_or_404(Item, id=id)
    get_role(request.user, item.category.menu.restaurant.id, UserRole.MANAGER)  # guard

    # default language (first from GET, if not, then default menu language)
    # XXX factorize into helper
    language = request.GET.get("l")
    if language:
        language = Language.objects.filter(abbr=language).first()
    if not language:
        language = item.category.menu.language

    item18n = ItemI18n.get_for_language(language, item)
    cat18n = CategoryI18n.get_for_language(language, item.category)

    form = ManageItemForm(item18n)
    if request.method == 'POST':
        ManageItemForm.save_allergens(request.POST, item)
        form = ManageItemForm(item18n, request.POST, request.FILES)
        if form.is_valid():
            item18n = form.save(language)
            form = ManageItemForm(item18n)  # needed or the image won't show up in the form. XXX

    # languages (language, is_current_language, translation)
    languages = []
    for lang in item.category.menu.all_languages():
        tr = ItemI18n.objects.filter(language=lang, item=item).first()
        languages.append((lang, lang == language, tr,))

    return render(request, "manager/manage-item.html", {
        "restaurant": item.category.menu.restaurant,
        "cat18n": cat18n,
        "item18n": item18n,
        "form": form,
        "allergens": AllergenI18n.for_item(item, language),
        "languages": languages,
        "language": language,
    })


@login_required()
def add_item(request, id):
    cat = get_object_or_404(Category, id=id)
    get_role(request.user, cat.menu.restaurant.id, UserRole.MANAGER)  # guard

    language = cat.menu.language
    form = AddItemForm(cat.menu)

    if request.method == "POST":
        form = AddItemForm(cat.menu, request.POST, request.FILES)
        if form.is_valid():
            item18n = form.save(cat, language)
            AddItemForm.save_allergens(request.POST, item18n.item)
            return redirect("manager:manage_item", item18n.item.id)

    return render(request, "manager/add-item.html", {
        "form": form,
        "language": language,
        "currency": cat.menu.currency,
        "restaurant": cat.menu.restaurant,
        "cat18n": CategoryI18n.get_for_language(language, cat),
        "allergens": AllergenI18n.for_item(None, language),
    })


@login_required
def delete_item(request, id):
    item = get_object_or_404(Item, id=id)
    category = item.category
    get_role(request.user, category.menu.restaurant.id, UserRole.MANAGER)  # guard

    lang = category.menu.language
    item18n = ItemI18n.objects.filter(language=lang, item=item).first()
    # XXX assert item18n

    # XXX add a delete method to item, use here and in category delete
    if "_delete" in request.POST:
        ItemI18n.objects.filter(item=item).delete()
        item.delete()
        return redirect("manager:manage_category", category.id)

    return render(request, "manager/delete-item.html", {
        "item18n": item18n,
        # restaurant and cat18n are needed for the header
        "restaurant": category.menu.restaurant,
        "cat18n": CategoryI18n.get_for_language(lang, category),
    })


@login_required
def add_category(request, id):
    menu = get_object_or_404(Menu, id=id)
    get_role(request.user, menu.restaurant.id, UserRole.MANAGER)

    if request.method == 'POST':
        # unorthodox form use XXX
        language = menu.language
        form = AddCategoryForm(request.POST)

        if form.is_valid():
            name = form.cleaned_data["name"]
            view = form.cleaned_data["view"]
            cat = Category()
            cat.menu = menu
            cat.view = view
            cat.save()
            cat18n = CategoryI18n()
            cat18n.category = cat
            cat18n.language = language
            cat18n.name = name
            cat18n.save()

    return redirect("manager:manage_menu", id)


@login_required
def add_translation(request, menu_id):
    menu = Menu.objects.get(id=menu_id)
    get_role(request.user, menu.restaurant.id, UserRole.MANAGER)  # guard

    if request.POST:
        form = AddTranslationForm(menu, request.POST)
        if form.is_valid():
            lang = form.cleaned_data.get("language")
            menu.translations.add(lang)

    return redirect("manager:manage_menu", menu.id)


@login_required
def delete_translation(request, menu_id, lang_id):
    menu = Menu.objects.get(id=menu_id)
    get_role(request.user, menu.restaurant.id, UserRole.MANAGER)  # guard

    language = Language.objects.get(id=lang_id)

    if "_delete" in request.POST:
        categories = CategoryI18n.objects.filter(language=language, category__menu=menu)
        for cat in categories:
            ItemI18n.objects.filter(language=language, item__category=cat.category).delete()
        categories.delete()
        menu.translations.remove(language)
        return redirect("manager:manage_menu", menu.id)

    return render(request, "manager/delete-translation.html", {
        "language": language,
    })


@login_required
def statistics(request, id):
    restaurant = Restaurant.objects.filter(id=id).first()
    return render(request, "manager/statistics.html", {
        "restaurant": restaurant,
    })


@login_required
def delete_restaurant(request, id):
    restaurant = get_object_or_404(Restaurant, id=id)

    if "_delete" in request.POST:
        restaurant.delete()
        return redirect("manager:index")

    return render(request, "manager/delete-restaurant.html", {
        "restaurant": restaurant,
    })


@login_required()
def delete_category(request, id):
    cat = get_object_or_404(Category, id=id)
    get_role(request.user, cat.menu.restaurant.id, UserRole.MANAGER)  # guard
    # XXX factorise guard into an annotation (@require_role=UserRole.MANAGER)

    language = cat.menu.language

    menu = cat.menu
    cat18n = CategoryI18n.objects.filter(language=language, category=cat).first()

    if "_delete" in request.POST:
        # delete items
        for i in Item.objects.filter(category=cat).all():
            ItemI18n.objects.filter(item=i).delete()
            i.delete()
        cat.delete()
        return redirect("manager:manage_menu", menu.id)

    return render(request, "manager/delete-category.html", {
        "restaurant": cat18n.category.menu.restaurant,
        "cat18n": cat18n,
    })


@login_required()
def rename_category(request, id):
    cat = get_object_or_404(Category, id=id)
    get_role(request.user, cat.menu.restaurant.id, UserRole.MANAGER)  # guard

    if request.POST:
        lang = Language.objects.filter(abbr=request.POST["language"]).first()
        cat18n = CategoryI18n.objects.get_or_create(category=cat, language=lang)[0]
        cat18n.name = request.POST["name"]
        cat18n.save()

    redir = util.get_next_page(request)
    if redir:
        return redir

    return redirect("manager:manage_category", cat.id)


@login_required
def table_index(request, id):
    restaurant = get_object_or_404(Restaurant, id=id)

    tables = Table.objects.filter(restaurant=restaurant).all()
    return render(request, "manager/table.html", {
        "restaurant": restaurant,
        "add_table_form": TableForm(),
        "tables": tables,
    })


@login_required
def add_table(request, id):
    restaurant = get_object_or_404(Restaurant, id=id)

    if request.method == "POST":
        form = TableForm(request.POST)
        table = form.save(commit=False)
        table.restaurant = restaurant
        table.save()

    return redirect("manager:table_index", restaurant.id)


@login_required
def delete_table(request, id):
    table = get_object_or_404(Table, id=id)
    restaurant = table.restaurant

    table.delete()

    return redirect("manager:table_index", restaurant.id)


@login_required
def set_category_ordering(request, id):
    menu = get_object_or_404(Menu, id=id)
    order = request.POST.get("category_ordering")

    if order:
        categories = ordered(menu.category_set.all(), order)
        # save
        i = 0
        for cat in categories:
            cat.ordering = i
            cat.save()
            i += 1
    return HttpResponse("")


@login_required
def set_category_view(request, id, view_id):
    """AJAX call to set view
    """
    cat = get_object_or_404(Category, id=id)
    view = get_object_or_404(CategoryView, id=view_id)

    cat.view = view
    cat.save()

    return HttpResponse("")


@login_required
def set_item_ordering(request, id):
    cat = get_object_or_404(Category, id=id)
    order = request.POST.get("item_ordering")

    if order:
        items = ordered(cat.item_set.all(), order)
        # save
        i = 0
        for item in items:
            item.ordering = i
            item.save()
            i += 1
    return HttpResponse("")
