from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import ForeignKey
import re
from config import db, bcrypt

class User(db.Model, SerializerMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True,nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    #relationship
    revews = db.relationship('Review', back_populates='user',lazy='dynamic')
    reading_list = db.relationship('ReadingList', back_populates='user', lazy='dynamic')

    #validation and password handling]
    @validates('username')
    def validate_username(self,key,username):
        if not username or len(username) < 3:
            raise ValueError("Username must be atleast 3 characters long")
        if username.isdigit(): #check if the username consists of only digits
            raise ValueError("Username cannot be just numbers.")
        if not re.match("^[A-Za-z0-9_]+$", username): #restrict to alphanumeric + underscores
            raise ValueError("Username can only contain letters,numbers and underscores")
        return username
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

#book model
class Book(db.Model, SerializerMixin):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(100))
    description = db.Column(db.Text)
    page_count = db.Column(db.Integer)
    image_url = db.Column(db.String(255))
    publication_year = db.Column(db.Integer)

    #relationship
    reviews=db.relationship('Review', back_populates='book',lazy='dynamic')
    reading_list_books= db.relationship('ReadingListBook', back_populates='book')
    
    