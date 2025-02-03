# Book Management API

This is a RESTful API built using Flask for managing books, reviews, and user authentication. It supports operations for adding, retrieving, updating, and deleting books and reviews, along with session-based user authentication.

## Prerequisites

Before using this repository, you should be familiar with:

- Python and Flask
- RESTful API concepts
- SQLAlchemy ORM for database interactions
- PostgreSQL (as the database)
- Flask-Migrate for database migrations
- Flask-Bcrypt for password hashing
- Flask-Login for session-based authentication

## Installation

### Setup and Installation

1. Clone the repository,
   ```sh
     git clone https://github.com/kabakadev/book_app_backend.git
   ```
   and cd:
   ```sh
    cd book_app_backend
   ```
2. Create and activate a virtual environment:

   ```sh
   pipenv shell

   ```

3. Install dependencies:
   ```sh
   pipenv install -r requirements.txt
   ```
4. Set up the database:
   ```sh
   flask db init
   flask db migrate
   flask db upgrade
   ```
5. Run the application:
   ```sh
   python app.py
   ```

## API Endpoints

### Authentication

#### POST /signup

Register a new user.

- **Request Body:**
  ```json
  {
    "username": "newuser",
    "password": "password123"
  }
  ```
- **Response:**
  ```json
  {
    "message": "Signup successful",
    "user": {
      "id": 1,
      "username": "newuser"
    }
  }
  ```

#### POST /login

Log in an existing user.

- **Request Body:**
  ```json
  {
    "username": "newuser",
    "password": "password123"
  }
  ```
- **Response:**
  ```json
  {
    "message": "Login successful",
    "user": {
      "id": 1,
      "username": "newuser"
    }
  }
  ```

#### POST /logout

Log out the current user.

- **Response:**
  ```json
  {
    "message": "Logged out successfully"
  }
  ```

#### GET /check-auth

Check if a user is authenticated.

- **Response:**
  ```json
  {
    "authenticated": true,
    "user": {
      "id": 1,
      "username": "newuser"
    }
  }
  ```

### Books Resource

#### GET /books

Retrieve a list of all books.

#### GET /books/<id>

Retrieve a single book by its ID.

#### POST /books

Create a new book entry. (Requires authentication)

```json
{
  "title": "Book Title",
  "author": "Book Author",
  "genre": "Fiction",
  "description": "A brief description of the book.",
  "page_count": 300,
  "image_url": "http://example.com/image.jpg",
  "publication_year": 2021
}
```

#### DELETE /books/<id>

Delete a book by ID. (Requires authentication)

### Reviews Resource

#### GET /reviews

Retrieve a list of all reviews.

#### GET /reviews/<id>

Retrieve a single review by its ID.

#### POST /reviews

### Reading Lists Resource

#### GET /reading-lists

Retrieve a list of all reading lists for a specific user.

Query Parameters:

- user_id (int): The ID of the user whose reading lists are to be retrieved.

#### GET /reading-lists/<list_id>

Retrieve a single reading list by its ID.

#### POST /reading-lists

Create a new reading list. (Requires authentication)

```json
{
  "name": "My Reading List",
  "user_id": 1,
  "book_ids": [1, 2, 3]
}
```

#### DELETE /reading-lists/<list_id>

Delete a reading list. (Requires authentication)

response:

#### PUT /reading-lists/<list_id>

Update an existing reading list. (Requires authentication)

```json
{
  "name": "Updated Reading List Name",
  "book_ids": [1, 2, 4]
}
```

#### DELETE /reading-lists/<list_id>

DDelete a reading list. (Requires authentication)

### User Resource

#### GET /users

Retrieve a list of all users.

#### GET /users/<id>

Retrieve a single user by ID.

### Protected Routes

The following endpoints require authentication:

- `POST /books`
- `DELETE /books/<id>`
- `POST /reviews`
- `DELETE /reviews/<id>`
- `GET /reading-lists`

## Technologies Used

- Flask
- Flask-RESTful
- Flask-Bcrypt
- Flask-Migrate
- Flask-Login
- SQLAlchemy
- PostgreSQL

## Error Handling

- **401 Unauthorized:** Returned when accessing protected endpoints without authentication.
- **400 Bad Request:** Returned for missing or invalid request parameters.
- **404 Not Found:** Returned when a requested resource is not found.

## License

T## License
MIT License

Copyright (c) 2023 Ian Kabaka

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
For any issues or contributions, feel free to open a pull request or raise an issue!
