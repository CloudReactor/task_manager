from typing import Any, Collection, Mapping, NoReturn, Optional

import logging

from django.contrib.auth.models import Group, User

from rest_framework.settings import api_settings
from rest_framework.exceptions import (
    ErrorDetail, NotFound
)
from rest_framework import serializers

from crontab import CronTab

from ..models import RunEnvironment, Schedulable
from ..exception import UnprocessableEntity

logger = logging.getLogger(__name__)


class SerializerHelpers(serializers.BaseSerializer):
    def get_request_user(self) -> Optional[User]:
        request = self.context['request']
        return request.user

    def get_request_group(self) -> Optional[Group]:
        request = self.context['request']

        group = None
        if request.auth and hasattr(request.auth, 'group'):
            group = request.auth.group
        else:
            # For compatibility with existing code that requires a single group for a request.
            # For users with multiple groups, the group is None
            groups = list(request.user.groups.all())
            if len(groups) == 1:
                group = groups[0]
            else:
                logger.warning('get_request_group(): user has multiple groups, returning None')
        return group

    # Legacy
    def set_validated_alert_methods(self,
            data: Mapping[str, Any],
            validated: dict[str, Any],
            run_environment: Optional[RunEnvironment],
            property_name: str = 'alert_methods',
            allow_any_run_environment: bool = False):
        from processes.models import AlertMethod

        group = validated['created_by_group']

        body_alert_methods = data.get(property_name)

        if body_alert_methods is not None:
            updated_alert_methods = []

            for body_alert_method in body_alert_methods:
                try:
                    am = AlertMethod.find_by_uuid_or_name(body_alert_method,
                            required_group=group,
                            allowed_run_environment=run_environment,
                            allow_any_run_environment=allow_any_run_environment)
                except serializers.ValidationError as validation_error:
                    self.handle_to_internal_value_exception(validation_error, field_name='alert_methods')
                except NotFound as nfe:
                    raise UnprocessableEntity({
                        property_name: [
                            ErrorDetail('Alert method not found', code='invalid')
                        ]
                    }) from nfe

                updated_alert_methods.append(am)

            validated[property_name] = updated_alert_methods


    def set_validated_notification_profiles(self,
            data: Mapping[str, Any],
            validated: dict[str, Any],
            run_environment: Optional[RunEnvironment],
            property_name: str = 'notification_profiles',
            allow_any_run_environment: bool = False):
        from processes.models import NotificationProfile

        group = validated['created_by_group']

        body_notification_profiles = data.get(property_name)

        if body_notification_profiles is not None:
            updated_notification_profiles = []

            for body_notification_profile in body_notification_profiles:
                try:
                    am = NotificationProfile.find_by_uuid_or_name(body_notification_profile,
                            required_group=group,
                            allowed_run_environment=run_environment,
                            allow_any_run_environment=allow_any_run_environment)
                except serializers.ValidationError as validation_error:
                    self.handle_to_internal_value_exception(validation_error, field_name='notification_profiles')
                except NotFound as nfe:
                    raise UnprocessableEntity({
                        property_name: [
                            ErrorDetail('Notification Method not found', code='invalid')
                        ]
                    }) from nfe

                updated_notification_profiles.append(am)

            validated[property_name] = updated_notification_profiles


    @staticmethod
    def validate_schedule(schedule: Optional[str]) -> Optional[str]:
        if schedule is None:
            return None

        schedule = schedule.strip()

        if schedule:
            if not schedule.startswith('cron(') \
                    and not schedule.startswith('rate('):
                schedule = f"cron({schedule})"

            m = Schedulable.CRON_REGEX.match(schedule)

            if m:
                cron_expr = m.group(1)

                try:
                    CronTab(cron_expr)
                    logger.debug(f"Schedule '{schedule}' contains a valid cron expression")
                except Exception as ex:
                    raise serializers.ValidationError(
                        detail=f"Cron expression '{cron_expr}' is invalid") from ex
            elif Schedulable.RATE_REGEX.match(schedule):
                logger.debug(f"Schedule '{schedule}' is a valid rate expression")
            else:
                raise serializers.ValidationError(
                    detail=f"Schedule '{schedule}' is not a supported schedule expression")

        logger.info(f"validated schedule = '{schedule}'")

        return schedule

    # Translate validation errors raised by to_internal_value() implementations to
    # their expected format.
    # See https://github.com/encode/django-rest-framework/issues/3864
    @staticmethod
    def handle_to_internal_value_exception(ex: Exception,
            field_name: Optional[str] = None) -> NoReturn:
        if isinstance(ex, serializers.ValidationError):
            detail = ex.detail

            if isinstance(detail, list) and (len(detail) == 1) and \
                isinstance(detail[0], ErrorDetail):
                field_name = field_name or api_settings.NON_FIELD_ERRORS_KEY
                raise serializers.ValidationError({field_name: [str(detail[0])]})
        raise ex

    @staticmethod
    def copy_props_with_prefix(dest_dict: dict[str, Any],
            src_dict: Mapping[str, Any], dest_prefix='',
            included_keys: Optional[Collection[str]] = None,
            except_keys: Optional[Collection[str]] = None,
            none_to_empty_strings: bool = False) -> dict[str, Any]:
        included_key_set = None if (included_keys is None) else set(included_keys)
        except_key_set = set(except_keys or [])
        for key, value in src_dict.items():
            if ((included_key_set is None) or (key in included_key_set)) \
                    and (key not in except_key_set):
                if none_to_empty_strings and (value is None):
                    value = ''

                dest_dict[dest_prefix + key] = value
        return dest_dict
