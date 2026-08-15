"""
HTTP client for making requests to payment gateways.
"""
import json
import logging
from typing import Dict, Any, Optional, Union, List

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from paytechuz.core.exceptions import (
    ExternalServiceError,
    TimeoutError as PaymentTimeoutError,
    InternalServiceError
)

logger = logging.getLogger(__name__)


class HttpClient:
    """
    HTTP client for making requests to payment gateways.

    This class provides a simple interface for making HTTP requests to payment
    gateways with proper error handling and logging.
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        verify_ssl: bool = True
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL for the API
            headers: Default headers to include in all requests
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.headers = headers or {}
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    def _build_url(self, endpoint: str) -> str:
        """
        Build the full URL for the given endpoint.

        Args:
            endpoint: API endpoint

        Returns:
            Full URL
        """
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{endpoint}"

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle the response from the API.

        Args:
            response: Response object

        Returns:
            Response data as dictionary

        Raises:
            ExternalServiceError: If the response status code is not 2xx
        """
        try:
            response.raise_for_status()
            return response.json()
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON response: {response.text}")
            raise InternalServiceError("Failed to decode JSON response")
        except requests.HTTPError as e:
            logger.error(f"HTTP error: {e}, Response: {response.text}")
            try:
                error_data = response.json()
            except json.JSONDecodeError:
                error_data = {"raw_response": response.text}

            raise ExternalServiceError(
                message=f"HTTP error: {response.status_code}",
                data=error_data
            )

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Form data
            headers: Request headers
            json_data: JSON data
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary

        Raises:
            ExternalServiceError: If the request fails
            TimeoutError: If the request times out
        """
        url = self._build_url(endpoint)
        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)

        timeout = timeout or self.timeout

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                headers=request_headers,
                json=json_data,
                timeout=timeout,
                verify=self.verify_ssl
            )
            return self._handle_response(response)
        except Timeout:
            logger.error(f"Request timed out: {method} {url}")
            raise PaymentTimeoutError(f"Request timed out: {method} {url}")
        except ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise ExternalServiceError(f"Connection error: {str(e)}")
        except RequestException as e:
            logger.error(f"Request error: {e}")
            raise ExternalServiceError(f"Request error: {str(e)}")

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make a GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary
        """
        return self.request(
            method="GET",
            endpoint=endpoint,
            params=params,
            headers=headers,
            timeout=timeout
        )

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint
            data: Form data
            json_data: JSON data
            params: Query parameters
            headers: Request headers
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary
        """
        return self.request(
            method="POST",
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            params=params,
            headers=headers,
            timeout=timeout
        )

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make a PUT request.

        Args:
            endpoint: API endpoint
            data: Form data
            json_data: JSON data
            params: Query parameters
            headers: Request headers
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary
        """
        return self.request(
            method="PUT",
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            params=params,
            headers=headers,
            timeout=timeout
        )

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make a DELETE request.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary
        """
        return self.request(
            method="DELETE",
            endpoint=endpoint,
            params=params,
            headers=headers,
            timeout=timeout
        )
