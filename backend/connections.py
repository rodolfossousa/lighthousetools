"""
Gerencia conexões Lighthouse por sessão do utilizador.
"""
import threading
from lighthouse import connect, clients, Lighthouse

_lock = threading.Lock()
_store: dict[str, Lighthouse] = {}


def get_environments() -> dict:
    return {env: list(cls.keys()) for env, cls in clients.items()}


def connect_environment(user_id: int, environment: str, client_name: str) -> Lighthouse:
    key = f"{user_id}:{environment}:{client_name}"
    ws = connect(client_name, environment, debug=False)
    with _lock:
        _store[key] = ws
    return ws


def get_connection(user_id: int, environment: str, client_name: str) -> Lighthouse | None:
    key = f"{user_id}:{environment}:{client_name}"
    with _lock:
        return _store.get(key)


def disconnect(user_id: int):
    with _lock:
        keys_to_remove = [k for k in _store if k.startswith(f"{user_id}:")]
        for k in keys_to_remove:
            del _store[k]
