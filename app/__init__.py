from flask import Flask
from .config import Config
from .models.db import init_db, init_fts
from .models.youtube_db import init_youtube_db

def create_app():
    from .services.embedding_service import init_embedding_service
    from .services.scheduler import init_scheduler

    app = Flask(__name__)

    # store config on the app so routes can access it
    app.config.from_object(Config)

    # Initialize daatabase
    init_db()
    init_youtube_db()
    init_fts()

    # Call the embedding_service
    init_embedding_service()

    init_scheduler(app)

    # register blueprints (we'll add routes later)
    from .routes import chat
    from .routes import health
    from .routes import youtube
    app.register_blueprint(health.health_bp)
    app.register_blueprint(chat.chat_bp)
    app.register_blueprint(youtube.youtube_bp)

    return app 
    