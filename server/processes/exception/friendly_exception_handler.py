from typing import Optional

import logging
import traceback
from collections.abc import Mapping

from rest_framework.exceptions import APIException, ErrorDetail
from rest_framework.response import Response
from rest_framework import serializers

logger = logging.getLogger(__name__)


def friendly_exception_handler(exc, context):
    from rest_framework.views import exception_handler

    ex_traceback = exc.__traceback__
    tb_lines = [line.rstrip('\n') for line in
                traceback.format_exception(exc.__class__, exc, ex_traceback)]
    logger.error(tb_lines)

    response = exception_handler(exc, context)

    if (response is None) or isinstance(exc, APIException):
        if response is None:
            response = Response({})

        error_code: Optional[str] = None
        try:
            response.status_code = 500

            if isinstance(exc, APIException):
                response.status_code = exc.status_code
                if isinstance(exc.detail, ErrorDetail):
                    error_code = exc.detail.code

            if isinstance(exc, serializers.ValidationError):
                codes = exc.get_codes()

                if isinstance(codes, dict):
                    for _field_name, field_codes in codes.items():
                        if not isinstance(field_codes, list):
                            field_codes = [field_codes]

                        if 'unique' in field_codes:
                            response.status_code = 409
                            break

            should_modify_data = True
            if response.data is None:
                response.data = {}
            elif not isinstance(response.data, Mapping):
                should_modify_data = False

            if should_modify_data:
                if error_code:
                    response.data['error_code'] = error_code
                response.data['error_class'] = exc.__class__.__name__
                response.data['error_message'] = str(exc)
        except Exception:
            logger.exception('Error handling exception')

    return response
