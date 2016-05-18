import logging

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
