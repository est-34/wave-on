from sqlalchemy import select
from ....adapters.unit_of_work import SqlUnitOfWork
from ..domain.entities import User


class IdentityRepository(SqlUnitOfWork):
    def list_users(self):
        return list(self.session.scalars(select(User).order_by(User.created_at)))


