"""Entry point: `python app.py` for local development, or `flask --app app run`."""
import os

from eduquest import create_app

app = create_app()

if __name__ == "__main__":
    # Debug mode runs an interactive console, so it is opt-in and never the default
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
