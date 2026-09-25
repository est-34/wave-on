class SqlUnitOfWork:
    def __init__(self, session):
        self.session = session

    def get(self, entity, key):
        return self.session.get(entity, key)

    def add(self, entity):
        self.session.add(entity)

    def add_all(self, entities):
        self.session.add_all(entities)

    def delete(self, entity):
        self.session.delete(entity)

    def flush(self):
        self.session.flush()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()


