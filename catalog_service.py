from __future__ import print_function

import json
import os
import logging
import zipfile
import boto3

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def zipdir(path, ziph):
    """Add directory to zip file.

    :param path: The top level path to traverse to discover files to add.
    :param ziph: A handle to a zip file to add files to.
    """
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))


def create_deployment_package(package_name, file_names):
    """Create a deployment package for Lambda.

    :param package_name: The name of the package. Full or relative path.
    :param file_names: Files or folders to add to the package.
    """
    ziph = zipfile.ZipFile(package_name, "w", zipfile.ZIP_DEFLATED)
    for file_name in file_names:
        if (os.path.isdir(file_name)):
            zipdir(file_name, ziph)
        else:
            ziph.write(file_name)
    ziph.close()


def create_lambda_function(package_name, function_name, role,
                           handler, description, account_number):
    """Create a Lambda function from zip-file.

    :param package_name: The name of the package. Full or relative path.
    :param function_name: The name of the Lambda function to create.
    :param role: The Role ARN to use when executing Lambda function
    :param handler: The handler to execute when the Lambda function is called.
    :param description: The description of the Lambda function.
    :param: account_number: The Account number of the API Gateway using this
                            function.
    :return: The ARN for the Lambda function.
    """
    with open(package_name, "rb") as package_file:
        package_data = package_file.read()

    client = boto3.client('lambda')

    response = client.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=role,
        Handler=handler,
        Code={'ZipFile': package_data},
        Description=description,
        Timeout=60,
        MemorySize=128,
        Publish=True
    )

    function_arn = response['FunctionArn']
    function_name = response['FunctionName']

    response = client.add_permission(
        FunctionName=response['FunctionArn'],
        StatementId=response['FunctionName']+"-invoke",
        Action="lambda:InvokeFunction",
        Principal="apigateway.amazonaws.com",
        SourceArn='arn:aws:execute-api:us-east-1:'+account_number+':*'
    )

    return function_arn


def replace_instances_in_file(filename_source, filename_target, old, new):
    """Replace string occurence in file.

    :param filename_source: The name of the file to read in.
    :param filename_target: The name of the file to write to.
    :param old: The string to find in the file.
    :param new: The string to replace any found occurrences with.
    """
    with open(filename_source, 'r') as f:
        newlines = []
        for line in f.readlines():
            newlines.append(line.replace(old, new))
    with open(filename_target, 'w') as f:
        for line in newlines:
            f.write(line)


def get_rest_api_name(swagger_file):
    """Get Rest API Name from Swagger file.

    :param swagger_file: The name of the swagger file. Full or relative path.
    :return: The name of the API defined in the Swagger file.
    """
    with open(swagger_file) as json_data:
        api_def = json.load(json_data)
        json_data.close()
        rest_api_name = api_def["info"]["title"]
        return rest_api_name


def create_api(swagger_file_name):
    """Create an API defined in Swagger.

    :param swagger_file_name: The name of the swagger file.
                              Full or relative path.
    :return: The id of the REST API.
    """
    with open(swagger_file_name, "r") as swagger_file:
        swagger_data = swagger_file.read()

    client = boto3.client('apigateway')
    response = client.import_rest_api(body=swagger_data)

    return response['id']


def deploy_api(api_id, swagger_file, stage):
    """Deploy API to the given stage.

    :param api_id: The id of the API.
    :param swagger_file: The name of the swagger file. Full or relative path.
    :param stage: The name of the stage to deploy to.
    :return: Tuple of Rest API ID, stage and Enpoint URL.
    """
    client = boto3.client('apigateway')

    with open(swagger_file) as json_data:
        api_def = json.load(json_data)
        json_data.close()
        logger.info("deploying: "+api_id+" to "+stage)
        client.create_deployment(restApiId=api_id,
                                 stageName=stage)

        logger.info("--------------------- END POINTS (START) ---------------")
        for path, path_object in iter(api_def["paths"].items()):
            logger.info("End Point: https://%s"
                        ".execute-api.us-east-1.amazonaws.com/"
                        "%s%s" % (api_id, stage, path))
        logger.info("--------------------- END POINTS (END) -----------------")

        enpoint_url = ("https://%s"
                       ".execute-api.us-east-1.amazonaws.com/"
                       "%s" % (api_id, stage))
        return api_id, stage, enpoint_url


def lambda_handler(api_parameters, context):
    """Lambda hander for service lookup."""
    logger.info("lambda_handler - service_name: %s"
                " service_version: %s"
                % (api_parameters["service_name"],
                   api_parameters["service_version"]))

    response = {
            "endpoint_url": "notarealurl",
            "ttl": "300",
            "status": "healthy"
         }

    return response


if __name__ == '__main__':
    import sys
    from pathlib import Path

    if len(sys.argv) != 2:
        print('Missing AWS Account ID (12-digit)', file=sys.stderr)
        sys.exit(1)

    ACCOUNT_NUMBER = sys.argv[1]

    build = Path('build')
    build.mkdir(parents=True, exist_ok=True)
    catalog_service_package_file = str(build / "catalog_service.zip")
    catalog_service_swagger_file = str(build / "swagger_with_arn.json")

    create_deployment_package(
        catalog_service_package_file,
        ["catalog_service.py"]
    )
    function_arn = create_lambda_function(
        catalog_service_package_file,
        "catalog_service",
        "arn:aws:iam::"+ACCOUNT_NUMBER+":role/lambda_s3",
        "catalog_service.lambda_handler",
        "Looking up service information.",
        ACCOUNT_NUMBER
    )
    replace_instances_in_file(
        "catalog_service.swagger.json",
        catalog_service_swagger_file,
        "$catalog_serviceARN$",
        function_arn
    )
    api_id = create_api(
        catalog_service_swagger_file
    )
    deploy_api(
        api_id,
        catalog_service_swagger_file,
        "dev"
    )
