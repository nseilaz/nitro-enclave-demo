import socket
import requests
import json
import boto3
import base64
import time

def aws_api_call(credential):
    """
    Make AWS API call using credential obtained from parent EC2 instance
    """

    client = boto3.client(
        'kms',
        region_name = 'ap-southeast-2',
        aws_access_key_id = credential['access_key_id'],
        aws_secret_access_key = credential['secret_access_key'],
        aws_session_token = credential['token']
    )

    enccardnum = credential['enccardnum']
    cardnum = enccardnum[0]
    #print(enccardnum)
    print("The encrypted card number is " + cardnum)

    # Decrypt card number
    binary_data = base64.b64decode(cardnum)
    meta = client.decrypt(CiphertextBlob=binary_data)
    plaintext = meta[u'Plaintext']
    decrcardnum = plaintext.decode()

    print("The decrypted card number is " + decrcardnum)

    # Return some data from API response
    return(decrcardnum[12:16])

def main():
    print("Starting server...")

    # Create a vsock socket object
    s = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)

    # Listen for connection from any CID
    cid = socket.VMADDR_CID_ANY

    # The port should match the client running in parent EC2 instance
    port = 5000

    # Bind the socket to CID and port

    s.bind((cid, port))

    # Listen for connection from client
    s.listen()

    while True:
        try:
            c, addr = s.accept()

            # Get AWS credential sent from parent instance
            payload = c.recv(4096)
            credential = json.loads(payload.decode())

            # Get data from AWS API call
            content = aws_api_call(credential)

            # Send the response back to parent instance
            c.send(str.encode(json.dumps(content)))

            # Close the connection
            c.close()

        except Exception as e:
            print(e)

if __name__ == '__main__':
        main()
