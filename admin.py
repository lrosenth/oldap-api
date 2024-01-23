from flask import Blueprint

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/login', methods=['GET', 'POST'])
def login_page():
    return "kappa"