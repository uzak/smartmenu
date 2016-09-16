# vim: set fileencoding=utf-8

from django.core.management.base import BaseCommand
from main.models import Order, Review
import random


class Command(BaseCommand):
    help = 'Generate test reviews for orders'

    def add_arguments(self, parser):
        parser.add_argument('reviews', type=int)

    def handle(self, *args, **options):
        count = options["reviews"]

        ignored = 0
        # generate reviews
        for i in range(count):
            print "generate review %d" % (i + 1)
            order = random.choice(Order.objects.all())
            if not order.orderitem_set.all():
                print "ignore order: %d, it has no orderitems" % order.id
                continue
            orderitem = random.choice(order.orderitem_set.all())
            if Review.objects.filter(orderitem=orderitem).first():
                print "ignoring orderitem: %s, it has a review already" % orderitem
                ignored += 1
                continue
            r = Review()
            r.orderitem = orderitem
            r.rating = random.randint(1, 5)
            r.language = order.table.restaurant.menu.language
            r.text = random.choice(review_texts)
            r.user = order.user
            r.save()

        self.stdout.write('Successfully added %d reviews' % (count - ignored))


review_texts = """very good
mostly OK
best kind of this dish I ever had
was rather disappointed, had better elsewhere
never again
yum yum
""".splitlines()
