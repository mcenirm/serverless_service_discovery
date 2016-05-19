# Serverless Service Discovery

Working through the example of Serverless Service Discovery
presented by the
[AWS Developer Blog](https://aws.amazon.com/blogs/developer/).

* [Part 1: Get Started](https://aws.amazon.com/blogs/developer/serverless-service-discovery-part-1-get-started/)
* [Part 2: Lookup](https://aws.amazon.com/blogs/developer/serverless-service-discovery-part-2-lookup/)
* [Part 3: Registration](https://aws.amazon.com/blogs/developer/serverless-service-discovery-part-3-registration/)
* [Part 4: Registrar](https://aws.amazon.com/blogs/developer/serverless-service-discovery-part-4-registrar/)


## Part 1: Get Started

1. Add IAM user `serverless_service_discovery`.
2. Attach `AWSLambdaFullAccess` and `AmazonAPIGatewayAdministrator` policies to user `serverless_service_discovery`.
3. Create role `lambda_s3`.
4. Attach `AWSLambdaExecute` policy to `lambda_s3`.
5. Run `AWS_PROFILE={profile} python deploy_catalog_service.py {account_id}`

```
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
INFO:botocore.vendored.requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): lambda.us-east-1.amazonaws.com
INFO:botocore.vendored.requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): apigateway.us-east-1.amazonaws.com
INFO:root:deploying: XXXXXXXXXX to dev
INFO:botocore.vendored.requests.packages.urllib3.connectionpool:Starting new HTTPS connection (1): apigateway.us-east-1.amazonaws.com
INFO:root:--------------------- END POINTS (START) ---------------
INFO:root:End Point: https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/dev/catalog/{serviceName}/{serviceVersion}
INFO:root:--------------------- END POINTS (END) -----------------
```

6. Note end point URL in output.
7. Run `curl -s https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/dev/catalog/testservice1/1.0`

```JSON
{"status": "healthy", "endpoint_url": "notarealurl", "ttl": "300"}
```


## Part 2: Lookup

1. Prepare DynamoDB "Services" table

```Shell
AWS_PROFILE={profile} python prepare_services_db.py
```
