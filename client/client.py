import sys
import socket
import requests
import json
import time
import boto3

#Set SQS queue details
sqs = boto3.client('sqs', region_name='ap-southeast-2')
queue_url = 'ENTER AMAZON SQS URL HERE'

def create_payload():
    #Create a payload comprising of creditals and the encrypted card number from SQS
    """
    Get the AWS credential from EC2 instance metadata
    """
    r = requests.get("http://169.254.169.254/latest/meta-data/iam/security-credentials/")
    instance_profile_name = r.text

    r = requests.get("http://169.254.169.254/latest/meta-data/iam/security-credentials/%s" % instance_profile_name)
    response = r.json()

    #Get message from SQS queue
    # Receive message from SQS queue
    response2 = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
        )

    message = response2['Messages'][0]
    receipt_handle = message['ReceiptHandle']

    msgbody = response2['Messages'][0]['Body'] 
    x = msgbody.split(";")

    enccardnum, last4dig = x 
    print("The last for card digits are XXXX-XXXX-XXXX-" + last4dig)
    print("The encrypted card number sent to the enclave is -> " + enccardnum )

    # Delete received message from queue
    sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )

    #Generate payload
    payload = {
        'access_key_id' : response['AccessKeyId'],
        'secret_access_key' : response['SecretAccessKey'],
        'token' : response['Token'],
        'enccardnum' : [enccardnum]
    }

    return payload

def main():

    # Get EC2 instance metedata
    payload = create_payload()

    # Create a vsock socket object
    s = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)

    # Get CID from command line parameter
    cid = int(sys.argv[1])

    # The port should match the server running in enclave
    port = 5000

    # Connect to the server
    s.connect((cid, port))

    # Send AWS credential to the server running in enclave
    s.send(str.encode(json.dumps(payload)))

    # receive data from the server
    print("The enclave returned last 4 digits of card from decrypt as -> " + s.recv(1024).decode())

    # close the connection
    s.close()

if __name__ == '__main__':
    main()
