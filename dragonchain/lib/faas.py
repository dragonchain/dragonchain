import os
import base64
import json
from typing import List, Dict, Optional, cast, Any

import requests

from dragonchain import exceptions

FAAS_GATEWAY = os.environ.get("FAAS_LOGS_GATEWAY") or os.environ["FAAS_GATEWAY"]


def get_faas_auth() -> str:
    """Gets authorization to use OpenFaaS

    Returns:
        A string containing authorization for OpenFaaS.
        Returns empty string if authorization is not found, in the case of managed services
    """
    try:
        with open("/etc/openfaas-secret/user", "r") as file:
            username = file.read()
        with open("/etc/openfaas-secret/password", "r") as file:
            password = file.read()
    except FileNotFoundError:
        return ""

    return f"Basic {base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('ascii')}"


def _get_raw_logs(contract_id: str, since: Optional[str] = None, tail: Optional[int] = 100) -> List[str]:
    """Calls openfaas /system/logs endpoint with query parameters for a specific contract

    Returns:
        A list of log JSON strings
    """
    query_params = cast(Dict[str, Any], {"name": f"contract-{contract_id}", "tail": tail or 100, "since": since})
    response = requests.get(f"{FAAS_GATEWAY}/system/logs", params=query_params, headers={"Authorization": get_faas_auth()})
    if response.status_code != 200:
        raise exceptions.OpenFaasException("Error getting contract logs, non-2XX response from OpenFaaS gateway")

    return response.text.split("\n")


def get_logs(contract_id: str, since: Optional[str] = None, tail: Optional[int] = 100) -> List[Dict[str, str]]:
    """Gets the raw logs from openfaas and parses the ndjson into a list of dictionaries

    Returns:
        A list of log dictionaries
    """
    return [json.loads(log) for log in _get_raw_logs(contract_id, since, tail) if log != ""]
