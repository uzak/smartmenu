from django.conf.urls import url
from main import views

urlpatterns = [
    url(r"^register$", views.register, name="register"),
    url(r"^profile$", views.profile, name="profile"),
    url(r"^profile/delete$", views.profile_delete, name="profile_delete"),
    url(r"^logout$", views.logout_user, name="logout"),

    # AJAX stuff
    url(r"^profile/menu_languages/ordering$", views.set_menu_language_order, name="set_menu_language_order"),
]
