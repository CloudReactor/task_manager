from typing import TYPE_CHECKING, Type

import base64
import hashlib
import hmac
import logging
import os

from django.apps import AppConfig

if TYPE_CHECKING:
    from django.contrib.auth.models import User

from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)


def pre_save_user(sender: 'Type[User]', **kwargs) -> None:
    instance = kwargs['instance']
    logger.info(f"pre-save with user {instance}, {instance._state.adding=}")

    # https://stackoverflow.com/questions/2037320/what-is-the-canonical-way-to-find-out-if-a-django-model-is-saved-to-db
    if not instance._state.adding:
        logger.info('Updating an existing User')
        return

    from django.contrib.auth.models import User

    existing_user_count = User.objects.count()

    if existing_user_count >= 10:
        user_limit_verified = False
        user_limit_b64_str = os.environ.get('CLOUDREACTOR_USER_LIMIT_KEY')

        if user_limit_b64_str:
            byte_key = base64.b64decode(user_limit_b64_str)

            messages = [
              'CloudReactor Unlimited User License',
            ]
            digests = [
              b'ApO0puwp41WMR5elJWCIomKFAoKuzWYn/zNTPCIsGl0=',
            ]

            if existing_user_count < 25:
                messages.append('CloudReactor 25 User License')
                digests.append(b'zCrl5shIiKOvLA5VJ9RltfB0qzDvC/cvKGN5q3H9N4M=')

            if existing_user_count < 100:
                messages.append('CloudReactor 100 User License')
                digests.append(b'kN2PcmQhHlrBIpFLlNqDELPFLKlVUa820FBiT/0c6A4=')

            if existing_user_count < 250:
                messages.append('CloudReactor 250 User License')
                digests.append(b'sYaY1LhrSZ0UMBmaUsfm7mtGkG2ksJ1rdQbqS+X5yz4=')

            if existing_user_count < 500:
                messages.append('CloudReactor 500 User License')
                digests.append(b'a545VGl0V+Vxm1VCs5dgCG9xDB7DE7xUtT0ITNDetkU=')

            if existing_user_count < 1000:
                messages.append('CloudReactor 1000 User License')
                digests.append(b'M0pU4/E/Df8b788WZ/VPUQuA8yHyPaM3U+3x3ax65mk=')

            for index, message in enumerate(messages):
                digest = base64.b64encode(hmac.new(byte_key,
                        message.encode('UTF-8'), hashlib.sha256).digest())
                user_limit_verified = (digest == digests[index])

                if user_limit_verified:
                    break
        elif (existing_user_count < 50) and (os.environ.get('IN_PYTEST') == 'TRUE'):
            user_limit_verified = True
        else:
            logger.error('The environment variable CLOUDREACTOR_USER_LIMIT_KEY must be set to add more than 10 users')

        if user_limit_verified:
            logger.debug('User limit verified')
        else:
            raise PermissionDenied(code='free_usage_tier_exceeded',
                    detail='You have exceeded the free usage tier. Please contact licensing@cloudreactor.io for a license key.')


class ProcessesConfig(AppConfig):
    name = 'processes'

    def ready(self):
        # Patch django-typed-models for Django 4.2+ compatibility
        # The declared_fields attribute was removed in Django 4.2, but typedmodels still tries to access it
        self._patch_typedmodels_compatibility()

        # This is needed to load the signal handlers for this app.
        import processes.signal_handlers # pylint: disable=unused-import
        from django.db.models.signals import pre_save
        pre_save.connect(pre_save_user, sender='auth.User')

    @staticmethod
    def _patch_typedmodels_compatibility():
        """Patch typedmodels._model_has_field to handle Django 4.2+ where declared_fields was removed."""
        try:
            from typedmodels.models import TypedModelMetaclass

            original_model_has_field = TypedModelMetaclass._model_has_field

            @staticmethod
            def patched_model_has_field(cls, base_class, field_name):
                if field_name in base_class._meta._typedmodels_original_many_to_many:
                    return True
                if field_name in base_class._meta._typedmodels_original_fields:
                    return True
                if any(f.name == field_name for f in base_class._meta.private_fields):
                    return True
                for ancestor in cls.mro():
                    if issubclass(ancestor, base_class) and ancestor != base_class:
                        # declared_fields was removed in Django 4.2+
                        if hasattr(ancestor._meta, 'declared_fields') and field_name in ancestor._meta.declared_fields.keys():
                            return True

                if field_name in cls._meta.fields_map:
                    # Crazy case where a reverse M2M from another typedmodels proxy points to this proxy
                    return True
                return False

            TypedModelMetaclass._model_has_field = patched_model_has_field
        except ImportError:
            pass  # typedmodels not installed
