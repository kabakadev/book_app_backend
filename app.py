from flask import request, jsonify, session, send_file, Response
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from config import app, db, api
from models import User, Book, Review, ReadingList, ReadingListBook, ReadingProgress, ContentReport
import logging
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os
import requests
from io import BytesIO
from PyPDF2 import PdfReader
from sqlalchemy import func, text
from datetime import datetime
from werkzeug.utils import secure_filename
import tempfile

# Configure Cloudinary
cloudinary.config( 
    cloud_name=os.getenv('CLOUD_NAME'),
    api_key=os.getenv('CLOUD_API_KEY'),
    api_secret=os.getenv('CLOUD_API_SECRET'),
    secure=True
)

# Session-based authentication check function
def check_auth():
    if 'user_id' not in session:
        return False
    return True
# PDF proxy endpoint with improved authentication handling
@app.route('/pdf-proxy/<int:book_id>', methods=['GET'])
def pdf_proxy(book_id):
    """Proxy PDF content from Cloudinary through the backend"""
    # Check if user is logged in using session
    if 'user_id' not in session:
        print(f"PDF Proxy: Authentication failed - no user_id in session")
        return jsonify({"error": "Unauthorized. Please log in."}), 401
        
    user_id = session.get('user_id')
    print(f"PDF Proxy: User {user_id} requesting PDF for book {book_id}")
    
    book = Book.query.get(book_id)
    
    if not book or not book.pdf_url:
        print(f"PDF Proxy: Book {book_id} not found or has no PDF URL")
        return jsonify({"error": "PDF not found"}), 404
        
    try:
        print(f"PDF Proxy: Fetching PDF from {book.pdf_url}")
        # Fetch the PDF from Cloudinary
        response = requests.get(book.pdf_url, stream=True)
        
        if not response.ok:
            print(f"PDF Proxy: Cloudinary returned error {response.status_code}")
            return jsonify({"error": f"Failed to fetch PDF: {response.status_code}"}), 500
            
        # Return the PDF content
        print(f"PDF Proxy: Successfully fetched PDF, returning to client")
        return Response(
            response.iter_content(chunk_size=1024),
            content_type=response.headers.get('Content-Type', 'application/pdf'),
            headers={
                'Content-Disposition': f'inline; filename="{book.title}.pdf"',
                'Access-Control-Allow-Origin': '*',  # Allow CORS for PDF.js
                'Access-Control-Allow-Credentials': 'true'  # Allow credentials
            }
        )
    except Exception as e:
        print(f"PDF Proxy: Exception occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/search')
def search():
    query = request.args.get('q')
    results = Book.query.filter(
        func.to_tsvector('english', Book.title + ' ' + Book.author + ' ' + Book.description)
        .match(func.to_tsquery('english', query))
    ).all()
    return jsonify([book.to_dict() for book in results])

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    # Check if user is logged in
    if not check_auth():
        return jsonify({"error": "Unauthorized. Please log in."}), 401
        
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file uploaded"}), 400
    
    file = request.files['pdf']
    # Check file size (limit to 10MB)
    if len(file.read()) > 10 * 1024 * 1024:  # 10MB in bytes
        return jsonify({"error": "File size exceeds 10MB limit"}), 400
    #reset file pointer after reading
    file.seek(0)
    
    # Step 1: Upload PDF to Cloudinary
    try:
        upload_result = cloudinary.uploader.upload(
            file,
            resource_type="raw",
            folder="pdf_books",  # Optional: Organize PDFs in Cloudinary
            format="pdf",
            type="upload",
            access_mode="public",  # Make sure it's public
            use_filename=True,
            unique_filename=True
        )
        pdf_url = upload_result["secure_url"]
        file_size = upload_result.get("bytes", 0)
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500
    
    # Reset file pointer for metadata extraction
    file.seek(0)
    
    # Step 2: Extract Metadata and content preview
    try:
        metadata = extract_pdf_metadata(file)

        #extract content preview for search (first few pages)
        file.seek(0)
        content_preview = extract_content_preview(file)
    except Exception as e:
        return jsonify({"error": f"Metadata extraction failed: {str(e)}"}), 500

    # Step 3: Save to Database
    try:
        book = Book(
            title=metadata["title"],
            author=metadata["author"],
            page_count=metadata["page_count"],
            pdf_url=pdf_url,
            is_pdf=True,
            file_size=file_size,
            content_preview=content_preview,
            upload_date=datetime.utcnow(),
            # Optional: Set other fields (genre, description, etc.)
        )
        db.session.add(book)
        db.session.commit()
        
        # Update search vector
        Book.update_search_vector()
        
        return jsonify(book.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500

def extract_pdf_metadata(pdf_file):
    pdf = PdfReader(pdf_file)
    
    # Extract title and author with fallbacks
    title = pdf.metadata.get("/Title", "")
    if not title:
        # Use filename as fallback
        title = pdf_file.filename.replace(".pdf", "")
    
    author = pdf.metadata.get("/Author", "Unknown")
    
    return {
        "title": title,
        "author": author,
        "page_count": len(pdf.pages)
    }

def extract_content_preview(pdf_file, max_pages=5, max_chars=10000):
    """Extract text from the first few pages for search indexing"""
    pdf = PdfReader(pdf_file)
    content = []
    
    # Extract text from first few pages
    for i in range(min(max_pages, len(pdf.pages))):
        page = pdf.pages[i]
        content.append(page.extract_text())
        
        # Check if we've extracted enough text
        if sum(len(text) for text in content) >= max_chars:
            break
    
    return " ".join(content)[:max_chars]

# Replace both search_pdfs functions with this one
@app.route('/search-pdfs')
def search_pdfs():
    query = request.args.get('q')
    if not query:
        return jsonify([])
    
    # Use PostgreSQL's full-text search capabilities
    results = Book.query.filter(
        func.to_tsvector('english', 
            Book.title + ' ' + 
            Book.author + ' ' + 
            func.coalesce(Book.description, '') + ' ' + 
            func.coalesce(Book.content_preview, '')
        ).match(func.to_tsquery('english', query))
    ).all()
    
    return jsonify([book.to_dict() for book in results])

# Endpoint to track reading progress
@app.route('/reading-progress', methods=['POST'])
def update_reading_progress():
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401
    
    user_id = session['user_id']
    data = request.json
    
    if not data or 'book_id' not in data or 'page' not in data or 'percentage' not in data:
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        # Check if progress record exists
        progress = ReadingProgress.query.filter_by(
            user_id=user_id,
            book_id=data['book_id']
        ).first()
        
        if progress:
            progress.current_page = data['page']
            progress.percentage = data['percentage']
            progress.last_read = datetime.utcnow()
        else:
            progress = ReadingProgress(
                user_id=user_id,
                book_id=data['book_id'],
                current_page=data['page'],
                percentage=data['percentage'],
                last_read=datetime.utcnow()
            )
            db.session.add(progress)
        
        db.session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update reading progress: {str(e)}"}), 500

# Endpoint to report unauthorized content
@app.route('/report-content', methods=['POST'])
def report_content():
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401
    
    user_id = session['user_id']
    data = request.json
    
    if not data or 'book_id' not in data or 'reason' not in data:
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        report = ContentReport(
            user_id=user_id,
            book_id=data['book_id'],
            reason=data['reason'],
            details=data.get('details', ''),
            report_date=datetime.utcnow()
        )
        db.session.add(report)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Report submitted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to submit report: {str(e)}"}), 500

# Add a new endpoint to get reading progress for a book
@app.route('/reading-progress/<int:book_id>', methods=['GET'])
def get_reading_progress(book_id):
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401
    
    user_id = session['user_id']
    
    try:
        progress = ReadingProgress.query.filter_by(
            user_id=user_id,
            book_id=book_id
        ).first()
        
        if progress:
            return jsonify({
                "current_page": progress.current_page,
                "percentage": progress.percentage,
                "last_read": progress.last_read.isoformat()
            }), 200
        else:
            return jsonify({
                "current_page": 1,
                "percentage": 0,
                "last_read": None
            }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get reading progress: {str(e)}"}), 500

# Add an endpoint to get bookmarks for a book
@app.route('/bookmarks/<int:book_id>', methods=['GET', 'POST', 'DELETE'])
def manage_bookmarks(book_id):
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401
    
    user_id = session['user_id']
    
    # GET: Retrieve bookmarks
    if request.method == 'GET':
        try:
            # This would require a Bookmark model, which we'll need to add
            # For now, we'll use localStorage in the frontend
            return jsonify({"message": "Bookmark functionality will be implemented soon"}), 200
        except Exception as e:
            return jsonify({"error": f"Failed to get bookmarks: {str(e)}"}), 500
    
    # Other methods would be implemented similarly
    return jsonify({"message": "Endpoint not fully implemented yet"}), 501

@app.route('/health')
def health_check():
    return jsonify({"status":"ok"}),200

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
def check_auth_route():
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