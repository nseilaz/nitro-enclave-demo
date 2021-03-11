# nitro-enclave-demo
**Nitro Enclave Demo is a proof of concept for learning purposes and is not production grade ready**

- [**richardfan1126**](https://github.com/richardfan1126/nitro-enclave-python-demo) - post on building a http-proxy with python providing credit to his efforts which provided a base for me to proceed from.  

I used the base of the http proxy and then built further the following example for my own understanding.

1. Read a file with a list of simulated debit/credit card numbers into an array, then randomly select one of the cards, encrypt it with a symmetric KMS key. 
2. Create SQS messages, which includes the encrypted card number, and place that message onto an Amazon SQS queue. 
3. Take the message off the queue; generate a payload, which includes credentials and the encrypted card number taken out the message retried from SQS. Using the sockets method from richardfan1126 send that payload into the Nitro Enclave.
4. A process in the Nitro Enclave then decrypts the bankcard number, to do this the enclave needs to connect out to KMS to obtain the key, here it uses richardfan1126 proxy to do that, and then it will decrypt the card number.
5. Then return to the calling client the last four digits of the bankcard.

Although this is a simple example, it demonstrates a use case for Nitro Enclaves where sensitive data is handled in a secure location.  

Below I shall explain how to deploy the demo and some learning gained.

## Architecture

![Architecture](https://github.com/nseilaz/nitro-enclave-demo/blob/main/docs/architecture.png)

There are 3 separate aspects occurring in this demo.

1. sqssend.py, reads the file ccnum.txt into an array, a random card number is chosen from the array and encrypted using a symmetric key from KMS.  The encrypted card number is sent to an SQS queue.
2. client.py will then read a message off the queue, extract the encrypted card number, compile a set of credentials from the EC2 host, take the credentials and encrypted card number and create a json payload.  The payload is passed into the Nitro Enclave over a socket connection.
3. server.py runs inside of the enclave, it listens for a socket connection, when a connection is made, it takes they payload, disseminates the payload accordingly, connects out of the socket connection and vsock-proxy to KMS to obtain the key used for encryption, then decrypts the card number and returns back to client.py the last 4 digits. 

Although this is not a complex example or a secure example, it purpose is to show the ability to execute work inside of an enclave. 

A few items to note, when setting up the enclave, on the parent host, for the vsock-proxy, if you want to allow other AWS API endpoints, there is a file under /etc/nitro-enclave/vsock-proxy.yaml that needs to be edited.

A thought from my experience, initially I had considered running an "application" in an enclave. As I proceeded with this example, one item to consider is that you do not have access to the enclave in the view of SSH, although you can get a console debug view, but what you see on the console is dependent on what you have outputted and second if you have started the enclave with a debug option.  The importance of this is that if you have a complex application running in the enclave you do not have all the monitoring, log access, telemetry etc.  If the enclave appliaction fails or something is failing it not a simple affair to troubleshoot it. One really needs to consider this.  My experience to date seems to lead me to the view that a specific function of an application is moved into an enclave and multiple enclaves may be a consideration for different application functions.

## Installation guide

Note the EC2 instance being used for Nitro Enclaves are not free tier, check the relevant EC2 pricing for the respective region you will be utilizing. 

1. Create an EC2 instance with Nitro Enclave enabled. See [AWS documentation](https://docs.aws.amazon.com/enclaves/latest/user/create-enclave.html) for steps and requirement.  I launched a C5 xlarge.  Ensure to provide sufficient storage space on the instance root volume, 20 GB is what I used, if you do not provide sufficient storage space the enclave containers will fail to build. You need to SSH into the EC2 instances, ensure that it has a security group that allows that to happen, the instance also requires access to the internet to be able to download packages, you can place it behind a NAT GW if you desire or in a public facing subnet and maintain a good security posture, lock down access to know IP address.

Use the Amazon Linux 2 AMI.

1. Create a new IAM role use case EC2, attach the policy `AWSKeyManagementServicePowerUser` and `AmazonSQSFullAccess` policy to the role.  I named my role `Nitro-Enclave-Demo-KMS-SQS-Role`

   See [AWS Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html#working-with-iam-roles) for more detail
   
1. Attach the role to the EC2 instance you launched in the first step.

1. SSH into the instance. Install nitro environment and some additional items required for the example.

   ```
   sudo yum update -y
   sudo amazon-linux-extras install aws-nitro-enclaves-cli -y
   sudo yum install aws-nitro-enclaves-cli-devel python3 git -y
   sudo pip3 install boto3 requests
   sudo usermod -aG ne $USER
   sudo usermod -aG docker $USER
   ```

1. Modify the pre-allocated memory for the enclave to 2048 MB.

   Modify the file `/etc/nitro_enclaves/allocator.yaml`, change the following line:

   ```
   # memory_mib: 512
   memory_mib: 2300
   ```
1. Enable Docker and Nitro Enclaves Allocator

   ```
   sudo systemctl start nitro-enclaves-allocator.service && sudo systemctl enable nitro-enclaves-allocator.service
   sudo systemctl start docker && sudo systemctl enable docker
   ```

1. Reboot the instance

1. Log in to the instance, clone the repository

   ```
   git clone https://github.com/nseilaz/nitro-enclave-demo.git
   ```

1. Go to AWS console, Key Management Service (KMS) 

   Create a Symmetric Key; provide an Alias, for key admin, select either your username or role you are federated in with, for the key user, select the IAM role you assigned to the EC2 instances earlier. 

1. Go to AWS console, IAM

   From roles, find the role you assigned to the EC2 instance and copy the Role ARN, you will require it in the next step

1. Go to AWS console, Simple Queue Service

   Create queue, select standard and provide a name
   Under the access policy select for both send and receive "Only the specified AWS accounts, IAM users and roles"  paste the ARN you copied into the entry box. 
   Select Create queue button

1. Edit `/sqssend/sqssend.py`, edit the region_name to be the correct region, paste your key alias, ensure you have alias/ before your name. Then paste your sqs queue URL

   ```
        #Set boto3
        kms = boto3.setup_default_session(region_name='ap-southeast-2')
        kms = boto3.client('kms')
        key_id = 'alias/ENTER KEY NAME HERE'  #alias/keyname

        sqs = boto3.client('sqs')
        queue_url = 'ENTER AMAZON SQS URL HERE'
   ```

   The following python script reads the ccnum.txt file into an array; it then encrypts the card number and places a message on the sqs queue.  

   ```
   python3 sqssend.py
   ```

   You should get some output that looks as follows

   ```
    [ec2-user@ip-10-0-1-23 sqssend]$ python3 sqssend.py
    AQICAHgjhjqBDOerXa7hnl+xxMctzt6QXhG/nF85qrJNHIMGawE+cJP3YQkEW/RTs8dViIBdAAAAbjBsBgkqhkiG9w0BBwagXzBdAgEAMFgGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQM+HMPdnSkV6qUl3XNAgEQgCvLmJYB6a4UBjfuJhbuyG+wCvDKwSLfvy0B/AqWqFbCxI63+M/sbcVciN2t
    8110
   ```
   If you do not get this output but an error, the most likely causes could be
   
   Didn't attach the IAM role to the EC2 instance
   The KMS alias is incorrect, make sure the file you have alias/your key alias 
   The SQS queue you have no allowed the IAM role attached to EC2 instance permission to read/write to the SQS queue
   The URL for the SQS queue is not correct.

1. Use the build script to build and run the enclave image

   Before building the enclave, you need to modify a few files in the server folder.

   server.py, check the region_name has the correct region defined.
   run.sh, you need to make sure the dns name is correct for the region that you are using

   Below is the Sydney region but it you were using North Virgina you would change the ap-southeast-2 to us-east-1 retaining the rest of the string.

   ```
    echo "127.0.0.1   kms.ap-southeast-2.amazonaws.com" >> /etc/hosts
   ```
   To build the enclave you run the following 

   ```
   cd nitro-enclave-demo/server/server
   chmod +x build.sh
   ./build.sh
   ```

1. After the enclave has launched, you can find the CID of it.

   Find the following line in the launch output, and take note of the `enclave-cid` value

   ```
   Started enclave with enclave-cid: 16, memory: 1024 MiB, cpu-ids: [1, 3]
   ```
   If you get an error indicating an out of memory as follows
   
   Start allocating memory...
   [ E27 ] Insufficient memory available. User provided `memory` is 2244 MB, which is more than the available hugepage memory.
      
   Look to the end of this document for the troubleshooting section.

1. Open a new SSH session, run the `vsock-proxy` tool

   Note you need to update the URL to match the region you are using

   ```
   vsock-proxy 8000 kms.ap-southeast-2.amazonaws.com 443
   ```

1. Run the client app, replace `<cid>` with the enclave CID you get in step 11

   client.py is found in the client directory, open it for editing and update the SQS queue_url with your queue url.

   Then run the client.py with the cid as explained earlier

   ```
   $ python3 client.py <cid>
   ```

   If everything is working correctly, you should get the following response 

   ```
   [ec2-user@ip-10-0-1-21 client]$ python3 client.py 16
   The last for card digits are XXXX-XXXX-XXXX-4242
   The encrypted card number sent to the enclave is -> AQICAHi7Be/X4UaC+zK1hGQo4flo8YJgNGNdfZHnLt7YNC/n1AEm+EHESG8bSehWPe08BcwCAAAAbjBsBgkqhkiG9w0BBwagXzBdAgEAMFgGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMeUeYJRWooST1RjsiAgEQgCvL/tF6ZXTIU0UbYvDw6p0P+vRb7Xg62wOTGxmgh+YQ+u4cEMQI0LjiZ84w
   The enclave returned last 4 digits of card from decrypt as -> "4242"
   ```

##Clean up

1. Terminate the EC2 instances
2. Delete the SQS Queue
3. Delete the KMS key, this is done by scheduling the deletion.
4. Delete the IAM Role

Troubleshooting
[ E27 ] Insufficient memory available. User provided `memory` is 2244 MB, which is more than the available hugepage memory.
The size of the image may change over time that is used for the build.  The following process should resolve the issue. 
Note on the error line it indicates how much memory is required, this will be higher then what has been allocated in the 
/etc/nitro_enclaves/allocator.yaml.  Edit the file and increase the memory size to be higher.

Reboot the EC2 instance. 

Then 

change to the server directory, run the following
nitro-cli run-enclave --cpu-count 2 --memory 2300 --eif-path nitro-enclave-demo.eif --debug-mode

You will need to open up additional SSH terminals for the rest of the exercise

To get a console debug view of the enclave you need to run these commands
nitro-cli describe-enclaves

Then note you enclaveID
nitro-cli console --enclave-id  PASTE_ENCLAVE_ID here you noted in the previous output. 
