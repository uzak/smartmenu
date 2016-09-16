from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect

from main.forms import *


def register(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            # create user and his profile
            user = form.save()
            user.set_password(user.password)
            user.save()
            profile = UserProfile.for_user(user)
            profile.user = user
            profile.save()
            # auth created user
            user = authenticate(username=form.cleaned_data['username'],
                                password=form.cleaned_data['password'],
                                )
            login(request, user)
            return redirect("main:profile")
    else:
        form = UserForm()
    return render(request, 'main/register.html', {"userform": form})


@login_required
def set_menu_language_order(request):
    """set the ordering field for languages"""
    profile = UserProfile.for_user(request.user)
    order = request.POST.get("menu_language_order")
    profile.menu_language_order = order
    profile.save()
    return HttpResponse("")


@login_required
def profile_delete(request):
    if request.POST and "_delete" in request.POST:
        UserProfile.for_user(request.user).delete()
        request.user.delete()
        return redirect("customer:index", next=None)
    return render(request, "main/profile_delete.html")


@login_required
def profile(request):
    # default form data (GET)
    # find all orders that are finished (check_out) and sort by latest checkin date
    orders = Order.objects.filter(user=request.user, checkout__isnull=False).order_by("-checkin")

    lang = Language.get_current()
    form = UserProfileForm(request.user, lang)

    # is there data to save? (POST)
    if request.POST:
        form = UserProfileForm(request.user, lang, request.POST)
        if form.is_valid():
            form.save()
            return redirect("main:profile")

    result = render(request, "main/profile.html", {
        "form": form,
        "orders": orders,
        "profile": profile,
        "goto_allergens": "_allergens" in request.POST,
    })
    return result


def logout_user(request):
    logout(request)
    return redirect(request.GET.get("next", "/"))


def get_role(user, restaurant_id, rolestr):
    """return the waiter/manager's role at given restaurant or raise a HTTP exception"""
    assert rolestr in (UserRole.WAITER, UserRole.MANAGER)
    role = UserRole.objects.filter(user=user, role__name__icontains=rolestr, restaurant__id=restaurant_id).first()
    if not role:
        raise Http404("You are not registered as %s at the restaurant (id=%s)" % (rolestr, restaurant_id))
    return role
