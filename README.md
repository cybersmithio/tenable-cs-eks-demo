# tenable-cs-eks-demo
Files to help demonstrate using Tenable Container Security with Amazon EKS




# Prerequisites:
On your laptop:
  Install kubectl from https://kubernetes.io/docs/tasks/tools/install-kubectl/
  Install aws-iam-authenticator from https://docs.aws.amazon.com/eks/latest/userguide/install-aws-iam-authenticator.html
  Install aws cli from https://aws.amazon.com/cli/
  Install AWS Python library: pip install boto3

In AWS:
  Create a policy called EKS-Admin-policy that has all access to eks:.
  Create a policy called CloudFormation-Admin-policy that has all access to cloudformation:.
  Create a new account with limited access. don't use your AWS root account.
  Create eks-admin group with these permission policies:
    AmazonEC2FullAccess
    IAMFullAccess
    AmazonS3FullAccess
    AmazonVPCFullAccess
    AmazonElasticFileSystemFullAccess
    EKS-Admin-policy (user created)
    CloudFormation-Admin-policy (user created)
  Create EKS-kubernetes-role with these policies:
    AmazonEKSClusterPolicy
    AmazonEKSServicePolicy

# Create API keys for user and put them into ~/.aws/credentials.  For example:
[default]
aws_access_key_id=******************
aws_secret_access_key=***************************
region=us-east-1
output=json


# Example
export ROLEARN=arn:aws:iam::0000000000:role/EKS-course-role
export AGENTKEY=****************************
python3 ./build.py --stackname tenable-eks-cs-demo-stack --stackyamlfile tenable-cs-eks-demo-vpc.yaml --rolearn $ROLEARN --wngyamlfile tenable-cs-eks-demo-nodegroup.yaml --agentkey $AGENTKEY --agentgroup "AWS EKS Worker Nodes"

python3 ./delete.py