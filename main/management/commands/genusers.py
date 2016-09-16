# vim: set fileencoding=utf-8

from django.core.management.base import BaseCommand
from main.models import Role, UserRole, Restaurant, UserProfile
from django.contrib.auth.models import User
from common import gen_unique_name, get_or_create_objects
import random
import string

_roles = get_or_create_objects(Role, (UserRole.MANAGER, UserRole.WAITER))


class Command(BaseCommand):
    help = 'Generate user related data in the db for testing purposes'

    def add_arguments(self, parser):
        parser.add_argument('users', type=int)

    def handle(self, *args, **options):
        count = options["users"]

        users = []
        waiters = []
        managers = []

        _usernames = []
        # generate users
        for i in range(count):
            n = gen_unique_name(_usernames, ("user_" + "".join(random.sample(string.lowercase, 3)),))
            print "generate %d. user (%s)" % (i + 1, n)
            u = User()
            u.username = n
            u.password1 = "".join(random.sample(string.lowercase + string.digits, 10))
            u.password2 = u.password1
            users.append(u)
            u.save()
            # generate user roles
            # waiters
            if i % 20 == 1:
                ur = UserRole()
                ur.user = u
                ur.role = _roles[1]
                ur.restaurant = random.choice(Restaurant.objects.all())
                ur.save()
                print "marking %s as waiter" % u.username
                waiters.append(u)
                if u in users:
                    users.remove(u)
            # managers
            if i % 40 == 1:
                ur = UserRole()
                ur.user = u
                ur.role = _roles[0]
                ur.restaurant = random.choice(Restaurant.objects.all())
                ur.save()
                print "marking %s as manager" % u.username
                managers.append(u)
                if u in users:
                    users.remove(u)
            # every 2nd user a profile
            if i % 2 == 0:
                print "Adding user profile"
                profile = UserProfile()
                profile.user = u
                profile.save()

        self.stdout.write('Successfully added %d users' % count)
