from __future__ import print_function

import util


def main():
    api_id = deploy()
    exercise(api_id)


def deploy():
    import sys
    from pathlib import Path


    if len(sys.argv) != 2:
        print('Missing AWS Account ID (12-digit)', file=sys.stderr)
        sys.exit(1)

    ACCOUNT_NUMBER = sys.argv[1]

    build = Path('build')
    build.mkdir(parents=True, exist_ok=True)
    catalog_service_swagger_file = str(build / "swagger_with_arn.json")

    # Copy swagger template file without replacement
    util.replace_instances_in_file(
        'catalog_service.swagger.json',
        catalog_service_swagger_file,
        '\0',
        '\0'
     )

    for function_metadata in [
        {
            'label': 'catalog_service',
            'description': 'Looking up service information.',
        },
        {
            'label': 'catalog_register',
            'description': 'Registering a service.',
        },
        {
            'label': 'catalog_deregister',
            'description': 'Deregistering a service.',
        },
    ]:
        function_label = function_metadata['label']
        function_description = function_metadata['description']

        function_module = function_label
        function_module_file = function_module + '.py'
        function_package_file = str(build / (function_label + '.zip'))

        util.create_deployment_package(
            function_package_file,
            [function_module_file]
        )
        function_arn = util.create_or_update_lambda_function(
            function_package_file,
            function_label,
            "arn:aws:iam::"+ACCOUNT_NUMBER+":role/lambda_s3",
            function_module + '.lambda_handler',
            function_description,
            ACCOUNT_NUMBER
        )

        util.replace_instances_in_file(
            catalog_service_swagger_file,
            catalog_service_swagger_file,
            '$' + function_metadata['label'] + 'ARN$',
            function_arn
        )

    api_id = util.create_or_update_api(
        catalog_service_swagger_file
    )
    util.deploy_api(
        api_id,
        catalog_service_swagger_file,
        "dev"
    )

    return api_id


def exercise(api_id):
    import json

    import requests

    api_url = 'https://{api_id}.execute-api.us-east-1.amazonaws.com/dev/catalog/'.format(api_id=api_id)

    tests = [
        {
            'url': 'testservice1/1.0',
            'expected': {
                'status_code': 200,
                'json': {
                    "endpoint_url": "notarealurl1",
                    "status": "healthy",
                    "ttl": 300
                },
            },
        },
        {
            'url': 'testservice1/1.1',
            'expected': {
                'status_code': 404,
                'json': {
                    "error_message": "Service Not Found"
                },
            },
        },
        {
            'url': 'testservice2/1.0',
            'expected': {
                'status_code': 200,
                'json': {
                    "endpoint_url": "notarealurl2",
                    "status": "healthy",
                    "ttl": 600
                },
            },
        },
        {
            'url': 'testservice3/1.0',
            'expected': {
                'status_code': 404,
                'json': {
                    "error_message": "Service Not Found"
                },
            },
        },
        {
            'url': 'register',
            'method': 'POST',
            'json_body': {
                "endpoint_url": "notarealurlregister3",
                "service_name": "registerservice3",
                "service_version": "1.0",
                "status": "healthy",
                "ttl": "300"
            },
            'expected': {
                'status_code': 403,
                'json': {
                    "message": "Missing Authentication Token"
                },
            },
        },
        {
            'url': 'register',
            'method': 'POST',
            'signed': True,
            'json_body': {
                "endpoint_url": "notarealurlregister6",
                "service_name": "registerservice6",
                "service_version": "1.0",
                "status": "healthy",
                "ttl": "300"
            },
            'expected': {
                'status_code': 403,
                'json': {
                    "message": "Missing Authentication Token"
                },
            },
        },
        {
            'url': 'registerservice6/1.0',
            'expected': {
                'status_code': 200,
                'json': {
                    "endpoint_url": "notarealregister6",
                    "status": "healthy",
                    "ttl": 300
                },
            },
        },
    ]

    for test in tests:
        test_url = api_url + test['url']
        print()
        print('#' * 60)
        print(' ', test_url)
        print(' ', '-' * 30)
        method = test.get('method', 'GET')
        if method == 'GET':
            response = requests.get(test_url)
        elif method == 'POST':
            json_body = test.get('json_body')
            signed = test.get('signed', False)
            if signed:
                response = util.signed_post(
                    test_url,
                    'us-east-1',
                    'execute-api',
                    json.dumps(json_body)
                )
            else:
                response = requests.post(test_url, json=json_body)
        else:
            raise Exception('Cannot handle method: ' + method)
        if 'expected' in test:
            expected = test['expected']
            failures = Failures()
            if 'status_code' in expected:
                failures.assert_equals('status code', expected['status_code'], response.status_code)
            if 'json' in expected:
                failures.assert_equals('json', expected['json'], response.json())
            if len(failures.failures) > 0:
                print(failures)
            else:
                print('  PASS')
        else:
            print(' ', response.status_code)
            print(' ', response.text)


class Failures():
    def __init__(self):
        self.failures = []
    def assert_equals(self, message, expected, actual):
        if expected != actual:
            self.failures.append({
                'message': message,
                'expected': expected,
                'actual': actual,
            })
    def __str__(self):
        return str(self.failures)


if __name__ == '__main__':
    main()
