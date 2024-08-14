"""
This script provides a RESTful API for managing users and projects and permissionsets.
It uses Flask and oldaplib to perform CRUD operations on user, project data and permissionsets.
The API offers endpoints for creating, reading, updating, searching and deleting users, projects nad permissionsets.

Available endpoints:
- POST /admin/auth/<userid>: Logs in a user and returns a token.
- DELETE /admin/auth/<userid>: Logs out a user.
- PUT /admin/user/<userid>: Creates a new user.
- GET /admin/user/<userid>: Reads the data of a user.
- DELETE /admin/user/<userid>: Deletes a user.
- POST /admin/user/<userid>: Updates the data of a user.
- PUT /admin/project/<projectid>: Creates a new project.
- GET /admin/project/<projectid>: Reads the data of a project.
- DELETE /admin/project/<projectid>: Deletes a project.
- POST /admin/project/<projectid>: Updates the data of a project.
- PUT /admin/permissionset/<permissionsetid>: Creates a new permission set.
- GET /admin/permissionset/<permissionlabel>: Reads the data of a permission set.
- DELETE /admin/permissionset/<permissionlabel>: Deletes a permission set.
- GET /admin/permissionset/search: Searches for permission sets.

The implementation includes error handling and validation for most operations.
"""
from flask import Blueprint

bp = Blueprint('admin', __name__, url_prefix='/admin')


# Function to log into a user


# Function to create a user


# Function to read the contents of a user


# Function to delete a user


