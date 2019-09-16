import os
import json
from typing import List, Dict, Optional

import requests

from dragonchain.lib.faas import get_faas_auth

FAAS_GATEWAY = os.environ["FAAS_GATEWAY"]


def get_raw_logs(contract_id: str, since: Optional[str], tail: Optional[int]) -> List[str]:
    endpoint = f"{FAAS_GATEWAY}/system/logs?name=contract-{contract_id}"

    if tail:
        endpoint += f"&tail={tail}"
    if since:
        endpoint += f"&since={since}"

    response = requests.get(endpoint, headers={"Authorization": get_faas_auth()})
    if response.status_code != 200:
        raise RuntimeError("Error getting contract logs, non-2XX response from OpenFaaS gateway")

    return response.text.split("\n")


def get_logs(contract_id: str, since: Optional[str] = None, tail: Optional[int] = 100) -> List[Dict[str, str]]:
    raw_logs = get_raw_logs(contract_id, since, tail)
    return list(map(lambda x: json.parse(x), raw_logs))
