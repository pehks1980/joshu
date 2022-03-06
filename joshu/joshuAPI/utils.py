from rest_framework.views import exception_handler
from rest_framework.response import Response
from joshuAPI.api_error_list import response_api_error
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        response.data['status_code'] = response.status_code

    return response
    HTTP_400_BAD_REQUEST
    HTTP_401_UNAUTHORIZED
    HTTP_402_PAYMENT_REQUIRED
    HTTP_403_FORBIDDEN
    HTTP_404_NOT_FOUND
    HTTP_405_METHOD_NOT_ALLOWED
    HTTP_406_NOT_ACCEPTABLE
    HTTP_407_PROXY_AUTHENTICATION_REQUIRED
    HTTP_408_REQUEST_TIMEOUT
    HTTP_409_CONFLICT
    """
    response = exception_handler(exc, context)
    if response:
        if response.status_code == 401:
            res = {
                "errors": response_api_error(401)
            }
            return Response(res, status.HTTP_401_UNAUTHORIZED)
        elif response.status_code == '402':
            res = {
                "errors": response_api_error(402)
            }
            return Response(res, status.HTTP_402_PAYMENT_REQUIRED)
        elif response.status_code == '403':
            res = {
                "errors": response_api_error(403)
            }
            return Response(res, status.HTTP_403_FORBIDDEN)
        elif response.status_code == '404':
            res = {
                "errors": response_api_error(404)
            }
            return Response(res, status.HTTP_404_NOT_FOUND)
        elif response.status_code == 405:
            res = {
                "errors": response_api_error(405)
            }
            return Response(res, status.HTTP_405_METHOD_NOT_ALLOWED)

        else:
            res = {
                "errors": response_api_error(400)
            }
            return Response(res, status.HTTP_400_BAD_REQUEST)

