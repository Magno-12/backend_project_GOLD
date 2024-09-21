from dependency_injector import containers, providers
from app.db.session import SessionLocal
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.core.config import settings, ld_client

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    db = providers.Singleton(SessionLocal)
    auth_service = providers.Factory(
        AuthService,
        db=db,
        settings=settings
    )
    user_service = providers.Factory(
        UserService,
        db=db,
        settings=settings
    )
    feature_flags = providers.Object(ld_client)

container = Container()
