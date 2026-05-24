import os
from flask import Flask
from flask_session import Session
from config import Config
from db import init_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    Session(app)
    init_db()

    from auth.routes import auth_bp
    from admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    return app


if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    app = create_app()
    app.run(debug=True, port=5000)
