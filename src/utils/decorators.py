from functools import wraps
from flask import session, redirect, url_for

"""
The provided code defines a custom @login_required 
decorator for a Flask application. Its purpose is to 
restrict access to certain view functions (routes) 
to only authenticated users, 
redirecting unauthorized users to the login page. 

"""

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'school_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
