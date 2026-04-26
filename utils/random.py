import uuid
import random
import string


def generate_uuid() -> str:
    return str(uuid.uuid4()).replace("-", "")


def generate_key() -> str:
    return "sk-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=48))


def get_random_string(length: int = 4) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
