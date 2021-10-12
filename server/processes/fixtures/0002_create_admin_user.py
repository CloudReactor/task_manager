from dynamic_fixtures.fixtures import BaseFixture

from django.contrib.auth.models import User, Group


class Fixture(BaseFixture):
    def load(self):
        if not User.objects.filter(is_superuser=True).exists():
            admin = User(username='admin', email='admin@cloudreactor.io',
                first_name='Admin', last_name='User',
                is_superuser=True, is_staff=True, is_active=True
            )
            admin.set_password('adminpassword')
            admin.save()

            if not Group.objects.filter(name='CloudReactor').exists():
                group = Group(name='CloudReactor')
                group.save()

                admin.groups.add(group)
                admin.save()
