from __future__ import print_function


def main():
    api_id = deploy()
    exercise(api_id)


def deploy():
    import sys
    from pathlib import Path

    import util


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
    import requests

    api_url = 'https://{api_id}.execute-api.us-east-1.amazonaws.com/dev/catalog/'.format(api_id=api_id)

    tests = [
        { 'url': 'testservice1/1.0' },
        { 'url': 'testservice1/1.1' },
        { 'url': 'testservice2/1.0' },
        { 'url': 'testservice3/1.0' },
    ]

    for test in tests:
        test_url = api_url + test['url']
        response = requests.get(test_url)
        print('#' * 60)
        print(' ', test_url)
        print(' ', '-' * 30)
        print(' ', response.status_code)
        print(' ', response.text)
        print()


if __name__ == '__main__':
    main()
