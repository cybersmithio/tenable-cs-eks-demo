# tenable-cs-eks-demo
Files to help demonstrate using Tenable Container Security with Amazon EKS




# Prerequisites:
On your laptop:
  pip install boto3
  kubectl installed on your system
  aws cli installed on your system

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
  Create API keys for user





# Example
export ROLEARN=arn:aws:iam::0000000000:role/EKS-course-role
export AGENTKEY=****************************
./build.py --stackname tenable-eks-cs-demo-stack --stackyamlfile tenable-cs-eks-demo-vpc.yaml --rolearn $ROLEARN --wngyamlfile tenable-cs-eks-demo-nodegroup.yaml --sshprivatekey ~/.ssh/aws-eks-course-cybersmith-keypair.pem --agentkey $AGENTKEY --agentgroup "AWS EKS Worker Nodes"

python3 ./delete.py --sshprivatekey ~/.ssh/aws-eks-course-cybersmith-keypair.pem