from flask import Flask
from .config import Config
from .models.db import init_db

def create_app():
    app = Flask(__name__)

    # store config on the app so routes can access it
    app.config.from_object(Config)

    # Initialize daatabase
    init_db()

    # register blueprints (we'll add routes later)
    from .routes import chat
    app.register_blueprint(chat.chat_bp)

    return app 
    