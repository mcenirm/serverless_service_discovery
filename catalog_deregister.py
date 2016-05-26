import logging
import boto3

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(api_parameters, context):
    """Lambda hander for deregistering a service."""
    logger.info("lambda_handler - service_name: %s"
                " service_version: %s"
                % (api_parameters["service_name"],
                   api_parameters["service_version"]))

    table = boto3.resource('dynamodb',
                           region_name='us-east-1').Table('Services')

    table.delete_item(
            Key={
                'name': api_parameters["service_name"],
                'version': api_parameters["service_version"]
            }
        )
