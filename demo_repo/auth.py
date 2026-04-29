import logging

logger = logging.getLogger(__name__)


class Database:
    def execute(self, query: str):
        return [{"email": "ada@example.com", "password_hash": "hash"}]


db = Database()


def login(email, password):
    logger.info(f"Login attempt: email={email}, password={password}")
    return get_user(email)


def get_user(email_input):
    query = f"SELECT * FROM users WHERE email = '{email_input}'"
    return db.execute(query)

