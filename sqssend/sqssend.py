import boto3
import base64
import time
from random import randrange

#Set boto3
kms = boto3.setup_default_session(region_name='ap-southeast-2')
kms = boto3.client('kms')
key_id = 'alias/ENTER KEY NAME HERE'  #alias/keyname

sqs = boto3.client('sqs')
queue_url = 'ENTER AMAZON SQS URL HERE'


def readFile(fileName):
        global ccarray  #make a global array so we can use it

        fileObj = open(fileName, "r") #opens the file in read mode
        ccarray = fileObj.read().splitlines() #puts the file into an array
        fileObj.close()

def loopccarray():
        arraylen = len(ccarray)
        ccnumval = ccarray[randrange(arraylen)]
        stuff = kms.encrypt(KeyId=key_id, Plaintext=ccnumval)
        binary_encrypted = stuff[u'CiphertextBlob']
        encrypted_ccnum = base64.b64encode(binary_encrypted)
        print(encrypted_ccnum.decode())
        print(ccnumval[12:16])

        #Send message to SQS queue
        response = sqs.send_message(
            QueueUrl=queue_url,
            DelaySeconds=10,
            MessageBody=(encrypted_ccnum.decode()+';'+ccnumval[12:16])
            )

        print(response['MessageId'])

if __name__ == '__main__':

        readFile('ccnum.txt') #read list of card numbers
        while(True):

                try:
                        loopccarray()
                        time.sleep(5)
                except:
                        print("error, sleep 5 try again")
                        time.sleep(5)
