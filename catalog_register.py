import logging
import boto3

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(api_parameters, context):
    """Lambda hander for registering a service."""
    logger.info("lambda_handler - service_name: %s"
                " service_version: %s"
                % (api_parameters["service_name"],
                   api_parameters["service_version"]))

    table = boto3.resource('dynamodb',
                           region_name='us-east-1').Table('Services')

    table.put_item(
           Item={
                'name': api_parameters["service_name"],
                'version': api_parameters["service_version"],
                'endpoint_url': api_parameters["endpoint_url"],
                'ttl': int(api_parameters["ttl"]),
                'status': api_parameters["status"],
            }
        )
