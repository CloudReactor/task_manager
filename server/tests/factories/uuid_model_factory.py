from django.utils import timezone

from processes.models import NamedWithUuidModel, UserGroupAccessLevel

import factory

class UuidModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True
        skip_postgeneration_save = True 

    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)