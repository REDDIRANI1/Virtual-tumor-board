from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound

class StaleVersionError(Exception):
    pass

class InvalidTransitionError(Exception):
    pass

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    error_code = 'SERVER_ERROR'
    message = str(exc)
    detail = {}
    status_code = 500

    exc_class_name = exc.__class__.__name__

    if exc_class_name == 'StaleVersionError':
        status_code = 409
        error_code = 'STALE_VERSION'
    elif exc_class_name == 'InvalidTransitionError':
        status_code = 400
        error_code = 'INVALID_TRANSITION'
    elif isinstance(exc, PermissionDenied):
        status_code = 403
        error_code = 'PERMISSION_DENIED'
        if response is not None:
            status_code = response.status_code
    elif isinstance(exc, NotFound):
        status_code = 404
        error_code = 'NOT_FOUND'
        if response is not None:
            status_code = response.status_code
    elif isinstance(exc, ValidationError):
        status_code = 400
        error_code = 'VALIDATION_ERROR'
        if response is not None:
            status_code = response.status_code
            detail = response.data
    else:
        if response is not None:
            status_code = response.status_code
            error_code = 'API_ERROR'
            if isinstance(response.data, dict) and 'detail' in response.data:
                message = str(response.data.get('detail', ''))
            detail = response.data
        else:
            # Use default behavior for unhandled 500s
            return None

    # Sanitize error bodies to prevent author/user ID leakage
    def sanitize(data):
        if isinstance(data, dict):
            return {k: sanitize(v) for k, v in data.items() if k not in ['author', 'author_id', 'author_username', 'email', 'profile']}
        elif isinstance(data, list):
            return [sanitize(v) for v in data]
        return data

    sanitized_detail = sanitize(detail)

    custom_response_data = {
        'error': {
            'code': error_code,
            'message': message,
            'detail': sanitized_detail
        }
    }

    if response is not None:
        response.data = custom_response_data
        response.status_code = status_code
    else:
        from rest_framework.response import Response
        response = Response(custom_response_data, status=status_code)

    return response
