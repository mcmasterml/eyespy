import os
from decouple import config

BASE_DIR = os.path.abspath(os.path.dirname(__file__))



class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '5WjKWBaQa5TaD594H2oOKw'
    home = BASE_DIR


class DevelopmentConfig(Config):
    DEBUG = True
    IMAGE_FOLDER = os.path.join(Config.home, 'tmp/images')
    VIDEO_FOLDER = os.path.join(Config.home, 'tmp/videos')
    CSV_FOLDER = os.path.join(Config.home, 'tmp/csvs')


class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    IMAGE_FOLDER = os.path.join(Config.home, 'tmp/images')
    VIDEO_FOLDER = os.path.join(Config.home, 'tmp/videos')
    CSV_FOLDER = os.path.join(Config.home, 'tmp/csvs')


class ProductionConfig(Config):
    DEBUG = False
    IMAGE_FOLDER = os.path.join(Config.home, 'tmp/images')
    VIDEO_FOLDER = os.path.join(Config.home, 'tmp/videos')
    CSV_FOLDER = os.path.join(Config.home, 'tmp/csvs')
