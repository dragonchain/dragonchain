import base64


def get_faas_auth() -> str:
    """Gets authorization to use OpenFaaS

        Returns:
            A string containing authorization for OpenFaaS.
    """
    with open("/etc/openfaas-secret/user", "r") as file:
        username = file.read()
    with open("/etc/openfaas-secret/password", "r") as file:
        password = file.read()

    return f"Basic {base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('ascii')}"
