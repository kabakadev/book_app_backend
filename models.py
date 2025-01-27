from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import ForeignKey
from config import db, bcrypt

class User(db.Model, SerializerMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), unique=True,nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    #relationship
    revews = db.relationship('Review', back_populates='user',lazy='dynamic')
    reading_list = db.relationship('ReadingList', back_populates='user', lazy='dynamic')

    
    
