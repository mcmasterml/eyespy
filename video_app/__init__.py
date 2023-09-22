from flask import Flask
from config import DevelopmentConfig, ProductionConfig, TestingConfig
from video_app.routes.main_routes import main

import os
import logging
from logging.handlers import RotatingFileHandler


configurations = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}


def create_app(config_name='production'):
    app = Flask(__name__)

    # Load the configuration
    app.config.from_object(configurations[config_name])

    # Register the blueprints
    app.register_blueprint(main)

    # Initialize empty cache for models
    app.model_cache = {}

    # Set up logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            'logs/video_app.log', maxBytes=10240, backupCount=20)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Video App startup')

    return app
