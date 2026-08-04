"""
This script is part of a RESTful API for managing functionalities of oldaplib.
It uses Flask and oldaplib to perform CRUD operations on user, project data, permissionsets and more.
The API offers endpoints for creating, reading, updating, searching and deleting functions to interact with the database.

- POST /admin/auth/<userid>: Logs in a user and returns an access token.
- POST /admin/auth/refresh: Exchanges the refresh cookie for an access token.
- POST /admin/auth/logout: Globally revokes refresh tokens and clears the cookie.
- DELETE /admin/auth/<userid>: Deprecated compatibility logout route.
- POST /mobile/v1/auth/login: Returns access and refresh tokens in JSON for native clients.
- POST /mobile/v1/auth/refresh: Exchanges a JSON refresh token for an access token.
- POST /admin/auth/password-reset/request: Requests a password reset link.
- POST /admin/auth/password-reset/confirm: Sets a new password with a reset token.

The implementation includes error handling and validation for most operations.
"""

import os
import smtplib
from datetime import datetime, timedelta, UTC
from email.message import EmailMessage
from html import escape
from urllib.parse import quote, urlsplit

import jwt
import requests
from flask import request, jsonify, Blueprint, current_app, make_response
from oldaplib.src.authentication import AuthorizationContext, TokenCodec
from oldaplib.src.connection import Connection
from oldaplib.src.enums.userattr import UserAttr
from oldaplib.src.helpers.oldaperror import (
    OldapErrorNotFound,
    OldapError,
    OldapErrorValue,
    OldapErrorNoPermission,
    OldapErrorUpdateFailed,
    OldapErrorConfiguration,
    OldapErrorToken,
)
from oldaplib.src.user import User
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetimestamp import Xsd_dateTimeStamp

auth_bp = Blueprint("auth", __name__, url_prefix="/admin")
mobile_auth_bp = Blueprint("mobile_auth", __name__, url_prefix="/mobile/v1/auth")

PASSWORD_RESET_PURPOSE = "password-reset"
PASSWORD_RESET_EXPIRATION_SECONDS = 2 * 60 * 60
PASSWORD_RESET_AUDIENCE_SUFFIX = "-password-reset"
REFRESH_COOKIE_PATH = "/admin/auth"
PASSWORD_MAX_BYTES = 72


def _token_codec() -> TokenCodec:
    """Return a codec loaded from the current process environment."""
    return TokenCodec.from_environment()


def _authentication_connection() -> Connection:
    """Create the privileged connection used for refresh and revocation."""
    userid = os.getenv("OLDAP_AUTH_ADMIN_USER")
    password = os.getenv("OLDAP_AUTH_ADMIN_PASSWORD")
    if not userid or not password:
        raise RuntimeError(
            "OLDAP_AUTH_ADMIN_USER and OLDAP_AUTH_ADMIN_PASSWORD must be configured."
        )
    try:
        return Connection(userId=userid, credentials=password, context_name="DEFAULT")
    except OldapError as error:
        raise RuntimeError("The authentication service connection failed.") from error


def _boolean_environment(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be true or false.")


def _refresh_cookie_settings() -> dict:
    same_site = os.getenv("OLDAP_REFRESH_COOKIE_SAMESITE", "Lax").strip().capitalize()
    if same_site not in {"Lax", "Strict", "None"}:
        raise RuntimeError(
            "OLDAP_REFRESH_COOKIE_SAMESITE must be Lax, Strict, or None."
        )
    secure = _boolean_environment("OLDAP_REFRESH_COOKIE_SECURE", True)
    if same_site == "None" and not secure:
        raise RuntimeError("SameSite=None requires OLDAP_REFRESH_COOKIE_SECURE=true.")
    return {
        "httponly": True,
        "secure": secure,
        "samesite": same_site,
        "path": REFRESH_COOKIE_PATH,
    }


def _refresh_cookie_name() -> str:
    return os.getenv("OLDAP_REFRESH_COOKIE_NAME", "oldap_refresh")


def _set_refresh_cookie(response, token: str, codec: TokenCodec) -> None:
    response.set_cookie(
        _refresh_cookie_name(),
        token,
        max_age=codec.settings.refresh_ttl_seconds,
        **_refresh_cookie_settings(),
    )


def _clear_refresh_cookie(response) -> None:
    response.delete_cookie(_refresh_cookie_name(), **_refresh_cookie_settings())


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return response


def _access_response(token: str, codec: TokenCodec, status: int = 200):
    response = jsonify(
        {
            "message": "Login succeeded",
            "accessToken": token,
            "tokenType": "Bearer",
            "expiresIn": codec.settings.access_ttl_seconds,
            "token": token,
        }
    )
    response.status_code = status
    return _no_store(response)


def _mobile_token_response(
    access_token: str,
    codec: TokenCodec,
    *,
    refresh_token: str | None = None,
):
    """Return native-client tokens without creating an authentication cookie."""
    payload = {
        "accessToken": access_token,
        "tokenType": "Bearer",
        "expiresIn": codec.settings.access_ttl_seconds,
    }
    if refresh_token is not None:
        payload["refreshToken"] = refresh_token
        payload["refreshTokenExpiresIn"] = codec.settings.refresh_ttl_seconds
    return _no_store(jsonify(payload))


def _mobile_auth_error(status: int, code: str, message: str):
    """Return a cache-safe error with a stable native-client code."""
    response = jsonify({"code": code, "message": message})
    response.status_code = status
    if status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    return _no_store(response)


def _mobile_auth_unavailable(operation: str, error: Exception):
    """Return the uniform mobile response for configuration or backend failures."""
    current_app.logger.error("Mobile %s is unavailable: %s", operation, error)
    return _mobile_auth_error(
        503,
        "authentication_unavailable",
        "Authentication is unavailable.",
    )


def _authentication_unavailable():
    """Return a cache-safe 503 for browser authentication backend outages."""
    response = jsonify({"message": "Authentication is unavailable."})
    response.status_code = 503
    return _no_store(response)


def _oldap_error_has_http_status(error: OldapError) -> bool:
    """Identify oldaplib transport errors that retain an HTTP status argument."""
    return (
        bool(error.args)
        and isinstance(error.args[0], int)
        and not isinstance(error.args[0], bool)
    )


def _refresh_failure():
    response = jsonify({"message": "Authentication failed."})
    response.status_code = 401
    try:
        _clear_refresh_cookie(response)
    except RuntimeError:
        pass
    return _no_store(response)


def _normalized_origin(value: str) -> str | None:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _origin_is_allowed() -> bool:
    """Accept absent/same-origin requests and exact configured origins."""
    origin = request.headers.get("Origin")
    if not origin:
        return True
    normalized = _normalized_origin(origin)
    if normalized is None:
        return False
    if normalized == _normalized_origin(request.host_url):
        return True
    configured = os.getenv("OLDAP_AUTH_ALLOWED_ORIGINS", "")
    allowed = {
        _normalized_origin(item.strip())
        for item in configured.split(",")
        if item.strip()
    }
    return normalized in allowed


def _password_reset_secret() -> str:
    secret = os.getenv("OLDAP_PASSWORD_RESET_JWT_SECRET")
    if not secret or len(secret.encode("utf-8")) < 32:
        raise RuntimeError(
            "OLDAP_PASSWORD_RESET_JWT_SECRET must contain at least 32 bytes."
        )
    other_secrets = (
        os.getenv("OLDAP_ACCESS_JWT_SECRET"),
        os.getenv("OLDAP_REFRESH_JWT_SECRET"),
        os.getenv("OLDAP_MEDIA_JWT_SECRET"),
    )
    if secret in {value for value in other_secrets if value}:
        raise RuntimeError(
            "OLDAP_PASSWORD_RESET_JWT_SECRET must differ from access, refresh, and media JWT secrets."
        )
    return secret


def _password_reset_connection() -> Connection:
    userid = os.getenv("OLDAP_PASSWORD_RESET_ADMIN_USER")
    password = os.getenv("OLDAP_PASSWORD_RESET_ADMIN_PASSWORD")
    if not userid or not password:
        raise RuntimeError(
            "OLDAP_PASSWORD_RESET_ADMIN_USER and OLDAP_PASSWORD_RESET_ADMIN_PASSWORD must be configured."
        )
    try:
        return Connection(userId=userid, credentials=password, context_name="DEFAULT")
    except OldapError as error:
        raise RuntimeError("The password-reset service connection failed.") from error


def _password_reset_frontend_url() -> str:
    base_url = os.getenv("OLDAP_PASSWORD_RESET_FRONTEND_URL") or os.getenv(
        "OLDAP_PUBLIC_APP_URL"
    )
    if not base_url:
        raise RuntimeError(
            "OLDAP_PASSWORD_RESET_FRONTEND_URL or OLDAP_PUBLIC_APP_URL must be configured."
        )
    return base_url.rstrip("/")


def _resolve_password_reset_user(
    con: Connection, data: dict
) -> tuple[User | None, str | None]:
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


def _build_password_reset_token(
    user: User, reset_requested_at: Xsd_dateTimeStamp
) -> str:
    now = datetime.now(UTC)
    codec = _token_codec()
    payload = {
        "typ": PASSWORD_RESET_PURPOSE,
        "sub": str(user.userId),
        "userIri": str(user.userIri),
        "resetRequestedAt": str(reset_requested_at),
        "iat": now,
        "exp": now + timedelta(seconds=PASSWORD_RESET_EXPIRATION_SECONDS),
        "iss": codec.settings.issuer,
        "aud": f"{codec.settings.audience}{PASSWORD_RESET_AUDIENCE_SUFFIX}",
    }
    return jwt.encode(payload, _password_reset_secret(), algorithm="HS256")


def _password_reset_link(token: str) -> str:
    """Build a reset URL that remains clickable in plain-text mail clients.

    JWT segment separators are valid URL characters, but some mail clients stop
    automatic link detection at the first dot. Percent-encoding the separators
    preserves the token after query parsing and keeps the complete URL linked.

    Args:
        token: Three-segment password-reset JWT.

    Returns:
        Absolute frontend reset URL with an encoded token query parameter.
    """
    encoded_token = quote(token, safe="").replace(".", "%2E")
    return f"{_password_reset_frontend_url()}/password-reset?token={encoded_token}"


def _password_reset_email_content(
    user: User, link: str, identified_by_email: bool
) -> tuple[str, str]:
    """Create UTF-8 plain-text and HTML password-reset mail bodies.

    Args:
        user: Reset recipient whose display name and optional User-ID are shown.
        link: Complete, percent-encoded reset URL.
        identified_by_email: Whether to include the resolved OLDAP User-ID.

    Returns:
        Plain-text and HTML representations of the same reset message.
    """
    user_id_line = (
        f"\nIhre User-ID lautet: {user.userId}\n" if identified_by_email else ""
    )
    plain_body = (
        f"Guten Tag {user.givenName} {user.familyName}\n\n"
        "Für Ihr OLDAP-/fasnacht.digital-Konto wurde ein Passwort-Reset angefordert."
        f"{user_id_line}\n"
        "Bitte verwenden Sie den folgenden Link, um ein neues Passwort zu setzen:\n\n"
        f"{link}\n\n"
        "Der Link ist 2 Stunden gültig. Falls Sie den Reset nicht angefordert haben, "
        "können Sie diese E-Mail ignorieren.\n"
    )

    display_name = escape(f"{user.givenName} {user.familyName}")
    escaped_link = escape(link, quote=True)
    html_user_id = (
        f"<p>Ihre User-ID lautet: <strong>{escape(str(user.userId))}</strong></p>"
        if identified_by_email
        else ""
    )
    html_body = f"""\
<!doctype html>
<html lang="de">
  <body style="font-family: Arial, sans-serif; color: #172033; line-height: 1.5;">
    <p>Guten Tag {display_name}</p>
    <p>Für Ihr OLDAP-/fasnacht.digital-Konto wurde ein Passwort-Reset angefordert.</p>
    {html_user_id}
    <p>Bitte verwenden Sie den folgenden Link, um ein neues Passwort zu setzen:</p>
    <p style="margin: 24px 0;">
      <a href="{escaped_link}" style="background: #1f5eff; color: #ffffff; padding: 12px 18px; text-decoration: none; border-radius: 6px; display: inline-block;">Passwort neu setzen</a>
    </p>
    <p style="font-size: 13px; color: #526079;">Falls der Button nicht funktioniert, kopieren Sie diesen vollständigen Link in den Browser:</p>
    <p style="font-size: 13px; overflow-wrap: anywhere;"><a href="{escaped_link}">{escaped_link}</a></p>
    <p>Der Link ist 2 Stunden gültig. Falls Sie den Reset nicht angefordert haben, können Sie diese E-Mail ignorieren.</p>
  </body>
</html>
"""
    return plain_body, html_body


def _send_password_reset_email(
    user: User, link: str, identified_by_email: bool
) -> None:
    """Deliver a multipart password-reset message through console or SMTP."""
    subject = "Passwort zurücksetzen"
    plain_body, html_body = _password_reset_email_content(
        user, link, identified_by_email
    )

    backend = os.getenv("OLDAP_PASSWORD_RESET_EMAIL_BACKEND", "console").lower()
    if backend == "console":
        current_app.logger.info(
            "Password reset mail for %s:\n%s", user.email, plain_body
        )
        return
    if backend != "smtp":
        raise RuntimeError(f'Unknown OLDAP_PASSWORD_RESET_EMAIL_BACKEND "{backend}".')

    sender = os.getenv("OLDAP_MAIL_FROM")
    host = os.getenv("OLDAP_MAIL_HOST")
    port = int(os.getenv("OLDAP_MAIL_PORT", "587"))
    username = os.getenv("OLDAP_MAIL_USERNAME")
    password = os.getenv("OLDAP_MAIL_PASSWORD")
    use_tls = os.getenv("OLDAP_MAIL_USE_TLS", "true").lower() not in {
        "0",
        "false",
        "no",
    }
    if not sender or not host:
        raise RuntimeError(
            "OLDAP_MAIL_FROM and OLDAP_MAIL_HOST must be configured for SMTP password reset mail."
        )

    message = EmailMessage()
    message["From"] = sender
    message["To"] = str(user.email)
    message["Subject"] = subject
    message.set_content(plain_body)
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(host, port) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password or "")
        smtp.send_message(message)


@auth_bp.route("/auth/<userid>", methods=["POST"])
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
        if not isinstance(data, dict):
            return jsonify({"message": "JSON object expected."}), 400
        # The anonymous pseudo-user can always obtain a short access token but
        # never receives a refresh session.
        if userid == "unknown":
            current_app.logger.info(f"/auth/{userid}: Unknown pseudo-login requested")
            try:
                con = Connection(context_name="DEFAULT")
                current_app.logger.info(
                    f"/auth/{userid}: Unknown pseudo-login succeeded"
                )
                codec = con.token_codec
                response = _access_response(con.token, codec)
                _clear_refresh_cookie(response)
                return response
            except (OldapErrorConfiguration, RuntimeError) as error:
                current_app.logger.error("Authentication is not configured: %s", error)
                return jsonify({"message": str(error)}), 503
            except requests.RequestException as error:
                current_app.logger.error(
                    "Anonymous authentication backend failed: %s", error
                )
                return _authentication_unavailable()
            except OldapErrorNotFound as err:
                return jsonify({"message": str(err)}), 404
            except OldapError as error:
                return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        password = data.get("password")
        if password is None:
            return jsonify({"message": "Invalid content type, JSON required"}), 400
        try:
            con = Connection(
                userId=userid, credentials=password, context_name="DEFAULT"
            )
            current_app.logger.info(f"Login for {userid} succeeded.")
            codec = con.token_codec
            refresh_token = codec.issue_refresh_token(con.userid, con.auth_version)
            response = _access_response(con.token, codec)
            _set_refresh_cookie(response, refresh_token, codec)
            return response
        except (OldapErrorConfiguration, RuntimeError) as error:
            current_app.logger.error("Authentication is not configured: %s", error)
            return jsonify({"message": str(error)}), 503
        except requests.RequestException as error:
            current_app.logger.error("Authentication backend failed: %s", error)
            return _authentication_unavailable()
        except OldapErrorNotFound as err:
            current_app.logger.info(f"Login for {userid} failed.")
            return jsonify({"message": str(err)}), 404
        except OldapError as error:
            current_app.logger.info(f"Login for {userid} failed.")
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
    else:
        return (
            jsonify(
                {"message": f"JSON expected. Instead received {request.content_type}"}
            ),
            400,
        )


@mobile_auth_bp.route("/login", methods=["POST"])
def mobile_login():
    """Issue existing Variant D tokens in JSON for native secure storage."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _mobile_auth_error(400, "validation_failed", "JSON object expected.")
    if set(data) != {"userId", "password"}:
        return _mobile_auth_error(
            400,
            "validation_failed",
            "Exactly userId and password are required.",
        )

    user_id = data.get("userId")
    password = data.get("password")
    if not isinstance(user_id, str) or not user_id or not isinstance(password, str):
        return _mobile_auth_error(
            400,
            "validation_failed",
            "userId and password are required.",
        )
    try:
        user_id.encode("utf-8")
        password_bytes = password.encode("utf-8")
    except UnicodeEncodeError:
        return _mobile_auth_error(
            400,
            "validation_failed",
            "userId and password must be valid UTF-8 text.",
        )
    if len(password_bytes) > PASSWORD_MAX_BYTES:
        return _mobile_auth_error(
            400,
            "validation_failed",
            "password must not exceed 72 UTF-8 bytes.",
        )
    if user_id == "unknown":
        return _mobile_auth_error(401, "invalid_credentials", "Authentication failed.")

    try:
        con = Connection(userId=user_id, credentials=password, context_name="DEFAULT")
    except (
        OldapErrorConfiguration,
        RuntimeError,
        requests.RequestException,
        TypeError,
        ValueError,
    ) as error:
        return _mobile_auth_unavailable("authentication", error)
    except OldapError as error:
        if _oldap_error_has_http_status(error):
            return _mobile_auth_unavailable("authentication", error)
        return _mobile_auth_error(401, "invalid_credentials", "Authentication failed.")

    try:
        codec = con.token_codec
        refresh_token = codec.issue_refresh_token(con.userid, con.auth_version)
        return _mobile_token_response(
            con.token,
            codec,
            refresh_token=refresh_token,
        )
    except (OldapErrorConfiguration, RuntimeError, OldapError) as error:
        return _mobile_auth_unavailable("authentication", error)


@mobile_auth_bp.route("/refresh", methods=["POST"])
def mobile_refresh_access_token():
    """Issue a new access token from a stateless refresh JWT in JSON."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _mobile_auth_error(400, "validation_failed", "JSON object expected.")
    if set(data) != {"refreshToken"}:
        return _mobile_auth_error(
            400,
            "validation_failed",
            "Exactly refreshToken is required.",
        )
    token = data.get("refreshToken")
    if not isinstance(token, str) or not token:
        return _mobile_auth_error(
            400,
            "validation_failed",
            "refreshToken is required.",
        )

    try:
        codec = _token_codec()
        claims = codec.decode_refresh_token(token)
    except (OldapErrorConfiguration, RuntimeError) as error:
        return _mobile_auth_unavailable("refresh", error)
    except OldapError:
        return _mobile_auth_error(
            401,
            "refresh_token_invalid",
            "Authentication failed.",
        )

    try:
        con = _authentication_connection()
        user = User.read(con=con, userId=claims.userId, ignore_cache=True)
        if not user.isActive or int(user.authVersion) != claims.authVersion:
            return _mobile_auth_error(
                401,
                "refresh_token_invalid",
                "Authentication failed.",
            )
        context = AuthorizationContext.from_user(user)
        return _mobile_token_response(codec.issue_access_token(context), codec)
    except OldapErrorNotFound:
        return _mobile_auth_error(
            401,
            "refresh_token_invalid",
            "Authentication failed.",
        )
    except (
        OldapErrorConfiguration,
        RuntimeError,
        requests.RequestException,
        OldapError,
        TypeError,
        ValueError,
    ) as error:
        return _mobile_auth_unavailable("refresh", error)


@auth_bp.route("/auth/password-reset/request", methods=["POST"])
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
        return (
            jsonify(
                {"message": f"JSON expected. Instead received {request.content_type}"}
            ),
            400,
        )

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"message": "JSON object expected."}), 400
    unknown_json_field = set(data.keys()) - {"userId", "email"}
    if unknown_json_field:
        return (
            jsonify(
                {
                    "message": f"The Field/s {unknown_json_field} is/are not used to request a password reset."
                }
            ),
            400,
        )

    try:
        con = _password_reset_connection()
        user, resolution_error = _resolve_password_reset_user(con, data)
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except (RuntimeError, OldapErrorConfiguration) as error:
        current_app.logger.error("Password reset is not configured: %s", error)
        return jsonify({"message": str(error)}), 503
    except OldapError as error:
        current_app.logger.error("Password reset lookup failed: %s", error)
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    if resolution_error or user is None:
        return (
            jsonify(
                {
                    "message": "Passwort reset unmöglich, kontaktieren sie info@fasnacht.digital"
                }
            ),
            409,
        )

    reset_requested_at = Xsd_dateTimeStamp(datetime.now(UTC))
    try:
        user.passwordResetRequestAt = reset_requested_at
        user.update()
        token = _build_password_reset_token(user, reset_requested_at)
        link = _password_reset_link(token)
        _send_password_reset_email(
            user, link, identified_by_email=bool((data.get("email") or "").strip())
        )
    except (RuntimeError, OldapErrorConfiguration) as error:
        current_app.logger.error(
            "Password reset mail/token configuration failed: %s", error
        )
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

    return (
        jsonify(
            {
                "message": "Sie werden eine Email erhalten mit einem Link, um das Passwort neu zu setzen."
            }
        ),
        200,
    )


@auth_bp.route("/auth/password-reset/confirm", methods=["POST"])
def confirm_password_reset():
    """
    Set a new password using a password reset JWT.

    The token is valid only while its resetRequestedAt claim equals the current
    oldap:passwordResetRequestAt value stored on the user. Confirming the reset
    clears that value, which makes the token one-time-use.
    """
    current_app.logger.info("/auth/password-reset/confirm with POST called")
    if not request.is_json:
        return (
            jsonify(
                {"message": f"JSON expected. Instead received {request.content_type}"}
            ),
            400,
        )

    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"message": "JSON object expected."}), 400
    unknown_json_field = set(data.keys()) - {"token", "password"}
    if unknown_json_field:
        return (
            jsonify(
                {
                    "message": f"The Field/s {unknown_json_field} is/are not used to confirm a password reset."
                }
            ),
            400,
        )

    token = data.get("token")
    password = data.get("password")
    if not token or not password:
        return jsonify({"message": "token and password are required."}), 400

    try:
        codec = _token_codec()
        payload = jwt.decode(
            token,
            _password_reset_secret(),
            algorithms=["HS256"],
            issuer=codec.settings.issuer,
            audience=f"{codec.settings.audience}{PASSWORD_RESET_AUDIENCE_SUFFIX}",
            options={
                "require": [
                    "typ",
                    "sub",
                    "iss",
                    "aud",
                    "iat",
                    "exp",
                    "resetRequestedAt",
                ]
            },
        )
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Password reset token has expired."}), 400
    except jwt.InvalidTokenError:
        return jsonify({"message": "Password reset token is invalid."}), 400
    except (RuntimeError, OldapErrorConfiguration) as error:
        current_app.logger.error("Password reset is not configured: %s", error)
        return jsonify({"message": str(error)}), 503

    if payload.get("typ") != PASSWORD_RESET_PURPOSE:
        return jsonify({"message": "Password reset token is invalid."}), 400
    user_id = payload.get("sub")
    reset_requested_at = payload.get("resetRequestedAt")
    if not user_id or not reset_requested_at:
        return jsonify({"message": "Password reset token is invalid."}), 400

    try:
        con = _password_reset_connection()
        user = User.read(con=con, userId=user_id, ignore_cache=True)
        if str(user.passwordResetRequestAt) != reset_requested_at:
            return (
                jsonify(
                    {
                        "message": "Password reset token is invalid or has already been used."
                    }
                ),
                400,
            )
        user.credentials = password
        del user[UserAttr.PASSWORD_RESET_REQUEST_AT]
        user.update()
    except (RuntimeError, OldapErrorConfiguration) as error:
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


@auth_bp.route("/auth/refresh", methods=["POST"])
def refresh_access_token():
    """Issue an access token from a valid, non-revoked refresh cookie."""
    if not _origin_is_allowed():
        response = jsonify({"message": "Origin is not allowed."})
        response.status_code = 403
        return _no_store(response)

    token = request.cookies.get(_refresh_cookie_name())
    if not token:
        return _refresh_failure()

    try:
        codec = _token_codec()
        claims = codec.decode_refresh_token(token)
        con = _authentication_connection()
        user = User.read(con=con, userId=claims.userId, ignore_cache=True)
        if not user.isActive or int(user.authVersion) != claims.authVersion:
            return _refresh_failure()
        context = AuthorizationContext.from_user(user)
        return _access_response(codec.issue_access_token(context), codec)
    except (OldapErrorConfiguration, RuntimeError) as error:
        current_app.logger.error("Authentication is not configured: %s", error)
        response = jsonify({"message": str(error)})
        response.status_code = 503
        return _no_store(response)
    except requests.RequestException as error:
        current_app.logger.error("Authentication refresh backend failed: %s", error)
        return _authentication_unavailable()
    except OldapError:
        return _refresh_failure()


def _logout_response(status: int):
    response = make_response("", status)
    _clear_refresh_cookie(response)
    return _no_store(response)


def _perform_logout(status: int = 204):
    """Globally revoke a valid current refresh token and always clear it."""
    if not _origin_is_allowed():
        response = jsonify({"message": "Origin is not allowed."})
        response.status_code = 403
        return _no_store(response)

    token = request.cookies.get(_refresh_cookie_name())
    if not token:
        return _logout_response(status)

    try:
        codec = _token_codec()
        claims = codec.decode_refresh_token(token)
        con = _authentication_connection()
        user = User.read(con=con, userId=claims.userId, ignore_cache=True)
        if int(user.authVersion) == claims.authVersion:
            user.revoke_authentication()
    except (OldapErrorToken, OldapErrorNotFound, OldapErrorUpdateFailed):
        pass
    except (OldapErrorConfiguration, RuntimeError, OldapError) as error:
        current_app.logger.error("Logout revocation failed: %s", error)
        response = jsonify({"message": "Logout could not be completed."})
        response.status_code = 503
        _clear_refresh_cookie(response)
        return _no_store(response)
    except requests.RequestException as error:
        current_app.logger.error("Logout revocation backend failed: %s", error)
        response = _authentication_unavailable()
        _clear_refresh_cookie(response)
        return response
    return _logout_response(status)


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    """Preferred global logout endpoint using refresh-token identity."""
    return _perform_logout()


@auth_bp.route("/auth/<userid>", methods=["DELETE"])
def legacy_logout(userid):
    """Deprecated logout route; the path identity is intentionally ignored."""
    return _perform_logout(status=200)
