from config import app, db
from models import User, Book, Review, ReadingList

# Ensure operations are within the application context
with app.app_context():
    db.drop_all()
    db.create_all()

    # Create users
    user1 = User(username="test_user_ian")
    user1.set_password("kabaka_ian")
    user2 = User(username="test_user_john")
    user2.set_password("doe_john")

    db.session.add_all([user1, user2])
    db.session.commit()

    # Create books
    book1 = Book(
        title="Rational Male",
        author="Rollo Tomassi",
        genre="non fiction",
        description="an interesting book",
        page_count=384,
        publication_year=2013,
        image_url="https://cdnattic.atticbooks.co.ke/img/N462777.jpg"
    )
    book2 = Book(
        title="48 laws of power",
        author="Robert Greene",
        genre="Non-Fiction",
        description="Another great book.",
        page_count=150,
        publication_year=2018,
        image_url="https://atticbooks.co.ke/books/the-48-laws-of-power"
    )
    db.session.add_all([book1, book2])
    db.session.commit()

    # Create reviews
    review1 = Review(user_id=user1.id, book_id=book1.id, review_text="Great book!", rating=5)
    review2 = Review(user_id=user2.id, book_id=book2.id, review_text="Not bad.", rating=3)

    db.session.add_all([review1, review2])
    db.session.commit()
    

    print("Database operation was a success!!")
