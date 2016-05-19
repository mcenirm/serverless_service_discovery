import logging
import boto3

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(api_parameters, context):
    """Lambda hander for service lookup."""
    logger.info("lambda_handler - service_name: %s"
                " service_version: %s"
                % (api_parameters["service_name"],
                   api_parameters["service_version"]))

    table = boto3.resource('dynamodb',region_name='us-east-1').Table('Services')

    dynamodb_response = table.get_item(
                    Key={
                        'name': str(api_parameters["service_name"]),
                        'version': str(api_parameters["service_version"])
                    }
                )

    if ('Item' in dynamodb_response):
        logger.info("found service with: %s" %
                     (dynamodb_response['Item']['endpoint_url'],))
        return {
            "endpoint_url": dynamodb_response['Item']['endpoint_url'],
            "ttl": dynamodb_response['Item']['ttl'],
            "status": dynamodb_response['Item']['status']
            }
    else:
        raise Exception('NotFound')
