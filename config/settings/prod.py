from .base import *
import os

DEBUG = False

# Read ALLOWED_HOSTS from environment variable, fallback to localhost for safety
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',')] if allowed_hosts_env else ['127.0.0.1', 'localhost']

