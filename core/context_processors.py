from django.db import DatabaseError


def user_is_owner(user):
    if not user.is_authenticated:
        return False
    return user.is_staff or user.groups.filter(name="Owners").exists()


def site_context(request):
    """Values every template needs, including the chat widget."""
    try:
        is_owner = user_is_owner(request.user)
    except DatabaseError:
        # Keep error pages renderable when the database is the problem.
        is_owner = False
    return {"SITE_NAME": "Gather & Co.", "is_owner": is_owner}
