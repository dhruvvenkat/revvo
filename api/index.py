import sys
import os
import json
from io import BytesIO

# Add the server directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

from app import create_app

# Create Flask app instance
app = create_app()

def handler(request):
    """
    Vercel serverless function handler for Flask app
    """
    try:
        # Extract path from request
        path = request.path
        if path.startswith('/api'):
            path = path[4:] or '/'
        if not path.startswith('/'):
            path = '/' + path
        
        # Get request body
        body = b''
        if hasattr(request, 'body'):
            if isinstance(request.body, str):
                body = request.body.encode('utf-8')
            elif request.body:
                body = request.body
        elif hasattr(request, 'json'):
            body = json.dumps(request.json).encode('utf-8')
        
        # Get query string
        query_string = ''
        if hasattr(request, 'query_string'):
            query_string = request.query_string or ''
        elif hasattr(request, 'query'):
            query_string = '&'.join([f'{k}={v}' for k, v in request.query.items()])
        
        # Build WSGI environ
        environ = {
            'REQUEST_METHOD': request.method if hasattr(request, 'method') else 'GET',
            'PATH_INFO': path,
            'QUERY_STRING': query_string,
            'CONTENT_TYPE': request.headers.get('content-type', '') if hasattr(request, 'headers') else '',
            'CONTENT_LENGTH': str(len(body)),
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '443',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https',
            'wsgi.input': BytesIO(body),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': True,
            'wsgi.run_once': False,
        }
        
        # Add HTTP headers
        if hasattr(request, 'headers'):
            for key, value in request.headers.items():
                key = key.upper().replace('-', '_')
                if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                    environ[f'HTTP_{key}'] = value
        
        # Response data
        response_data = []
        status_code = [200]
        headers = []
        
        def start_response(status, response_headers):
            status_code[0] = int(status.split()[0])
            headers.extend(response_headers)
        
        # Call Flask app
        app_iter = app(environ, start_response)
        
        try:
            for data in app_iter:
                response_data.append(data)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
        
        # Build response
        response_body = b''.join(response_data)
        if isinstance(response_body, bytes):
            try:
                response_body = response_body.decode('utf-8')
            except:
                response_body = str(response_body)
        
        # Convert headers to dict
        headers_dict = {name: value for name, value in headers}
        
        return {
            'statusCode': status_code[0],
            'headers': headers_dict,
            'body': response_body
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
