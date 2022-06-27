import os

from dynamic_fixtures.fixtures import BaseFixture

from django.contrib.auth.models import User, Group

from processes.models import SaasToken, UserGroupAccessLevel


class Fixture(BaseFixture):
    def load(self):
        if os.environ.get('DEPLOYMENT') != 'dev':
            return

        user = User.objects.filter(username='exampleuser').first()

        if not user:
            user = User(username='exampleuser', email='user@example.com',
                first_name='Example', last_name='User',
                is_active=True
            )
            user.set_password('examplepassword')
            user.save()

        group = Group.objects.filter(name='example').first()

        if not group:
            group = Group(name='example')
            group.save()

        user.groups.add(group)

        user.save()

        UserGroupAccessLevel.objects.update_or_create(user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_ADMIN)

        SaasToken.objects.update_or_create(name='Developer',
            user=user, group=group,
            access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
            defaults={
                'description': 'Developer Key for all Run Environments',
                'enabled': True
            })
