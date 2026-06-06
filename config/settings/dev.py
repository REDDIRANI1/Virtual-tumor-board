from .base import *

DEBUG = True

INSTALLED_APPS += ['corsheaders']
MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')

CORS_ALLOW_ALL_ORIGINS = True
