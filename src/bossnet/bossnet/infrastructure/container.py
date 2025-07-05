"""
Dependency injection container using dependency-injector
"""

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from src.application.services.auth_service import AuthService
from src.application.services.user_service import UserService
from src.config.settings import get_settings
from src.infrastructure.auth.jwt_service import JWTService
from src.infrastructure.persistence.sqlalchemy.database import get_database
from src.infrastructure.persistence.sqlalchemy.repositories.user_repository import SQLAlchemyUserRepository


class Container(containers.DeclarativeContainer):
    """Dependency injection container"""

    # Configuration
    config = providers.Singleton(get_settings)

    # Database
    database = providers.Resource(get_database)

    # Repositories
    user_repository = providers.Factory(SQLAlchemyUserRepository, session_factory=database.provided.session)

    # Services
    jwt_service = providers.Singleton(
        JWTService,
        secret_key=config.provided.SECRET_KEY,
        algorithm=config.provided.ALGORITHM,
        access_token_expire_minutes=config.provided.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days=config.provided.REFRESH_TOKEN_EXPIRE_DAYS,
    )

    auth_service = providers.Factory(AuthService, user_repository=user_repository, jwt_service=jwt_service)

    user_service = providers.Factory(UserService, user_repository=user_repository)
