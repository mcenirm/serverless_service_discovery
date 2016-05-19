from __future__ import print_function


def main():
    import sys
    from pathlib import Path

    import util


    if len(sys.argv) != 2:
        print('Missing AWS Account ID (12-digit)', file=sys.stderr)
        sys.exit(1)

    ACCOUNT_NUMBER = sys.argv[1]

    build = Path('build')
    build.mkdir(parents=True, exist_ok=True)
    catalog_service_package_file = str(build / "catalog_service.zip")
    catalog_service_swagger_file = str(build / "swagger_with_arn.json")

    util.create_deployment_package(
        catalog_service_package_file,
        ["catalog_service.py"]
    )
    function_arn = util.create_or_update_lambda_function(
        catalog_service_package_file,
        "catalog_service",
        "arn:aws:iam::"+ACCOUNT_NUMBER+":role/lambda_s3",
        "catalog_service.lambda_handler",
        "Looking up service information.",
        ACCOUNT_NUMBER
    )

    if function_arn is None:
        return

    util.replace_instances_in_file(
        "catalog_service.swagger.json",
        catalog_service_swagger_file,
        "$catalog_serviceARN$",
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


if __name__ == '__main__':
    main()
