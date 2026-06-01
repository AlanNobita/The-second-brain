from flask import Flask
from .config import Config
from .models.db import init_db

def create_app():
    from .services.embedding_service import init_embedding_service

    app = Flask(__name__)

    # store config on the app so routes can access it
    app.config.from_object(Config)

    # Initialize daatabase
    init_db()

    # Call the embedding_service
    init_embedding_service()

    # register blueprints (we'll add routes later)
    from .routes import chat
    from .routes import health
    app.register_blueprint(health.health_bp)
    app.register_blueprint(chat.chat_bp)

    return app 
    