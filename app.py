from flask import request,jsonify
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from config import app, db, api
from models import User, Book, Review, ReadingList, ReadingListBook


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
        try:
            data = request.get_json()
            new_user = User(username=data['username'])
            new_user.set_password(data['password'])
            db.session.add(new_user)
            db.session.commit()
            return jsonify(new_user.to_dict()), 201
        except IntegrityError:
            db.session.rollback()
            return {"error": "Username must be unique."}, 400
api.add_resource(UserInfo, '/users', '/users/<int:id>')