from flask import request,jsonify,session
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from config import app, db, api
from models import User, Book, Review, ReadingList,ReadingListBook
import logging

@app.route('/init-db')
def init_db():
    try:
        db.create_all()
        return jsonify({"message": "Database tables created successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.before_request
def check_protected_endpoints():
    protected_endpoints =['/books','/reading-lists']
    logging.debug(f"Session Data: {session.get('user_id')}")

    #allow preflight requests to pass
    if request.method == 'OPTIONS':
        return jsonify({"message":"Ok"}), 200

    if any(request.path.startswith(endpoint) for endpoint in protected_endpoints) and not session.get('user_id'):
        return jsonify({"error": "unauthorized. please log in"}), 401


@app.route('/check-auth', methods=['GET'])
def check_auth():
    print("Session data:", session)  # Debugging: Print session data
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            print(f"User authenticated: {user.id}")  # Debugging
            return jsonify({"authenticated": True, "user": {"id": user.id, "username": user.username}})
    print("User not authenticated")  # Debugging
    return jsonify({"authenticated": False}), 401

class HomeResource(Resource):
    def get(self):
        return jsonify({"message": "Welcome to the Book App API!"})
api.add_resource(HomeResource, "/")


class SignupResource(Resource):
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
            session['user_id'] = new_user.id  # Auto-login after signup
            return {"message": "Signup successful", "user": {"id": new_user.id, "username": new_user.username}}, 201
        except IntegrityError:
            db.session.rollback()
            return {"error": "Username already taken, try another one."}, 400

api.add_resource(SignupResource, '/signup')

class LoginResource(Resource):
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            print(f"Session set for user: {user.id}")  # Debugging
            return {"message": "Login successful", "user": {"id": user.id, "username": user.username}}, 200
        return {"error": "Invalid credentials"}, 401
class LogoutResource(Resource):
    def post(self):
        if 'user_id' not in session:
            return{"error":"Not logged in"}, 400
        session.pop('user_id', None)
        return {"message":"Logged out successfully"}, 200

api.add_resource(LoginResource, '/login')
api.add_resource(LogoutResource, '/logout')


@app.errorhandler(404)
def handle_404_error(e):
    return jsonify({"error":"The requested endpoint was not found, check the url for any typos"}),404

class UserInfo(Resource):
    def get(self, id=None):
        if id:
            user = User.query.get(id)
            if user:
                return user.to_dict()
            return {"error": "User not found"}, 404
        users = User.query.all()
        return [user.to_dict() for user in users]

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
            return new_user.to_dict(), 201
        except IntegrityError:
            db.session.rollback()
            return {"error": "Username must be unique."}, 400
api.add_resource(UserInfo, '/users', '/users/<int:id>')

class BookResource(Resource):
    def get(self, id=None):
        if id:
            book = Book.query.get(id)
            if book:
                return book.to_dict()
            return {"error": "Book not found"}, 404
        books = Book.query.all()
        return [book.to_dict() for book in books]

    def post(self):
        try:
            data = request.get_json()
            if not data.get('title') or not data.get('author'):
                return {"error": "Title and author are required."}, 400

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
            return new_book.to_dict(), 201
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Integrity error: {str(e)}")
            return {"error": "Failed to create book. Please check the data."}, 400
        except Exception as e:
            db.session.rollback()
            logging.error(f"Unexpected error: {str(e)}")
            return {"error": "An unexpected error occurred. Please try again."}, 500
api.add_resource(BookResource, '/books', '/books/<int:id>')

# Review Resource
class ReviewResource(Resource):
    def get(self, id=None):
        if id:
            review = Review.query.get(id)
            if review:
                return review.to_dict()
            return {"error": "Review not found"}, 404
        reviews = Review.query.all()
        return [review.to_dict() for review in reviews]

     # POST: Create a new review
    def post(self):
        data = request.get_json()

        user_id = data.get('user_id')
        book_id = data.get('book_id')
        review_text = data.get('review_text')
        rating = data.get('rating')

        if not user_id or not book_id or not review_text or not rating:
            return {'error': 'User ID, Book ID, review text, and rating are required'}, 422
        # Check if the user has already reviewed this book
        existing_review = Review.query.filter_by(user_id=user_id, book_id=book_id).first()
        if existing_review:
            return {"error": "You have already reviewed this book."}, 400


        try:
            new_review = Review(
                user_id=user_id,
                book_id=book_id,
                review_text=review_text,
                rating=rating
            )
            db.session.add(new_review)
            db.session.commit()
            return new_review.to_dict(), 201
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to create review. Please check the data."}, 400
        
    def put(self, id):
        data = request.get_json()

        review = Review.query.get(id)
        if not review:
            return {"error": "Review not found"}, 404

        review.review_text = data.get('review_text', review.review_text)  
        review.rating = data.get('rating', review.rating)  

        try:
            db.session.commit()
            return review.to_dict(), 200
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to update review. Please check the data."}, 400
    def delete(self, id):
      
        review = Review.query.get(id)
        if not review:
            return {"error": "Review not found"}, 404

        try:
            db.session.delete(review)
            db.session.commit()
            return {"message": "Review deleted successfully"}, 200
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to delete review."}, 400


api.add_resource(ReviewResource, '/reviews', '/reviews/<int:id>')
# Resource: ReadingList
class ReadingListResource(Resource):
    def get(self, list_id=None):
        if list_id:
            reading_list = ReadingList.query.get(list_id)
            if not reading_list:
                return {'error': 'Reading list not found'}, 404
            return reading_list.to_dict(rules=("books", "user")), 200

        user_id = request.args.get('user_id')
        if not user_id:
            return {'error': 'User ID is required'}, 400

        reading_lists = ReadingList.query.filter_by(user_id=user_id).all()
        return [rl.to_dict(rules=("books",)) for rl in reading_lists], 200

    def post(self):
        data = request.get_json()
        name = data.get('name')
        user_id = data.get('user_id')
        book_ids = data.get('book_ids', [])

        if not name or not user_id:
            return {'error': 'Name and User ID are required'}, 400
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}, 404
        if len(book_ids) != len(set(book_ids)):
            return {'error': 'Duplicate books are not allowed in the reading list'}, 400

        existing_reading_list = ReadingList.query.filter_by(user_id=user_id, name=name).first()
        if existing_reading_list:
            return {'error': 'A reading list with this name already exists for the user'}, 400
        books = Book.query.filter(Book.id.in_(book_ids)).all()
        if len(books) != len(book_ids):
            return {'error': 'One or more books not found'}, 404
      



        try:
            reading_list = ReadingList(name=name, user_id=user_id)
           

            for book_id in book_ids:
                book = Book.query.get(book_id)
                if book:
                    reading_list_book = ReadingListBook(book=book, reading_list=reading_list)
                    db.session.add(reading_list_book)

            db.session.add(reading_list)
            db.session.commit()
            return reading_list.to_dict(rules=("books",)), 201
        except IntegrityError:
            db.session.rollback()
            return {'error': 'Error creating reading list'}, 500
        

    def put(self, list_id):
        data = request.get_json()
        reading_list = ReadingList.query.get(list_id)

        if not reading_list:
            return {'error': 'Reading list not found'}, 404

        name = data.get('name')
        book_ids = data.get('book_ids', [])

        if name:
            reading_list.name = name
        if len(book_ids) != len(set(book_ids)):
            return {'error': 'Duplicate books are not allowed in the reading list'}, 400

    
        books = Book.query.filter(Book.id.in_(book_ids)).all()
        if len(books) != len(book_ids):
            return {'error': 'One or more books not found'}, 404
        


        ReadingListBook.query.filter_by(reading_list_id=reading_list.id).delete()
        for book in books:
            reading_list_book = ReadingListBook(book=book, reading_list=reading_list)
            db.session.add(reading_list_book)

        try:
            db.session.commit()
            return reading_list.to_dict(rules=("books",)), 200
        except IntegrityError:
            db.session.rollback()
            return {'error': 'Error updating reading list'}, 500

    def delete(self, list_id):
        reading_list = ReadingList.query.get(list_id)

        if not reading_list:
            return {'error': 'Reading list not found'}, 404

        try:
            ReadingListBook.query.filter_by(reading_list_id=reading_list.id).delete()
            db.session.delete(reading_list)
            db.session.commit()
            return {'message': 'Reading list deleted'}, 200
        except IntegrityError:
            db.session.rollback()
            return {'error': 'Error deleting reading list'}, 500

# Add the ReadingListResource to the API
api.add_resource(
    ReadingListResource,
    '/reading-lists',
    '/reading-lists/<int:list_id>'
)
if __name__ == "__main__":
    app.run(debug=True)
