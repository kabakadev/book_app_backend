from flask import request,jsonify
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from config import app, db, api
from models import User, Book, Review, ReadingList


class UserInfo(Resource):
    def get(self, id=None):
        if id:
            user = User.query.get(id)
            if user:
                return jsonify(user.to_dict())
            return {"error": "User not found"}, 404
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])

    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return {'error': 'Username and password are required'}, 422

        try:
    
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            return jsonify(new_user.to_dict()), 201
        except IntegrityError:
            db.session.rollback()
            return {"error": "Username must be unique."}, 400
api.add_resource(UserInfo, '/users', '/users/<int:id>')

class BookResource(Resource):
    def get(self, id=None):
        if id:
            book = Book.query.get(id)
            if book:
                return jsonify(book.to_dict())
            return {"error": "Book not found"}, 404
        books = Book.query.all()
        return jsonify([book.to_dict() for book in books])

    def post(self):
        try:
            data = request.get_json()
            new_book = Book(
                title=data['title'],
                author=data['author'],
                genre=data.get('genre'),
                description=data.get('description'),
                page_count=data.get('page_count'),
                image_url=data.get('image_url'),
                publication_year=data.get('publication_year'),
            )
            db.session.add(new_book)
            db.session.commit()
            return jsonify(new_book.to_dict()), 201
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to create book. Please check the data."}, 400
api.add_resource(BookResource, '/books', '/books/<int:id>')

# Review Resource
class ReviewResource(Resource):
    def get(self, id=None):
        if id:
            review = Review.query.get(id)
            if review:
                return jsonify(review.to_dict())
            return {"error": "Review not found"}, 404
        reviews = Review.query.all()
        return jsonify([review.to_dict() for review in reviews])

    def post(self):
        try:
            data = request.get_json()
            new_review = Review(
                user_id=data['user_id'],
                book_id=data['book_id'],
                review_text=data['review_text'],
                rating=data['rating'],
            )
            db.session.add(new_review)
            db.session.commit()
            return jsonify(new_review.to_dict()), 201
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to create review. Please check the data."}, 400

api.add_resource(ReviewResource, '/reviews', '/reviews/<int:id>')