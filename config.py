from flask import Flask
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from dotenv import load_dotenv
from flask_cors import CORS


import os


# Load environment variables from .env
load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Set JSON output formatting
app.json.compact = False

# Naming convention for SQLAlchemy
metadata = MetaData(naming_convention={
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
})

# Initialize extensions
db = SQLAlchemy(metadata=metadata)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
api = Api(app)

# Attach SQLAlchemy to Flask
db.init_app(app)

#allow cross origin requests
CORS(
    app, supports_credentials=True,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
    origins=["https://booknook254.netlify.app/"],
    allow_headers=["Content-Type", "Authorization"],
        )