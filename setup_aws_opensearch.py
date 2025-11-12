#!/usr/bin/env python3
"""
AWS OpenSearch Setup Script
Automates the creation of OpenSearch Serverless collection and indexes
"""

import boto3
import json
import time
import sys
import os
from typing import Dict, Any

def print_section(title: str):
    """Print a formatted section title"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def create_opensearch_collection(client, collection_name: str, account_id: str, region: str) -> str:
    """Create OpenSearch Serverless collection"""
    
    print_section("Creating OpenSearch Serverless Collection")
    
    try:
        # Check if collection already exists
        try:
            response = client.batch_get_collection(names=[collection_name])
            if response['collectionDetails']:
                print(f"✅ Collection '{collection_name}' already exists")
                collection_id = response['collectionDetails'][0]['id']
                endpoint = response['collectionDetails'][0]['collectionEndpoint']
                print(f"   Collection ID: {collection_id}")
                print(f"   Endpoint: {endpoint}")
                return endpoint
        except client.exceptions.ResourceNotFoundException:
            pass
        
        # Create encryption policy
        encryption_policy_name = f"{collection_name}-encryption"
        encryption_policy = {
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{collection_name}"]
                }
            ],
            "AWSOwnedKey": True
        }
        
        try:
            client.create_security_policy(
                name=encryption_policy_name,
                type='encryption',
                policy=json.dumps(encryption_policy)
            )
            print(f"✅ Created encryption policy: {encryption_policy_name}")
        except client.exceptions.ConflictException:
            print(f"ℹ️  Encryption policy already exists")
        
        # Create network policy (public access for initial setup)
        network_policy_name = f"{collection_name}-network"
        network_policy = [
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
        ]
        
        try:
            client.create_security_policy(
                name=network_policy_name,
                type='network',
                policy=json.dumps(network_policy)
            )
            print(f"✅ Created network policy: {network_policy_name}")
        except client.exceptions.ConflictException:
            print(f"ℹ️  Network policy already exists")
        
        # Create data access policy
        data_policy_name = f"{collection_name}-data-access"
        data_policy = [
            {
                "Rules": [
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
                    },
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{collection_name}"],
                        "Permission": ["aoss:CreateCollectionItems", "aoss:UpdateCollectionItems"]
                    }
                ],
                "Principal": [
                    f"arn:aws:iam::{account_id}:root"
                ]
            }
        ]
        
        try:
            client.create_access_policy(
                name=data_policy_name,
                type='data',
                policy=json.dumps(data_policy)
            )
            print(f"✅ Created data access policy: {data_policy_name}")
        except client.exceptions.ConflictException:
            print(f"ℹ️  Data access policy already exists")
        
        # Wait for policies to propagate
        print("⏳ Waiting for policies to propagate (10 seconds)...")
        time.sleep(10)
        
        # Create the collection
        print(f"🚀 Creating collection: {collection_name}...")
        response = client.create_collection(
            name=collection_name,
            type='VECTORSEARCH',
            description='Vector database for AI Organization Assistant'
        )
        
        collection_id = response['createCollectionDetail']['id']
        print(f"✅ Collection creation initiated")
        print(f"   Collection ID: {collection_id}")
        
        # Wait for collection to become active
        print("⏳ Waiting for collection to become active (this may take 5-10 minutes)...")
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            response = client.batch_get_collection(names=[collection_name])
            if response['collectionDetails']:
                status = response['collectionDetails'][0]['status']
                print(f"   Status: {status} (attempt {attempt + 1}/{max_attempts})")
                
                if status == 'ACTIVE':
                    endpoint = response['collectionDetails'][0]['collectionEndpoint']
                    print(f"\n✅ Collection is ACTIVE!")
                    print(f"   Endpoint: {endpoint}")
                    return endpoint
                elif status == 'FAILED':
                    print(f"❌ Collection creation failed")
                    sys.exit(1)
            
            time.sleep(10)
            attempt += 1
        
        print(f"⚠️  Collection is taking longer than expected. Check AWS Console.")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Error creating collection: {e}")
        sys.exit(1)

def update_env_file(endpoint: str, region: str):
    """Update .env file with OpenSearch endpoint"""
    
    print_section("Updating Environment Configuration")
    
    env_file = ".env"
    env_example = ".env.example"
    
    # Read existing .env or create from example
    if os.path.exists(env_file):
        print(f"📝 Updating existing {env_file}")
        with open(env_file, 'r') as f:
            lines = f.readlines()
    elif os.path.exists(env_example):
        print(f"📝 Creating {env_file} from {env_example}")
        with open(env_example, 'r') as f:
            lines = f.readlines()
    else:
        print(f"⚠️  No .env or .env.example found, creating new .env")
        lines = []
    
    # Update OpenSearch configuration
    updated_lines = []
    endpoint_found = False
    region_found = False
    db_type_found = False
    
    for line in lines:
        if line.startswith('AWS_OPENSEARCH_ENDPOINT='):
            updated_lines.append(f'AWS_OPENSEARCH_ENDPOINT={endpoint}\n')
            endpoint_found = True
        elif line.startswith('AWS_OPENSEARCH_REGION='):
            updated_lines.append(f'AWS_OPENSEARCH_REGION={region}\n')
            region_found = True
        elif line.startswith('VECTOR_DB_TYPE='):
            updated_lines.append('VECTOR_DB_TYPE=opensearch\n')
            db_type_found = True
        else:
            updated_lines.append(line)
    
    # Add missing configuration
    if not endpoint_found:
        updated_lines.append(f'AWS_OPENSEARCH_ENDPOINT={endpoint}\n')
    if not region_found:
        updated_lines.append(f'AWS_OPENSEARCH_REGION={region}\n')
    if not db_type_found:
        updated_lines.append('VECTOR_DB_TYPE=opensearch\n')
    
    # Write updated .env
    with open(env_file, 'w') as f:
        f.writelines(updated_lines)
    
    print(f"✅ Updated {env_file}")
    print(f"   AWS_OPENSEARCH_ENDPOINT={endpoint}")
    print(f"   AWS_OPENSEARCH_REGION={region}")
    print(f"   VECTOR_DB_TYPE=opensearch")

def main():
    """Main setup function"""
    
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║              AWS OpenSearch Serverless Setup Script                     ║
    ║              for AI Organization Assistant                               ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Get configuration
    collection_name = input("Enter collection name [ai-org-assistant-vectors]: ").strip()
    if not collection_name:
        collection_name = "ai-org-assistant-vectors"
    
    region = input("Enter AWS region [us-east-1]: ").strip()
    if not region:
        region = "us-east-1"
    
    print(f"\n📋 Configuration:")
    print(f"   Collection Name: {collection_name}")
    print(f"   AWS Region: {region}")
    
    confirm = input("\nProceed with setup? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("❌ Setup cancelled")
        sys.exit(0)
    
    # Initialize AWS clients
    try:
        session = boto3.Session(region_name=region)
        aoss_client = session.client('opensearchserverless')
        sts_client = session.client('sts')
        
        # Get AWS account ID
        account_id = sts_client.get_caller_identity()['Account']
        print(f"\n✅ AWS Session initialized")
        print(f"   Account ID: {account_id}")
        print(f"   Region: {region}")
        
    except Exception as e:
        print(f"❌ Failed to initialize AWS session: {e}")
        print("\nMake sure you have:")
        print("  1. AWS CLI configured (aws configure)")
        print("  2. Valid AWS credentials")
        print("  3. Required IAM permissions for OpenSearch Serverless")
        sys.exit(1)
    
    # Create OpenSearch collection
    endpoint = create_opensearch_collection(aoss_client, collection_name, account_id, region)
    
    # Update .env file
    update_env_file(endpoint, region)
    
    # Print next steps
    print_section("Setup Complete! 🎉")
    print("""
Next steps:

1. Test the connection:
   python -c "from aws_vector_store import OpenSearchVectorStore; import os; vs = OpenSearchVectorStore(endpoint=os.getenv('AWS_OPENSEARCH_ENDPOINT'), region=os.getenv('AWS_OPENSEARCH_REGION')); print(vs.get_health())"

2. Start your application:
   python main.py

3. Sync your data:
   curl -X POST "http://localhost:8000/sync" \\
     -H "Content-Type: application/json" \\
     -d '{"sources": ["github", "confluence"]}'

4. Query your assistant:
   curl -X POST "http://localhost:8000/query" \\
     -H "Content-Type: application/json" \\
     -d '{"question": "How to deploy?", "user_role": "developer"}'

For production:
- Review and tighten data access policies
- Configure VPC access instead of public access
- Set up CloudWatch monitoring
- Review cost optimization settings

Documentation: AWS_VECTOR_DB_MIGRATION_GUIDE.md
    """)

if __name__ == "__main__":
    main()




