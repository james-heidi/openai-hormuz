class App:
    def get(self, path):
        def decorator(fn):
            return fn

        return decorator


class User:
    password_hash = "hash"
    ssn = "123-45-6789"
    dob = "1990-01-01"


class Query:
    def get(self, id):
        return User()

    def all(self):
        return [User()]


class Database:
    def query(self, _model):
        return Query()


app = App()
db = Database()


@app.get("/users/{id}")
def get_user(id: int):
    user = db.query(User).get(id)
    return user.__dict__  # exposes password_hash, ssn, dob


@app.get("/admin/all-users")
def get_all_users():
    return db.query(User).all()

