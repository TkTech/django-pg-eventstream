import pytest
from pytest_postgresql.executor import PostgreSQLExecutor
from django.conf import settings


@pytest.fixture(scope='session')
def django_db_modify_db_settings(postgresql_proc: PostgreSQLExecutor):
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': postgresql_proc.host,
        'PORT': postgresql_proc.port,
        'USER': postgresql_proc.user,
        'PASSWORD': postgresql_proc.password,
        'NAME': 'postgres'
    }