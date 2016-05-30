from collections import OrderedDict
import base64
import datetime
import hashlib
import hmac
import json
import logging
import os
import urllib
import zipfile

from botocore.credentials import get_credentials
from botocore.session import get_session
import boto3
import botocore

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


def create_or_update_lambda_function(package_name, function_name, role,
                           handler, description, account_number):
    '''Create or update a Lambda function from zip-file.

    :param package_name: The name of the package. Full or relative path.
    :param function_name: The name of the Lambda function to create.
    :param role: The Role ARN to use when executing Lambda function
    :param handler: The handler to execute when the Lambda function is called.
    :param description: The description of the Lambda function.
    :param: account_number: The Account number of the API Gateway using this
                            function.
    :return: The ARN for the Lambda function.
    '''
    with open(package_name, "rb") as package_file:
        package_data = package_file.read()

    function_arn = None

    try:
        function_info = get_function(function_name)
        logger.debug('Function details: ' + repr(function_info))
        old_code_sha_256 = function_info['Configuration']['CodeSha256']
        new_code_sha_256 = calculate_code_sha_256(package_data)
        logger.debug('Old CodeSha256: ' + old_code_sha_256)
        logger.debug('New CodeSha256: ' + new_code_sha_256)

        # Don't update if code has not changed
        if old_code_sha_256 == new_code_sha_256:
            function_arn = function_info['Configuration']['FunctionArn']
        else:
            function_arn = update_lambda_function(
                package_data,
                function_name
            )
            logger.info('Updated function ' + function_arn)

    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            function_arn = create_lambda_function(
                package_data,
                function_name,
                role,
                handler,
                description,
                account_number
            )
            logger.info('Created function ' + function_arn)
        else:
            raise e

    return function_arn


def create_lambda_function(package_data, function_name, role,
                           handler, description, account_number):
    """Create a Lambda function from zip-file.

    :param package_data: The byte contents of the zip-file.
    :param function_name: The name of the Lambda function to create.
    :param role: The Role ARN to use when executing Lambda function
    :param handler: The handler to execute when the Lambda function is called.
    :param description: The description of the Lambda function.
    :param: account_number: The Account number of the API Gateway using this
                            function.
    :return: The ARN for the Lambda function.
    """
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


def update_lambda_function(package_data, function_name):
    """Update a Lambda function from zip-file.

    :param package_data: The byte contents of the zip-file.
    :param function_name: The name of the Lambda function.
    :return: The ARN for the Lambda function.
    """
    # connect to Lambda API
    client = boto3.client('lambda')

    # update the function code
    response = client.update_function_code(
        FunctionName=function_name,
        ZipFile=package_data,
        Publish=True
    )

    # get function configuration to get top level ARN
    return response['FunctionArn']


def calculate_code_sha_256(package_data):
    '''Calculate the SHA256 hash of the deployment package.

    :param package_data: The byte contents of the zip-file.
    :return: The hex SHA256 hash of the deployment package.
    '''
    hash = hashlib.sha256()
    hash.update(package_data)
    return str(base64.b64encode(hash.digest()), 'utf-8')


def get_function(function_name):
    """Return function details given the Function Name.

    :param function_name: The name of the Lambda function.
    :return: The response from the get_function API call.
    """
    client = boto3.client('lambda')

    return client.get_function(
        FunctionName=function_name
    )


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


def create_or_update_api(swagger_file_name):
    '''Create or update an API defined in Swagger.
    :param swagger_file_name: The name of the swagger file.
                              Full or relative path.
    :return: The id of the REST API.
    '''
    with open(swagger_file_name, 'r') as swagger_file:
        swagger_data = swagger_file.read()
    api_name = get_rest_api_name(swagger_data)
    apis = get_existing_rest_apis_by_name(api_name)
    if len(apis) == 0:
        return create_api(swagger_data)
    else:
        # TODO: Use a better criteria than "first one"
        return update_api(apis[0]['id'], swagger_data)


def create_api(swagger_data):
    '''Create an API defined in Swagger.

    :param swagger_data: The contents of the swagger file.
    :return: The id of the REST API.
    '''
    client = boto3.client('apigateway')
    response = client.import_rest_api(body=swagger_data)

    return response['id']


def update_api(rest_api_id, swagger_data):
    '''Update an API defined in Swagger.

    :param rest_api_id: The id of the REST API.
    :param swagger_data: The contents of the swagger file.
    :return: The id of the REST API.
    '''
    client = boto3.client('apigateway')
    response = client.put_rest_api(restApiId=rest_api_id,
                                   body=swagger_data)

    return response['id']


def get_rest_api_name(swagger_data):
    '''Get Rest API Name from data read from a Swagger file.

    :param swagger_data: The contents of the swagger file.
    :return: The name of the API defined in the Swagger file.
    '''
    api_def = json.loads(swagger_data)
    rest_api_name = api_def["info"]["title"]
    return rest_api_name


def get_existing_rest_apis_by_name(rest_api_name):
    '''Get REST APIs with matching API name.

    :param rest_api_name: The name of the API.
    :return: A possibly empty list of APIs with matching name.
    '''
    # get the API Gateway ID of the existing API
    client = boto3.client('apigateway')
    paginator = client.get_paginator('get_rest_apis')
    rest_apis = []
    for response in paginator.paginate():
        for item in response["items"]:
            if (rest_api_name == item["name"]):
                rest_apis.append(item)
    return rest_apis


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


def delete_rest_api_by_name(api_name):
    '''Delete API with the given name.

    :param api_name: The name of the API.
    '''
    client = boto3.client('apigateway')
    deleted = []
    paginator = client.get_paginator('get_rest_apis')
    for page in paginator.paginate():
        for item in page['items']:
            logger.debug('Rest API: ' + repr(item))
            if item['name'] == api_name:
                client.delete_rest_api(restApiId=item['id'])
                logger.info('Deleted rest API: ' + item['id'])
                deleted.append(item)


def delete_function(function_name):
    '''Delete Lambda function with the given name.

    :param function_name: The name of the function.
    '''
    client = boto3.client('lambda')
    client.delete_function(
        FunctionName=function_name
    )
    logger.info('Deleted Lambda function: ' + function_name)


def sign(key, msg):
    """Sign string with key."""
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def getSignatureKey(key, dateStamp, regionName, serviceName):
    """Create signature key."""
    kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, 'aws4_request')
    return kSigning


def create_canonical_querystring(params):
    """Create canonical query string."""
    ordered_params = OrderedDict(sorted(params.items(), key=lambda t: t[0]))
    canonical_querystring = ""
    for key, value in iter(ordered_params.items()):
        if len(canonical_querystring) > 0:
            canonical_querystring += '&'
        canonical_querystring += urllib.parse.quote(key)+"="+value[0]
    return canonical_querystring


def create_canonical_uri(parsed_url):
    return parsed_url.path


def create_canonical_headers(parsed_url, amzdate, credentials):
    canonical_headers = ("host:%sn"
                         "x-amz-date:%sn" %
                         (parsed_url.hostname, amzdate))
    if (not (credentials.token is None)):
        canonical_headers += ("x-amz-security-token:%sn") % (credentials.token,)
    return canonical_headers


def create_signed_headers(credentials):
    signed_headers = 'host;x-amz-date'
    if (not (credentials.token is None)):
        signed_headers += ';x-amz-security-token'
    return signed_headers


def create_canonical_request(method, canonical_uri, canonical_querystring, canonical_headers, signed_headers, payload_hash):
    canonical_request = ("%sn%sn%sn%sn%sn%s" %
                         (method,
                          urllib.parse.quote(canonical_uri),
                          canonical_querystring,
                          canonical_headers,
                          signed_headers,
                          payload_hash))
    return canonical_request


def sign_request(method, url, credentials, region, service, body='', amzdate=None):
    """Sign a HTTP request with AWS V4 signature."""
    ###############################
    # 1. Create a Canonical Request
    ###############################
    if amzdate is not None:
        datestamp = amzdate.split('T')[0]
    else:
        t = datetime.datetime.utcnow()
        amzdate = t.strftime('%Y%m%dT%H%M%SZ')
        # Date w/o time, used in credential scope
        datestamp = t.strftime('%Y%m%d')

    # Create the different parts of the request, with content sorted
    # in the prescribed order
    parsed_url = urllib.parse.urlparse(url)
    canonical_uri = create_canonical_uri(parsed_url)
    canonical_querystring = create_canonical_querystring(
                              urllib.parse.parse_qs(parsed_url.query))
    canonical_headers = create_canonical_headers(parsed_url, amzdate, credentials)
    signed_headers = create_signed_headers(credentials)

    payload_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    canonical_request = create_canonical_request(
        method,
        canonical_uri,
        canonical_querystring,
        canonical_headers,
        signed_headers,
        payload_hash
    )

    #####################################
    # 2. Create a String to Sign
    #####################################
    algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = ("%s/%s/%s/aws4_request" %
                        (datestamp,
                         region,
                         service))
    string_to_sign = ("%sn%sn%sn%s" %
                       (algorithm,
                        amzdate,
                        credential_scope,
                        hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()))
    #####################################
    # 3. Create a Signature
    #####################################
    signing_key = getSignatureKey(credentials.secret_key,
                                  datestamp, region, service)
    signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'),
                         hashlib.sha256).hexdigest()

    ######################################################
    # 4. Assemble request to it can be used for submission
    ######################################################
    authorization_header = ("%s Credential=%s/%s, "
                            "SignedHeaders=%s, "
                            "Signature=%s" %
                            (algorithm,
                             credentials.access_key,
                             credential_scope,
                             signed_headers,
                             signature))
    headers = {'x-amz-date': amzdate, 'Authorization': authorization_header}
    if (not (credentials.token is None)):
        headers['x-amz-security-token'] = credentials.token
    request_url = ("%s://%s%s" %
                   (parsed_url.scheme,parsed_url.netloc,canonical_uri))
    if (len(canonical_querystring) > 0):
        request_url += ("?%s" % (canonical_querystring,))

    return request_url, headers, body


def signed_post(url, region, service, data, **kwargs):
    """Signed post with AWS V4 Signature."""

    import requests

    credentials = get_credentials(get_session())

    request_url, headers, body = sign_request(
        'POST',
        url,
        credentials,
        region,
        service,
        body=data
    )

    logger.info('Signed request: ' + str((request_url, headers, body)))
    response = requests.post(request_url, headers=headers, data=body, **kwargs)
    if(not response.ok):
        logger.error("Error code: %i" % (response.status_code,))
    else:
        logger.info("Successfully registered the service.")
    return response
