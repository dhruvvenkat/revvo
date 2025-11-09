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
        # Extract path from request - handle both Vercel request formats
        if hasattr(request, 'path'):
            path = request.path
        elif isinstance(request, dict) and 'path' in request:
            path = request['path']
        else:
            path = '/'
        
        # Remove /api prefix if present
        if path.startswith('/api'):
            path = path[4:] or '/'
        if not path.startswith('/'):
            path = '/' + path
        
        # Get HTTP method
        if hasattr(request, 'method'):
            method = request.method
        elif isinstance(request, dict) and 'method' in request:
            method = request['method']
        else:
            method = 'GET'
        
        # Get request body
        body = b''
        body_data = None
        if hasattr(request, 'body'):
            body_data = request.body
        elif isinstance(request, dict) and 'body' in request:
            body_data = request['body']
            
        if body_data:
            if isinstance(body_data, str):
                body = body_data.encode('utf-8')
            elif isinstance(body_data, bytes):
                body = body_data
            else:
                body = json.dumps(body_data).encode('utf-8')
        
        # Get query string
        query_string = ''
        if hasattr(request, 'query_string'):
            query_string = request.query_string or ''
        elif isinstance(request, dict) and 'query' in request:
            query = request['query']
            if isinstance(query, dict):
                query_string = '&'.join([f'{k}={v}' for k, v in query.items()])
            else:
                query_string = str(query)
        elif hasattr(request, 'query'):
            query = request.query
            if isinstance(query, dict):
                query_string = '&'.join([f'{k}={v}' for k, v in query.items()])
        
        # Get headers
        headers_dict = {}
        if hasattr(request, 'headers'):
            headers_dict = dict(request.headers)
        elif isinstance(request, dict) and 'headers' in request:
            headers_dict = request['headers']
        
        # Build WSGI environ
        environ = {
            'REQUEST_METHOD': method,
            'PATH_INFO': path,
            'QUERY_STRING': query_string,
            'CONTENT_TYPE': headers_dict.get('content-type', headers_dict.get('Content-Type', '')),
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
        for key, value in headers_dict.items():
            key_upper = key.upper().replace('-', '_')
            if key_upper not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                environ[f'HTTP_{key_upper}'] = value
        
        # Response data
        response_data = []
        status_code = [200]
        response_headers = []
        
        def start_response(status, response_headers_list):
            status_code[0] = int(status.split()[0])
            response_headers.extend(response_headers_list)
        
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
        final_headers = {name: value for name, value in response_headers}
        
        return {
            'statusCode': status_code[0],
            'headers': final_headers,
            'body': response_body
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e), 'traceback': traceback.format_exc()})
        }
