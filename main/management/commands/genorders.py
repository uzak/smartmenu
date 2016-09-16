# vim: set fileencoding=utf-8

from django.core.management.base import BaseCommand
from main.models import Table, Order, Item, Payment, ItemI18n
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import common
import random

_payment_methods = common.create_payment_methods()
_languages = common.create_languanges()


def _tz_date(year, month, day):
    """time-zone aware date"""
    return timezone.make_aware(timezone.datetime(year, month, day))


class Command(BaseCommand):
    help = 'Generate user related data in the db'

    def add_arguments(self, parser):
        parser.add_argument('orders', type=int)

    def handle(self, *args, **options):
        count = options["orders"]

        # generate orders
        for i in range(count):
            print "generate order %d" % (i + 1)
            t = random.choice(Table.objects.all())
            u = random.choice(User.objects.all())
            order = Order()
            order.table = t
            order.user = u
            # checkin at random date between 2014-1-1 and now
            order.checkin = _random_date(_tz_date(2014, 1, 1), timezone.now())
            # check out in between of .5 or 3h later
            order.checkout = _random_date(order.checkin,
                                          order.checkin + timedelta(seconds=random.randint(1800, 3600 * 3)))
            order.save()
            c = random.randint(1, 6)
            print "generate %d order items" % c
            for _ in range(c):
                item = random.choice(Item.objects.all())
                i18n = ItemI18n.objects.get(language=_languages[2], item=item)  # english
                oi = order.add_item(i18n, random.randint(1, 2))
                oi.confirmed = _random_date(order.checkin, order.checkin + timedelta(seconds=random.randint(100, 1800)))
                oi.save()
                # payment
            cur = order.table.restaurant.menu.currency
            print "generate payment %f %s" % (order.total(), cur)
            p = Payment()
            p.datetime = order.checkout - timedelta(seconds=random.randint(30, 60 * 5))
            p.order = order
            tip = random.randint(0, 10)
            p.amount = order.total() + tip
            # round up every second payment
            if random.randint(0, 1):
                p.amount = int("%d" % (p.amount + 1))
            p.currency = cur
            p.method = random.choice(_payment_methods)
            p.save()

        self.stdout.write('Successfully added %d orders' % count)


# http://stackoverflow.com/questions/553303/generate-a-random-date-between-two-other-dates
def _random_date(start, end):
    return start + timedelta(
        seconds=random.randint(0, int((end - start).total_seconds())))
