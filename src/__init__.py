import os, sys; sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from celery import app as celery_app

__all__ = ('celery_app',)