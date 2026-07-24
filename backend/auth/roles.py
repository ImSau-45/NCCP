from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from backend.models import User


def roles_required(*allowed_roles):
    """
    Decorator to restrict access based on user roles.

    Example:
        @jwt_required()
        @roles_required("admin")

        @jwt_required()
        @roles_required("admin", "developer")
    """

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            # Get logged-in user's ID from JWT
            user_id = get_jwt_identity()

            # Fetch user from database
            user = User.query.get(user_id)

            # User doesn't exist
            if not user:
                return jsonify({"error": "User not found"}), 404

            # User role is not allowed
            if user.role not in allowed_roles:
                return jsonify(
                    {
                        "error": "Access denied",
                        "message": "You do not have permission to perform this action."
                    }
                ), 403

            # Everything is OK
            return func(*args, **kwargs)

        return wrapper

    return decorator