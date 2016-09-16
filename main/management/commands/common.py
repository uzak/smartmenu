# vim: set fileencoding=utf-8

from main.models import PaymentMethod, Language
import random


def create_languanges():
    data = [("sk", "Slovensky"),
            ("de", "Deutsch"),
            ("en", "English"),
            ]
    result = []
    for abbr, name in data:
        l = Language.objects.get_or_create(abbr=abbr, name=name)
        l = l[0]
        l.save()
        result.append(l)
    return result


def create_payment_methods():
    return get_or_create_objects(
        PaymentMethod,
        ("Cash", "Visa", "Maestro", "Cheque Dejeuner"))


def get_or_create_objects(clazz, data):
    """Get or create objects of 'clazz' from the DB where the values for attributes 'name'
    for the objects are taken from the argument 'data'"""
    result = []
    for name in data:
        p = clazz.objects.get_or_create(name=name)[0]
        p.save()
        result.append(p)
    return result


def gen_unique_name(destination_list, source_list):
    """generate an unique name from source list. If the name is already in
    'destination_list' take the name, append 1 and repeat increasing the number
    until a free name is found."""
    n = random.choice(source_list)
    # name an unique name if "n" already in the destination
    if n in destination_list:
        i = 2
        while "%s %d" % (n, i) in destination_list:
            i += 1
        n = "%s %d" % (n, i)
    destination_list.append(n)
    return n
