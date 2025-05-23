from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import ForeignKey
import re
from config import db, bcrypt
from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy import func, Column, Integer, String, Boolean, Text, DateTime
from datetime import datetime

class User(db.Model, SerializerMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True,nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    serialize_only = ("id","username","reading_lists","reviews")

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
    search_vector = db.Column(TSVECTOR)  # Add this line
    pdf_url = db.Column(db.String(255))  # Cloudinary PDF URL
    is_pdf = db.Column(db.Boolean, default=False)  # Distinguish PDFs from regular books
    file_size = db.Column(db.Integer)  # Size in bytes
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    content_preview = db.Column(db.Text)  # First few pages of content for search
    serialize_only = ("id","title","author","genre","description","page_count","image_url","publication_year","reviews","reading_list_books", "pdf_url", "is_pdf")

    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'description': self.description,
            'cover_url': self.image_url,
            'pdf_url': self.pdf_url,
            'is_pdf': self.is_pdf,
            'page_count': self.page_count,
            'file_size': self.file_size,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None
        }
    # Add this method to update search_vector
    @classmethod
    def update_search_vector(cls):
        db.session.execute(text("""
            UPDATE books
            SET search_vector = to_tsvector('english', 
                COALESCE(title, '') || ' ' || 
                COALESCE(author, '') || ' ' || 
                COALESCE(description, '') || ' ' || 
                COALESCE(content_preview, '')
            )
        """))  # Added closing parenthesis here
        db.session.commit()
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
    serialize_only =("id","name","created_at","updated_at","user_id","books")

    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) == 0:
            raise ValueError("Reading list name cannot be empty.")
        if len(name) > 80:
            raise ValueError("Reading list name must be less than 80 characters.")
        return name

    #relationship
    user = db.relationship('User', back_populates='reading_lists')
    books = db.relationship('ReadingListBook', back_populates='reading_list', lazy='joined')

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

    serialize_only = ("id","reading_list_id","book_id","note","rating","book")

    @validates('note')
    def validate_note(self, key, note):
        if note and len(note) > 1000:
            raise ValueError("Note must be less than 1000 characters.")
        return note
    @validates('rating')
    def validate_rating(self, key, rating):
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            raise ValueError("Rating must be an integer between 1 and 5.")
        return rating

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
    serialize_only = ("id","user_id","book_id","review_text","rating","created_at","book")

    @validates('review_text')
    def validate_review_text(self, key, review_text):
        if not review_text or len(review_text.strip()) == 0:
            raise ValueError("Review text cannot be empty.")
        if len(review_text) > 5000:
            raise ValueError("Review text must be less than 5000 characters.")
        return review_text
    
    @validates('rating')
    def validate_rating(self, key, rating):
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            raise ValueError("Rating must be an integer between 1 and 5.")
        return rating

    #relationship
    user = db.relationship('User',back_populates='reviews')
    book = db.relationship('Book', back_populates='reviews')
    # serializer rules
    serialize_rules = ("-user.reviews", "-book.reviews")
    # Add these models to your models.py file

class ReadingProgress(db.Model, SerializerMixin):
    __tablename__ = 'reading_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, ForeignKey('books.id'), nullable=False)
    current_page = db.Column(db.Integer, default=1)
    percentage = db.Column(db.Integer, default=0)  # 0-100
    last_read = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('reading_progress', lazy='dynamic'))
    book = db.relationship('Book', backref=db.backref('reading_progress', lazy='dynamic'))
    
    # SerializerMixin rules
    serialize_only = ("id", "user_id", "book_id", "current_page", "percentage", "last_read")
    serialize_rules = ("-user.reading_progress", "-book.reading_progress")
    
    @validates('current_page')
    def validate_current_page(self, key, page):
        if not isinstance(page, int) or page < 1:
            raise ValueError("Current page must be a positive integer")
        return page
    
    @validates('percentage')
    def validate_percentage(self, key, percentage):
        if not isinstance(percentage, int) or percentage < 0 or percentage > 100:
            raise ValueError("Percentage must be an integer between 0 and 100")
        return percentage


class ContentReport(db.Model, SerializerMixin):
    __tablename__ = 'content_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, ForeignKey('books.id'), nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    report_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, reviewed, resolved
    
    # Relationships
    user = db.relationship('User', backref=db.backref('content_reports', lazy='dynamic'))
    book = db.relationship('Book', backref=db.backref('content_reports', lazy='dynamic'))
    
    # SerializerMixin rules
    serialize_only = ("id", "user_id", "book_id", "reason", "details", "report_date", "status")
    serialize_rules = ("-user.content_reports", "-book.content_reports")
    
    @validates('reason')
    def validate_reason(self, key, reason):
        if not reason or len(reason.strip()) == 0:
            raise ValueError("Reason cannot be empty")
        if len(reason) > 100:
            raise ValueError("Reason must be less than 100 characters")
        return reason
    
    @validates('status')
    def validate_status(self, key, status):
        valid_statuses = ['pending', 'reviewed', 'resolved']
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return status
