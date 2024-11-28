from typing import Any, Dict
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Optional

from cachelib.file import FileSystemCache
from flask import Flask
from flask_appbuilder.security.manager import AUTH_DB, AUTH_OAUTH
from s3cache.s3cache import S3Cache
from superset.stats_logger import StatsdStatsLogger
from custom_sso_security_manager import CustomSsoSecurityManager
CUSTOM_SECURITY_MANAGER = CustomSsoSecurityManager

logger = logging.getLogger()


def get_env_variable(var_name: str, default: Optional[str] = None) -> str:
    """Get the environment variable or raise exception."""
    try:
        return os.environ[var_name]
    except KeyError:
        if default is not None:
            return default
        else:
            error_msg = "The environment variable {} was missing, abort...".format(
                var_name
            )
            raise EnvironmentError(error_msg)


def get_json_string_env_variable(var_name: str, default: Optional[str] = None) -> Dict[
    Any, Any]:
    """Retrieve json_string_env from environment and parse it as JSON."""
    try:
        string_json = get_env_variable(var_name, default)
        return json.loads(string_json)  # Parse JSON string to dict
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON for {var_name}: {e}")


STATSD_HOST = get_env_variable("STATSD_HOST", "")
STATSD_PORT = get_env_variable("STATSD_PORT", "")
TENANT = get_env_variable("TENANT", "ZOMATO")

if not (STATSD_HOST == "" or STATSD_PORT == ""):
    STATS_LOGGER = StatsdStatsLogger(host=STATSD_HOST,
                                     port=STATSD_PORT,
                                     prefix='superset' if TENANT == "ZOMATO" else "blinkit_superset")

DATABASE_DIALECT = get_env_variable("DATABASE_DIALECT")
DATABASE_USER = get_env_variable("DATABASE_USER")
DATABASE_PASSWORD = get_env_variable("DATABASE_PASSWORD")
DATABASE_HOST = get_env_variable("DATABASE_HOST")
DATABASE_PORT = get_env_variable("DATABASE_PORT")
DATABASE_DB = get_env_variable("DATABASE_DB")

# The SQLAlchemy connection string.
SQLALCHEMY_DATABASE_URI = "%s://%s:%s@%s:%s/%s" % (
    DATABASE_DIALECT,
    DATABASE_USER,
    DATABASE_PASSWORD,
    DATABASE_HOST,
    DATABASE_PORT,
    DATABASE_DB,
)

REDIS_HOST = get_env_variable("REDIS_HOST")
REDIS_PORT = get_env_variable("REDIS_PORT")
REDIS_CELERY_DB = get_env_variable("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = get_env_variable("REDIS_RESULTS_DB", "1")
REDIS_CACHE_DB = get_env_variable("REDIS_CACHE_DB", "2")
REDIS_ASYNC_DB = get_env_variable("REDIS_ASYNC_DB", "13")

# Default cache 24 hour (in secs)
DEFAULT_CACHE_DURATION = get_env_variable("DEFAULT_CACHE_DURATION", 60 * 60 * 24)

STORE_CACHE_KEYS_IN_METADATA_DB = True  # Required for invalidating cache
MAPBOX_API_KEY = get_env_variable("SUPERSET_MAPBOX_API", "")
CACHE_TYPE = get_env_variable("CACHE_TYPE", "RedisCache")

# Default cache for Superset objects
CACHE_CONFIG = {
    'CACHE_TYPE': CACHE_TYPE,
    'CACHE_DEFAULT_TIMEOUT': DEFAULT_CACHE_DURATION,
    'CACHE_KEY_PREFIX': 'superset:',
    'CACHE_REDIS_URL': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CACHE_DB}',
}
if CACHE_TYPE == "RedisClusterCache":
    REDIS_CLUSTER_HOST = get_env_variable("REDIS_CLUSTER_HOST")
    CACHE_CONFIG = {
        'CACHE_TYPE': CACHE_TYPE,
        'CACHE_DEFAULT_TIMEOUT': DEFAULT_CACHE_DURATION,
        'CACHE_KEY_PREFIX': 'superset:',
        'CACHE_REDIS_CLUSTER': f'{REDIS_CLUSTER_HOST}:{REDIS_PORT}',
        'CACHE_OPTIONS': {
            'cluster': True,  # Enable Redis Cluster mode
            'skip_full_coverage_check': True
        }
    }

# Cache for datasource metadata and query results
DATA_CACHE_CONFIG = {**CACHE_CONFIG, "CACHE_KEY_PREFIX": "superset:dc:"}

# Cache for dashboard filter state
FILTER_STATE_CACHE_CONFIG = {**CACHE_CONFIG, "CACHE_KEY_PREFIX": "superset:filter:"}

# Cache for explore form data state
EXPLORE_FORM_DATA_CACHE_CONFIG = {**CACHE_CONFIG,
                                  "CACHE_KEY_PREFIX": "superset:explore:"}


def init_thumbnail_cache(app: Flask, config, cache_args, cache_options) -> S3Cache:
    print("Importing thumbnail cache from custom config at superset_config.py")
    return S3Cache(SUPERSET_CACHE_S3_BUCKET, SUPERSET_CACHE_THUMBNAIL_S3_KEY_PREFIX)


# thumbnail cache config
SUPERSET_CACHE_S3_BUCKET = get_env_variable("SUPERSET_CACHE_THUMBNAIL_S3_BUCKET", "")
SUPERSET_CACHE_THUMBNAIL_S3_KEY_PREFIX = get_env_variable(
    "SUPERSET_CACHE_THUMBNAIL_S3_KEY_PREFIX", "")
SUPERSET_CACHE_RESULTS_BACKEND_S3_KEY_PREFIX = get_env_variable(
    "SUPERSET_CACHE_RESULTS_BACKEND_S3_KEY_PREFIX", "")

if SUPERSET_CACHE_S3_BUCKET == "" or SUPERSET_CACHE_THUMBNAIL_S3_KEY_PREFIX == "":
    THUMBNAIL_CACHE_CONFIG = {
        "CACHE_TYPE": "RedisCache",
        "CACHE_DEFAULT_TIMEOUT": 60 * 60 * 24 * 7,
        "CACHE_KEY_PREFIX": "superset:thumbnail:",
        "CACHE_NO_NULL_WARNING": True,
        "CACHE_REDIS_URL": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CACHE_DB}",
    }
else:
    THUMBNAIL_CACHE_CONFIG = {'CACHE_TYPE': 'superset_config.init_thumbnail_cache'}

if SUPERSET_CACHE_S3_BUCKET == "" or SUPERSET_CACHE_RESULTS_BACKEND_S3_KEY_PREFIX == "":
    RESULTS_BACKEND = FileSystemCache("/app/superset_home/sqllab", threshold=1000,
                                      default_timeout=1000)
else:
    RESULTS_BACKEND = S3Cache(SUPERSET_CACHE_S3_BUCKET,
                              SUPERSET_CACHE_RESULTS_BACKEND_S3_KEY_PREFIX)

SCREENSHOT_PLAYWRIGHT_DEFAULT_TIMEOUT = int(
    timedelta(seconds=int(get_env_variable("SCREENSHOT_PLAYWRIGHT_DEFAULT_TIMEOUT",
                                           150))).total_seconds() * 1000)


class CeleryConfig(object):
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    imports = ("superset.sql_lab", "superset.tasks", "superset.tasks.thumbnails")
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
    CELERYD_LOG_LEVEL = get_env_variable("SUPERSET_LOG_LEVEL", "INFO")
    worker_prefetch_multiplier = 1
    task_acks_late = False
    task_annotations = {
        'sql_lab.get_sql_results': {
            'rate_limit': '100/s',
        }
    }

    # Separate queues to control workers
    task_routes = {
        "cache_dashboard_thumbnail": {"queue": "celery-low-priority"},
        "cache_chart_thumbnail": {"queue": "celery-low-priority"},
        "cache-warmup": {"queue": "celery-priority"},
        "cache_dashboard_screenshot": {"queue": "celery-priority"}
    }


DATABASE_QUEUE_REDIRECTION = get_json_string_env_variable("DATABASE_QUEUE_REDIRECTION",
                                                          "{\"zomato-ads-superset-store\": \"ads-queue\"}")

CELERY_CONFIG = CeleryConfig
# TODO: Make feature flags env driven
FEATURE_FLAGS = {"ALERT_REPORTS": True,
                 "THUMBNAILS": True,
                 "THUMBNAILS_SQLA_LISTENERS": True,
                 "ENABLE_TEMPLATE_PROCESSING": True,
                 "DASHBOARD_RBAC": True,
                 "HORIZONTAL_FILTER_BAR": True,
                 "TAGGING_SYSTEM": True,
                 "LISTVIEWS_DEFAULT_CARD_VIEW": True,
                 "USE_ANALAGOUS_COLORS": True,
                 "DATAPANEL_CLOSED_BY_DEFAULT": True,
                 "DASHBOARD_VIRTUALIZATION": True,
                 "GLOBAL_ASYNC_QUERIES": True,
                 "DRILL_TO_DETAIL": True,
                 "ENABLE_JAVASCRIPT_CONTROLS": True
                 }

# Global Async
GLOBAL_ASYNC_QUERIES_REDIS_CONFIG = {
    "host": REDIS_HOST,
    "port": REDIS_PORT,
    "db": int(REDIS_ASYNC_DB),
    "ssl": False
}
GLOBAL_ASYNC_QUERIES_REDIS_STREAM_PREFIX = "superset-async-events-"
GLOBAL_ASYNC_QUERIES_REDIS_STREAM_LIMIT = int(
    get_env_variable("GLOBAL_ASYNC_QUERIES_REDIS_STREAM_LIMIT", "1000"))
GLOBAL_ASYNC_QUERIES_REDIS_STREAM_LIMIT_FIREHOSE = int(
    get_env_variable("GLOBAL_ASYNC_QUERIES_REDIS_STREAM_LIMIT_FIREHOSE", "1000000"))
GLOBAL_ASYNC_QUERIES_JWT_COOKIE_NAME = "superset-async-token"
GLOBAL_ASYNC_QUERIES_JWT_COOKIE_SECURE = \
    get_env_variable("GLOBAL_ASYNC_QUERIES_JWT_COOKIE_SECURE", "true").lower() == "true"
GLOBAL_ASYNC_QUERIES_JWT_COOKIE_DOMAIN = None
GLOBAL_ASYNC_QUERIES_JWT_SECRET = get_env_variable("GLOBAL_ASYNC_QUERIES_JWT_SECRET",
                                                   "8d4931910ce2b9d011ad5728444a14b0a40937890d33a6e427359e3bd7beaaf3")
GLOBAL_ASYNC_QUERIES_TRANSPORT = get_env_variable("GLOBAL_ASYNC_QUERIES_TRANSPORT",
                                                  "polling")
GLOBAL_ASYNC_QUERIES_WEBSOCKET_URL = get_env_variable(
    "GLOBAL_ASYNC_QUERIES_WEBSOCKET_URL", "ws://127.0.0.1:8080/")
GLOBAL_ASYNC_QUERIES_POLLING_DELAY = int(
    get_env_variable("GLOBAL_ASYNC_QUERIES_POLLING_DELAY", "5000"))  # 5 seconds

# TODO: Introduce schema level behaviour for "CACHE_IMPERSONATION": True, will fix RLS cache issue.
ALERT_REPORTS_NOTIFICATION_DRY_RUN = False
WEBDRIVER_BASEURL = get_env_variable("WEBDRIVER_BASE_URL", "http://superset:8088")
# The base URL for the email report hyperlinks.
WEBDRIVER_BASEURL_USER_FRIENDLY = get_env_variable("WEBDRIVER_BASEURL_USER_FRIENDLY",
                                                   "https://superset.zomans.com")
THUMBNAIL_SELENIUM_USER = "jumbo"
WEBDRIVER_WINDOW = {
    "dashboard": (1600, 2000),
    "slice": (3000, 1200),
    "pixel_density": 2,
}

SQLLAB_CTAS_NO_LIMIT = True
SQL_MAX_ROW = int(get_env_variable("SQL_MAX_ROW", "1000000"))

SECRET_KEY = get_env_variable("SUPERSET_SECRET_KEY", "\2\1thisismyscretkey\1\2\e\y\y\h")

SCREENSHOT_LOAD_WAIT = int(get_env_variable("SUPERSET_SCREENSHOT_LOAD_WAIT", "1200"))
SCREENSHOT_LOCATE_WAIT = int(get_env_variable("SUPERSET_SCREENSHOT_LOCATE_WAIT", "300"))

AUTH_USER_REGISTRATION = True
FAB_ADD_SECURITY_API = True  # Access Control API Endpoints
AUTH_USER_REGISTRATION_ROLE = "Public"  # Role assigned to new authorized and registered users
AUTH_API_LOGIN_ALLOW_MULTIPLE_PROVIDERS = True  # For API User
CSRF_ENABLED = True  # TODO: Have to enable Talisman
SUPERSET_WEBSERVER_TIMEOUT = int(get_env_variable("SUPERSET_WEBSERVER_TIMEOUT", "1500"))

LOG_LEVEL = get_env_variable("SUPERSET_LOG_LEVEL", "INFO")

if os.environ.get("Environment", "dev") == "dev":
    AUTH_TYPE = AUTH_DB
else:
    AUTH_TYPE = AUTH_OAUTH
    ENABLE_PROXY_FIX = True
    SUPERSET_GOOGLE_OAUTH_CLIENT_ID = get_env_variable(
        "SUPERSET_GOOGLE_OAUTH_CLIENT_ID")
    SUPERSET_GOOGLE_OAUTH_CLIENT_SECRET = get_env_variable(
        "SUPERSET_GOOGLE_OAUTH_CLIENT_SECRET")
    OAUTH_PROVIDERS = [
        {
            'name': 'google',
            # email whitelist
            'whitelist': ['zomato.com', "grofers.com", "blinkit.com"],
            'icon': 'fa-google',
            'token_key': 'access_token',
            'remote_app': {
                'api_base_url': 'https://www.googleapis.com/oauth2/v2/',
                'client_kwargs': {
                    'scope': 'email profile'
                },
                'request_token_url': None,
                'access_token_url': "https://oauth2.googleapis.com/token",
                'authorize_url': "https://accounts.google.com/o/oauth2/auth",
                # google api & services client id and secret
                'client_id': SUPERSET_GOOGLE_OAUTH_CLIENT_ID,
                'client_secret': SUPERSET_GOOGLE_OAUTH_CLIENT_SECRET
            }
        }
    ]

# Any role which doesn't have zomato as a prefix, won't show up RBAC list
filter_query = "zomato%" if TENANT == "ZOMATO" else "blinkit%"


def role_filter(query):
    from superset import security_manager
    from sqlalchemy import or_, and_
    from flask import g

    role_model = security_manager.role_model
    filters = [role_model.name.like(filter_query)]

    # Add filter for user's own roles
    user_roles = [role.id for role in security_manager.get_user_roles()]
    filters.append(role_model.id.in_(user_roles))

    return query.filter(and_(*filters))


EXTRA_RELATED_QUERY_FILTERS = {
    "role": role_filter,
}


def custom_db_connection_mutator(uri, params, username, security_manager, source):
    backend_name = uri.get_backend_name()
    user = security_manager.find_user(username=username)
    logger.info(f"Passed username: {username}, user: {user}")
    if user and user.email and backend_name in tuple(
        get_env_variable("DB_MUTATOR_WHITELIST", "presto,trino").split(",")):
        #     logger.info(f"Email: {user.email}")
        #     uri = uri.update_query_dict({'username': user.email})
        #     logger.info(uri)
        #     logger.info(f"Passed un: {username}")

        if get_env_variable("FORCE_PARAM_OVERRIDING", "false").lower() == "true":
            try:
                params['connect_args']['user'] = user.email
            except Exception as e:
                logger.info(f"Something went wrong while overriding {e}")

    if username in get_env_variable("PRIORITY_CLUSTER_EMAIL", "jumbo@zomato.com"):
        uri = uri.update_query_dict({'host': get_env_variable("PRIORITY_CLUSTER", "")})
        logger.info(uri)
    logger.info(source)
    if source == 1 and get_env_variable("FORCE_ROUTING_DASHBOARDS",
                                        "true").lower() == "true":
        uri = uri.update_query_dict({'host': get_env_variable("REPORTING_CLUSTER", "")})
        logger.info(uri)

    return uri, params


DB_CONNECTION_MUTATOR = custom_db_connection_mutator

SHOW_DOWNLOAD_TO_CSV = get_env_variable("SHOW_DOWNLOAD_TO_CSV",
                                        "false").lower() == "true"
SHOW_CLIPBOARD = get_env_variable("SHOW_CLIPBOARD", "false").lower() == "true"
SHOW_DOWNLOAD_DASHBOARD = get_env_variable("SHOW_DOWNLOAD_DASHBOARD",
                                           "false").lower() == "true"
SHOW_DOWNLOAD_EXPLORE = get_env_variable("SHOW_DOWNLOAD_EXPLORE",
                                         "false").lower() == "true"
SHOW_CHART_DOWNLOAD_TO_CSV = get_env_variable("SHOW_CHART_DOWNLOAD_TO_CSV",
                                              "false").lower() == "true"


def SQL_QUERY_MUTATOR(sql: str,
                      security_manager,
                      database,
                      **kwargs: Any) -> str:
    from flask import request, g
    from superset.utils.core import QuerySource, get_username
    import json
    source = None
    dash_id = None
    slice_id = None
    username = get_username()
    user = security_manager.find_user(username=username)

    dttm = datetime.now().isoformat()

    if not source and request and request.referrer:
        if "/superset/dashboard/" in request.referrer:
            source = QuerySource.DASHBOARD
            dash_id = json.loads(request.args.get('dashboard_id', '{}'))
            slice_id = json.loads(request.args.get('form_data', '{}')).get('slice_id')
        elif "/explore/" in request.referrer:
            source = QuerySource.CHART
            slice_id = json.loads(request.args.get('form_data', '{}')).get('slice_id')
        elif "/sqllab/" in request.referrer:
            source = QuerySource.SQL_LAB

    return f"-- {user.email} {source} {dash_id} {slice_id} {database} {dttm}\n{sql}"


TRACKING_URL_TRANSFORMER = lambda url: url.replace(
    ".internal.zomato.farm:8889", ".zomans.com")

try:
    import superset_config_docker
    from superset_config_docker import *  # noqa

    logger.info(
        f"Loaded your Docker configuration at " f"[{superset_config_docker.__file__}]"
    )
except ImportError:
    logger.info("Using default Docker config...")
