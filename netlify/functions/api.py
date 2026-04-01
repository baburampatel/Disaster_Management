import sys
import os

# Add project root to path so we can import app
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from app import app

def handler(event, context):
    """Netlify Function handler - converts Lambda event to WSGI."""
    from io import BytesIO
    from urllib.parse import urlencode, unquote

    path = event.get('path', '/')
    # Strip the function prefix if present
    if path.startswith('/.netlify/functions/api'):
        path = path[len('/.netlify/functions/api'):] or '/'

    http_method = event.get('httpMethod', 'GET')
    headers = event.get('headers') or {}
    body = event.get('body') or ''
    is_base64 = event.get('isBase64Encoded', False)

    if is_base64:
        import base64
        body = base64.b64decode(body)
    else:
        body = body.encode('utf-8')

    qs = event.get('queryStringParameters') or {}
    query_string = urlencode(qs)

    environ = {
        'REQUEST_METHOD': http_method,
        'SCRIPT_NAME': '',
        'PATH_INFO': unquote(path),
        'QUERY_STRING': query_string,
        'CONTENT_TYPE': headers.get('content-type', ''),
        'CONTENT_LENGTH': str(len(body)),
        'SERVER_NAME': headers.get('host', 'localhost'),
        'SERVER_PORT': '443',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https',
        'wsgi.input': BytesIO(body),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
    }

    # Add HTTP headers to environ
    for key, value in headers.items():
        wsgi_key = 'HTTP_' + key.upper().replace('-', '_')
        environ[wsgi_key] = value

    # Capture response
    response_started = []
    response_body_parts = []

    def start_response(status, response_headers, exc_info=None):
        response_started.append((status, response_headers))
        return response_body_parts.append

    result = app(environ, start_response)

    try:
        for chunk in result:
            response_body_parts.append(chunk)
    finally:
        if hasattr(result, 'close'):
            result.close()

    status_str, resp_headers = response_started[0]
    status_code = int(status_str.split(' ', 1)[0])

    headers_dict = {}
    for name, value in resp_headers:
        headers_dict[name] = value

    response_body = b''.join(response_body_parts)

    return {
        'statusCode': status_code,
        'headers': headers_dict,
        'body': response_body.decode('utf-8', errors='replace'),
        'isBase64Encoded': False,
    }
