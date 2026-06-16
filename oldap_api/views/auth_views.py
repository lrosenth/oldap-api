"""
This script is part of a RESTful API for managing functionalities of oldaplib.
It uses Flask and oldaplib to perform CRUD operations on user, project data, permissionsets and more.
The API offers endpoints for creating, reading, updating, searching and deleting functions to interact with the database.

- POST /admin/auth/<userid>: Logs in a user and returns a token.
- DELETE /admin/auth/<userid>: Logs out a user.
- POST /admin/auth/password-reset/request: Requests a password reset link.
- POST /admin/auth/password-reset/confirm: Sets a new password with a reset token.

The implementation includes error handling and validation for most operations.
"""

import os
import smtplib
from datetime import datetime, timedelta, UTC
from email.message import EmailMessage
from urllib.parse import quote

import jwt
from flask import request, jsonify, Blueprint, current_app
from oldaplib.src.connection import Connection
from oldaplib.src.enums.userattr import UserAttr
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapError, OldapErrorValue, OldapErrorNoPermission, \
    OldapErrorUpdateFailed
from oldaplib.src.user import User
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetimestamp import Xsd_dateTimeStamp

auth_bp = Blueprint('auth', __name__, url_prefix='/admin')

PASSWORD_RESET_PURPOSE = "password-reset"
PASSWORD_RESET_EXPIRATION_SECONDS = 2 * 60 * 60


def _password_reset_secret() -> str:
    secret = os.getenv("OLDAP_PASSWORD_RESET_JWT_SECRET") or os.getenv("OLDAP_JWT_SECRET")
    if not secret:
        raise RuntimeError("OLDAP_PASSWORD_RESET_JWT_SECRET or OLDAP_JWT_SECRET must be configured.")
    return secret


def _password_reset_connection() -> Connection:
    userid = os.getenv("OLDAP_PASSWORD_RESET_ADMIN_USER")
    password = os.getenv("OLDAP_PASSWORD_RESET_ADMIN_PASSWORD")
    if not userid or not password:
        raise RuntimeError("OLDAP_PASSWORD_RESET_ADMIN_USER and OLDAP_PASSWORD_RESET_ADMIN_PASSWORD must be configured.")
    return Connection(userId=userid, credentials=password, context_name="DEFAULT")


def _password_reset_frontend_url() -> str:
    base_url = os.getenv("OLDAP_PASSWORD_RESET_FRONTEND_URL") or os.getenv("OLDAP_PUBLIC_APP_URL")
    if not base_url:
        raise RuntimeError("OLDAP_PASSWORD_RESET_FRONTEND_URL or OLDAP_PUBLIC_APP_URL must be configured.")
    return base_url.rstrip("/")


def _resolve_password_reset_user(con: Connection, data: dict) -> tuple[User | None, str | None]:
    user_id = (data.get("userId") or "").strip()
    email = (data.get("email") or "").strip()
    if bool(user_id) == bool(email):
        raise ValueError("Exactly one of userId or email must be supplied.")

    if user_id:
        try:
            return User.read(con=con, userId=user_id, ignore_cache=True), None
        except OldapErrorNotFound:
            return None, "not_unique"

    user_iris = User.search(con=con, email=email)
    if len(user_iris) != 1:
        return None, "not_unique"
    return User.read(con=con, userId=Iri(str(user_iris[0])), ignore_cache=True), None


def _build_password_reset_token(user: User, reset_requested_at: Xsd_dateTimeStamp) -> str:
    now = datetime.now(UTC)
    payload = {
        "purpose": PASSWORD_RESET_PURPOSE,
        "sub": str(user.userId),
        "userIri": str(user.userIri),
        "resetRequestedAt": str(reset_requested_at),
        "iat": now,
        "exp": now + timedelta(seconds=PASSWORD_RESET_EXPIRATION_SECONDS),
        "iss": "http://oldap.org",
    }
    return jwt.encode(payload, _password_reset_secret(), algorithm="HS256")


def _password_reset_link(token: str) -> str:
    return f"{_password_reset_frontend_url()}/password-reset?token={quote(token, safe='')}"


def _send_password_reset_email(user: User, link: str, identified_by_email: bool) -> None:
    subject = "Passwort zuruecksetzen"
    user_id_line = f"\nIhre User-ID lautet: {user.userId}\n" if identified_by_email else ""
    body = (
        f"Guten Tag {user.givenName} {user.familyName}\n\n"
        "Fuer Ihr OLDAP-/fasnacht.digital-Konto wurde ein Passwort-Reset angefordert."
        f"{user_id_line}\n"
        "Bitte verwenden Sie den folgenden Link, um ein neues Passwort zu setzen:\n\n"
        f"{link}\n\n"
        "Der Link ist 2 Stunden gueltig. Falls Sie den Reset nicht angefordert haben, koennen Sie diese E-Mail ignorieren.\n"
    )

    backend = os.getenv("OLDAP_PASSWORD_RESET_EMAIL_BACKEND", "console").lower()
    if backend == "console":
        current_app.logger.info("Password reset mail for %s:\n%s", user.email, body)
        return
    if backend != "smtp":
        raise RuntimeError(f'Unknown OLDAP_PASSWORD_RESET_EMAIL_BACKEND "{backend}".')

    sender = os.getenv("OLDAP_MAIL_FROM")
    host = os.getenv("OLDAP_MAIL_HOST")
    port = int(os.getenv("OLDAP_MAIL_PORT", "587"))
    username = os.getenv("OLDAP_MAIL_USERNAME")
    password = os.getenv("OLDAP_MAIL_PASSWORD")
    use_tls = os.getenv("OLDAP_MAIL_USE_TLS", "true").lower() not in {"0", "false", "no"}
    if not sender or not host:
        raise RuntimeError("OLDAP_MAIL_FROM and OLDAP_MAIL_HOST must be configured for SMTP password reset mail.")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = str(user.email)
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(host, port) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password or "")
        smtp.send_message(message)


@auth_bp.route('/auth/<userid>', methods=['POST'])
def login(userid):
    """
    Viewfunction to log into a user. A JSON is expected with the password. The userid is given via the URL parameter.
    The JSON that needs to be provided has the following form: json={'password': '*******'}
    :param userid: The userid of the loginaccount.
    :return: A JSON with the token that has the following form:
    json={'message': 'Login succeeded', 'token': token}
    """
    current_app.logger.info(f"/auth/{userid} with POST called")
    if request.is_json:
        data = request.get_json()
        if userid == "unknown":  # we have a "pesudo-login" for the anonymous unknown user
            current_app.logger.info(f"/auth/{userid}: Unknown pseudo-login requested")
            try:
                con = Connection(context_name="DEFAULT")
                current_app.logger.info(f"/auth/{userid}: Unknown pseudo-login succeeded")
                resp = jsonify({'message': 'Login succeeded', 'token': con.token}), 200
                return resp
            except OldapErrorNotFound as err:
                return jsonify({'message': str(err)}), 404
            except OldapError as error:
                return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        password = data.get('password')
        if password is None:
            return jsonify({"message": "Invalid content type, JSON required"}), 400
        try:
            con = Connection(userId=userid,
                             credentials=password,
                             context_name="DEFAULT")
            current_app.logger.info(f"Login for {userid} succeeded.")
            resp = jsonify({'message': 'Login succeeded', 'token': con.token}), 200
            return resp
        except OldapErrorNotFound as err:
            current_app.logger.info(f"Login for {userid} failed.")
            return jsonify({'message': str(err)}), 404
        except OldapError as error:
            current_app.logger.info(f"Login for {userid} failed.")
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@auth_bp.route('/auth/password-reset/request', methods=['POST'])
def request_password_reset():
    """
    Request a password reset link for exactly one user identifier.

    JSON body:
    - {"userId": "..."} or
    - {"email": "..."}

    If the identifier maps to exactly one user, the user's
    oldap:passwordResetRequestAt timestamp is replaced and a signed reset link
    is sent by mail. Ambiguous or missing identifiers are intentionally reported
    with the same message because the frontend cannot safely proceed.
    """
    current_app.logger.info("/auth/password-reset/request with POST called")
    if not request.is_json:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"message": "JSON object expected."}), 400
    unknown_json_field = set(data.keys()) - {"userId", "email"}
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to request a password reset."}), 400

    try:
        con = _password_reset_connection()
        user, resolution_error = _resolve_password_reset_user(con, data)
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except RuntimeError as error:
        current_app.logger.error("Password reset is not configured: %s", error)
        return jsonify({"message": str(error)}), 503
    except OldapError as error:
        current_app.logger.error("Password reset lookup failed: %s", error)
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    if resolution_error or user is None:
        return jsonify({"message": "Passwort reset unmöglich, kontaktieren sie info@fasnacht.digital"}), 409

    reset_requested_at = Xsd_dateTimeStamp(datetime.now(UTC))
    try:
        user.passwordResetRequestAt = reset_requested_at
        user.update()
        token = _build_password_reset_token(user, reset_requested_at)
        link = _password_reset_link(token)
        _send_password_reset_email(user, link, identified_by_email=bool((data.get("email") or "").strip()))
    except RuntimeError as error:
        current_app.logger.error("Password reset mail/token configuration failed: %s", error)
        return jsonify({"message": str(error)}), 503
    except OldapErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403
    except OldapErrorUpdateFailed as error:
        return jsonify({"message": str(error)}), 500
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapError as error:
        return jsonify({"message": str(error)}), 500
    except Exception as error:
        current_app.logger.error("Password reset mail failed: %s", error)
        return jsonify({"message": "Password reset mail could not be sent."}), 500

    return jsonify({"message": "Sie werden eine Email erhalten mit einem Link, um das Passwort neu zu setzen."}), 200


@auth_bp.route('/auth/password-reset/confirm', methods=['POST'])
def confirm_password_reset():
    """
    Set a new password using a password reset JWT.

    The token is valid only while its resetRequestedAt claim equals the current
    oldap:passwordResetRequestAt value stored on the user. Confirming the reset
    clears that value, which makes the token one-time-use.
    """
    current_app.logger.info("/auth/password-reset/confirm with POST called")
    if not request.is_json:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"message": "JSON object expected."}), 400
    unknown_json_field = set(data.keys()) - {"token", "password"}
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to confirm a password reset."}), 400

    token = data.get("token")
    password = data.get("password")
    if not token or not password:
        return jsonify({"message": "token and password are required."}), 400

    try:
        payload = jwt.decode(token, _password_reset_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Password reset token has expired."}), 400
    except jwt.InvalidTokenError:
        return jsonify({"message": "Password reset token is invalid."}), 400
    except RuntimeError as error:
        current_app.logger.error("Password reset is not configured: %s", error)
        return jsonify({"message": str(error)}), 503

    if payload.get("purpose") != PASSWORD_RESET_PURPOSE:
        return jsonify({"message": "Password reset token is invalid."}), 400
    user_id = payload.get("sub")
    reset_requested_at = payload.get("resetRequestedAt")
    if not user_id or not reset_requested_at:
        return jsonify({"message": "Password reset token is invalid."}), 400

    try:
        con = _password_reset_connection()
        user = User.read(con=con, userId=user_id, ignore_cache=True)
        if str(user.passwordResetRequestAt) != reset_requested_at:
            return jsonify({"message": "Password reset token is invalid or has already been used."}), 400
        user.credentials = password
        del user[UserAttr.PASSWORD_RESET_REQUEST_AT]
        user.update()
    except RuntimeError as error:
        current_app.logger.error("Password reset is not configured: %s", error)
        return jsonify({"message": str(error)}), 503
    except OldapErrorNotFound:
        return jsonify({"message": "Password reset token is invalid."}), 400
    except OldapErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403
    except OldapErrorUpdateFailed as error:
        return jsonify({"message": str(error)}), 500
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapError as error:
        return jsonify({"message": str(error)}), 500

    return jsonify({"message": "Password has been reset successfully."}), 200


@auth_bp.route('/auth/<userid>', methods=['DELETE'])
def logout(userid):
    """
    Viewfunction to log out of a user.
    :param userid: The userid of the logout account.
    :return:
    """
    # TODO: how to make a logout??? oldaplib does not yet have a solution! So we just return 200
    return '', 200
