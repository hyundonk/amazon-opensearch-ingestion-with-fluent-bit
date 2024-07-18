# amazon-opensearch-ingestion-with-fluent-bit
Demos on how to configure fluent-bit for Amazon Opensearch Ingestion. Please note that code in this repo is intended for demo purpose and not for production workload.



## Overview

Amazon OpenSearch Ingestion is a fully managed, serverless data collector service that delivers real-time log, metric, and trace data to Amazon OpenSearch Service.

Fluent-bit is a fast and flexible log processor and router supported by various operating system. It can be used to route logs to various AWS destinations including Amazon OpenSearch Ingestion Service as well as Amazon CloudWatch Logs, Amazon S3, Amazon OpenSearch Service, etc. 

Amazon OpenSearch Ingestion requires  [AWS Signature Version 4](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_aws-signing.html) authentication information in the request header or query string in all requests to OpenSearch Ingestion endpoint. Fluent-bit supports [AWS Signature Version 4](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_aws-signing.html) authentication by providing various plugins to configure AWS credentials in fluent-bit configuration file as describe in the link below.

https://github.com/fluent/fluent-bit-docs/blob/master/administration/aws-credentials.md

This repo contains demos for using AWS credentials in non-AWS environment scenarios.



## Scenario 1. Using AWS IAM User credential

This scenario is for using AWS IAM User credential in non-AWS environment. This demo is described for explanation but usually not recommended as it uses long-term credential which can add security risk and operational complexity in creating/distributing/renewing long-term credential in secure way. 



### Pre-requisites

- Deploy Amazon OpenSearch Service and Amazon OpenSearch Ingestion service. Declare Amazon OpenSearch Ingestion Endpoint URL as a environment variable and create 

```
export PIPELINE_INGEST_URL=$(aws osis get-pipeline --pipeline-name my-ingest-pipeline --query 'Pipeline.IngestEndpointUrls[0]' --output text)
```

- Prepare IAM user credential key which has a permission policy for "osis:Ingest" action to the Amazon OpenSearch 

```
AWS_ACCESS_KEY_ID={enter-my-aws-access-key-id-here}
AWS_SECRET_ACCESS_KEY={enter-my-aws-secret-access-key-here}
```

- Install docker and docker-compose



### Run demo

1) Go to '1-environment-variables' directory in the repo.

```
cd amazon-opensearch-ingestion-with-fluent-bit/1-environment-variables
```



2. Create fluent-bit configuration file

```
cat << EOF > fluent-bit/fluent-bit.conf
[SERVICE]
    Flush     1
    Daemon    Off
    Log_Level debug

[INPUT]
    Name                  forward
    Listen                0.0.0.0
    Port                  24224

[OUTPUT]
    Name http
    Match *
    Host ${PIPELINE_INGEST_URL}
    Port 443
    URI /log/ingest
    format json
    aws_auth true
    aws_region ap-northeast-2
    aws_service osis
    Log_Level info
    tls On
EOF
```



3. Create a file contains environment variables for AWS IAM User credential.

```
cat << EOF > .env
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
EOF
```



4. Login-in to docker for accessing fluent-bit container image in ECR

```
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin 906394416424.dkr.ecr.$AWS_REGION.amazonaws.com
```



5. Run docker-compose

```
docker-compose --env-file .env up --build &
```



## Scenario 2. Using AWS IAM Roles Anywhere

This scenario is for using temporary credential that AWS IAM Roles Anywhere provides in non-AWS environment. 


### Pre-requisites

- Deploy Amazon OpenSearch Service and Amazon OpenSearch Ingestion service. Declare Amazon OpenSearch Ingestion Endpoint URL as a environment variable 

```
export PIPELINE_INGEST_URL=$(aws osis get-pipeline --pipeline-name my-ingest-pipeline --query 'Pipeline.IngestEndpointUrls[0]' --output text)
```

- Create a IAM role with a trust policy to IAM roles anywhere service and a permission policy for "osis:Ingest" action to the Amazon OpenSearch Ingestion.

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "rolesanywhere.amazonaws.com"
            },
            "Action": [
                "sts:AssumeRole",
                "sts:SetSourceIdentity",
                "sts:TagSession"
            ]
        }
    ]
}

* Create a Anywhere IAM role 

aws iam create-role --role-name opensearchingestAnywhereRole --assume-role-policy-document file://rolesamywhere-trust-policy.json

aws iam put-role-policy \
    --role-name opensearchingestAnywhereRole \
    --policy-name onpremsrv-inline-policy \
     --policy-document file://onpremsrv-permissions-policy.json
```

- Create a Private certificate authority in AWS Private Certificate Authority and install CA certificate.
- Create a IAM Roles Anywhere **Trust anchor** with the private certificate authority and a **Profile** which has above IAM anywhere role.

- SET envrionment variables in below format 

```
AWS_REGION=ap-northeast-2
TRUST_ANCHOR_ARN=arn:aws:rolesanywhere:{region}:123456789012:trust-anchor/11111111-2222-3333-4444-555555555555
PROFILE_ARN=arn:aws:rolesanywhere:{region}:123456789012:profile/11111111-2222-3333-4444-555555555555
ROLE_ARN=arn:aws:iam::123456789012:role/opensearchingestAnywhereRole
```

- Install docker and docker-compose



### Run Demo

1. Go to '2-iam-roles-anywhere' directory in the repo.

```
cd amazon-opensearch-ingestion-with-fluent-bit/2-iam-roles-anywhere
```



2. Download 'aws_signing_helper' file for compute environment. (refer https://docs.aws.amazon.com/rolesanywhere/latest/userguide/credential-helper.html)

```
wget https://rolesanywhere.amazonaws.com/releases/1.1.1/X86_64/Linux/aws_signing_helper
chmod a+x aws_signing_helper
```



3. Create a certificate on AWS Certificate Manager and prepare certificate.pem and private_key.pem files in current directory. This will be used to get temporary credential from AWS IAM roles anywhere service.

```
ls *.pem
certificate.pem  private_key.pem
```



### 

4. Create aws_signing_helper_config.json file

```
cat << EOF > aws_signing_helper_config.json
[default]
credential_process = /bin/aws_signing_helper credential-process --certificate /etc/certificate.pem --private-key /etc/private_key.pem --trust-anchor-arn ${TRUST_ANCHOR_ARN} --profile-arn ${PROFILE_ARN} --role-arn ${ROLE_ARN}
EOF
```



5. Create fluent-bit configuration file

```
cat << EOF > fluent-bit/fluent-bit.conf
[SERVICE]
    Flush     1
    Daemon    Off
    Log_Level debug

[INPUT]
    Name                  forward
    Listen                0.0.0.0
    Port                  24224

[OUTPUT]
    Name http
    Match *
    Host ${PIPELINE_INGEST_URL}
    Port 443
    URI /log/ingest
    format json
    aws_auth true
    aws_region ap-northeast-2
    aws_service osis
    Log_Level info
    tls On
EOF
```



6. Login-in to docker for accessing fluent-bit container image in ECR

```
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin 906394416424.dkr.ecr.$AWS_REGION.amazonaws.com
```



7. Run docker-compose

```
$ docker-compose up --build &
[1] 525146
[+] Building 1.5s (19/19) FINISHED                                                                            docker:default
 => [fluent-bit internal] load build definition from Dockerfile.fluent-bit                                              0.0s
 => => transferring dockerfile: 277B                                                                                    0.0s
 => [fluent-bit internal] load metadata for 906394416424.dkr.ecr.ap-northeast-2.amazonaws.com/aws-for-fluent-bit:2.32.  0.1s
 => [fluent-bit auth] sharing credentials for 906394416424.dkr.ecr.ap-northeast-2.amazonaws.com                         0.0s
 => [fluent-bit internal] load .dockerignore                                                                            0.0s
 => => transferring context: 2B                                                                                         0.0s
 => [fluent-bit internal] load build context                                                                            0.0s
 => => transferring context: 101B                                                                                       0.0s
 => [fluent-bit 1/2] FROM 906394416424.dkr.ecr.ap-northeast-2.amazonaws.com/aws-for-fluent-bit:2.32.2.20240516@sha256:  0.0s
 => CACHED [fluent-bit 2/2] COPY ./aws_signing_helper /bin/aws_signing_helper                                           0.0s
 => [fluent-bit] exporting to image                                                                                     0.0s
 => => exporting layers                                                                                                 0.0s
 => => writing image sha256:e84360fdcc4d2cdcc243075a7f2e77822659112b0d03c96cd38f19c6b5554800                            0.0s
 => => naming to docker.io/library/2-iam-roles-anywhere_fluent-bit                                                      0.0s
 => [fluent-bit] resolving provenance for metadata file                                                                 0.0s
 => [python-app internal] load build definition from Dockerfile                                                         0.0s
 => => transferring dockerfile: 608B                                                                                    0.0s
 => [python-app internal] load metadata for docker.io/library/python:3.9-slim                                           1.2s
 => [python-app internal] load .dockerignore                                                                            0.0s
 => => transferring context: 2B                                                                                         0.0s
 => [python-app 1/4] FROM docker.io/library/python:3.9-slim@sha256:a6c12ec09f13df9d4b8b4e4d08678c1b212d89885be14b6c72b  0.0s
 => [python-app internal] load build context                                                                            0.0s
 => => transferring context: 270B                                                                                       0.0s
 => CACHED [python-app 2/4] WORKDIR /app                                                                                0.0s
 => CACHED [python-app 3/4] COPY . /app                                                                                 0.0s
 => CACHED [python-app 4/4] RUN pip install --no-cache-dir -r requirements.txt                                          0.0s
 => [python-app] exporting to image                                                                                     0.0s
 => => exporting layers                                                                                                 0.0s
 => => writing image sha256:18222bf9fb5860fdee455f06aa5a03b66bafe9deb0a0f67d32270e427b07ea1b                            0.0s
 => => naming to docker.io/library/2-iam-roles-anywhere_python-app                                                      0.0s
 => [python-app] resolving provenance for metadata file                                                                 0.0s
[+] Running 3/3
 ✔ Network 2-iam-roles-anywhere_logging_network  Created                                                                0.1s
 ✔ Container 2-iam-roles-anywhere_fluent-bit_1   Created                                                                0.1s
 ✔ Container 2-iam-roles-anywhere_python-app_1   Created                                                                0.0s
Attaching to fluent-bit_1, python-app_1
fluent-bit_1  | AWS for Fluent Bit Container Image Version 2.32.2.20240516
fluent-bit_1  | Fluent Bit v1.9.10
fluent-bit_1  | * Copyright (C) 2015-2022 The Fluent Bit Authors
fluent-bit_1  | * Fluent Bit is a CNCF sub-project under the umbrella of Fluentd
fluent-bit_1  | * https://fluentbit.io
fluent-bit_1  |
fluent-bit_1  | [2024/07/18 01:52:01] [ info] Configuration:
fluent-bit_1  | [2024/07/18 01:52:01] [ info]  flush time     | 1.000000 seconds
fluent-bit_1  | [2024/07/18 01:52:01] [ info]  grace          | 5 seconds
fluent-bit_1  | [2024/07/18 01:52:01] [ info]  daemon         | 0
fluent-bit_1  | [2024/07/18 01:52:01] [ info] ___________
fluent-bit_1  | [2024/07/18 01:52:01] [ info]  inputs:
fluent-bit_1  | [2024/07/18 01:52:01] [ info]      forward
fluent-bit_1  | [2024/07/18 01:52:01] [ info] ___________
fluent-bit_1  | [2024/07/18 01:52:01] [ info]  filters:
fluent-bit_1  | [2024/07/18 01:52:01] [ info] ___________
fluent-bit_1  | [2024/07/18 01:52:01] [ info]  outputs:
fluent-bit_1  | [2024/07/18 01:52:01] [ info]      http.0
fluent-bit_1  | [2024/07/18 01:52:01] [ info] ___________
fluent-bit_1  | [2024/07/18 01:52:01] [ info]  collectors:
fluent-bit_1  | [2024/07/18 01:52:01] [ info] [fluent bit] version=1.9.10, commit=06145a501d, pid=1
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [engine] coroutine stack size: 24576 bytes (24.0K)
fluent-bit_1  | [2024/07/18 01:52:01] [ info] [storage] version=1.4.0, type=memory-only, sync=normal, checksum=disabled, max_chunks_up=128
fluent-bit_1  | [2024/07/18 01:52:01] [ info] [cmetrics] version=0.3.7
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [forward:forward.0] created event channels: read=27 write=28
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [in_fw] Listen='0.0.0.0' TCP_Port=24224
fluent-bit_1  | [2024/07/18 01:52:01] [ info] [input:forward:forward.0] listening on 0.0.0.0:24224
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [http:http.0] created event channels: read=30 write=31
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [aws_credentials] Initialized Env Provider in standard chain
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [aws_credentials] Initialized AWS Profile Provider in standard chain
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [aws_credentials] Not initializing EKS provider because AWS_ROLE_ARN was not set
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [aws_credentials] Not initializing ECS Provider because AWS_CONTAINER_CREDENTIALS_RELATIVE_URI is not set
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [aws_credentials] Initialized EC2 Provider in standard chain
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [aws_credentials] Sync called on the EC2 provider
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [aws_credentials] Init called on the env provider
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [aws_credentials] Init called on the profile provider
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [aws_credentials] Reading shared config file.
fluent-bit_1  | [2024/07/18 01:52:01] [debug] [aws_credentials] executing credential_process /bin/aws_signing_helper
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [aws_credentials] credential_process /bin/aws_signing_helper exited successfully
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [aws_credentials] successfully parsed credentials from credential_process /bin/aws_signing_helper
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [aws_credentials] Async called on the EC2 provider
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [router] match rule forward.0:http.0
fluent-bit_1  | [2024/07/18 01:52:02] [ info] [sp] stream processor started
fluent-bit_1  | [2024/07/18 01:52:02] [ info] [output:http:http.0] worker #1 started
fluent-bit_1  | [2024/07/18 01:52:02] [ info] [output:http:http.0] worker #0 started
python-app_1  |  * Serving Flask app 'app' (lazy loading)
python-app_1  |  * Environment: production
python-app_1  |    WARNING: This is a development server. Do not use it in a production deployment.
python-app_1  |    Use a production WSGI server instead.
python-app_1  |  * Debug mode: off
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [input chunk] update output instances with new chunk size diff=198, records=1, input=forward.0
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [input chunk] update output instances with new chunk size diff=182, records=1, input=forward.0
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [input chunk] update output instances with new chunk size diff=240, records=1, input=forward.0
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [input chunk] update output instances with new chunk size diff=197, records=1, input=forward.0
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [input chunk] update output instances with new chunk size diff=174, records=1, input=forward.0
python-app_1  | INFO:werkzeug:WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
python-app_1  |  * Running on all addresses (0.0.0.0)
python-app_1  |  * Running on http://127.0.0.1:9090
python-app_1  |  * Running on http://172.20.10.1:9090
python-app_1  | INFO:werkzeug:Press CTRL+C to quit
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [input chunk] update output instances with new chunk size diff=302, records=1, input=forward.0
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [input chunk] update output instances with new chunk size diff=194, records=1, input=forward.0
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [input chunk] update output instances with new chunk size diff=192, records=1, input=forward.0
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [input chunk] update output instances with new chunk size diff=194, records=1, input=forward.0
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [input chunk] update output instances with new chunk size diff=200, records=1, input=forward.0
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [task] created task=0x7f3d93f7c370 id=0 OK
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [http_client] not using http_proxy for header
fluent-bit_1  | [2024/07/18 01:52:02] [ info] [output:http:http.0] xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.ap-northeast-2.osis.amazonaws.com:443, HTTP status=200
fluent-bit_1  | 200 OK
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [upstream] KA connection #54 to xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.ap-northeast-2.osis.amazonaws.com:443 is now available
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [out flush] cb_destroy coro_id=0
fluent-bit_1  | [2024/07/18 01:52:02] [debug] [task] destroy task=0x7f3d93f7c370 (task_id=0)
```





