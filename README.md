# tenable-cs-eks-demo
Files to help demonstrate using Tenable Container Security with Amazon EKS.  

# Details
This creates all the AWS infrastructure to run Kubernetes, 
and it starts up a Guestbook application with a Redis memory DB.
All the Kubernetes worker nodes will have Nessus Agents installed and automatically linked to Tenable.io


# Prerequisites For Your Workstation
Your workstation should be Linux, since this has not been tested on Windows.  Do the following on your workstation:
  
  * Install Python3
  * Install kubectl from https://kubernetes.io/docs/tasks/tools/install-kubectl/
  * Install aws-iam-authenticator from https://docs.aws.amazon.com/eks/latest/userguide/install-aws-iam-authenticator.html
  * Install aws cli from https://aws.amazon.com/cli/
  * Install AWS Python library: pip install boto3
  * Update your shell profile with ``` export KUBECONFIG=~/.kube/kube-config-eks ```
  * Make sure this is in your shell profile 

Before you can use this in AWS, some basic IAM objects must be created.
This is the only part of the configuration where you might use your AWS root account.  
Otherwise, for general security reasons do not use your AWS root account.

In AWS:
  * Create a policy called eks-admin-policy that has all access to eks:.
  * Create a policy called CloudFormation-Admin-policy that has all access to cloudformation:.
  * Create eks-admin group with these permission policies:
    AmazonEC2FullAccess
    IAMFullAccess
    AmazonS3FullAccess
    AmazonVPCFullAccess
    AmazonElasticFileSystemFullAccess
    EKS-Admin-policy (user created)
    CloudFormation-Admin-policy (user created)
  * Create EKS-kubernetes-role with these policies:
    AmazonEKSClusterPolicy
    AmazonEKSServicePolicy
  * Create a new account and put into eks-admin group. 
  * Create API keys for user and put them into ~/.aws/credentials.  For example:
```
[default]
aws_access_key_id=******************
aws_secret_access_key=***************************
region=us-east-1
output=json
```

# Running The Script

To create the AWS infrastructure and start everything up:
```
export AGENTKEY=****************************
python3 ./build.py --stackname tenable-eks-cs-demo-stack --stackyamlfile tenable-cs-eks-demo-vpc.yaml --eksrole EKS-role --wngyamlfile tenable-cs-eks-demo-nodegroup.yaml --agentkey $AGENTKEY --agentgroup "AWS EKS Worker Nodes" 
```

To delete everything:
```
python3 ./delete.py
```