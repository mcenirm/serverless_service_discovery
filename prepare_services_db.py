def main():
    import boto3

    dynamodb = boto3.resource('dynamodb', region_name = 'us-east-1')

    # create the table
    table = dynamodb.create_table(
        TableName='Services',
        KeySchema=[ { 'AttributeName': 'name', 'KeyType': 'HASH' },
                    { 'AttributeName': 'version', 'KeyType': 'RANGE' } ],
        AttributeDefinitions=[ { 'AttributeName': 'name',
                                'AttributeType': 'S' },
                            { 'AttributeName': 'version',
                                'AttributeType': 'S' }, ],
        ProvisionedThroughput={ 'ReadCapacityUnits': 10,
                                'WriteCapacityUnits': 10 } )

    # wait for the table to be ready
    # this will block until the table is ACTIVE
    table = boto3.resource('dynamodb').Table('Services')
    table.wait_until_exists()

    # insert some test data
    with table.batch_writer() as batch:
        batch.put_item(Item={
                    'name': 'testservice1',
                    'version': '1.0',
                    'endpoint_url': 'notarealurl1',
                    'ttl': 300,
                    'status': 'healthy' })
        batch.put_item(Item={
                    'name': 'testservice2',
                    'version': '1.0',
                    'endpoint_url': 'notarealurl2',
                    'ttl': 600,
                    'status': 'healthy' })


if __name__ == '__main__':
    main()
