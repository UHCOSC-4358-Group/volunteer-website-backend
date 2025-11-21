from requests import get, exceptions
from urllib.parse import quote
import os
from ..util import error

GOOGLE_GEOCODING_API_KEY = os.environ.get("GOOGLE_GEOCODING_API_KEY")


def geocode_address(address: str) -> tuple[float, float, str]:

    if GOOGLE_GEOCODING_API_KEY is None:
        raise error.ExternalServiceError(
            "Geocoding", "Environmental credentials are not loaded"
        )

    api_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={quote(address)}&key={GOOGLE_GEOCODING_API_KEY}"

    try:
        payload = get(api_url)
    except ConnectionError:
        raise error.ExternalServiceError("Geocoding", "Network problem during request")
    except exceptions.RequestException as e:
        raise error.ExternalServiceError(
            "Geocoding", f"Something went wrong during request: ${str(e)}"
        )

    content = payload.json()

    status = content["status"]

    if status == "ZERO_RESULTS":
        raise error.NotFoundError("Address", address)

    server_errors = [
        "OVER_QUERY_LIMIT",
        "REQUEST_DENIED",
        "INVALID_REQUEST",
        "UNKNOWN_ERROR",
    ]

    if status in server_errors:
        error_message = content["error_message"]
        if error_message:
            raise error.ExternalServiceError(
                "Geocoding", f"Returned status: {status}, Message : ${error_message}"
            )
        else:
            raise error.ExternalServiceError("Geocoding", f"Returned status: {status}")

    # Final check
    if status != "OK":
        raise error.ExternalServiceError("Geocoding", f"Returned status: {status}")

    # Grab first result
    result = content["results"][0]

    latitude: float = result["geometry"]["location"]["lat"]
    longitude: float = result["geometry"]["location"]["lng"]
    formatted_address = result["formatted_address"]

    return latitude, longitude, formatted_address
