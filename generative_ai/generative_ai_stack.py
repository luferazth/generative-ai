from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    aws_bedrock as bedrock,
    aws_opensearchserverless as opensearchserverless,
    CfnOutput,
)
from constructs import Construct
import json

class GenerativeAiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ===================================================================
        # S3 BUCKETS
        # ===================================================================
        
        input_bucket = s3.Bucket(
            self, "InputDocumentBucket",
            bucket_name=None,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=False,
        )

        output_bucket = s3.Bucket(
            self, "OutputSummaryBucket",
            bucket_name=None,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=False,
        )
        
        feedback_bucket = s3.Bucket(
            self, "FeedbackBucket",
            bucket_name=None,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=False,
        )
        
        kb_data_bucket = s3.Bucket(
            self, "KnowledgeBaseDataBucket",
            bucket_name=None,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=False,
        )
        
        # ===================================================================
        # BEDROCK KNOWLEDGE BASE ROLE (Create first for data access policy)
        # ===================================================================
        
        # IAM Role for KB - must be created before data access policy
        kb_role = iam.Role(
            self, "BedrockKBRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role for Bedrock Knowledge Base"
        )
        
        # ===================================================================
        # OPENSEARCH SERVERLESS FOR KNOWLEDGE BASE
        # ===================================================================
        
        # OpenSearch Serverless Collection
        collection_name = "insurance-kb-collection"
        
        # Encryption policy
        encryption_policy = opensearchserverless.CfnSecurityPolicy(
            self, "KBEncryptionPolicy",
            name="insurance-kb-encryption",
            type="encryption",
            policy=json.dumps({
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{collection_name}"]
                    }
                ],
                "AWSOwnedKey": True
            })
        )
        
        # Network policy (public access for POC)
        network_policy = opensearchserverless.CfnSecurityPolicy(
            self, "KBNetworkPolicy",
            name="insurance-kb-network",
            type="network",
            policy=json.dumps([
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{collection_name}"]
                        },
                        {
                            "ResourceType": "dashboard",
                            "Resource": [f"collection/{collection_name}"]
                        }
                    ],
                    "AllowFromPublic": True
                }
            ])
        )
        
        # Data access policy - MUST include Bedrock role AND Custom Resource Lambda role
        data_access_policy = opensearchserverless.CfnAccessPolicy(
            self, "KBDataAccessPolicy",
            name="insurance-kb-access",
            type="data",
            policy=json.dumps([
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{collection_name}"],
                            "Permission": [
                                "aoss:CreateCollectionItems",
                                "aoss:DeleteCollectionItems",
                                "aoss:UpdateCollectionItems",
                                "aoss:DescribeCollectionItems"
                            ]
                        },
                        {
                            "ResourceType": "index",
                            "Resource": [f"index/{collection_name}/*"],
                            "Permission": [
                                "aoss:CreateIndex",
                                "aoss:DeleteIndex",
                                "aoss:UpdateIndex",
                                "aoss:DescribeIndex",
                                "aoss:ReadDocument",
                                "aoss:WriteDocument"
                            ]
                        }
                    ],
                    "Principal": [
                        kb_role.role_arn,
                        f"arn:aws:iam::{self.account}:root"
                    ]
                }
            ])
        )
        
        data_access_policy.node.add_dependency(kb_role)
        
        # OpenSearch Serverless Collection
        aoss_collection = opensearchserverless.CfnCollection(
            self, "KBCollection",
            name=collection_name,
            type="VECTORSEARCH",
            description="Vector collection for insurance knowledge base"
        )
        
        aoss_collection.add_dependency(encryption_policy)
        aoss_collection.add_dependency(network_policy)
        aoss_collection.add_dependency(data_access_policy)
        
        # NOTE: The vector index must be created MANUALLY after the collection is active
        # See the post-deployment script: ./create_opensearch_index.sh
        
        # ===================================================================
        # BEDROCK KNOWLEDGE BASE PERMISSIONS
        # ===================================================================
        
        # Grant KB permissions to S3
        kb_data_bucket.grant_read(kb_role)
        
        # Grant KB permissions to invoke embedding model
        kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0"]
            )
        )
        
        # Grant KB permissions to OpenSearch Serverless (use wildcard to avoid circular dependency)
        kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "aoss:APIAccessAll"
                ],
                resources=[f"arn:aws:aoss:{self.region}:{self.account}:collection/*"]
            )
        )
        
        # ===================================================================
        # BEDROCK KNOWLEDGE BASE
        # ===================================================================
        
        # Bedrock Knowledge Base with OpenSearch Serverless
        knowledge_base = bedrock.CfnKnowledgeBase(
            self, "InsurancePolicyKB",
            name="insurance-policy-kb",
            description="Insurance policy information for claim processing",
            role_arn=kb_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0"
                )
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS",
                opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                    collection_arn=aoss_collection.attr_arn,
                    vector_index_name="insurance-policy-index",
                    field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                        vector_field="vector",
                        text_field="text",
                        metadata_field="metadata"
                    )
                )
            )
        )
        
        knowledge_base.add_dependency(aoss_collection)
        
        # Data Source
        kb_data_source = bedrock.CfnDataSource(
            self, "KBDataSource",
            name="insurance-policy-docs",
            description="Insurance policy documents from S3",
            knowledge_base_id=knowledge_base.attr_knowledge_base_id,
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=kb_data_bucket.bucket_arn,
                    inclusion_prefixes=["policies/"]
                )
            ),
            vector_ingestion_configuration=bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                    chunking_strategy="FIXED_SIZE",
                    fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
                        max_tokens=300,
                        overlap_percentage=20
                    )
                )
            )
        )
        
        # ===================================================================
        # LAMBDA FUNCTION
        # ===================================================================
        
        document_processor_lambda = lambda_.Function(
            self, "DocumentProcessorLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="lambda_handler.handler",
            code=lambda_.Code.from_asset("lambda"),
            timeout=Duration.seconds(300),
            memory_size=512,
            environment={
                "OUTPUT_BUCKET": output_bucket.bucket_name,
                "FEEDBACK_BUCKET": feedback_bucket.bucket_name,
                "KB_DATA_BUCKET": kb_data_bucket.bucket_name,
                "KNOWLEDGE_BASE_ID": knowledge_base.attr_knowledge_base_id,
                "DEFAULT_MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0",
            }
        )

        # Grant Lambda permissions
        input_bucket.grant_read(document_processor_lambda)
        output_bucket.grant_write(document_processor_lambda)
        feedback_bucket.grant_read_write(document_processor_lambda)
        kb_data_bucket.grant_read(document_processor_lambda)

        document_processor_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate"
                ],
                resources=["*"]
            )
        )
        
        # S3 event notification
        input_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(document_processor_lambda)
        )

        # ===================================================================
        # OUTPUTS
        # ===================================================================
        
        CfnOutput(self, "InputBucketName",
            value=input_bucket.bucket_name
        )
        
        CfnOutput(self, "OutputBucketName",
            value=output_bucket.bucket_name
        )
        
        CfnOutput(self, "FeedbackBucketName",
            value=feedback_bucket.bucket_name
        )
        
        CfnOutput(self, "KBDataBucketName",
            value=kb_data_bucket.bucket_name
        )
        
        CfnOutput(self, "KnowledgeBaseId",
            value=knowledge_base.attr_knowledge_base_id
        )
        
        CfnOutput(self, "DataSourceId",
            value=kb_data_source.attr_data_source_id
        )
        
        CfnOutput(self, "OpenSearchCollectionEndpoint",
            value=aoss_collection.attr_collection_endpoint
        )
        
        CfnOutput(self, "OpenSearchCollectionArn",
            value=aoss_collection.attr_arn
        )
        
        CfnOutput(self, "LambdaFunctionName",
            value=document_processor_lambda.function_name
        )
