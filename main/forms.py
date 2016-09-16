import imghdr
from django import forms
from django.contrib.auth.models import User
from models import *


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password")


class UserProfileForm(forms.ModelForm):
    allergens = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = UserProfile
        fields = ("allergens",)

    def save(self, *args, **kw):
        profile = UserProfile.for_user(self.user)
        allergen_ids = self.cleaned_data.get("allergens", ())
        # convert to objects
        allergens = map(lambda x: AllergenI18n.objects.get(id=x).allergen, allergen_ids)
        # save allergens (many2many style)
        profile.allergens.clear()
        for a in allergens:
            profile.allergens.add(a)
        profile.save()
        return profile

    def __init__(self, user, lang, *args, **kw):
        # user is needed for save()
        self.user = user
        super(UserProfileForm, self).__init__(*args, **kw)

        # allergens
        initial = map(lambda x: x.id, UserProfile.for_user(self.user).allergens.all())
        self.fields['allergens'].initial = initial
        allergens = [(a.allergen.id, a.name) for a in AllergenI18n.objects.filter(language=lang)]
        self.fields['allergens'].choices = allergens


class RestaurantForm(forms.ModelForm):
    payment_method = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=PaymentMethod.objects.all(),
        required=True,
        label="Supported Payment Methods"
    )
    name = forms.CharField(label="Restaurant's name")

    class Meta:
        model = Restaurant
        fields = ("name", "payment_method")

    def __init__(self, *args, **kw):
        super(RestaurantForm, self).__init__(*args, **kw)
        self.fields['name'].widget.attrs["class"] = "form-control"


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ("street", "street_no", "zip", "city", "country")

    def __init__(self, *args, **kw):
        super(AddressForm, self).__init__(*args, **kw)
        for k, v in self.fields.items():
            v.widget.attrs["class"] = "form-control"


class MenuForm(forms.ModelForm):
    show_numbers = forms.BooleanField(label="Show menu item numbers before names", required=False)

    class Meta:
        model = Menu
        fields = ("currency", "language", "show_numbers")

    language = forms.ModelChoiceField(
        queryset=Language.objects.all(),
        label="Default menu language"
    )

    def __init__(self, *args, **kw):
        super(MenuForm, self).__init__(*args, **kw)
        for label in ("currency", "language"):
            self.fields[label].empty_label = None
            self.fields[label].required = False
            self.fields[label].widget.attrs["class"] = "form-control"


class _ItemForm(forms.Form):
    no = forms.CharField()
    name = forms.CharField()
    description = forms.CharField(widget=forms.Textarea, required=False)
    price = forms.FloatField()
    image = forms.ImageField()

    @staticmethod
    def save_image(item, image):
        ext = imghdr.what(image)
        # sometimes imghdr returns None, in that case keep old extension
        if ext is None:
            ext = image.name.split(".")[-1]
        item.image.save("item%d.%s" % (item.id, ext), image)
        item.save()

    @staticmethod
    def save_allergens(post_data, item):
        # XXX many assumptions here
        # save allergens
        for k, v in post_data.iteritems():
            if k.startswith("allergen_"):
                id = int(k.split("_")[1])
                if v == "none":
                    obj = ItemAllergen.objects.filter(allergen_id=id, item=item).first()
                    if obj:
                        obj.delete()
                    continue
                ia = ItemAllergen.objects.get_or_create(allergen_id=id, item=item)[0]
                ia.traces = v == "traces"
                ia.save()


class AddItemForm(_ItemForm):
    def __init__(self, menu, *args, **kw):
        super(AddItemForm, self).__init__(*args, **kw)
        # default for no
        self.fields["no"].initial = Item.next_free_no(menu)

    def save(self, category, language):
        item = Item()
        item.no = self.cleaned_data["no"]
        item.category = category
        item.price = self.cleaned_data["price"]
        item.save()
        self.save_image(item, self.cleaned_data["image"])
        item18n = ItemI18n(item=item, language=language)
        item18n.name = self.cleaned_data["name"]
        item18n.description = self.cleaned_data["description"]
        item18n.save()
        return item18n


class ManageItemForm(_ItemForm):
    def __init__(self, item18n, *args, **kw):
        super(ManageItemForm, self).__init__(*args, **kw)
        self._item18n = item18n
        self.fields["no"].initial = item18n.item.no
        self.fields["name"].initial = item18n.name
        self.fields["description"].initial = item18n.description
        self.fields["price"].initial = item18n.item.price
        self.fields["price"].label_suffix = " (%s)" % item18n.item.category.menu.currency
        self.fields["image"].initial = item18n.item.image

    def save(self, language):
        # if self._item18n is in a different language,
        # create a new instance (used when there is no item for a translation yet)
        if self._item18n.language != language:
            self._item18n = ItemI18n(language=language, item=self._item18n.item)
        # item18n and item
        self._item18n.description = self.cleaned_data["description"]
        self._item18n.name = self.cleaned_data["name"]
        self._item18n.save()
        self._item18n.item.price = self.cleaned_data["price"]
        self._item18n.item.no = self.cleaned_data["no"]
        self.save_image(self._item18n.item, self.cleaned_data["image"])
        self._item18n.item.save()
        return self._item18n


class AddCategoryForm(forms.Form):
    name = forms.CharField(required=True)
    view = forms.ModelChoiceField(
        queryset=CategoryView.objects.all(),
        required=True,
        empty_label=None,
    )

    def __init__(self, *args, **kw):
        super(AddCategoryForm, self).__init__(*args, **kw)
        for k, v in self.fields.items():
            v.widget.attrs["class"] = "form-control"


class AddTranslationForm(forms.Form):
    language = forms.ChoiceField()

    def __init__(self, menu, *args, **kw):
        super(AddTranslationForm, self).__init__(*args, **kw)
        choices = list(Language.objects.all())
        for l in menu.all_languages():
            if l in choices:
                choices.remove(l)
        self.fields["language"].choices = [(l.id, l) for l in choices]
        self.fields["language"].widget.attrs["class"] = "form-control"


class ChangeViewForm(forms.Form):
    view = forms.ModelChoiceField(
        queryset=CategoryView.objects.all(),
        required=True,
        empty_label=None,
    )

    def __init__(self, category, *args, **kw):
        super(ChangeViewForm, self).__init__(*args, **kw)
        self.fields["view"].widget.attrs["class"] = "form-control"
        self.fields['view'].initial = category.view


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ["no", "description"]

    def __init__(self, *args, **kw):
        super(TableForm, self).__init__(*args, **kw)
        for k, v in self.fields.items():
            v.widget.attrs["class"] = "form-control"


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ("amount", "comment",)

    comment = forms.CharField(widget=forms.TextInput, required=False)
