import os
import json
import sys
from typing import Any

from dragonchain import exceptions

SECRET_LOCATION = os.environ["SECRET_LOCATION"]


def get_dc_secret(key: str) -> Any:
    """
    Get the secret value for this Dragonchain's owned secrets
    :param key: The name of the file containing the secret
    :returns: string of the dragonchain's secret
    """
    try:
        with open(SECRET_LOCATION) as f:
            return json.loads(f.read())[key]
    except Exception:
        raise exceptions.SecretClientBadResponse("Error occurred getting DC secret from file", sys.exc_info())
