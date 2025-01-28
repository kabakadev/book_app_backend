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
    reviews = db.relationship('Review', back_populates='user',lazy='dynamic')
    reading_lists = db.relationship('ReadingList', back_populates='user', lazy='dynamic')

    # SerializerMixin Rules
    serialize_rules =("-password_hash","-reviews.user","-reading_lists.user")

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
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(100))
    description = db.Column(db.Text)
    page_count = db.Column(db.Integer)
    image_url = db.Column(db.String(255))
    publication_year = db.Column(db.Integer)
    
    @validates('title', 'author', 'genre')
    def validate_book_fields(self, key, value):
        if not value or len(value.strip()) == 0:
            raise ValueError(f"{key.capitalize()} cannot be empty.")
        if key == 'genre' and len(value) > 100:
            raise ValueError("Genre must be less than 100 characters.")
        return value
    
    @validates('page_count', 'publication_year')
    def validate_numeric_fields(self, key, value):
        if key == 'page_count' and (not isinstance(value, int) or value <= 0):
            raise ValueError("Page count must be a positive integer.")
        if key == 'publication_year' and (not isinstance(value, int) or value < 0):
            raise ValueError("Publication year must be a non-negative integer.")
        return value

    #relationship
    reviews=db.relationship('Review', back_populates='book',lazy='dynamic')
    reading_list_books= db.relationship('ReadingListBook', back_populates='book')

    #SerializerMixin Rules
    serialize_rules=("-reviews.book","-reading_list_books.book")

#Reading List model
class ReadingList(db.Model, SerializerMixin):
    __tablename__ = 'reading_lists'

    id= db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)

    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) == 0:
            raise ValueError("Reading list name cannot be empty.")
        if len(name) > 80:
            raise ValueError("Reading list name must be less than 80 characters.")
        return name

    #relationship
    user = db.relationship('User', back_populates='reading_lists')
    books = db.relationship('ReadingListBook', back_populates='reading_list', lazy='dynamic')

    # Serializer rules
    serialize_rules=("-user.reading_lists", "-books.reading_list")

#Reading List book model
class ReadingListBook(db.Model, SerializerMixin):
    __tablename__ = 'reading_list_books'

    id = db.Column(db.Integer, primary_key=True)
    reading_list_id = db.Column(db.Integer, ForeignKey('reading_lists.id'), nullable=False)
    book_id = db.Column(db.Integer, ForeignKey('books.id'), nullable=False)
    note = db.Column(db.Text)
    rating = db.Column(db.Integer)

    #relationships
    reading_list = db.relationship('ReadingList', back_populates='books')
    book = db.relationship('Book', back_populates='reading_list_books')

    # serializer Rules
    serialize_rules = ("-reading_list.books", "-book.reading_list_books")

#review Model
class Review(db.Model, SerializerMixin):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, ForeignKey('books.id'), nullable=False)
    review_text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    #relationship
    user = db.relationship('User',back_populates='reviews')
    book = db.relationship('Book', back_populates='reviews')
    # serializer rules
    serialize_rules = ("-user.reviews", "-book.reviews")


