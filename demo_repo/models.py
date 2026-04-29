class Column:
    def __init__(self, column_type):
        self.column_type = column_type


class String:
    pass


class Base:
    pass


class User(Base):
    password = Column(String)  # not hashed

    # No deletion policy, no retention timestamp
    pass

