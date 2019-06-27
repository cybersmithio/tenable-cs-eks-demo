# tenable-cs-eks-demo
Files to help demonstrate using Tenable Container Security with Amazon EKS


Don't use your AWS root account for anything that isn't absolutely required.  Instead, create other accounts with more limited access to do things.
For this course we need read-write-admin privileges throughout the environment, so AdministratorAccess IAM role will work.  A more locked down version is available in the offline course text:
Create these policies that allow all access to certain areas:
EKS-Admin-policy has all access to eks:
CloudFormation-Admin-policy has all access to cloudformation:
Also provide these policies:
AmazonEC2FullAccess
IAMFullAccess
AmazonVPCFullAccess
CloudFormation-Admin-policy (user created)
EKS-Admin-policy (user created)
Also S3FullAccess (this changed from the creation of the courseware)
Also AmazonElasticFileSystemFullAccess (this seems to be new from the creation of the courseware)
Setup IAM role:
Allows Kubernetes to manage AWS resources
Create an IAM role called EKS-course-role that has all the AmazonEKSClusterPolicy and AmazonEKSServicePolicy
SSH key to EC2 instance
Go to EC2 and click key pairs
Create keypair called EKS-course-keypair
Create API keys for user


# Prerequisites:
Need SSH keypair created
Need a role to manage AWS resources
Need user created for managing EKS and all the infrastructure
Need API keys for the above user
Need kubectl installed on your system
Need aws-iam-authenicator installed on your system



# Example
export ROLEARN=arn:aws:iam::0000000000:role/EKS-course-role
export AGENTKEY=****************************
python3 ./build.py --stackname tenable-eks-cs-demo-stack --stackyamlfile tenable-cs-eks-demo-vpc.yaml --rolearn $ROLEARN --wngyamlfile tenable-cs-eks-demo-nodegroup.yaml --sshkeypair EKS-course-keypair --sshprivatekey ~/.ssh/aws-eks-course-cybersmith-keypair.pem --agentkey $AGENTKEY --agentgroup "AWS EKS Worker Nodes"

python3 ./delete.py --sshprivatekey ~/.ssh/aws-eks-course-cybersmith-keypair.pem