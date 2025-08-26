terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.65.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# ─────────────────────────────────────────────────────────────────────────────
# 1) S3 bucket with your documents
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "kb_docs" {
  bucket = var.docs_bucket_name
  force_destroy = true
}

# Optional: block all public access
resource "aws_s3_bucket_public_access_block" "kb_docs_block" {
  bucket                  = aws_s3_bucket.kb_docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─────────────────────────────────────────────────────────────────────────────
# 2) OpenSearch Serverless (Vector engine) for the Knowledge Base
#    Needs: encryption policy, network policy, data access policy + collection
# ─────────────────────────────────────────────────────────────────────────────
# Encryption policy (use AWS-owned key by default)
resource "aws_opensearchserverless_security_policy" "enc" {
  name        = "${var.name_prefix}-enc"
  type        = "encryption"
  description = "OSS encryption policy"
  policy      = jsonencode({
    Rules = [{
      ResourceType = "collection"
      Resource     = ["collection/${var.name_prefix}-vec"]
    }]
    AWSOwnedKey = true
  })
}

# Network policy (allow from AWS services / your account principals)
resource "aws_opensearchserverless_security_policy" "net" {
  name        = "${var.name_prefix}-net"
  type        = "network"
  description = "OSS network policy"
  policy      = jsonencode([{
    Rules = [{
      ResourceType = "collection"
      Resource     = ["collection/${var.name_prefix}-vec"]
    }]
    AllowFromPublic = true  # flip to false + add VPC endpoint rules for private-only
  }])
}

# The vector collection
resource "aws_opensearchserverless_collection" "vec" {
  name        = "${var.name_prefix}-vec"
  description = "Vector collection for Bedrock KB"
  type        = "VECTORSEARCH"
  depends_on  = [
    aws_opensearchserverless_security_policy.enc,
    aws_opensearchserverless_security_policy.net
  ]
}

# IAM role Bedrock KB will assume to read S3, write vectors, and call embeddings
data "aws_caller_identity" "me" {}

resource "aws_iam_role" "kb_role" {
  name = "${var.name_prefix}-kb-role"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "bedrock.amazonaws.com" },
      Action    = "sts:AssumeRole",
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.me.account_id
        }
      }
    }]
  })
}

# KB role policy: S3 read, OSSS access, and invoke embeddings model
resource "aws_iam_role_policy" "kb_inline" {
  name = "${var.name_prefix}-kb-inline"
  role = aws_iam_role.kb_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      # Read docs from S3
      {
        Effect: "Allow",
        Action: ["s3:GetObject", "s3:ListBucket"],
        Resource: [
          aws_s3_bucket.kb_docs.arn,
          "${aws_s3_bucket.kb_docs.arn}/*"
        ]
      },
      # OpenSearch Serverless data-plane for the collection & indexes
      {
        Effect: "Allow",
        Action: [
          "aoss:APIAccessAll",   # simplest for demo; scope down in production
          "aoss:DashboardsAccessAll"
        ],
        Resource: [
          aws_opensearchserverless_collection.vec.arn
        ]
      },
      # Invoke Bedrock embeddings model
      {
        Effect: "Allow",
        Action: [
          "bedrock:InvokeModel"
        ],
        Resource: [
          var.embedding_model_arn
        ]
      }
    ]
  })
}

# Data access policy (allow the KB role to write/read vectors in this collection)
resource "aws_opensearchserverless_access_policy" "data" {
  name        = "${var.name_prefix}-data"
  type        = "data"
  description = "Data access for KB role"
  policy      = jsonencode([{
    Rules = [{
      ResourceType = "index",
      Resource     = [
        "index/${aws_opensearchserverless_collection.vec.name}/*"
      ],
      Permission   = ["aoss:ReadDocument", "aoss:WriteDocument", "aoss:CreateIndex", "aoss:DescribeIndex"]
    },{
      ResourceType = "collection",
      Resource     = ["collection/${aws_opensearchserverless_collection.vec.name}"],
      Permission   = ["aoss:DescribeCollectionItems"]
    }],
    Principal = [aws_iam_role.kb_role.arn]
  }])
  depends_on = [aws_opensearchserverless_collection.vec]
}

# ─────────────────────────────────────────────────────────────────────────────
# 3) Bedrock Knowledge Base + S3 Data Source
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_bedrockagent_knowledge_base" "kb" {
  name     = "${var.name_prefix}-kb"
  role_arn = aws_iam_role.kb_role.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = var.embedding_model_arn  # e.g., arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.vec.arn
      vector_index_name = var.vector_index_name       # e.g., "kb-index"
      field_mapping {
        vector_field   = var.vector_field_name        # "vector"
        text_field     = var.text_field_name          # "text"
        metadata_field = var.metadata_field_name      # "metadata"
      }
    }
  }

  depends_on = [aws_opensearchserverless_access_policy.data]
}

# S3 Data Source → connects bucket to the KB
resource "aws_bedrockagent_data_source" "kb_s3" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.kb.id
  name              = "${var.name_prefix}-kb-s3"
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn      = aws_s3_bucket.kb_docs.arn
      inclusion_prefixes = var.inclusion_prefixes     # e.g., ["docs/"]
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# 4) Bedrock Agent + KB association + Alias
#    (Agent must be prepared before alias can route to a version)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_bedrockagent_agent" "agent" {
  agent_name              = "${var.name_prefix}-agent"
  foundation_model        = var.agent_model_id       # e.g., "anthropic.claude-3-sonnet-20240229-v1:0"
  instruction             = var.agent_instruction
  idle_session_ttl_in_seconds = 300
  customer_encryption_key_id  = null  # set a KMS key ARN if you want CMK
  # Optional: guardrail_identifier / guardrail_version can be set here (if using Guardrails)
}

# Attach KB to the Agent
resource "aws_bedrockagent_agent_knowledge_base_association" "agent_kb" {
  agent_id         = aws_bedrockagent_agent.agent.agent_id
  knowledge_base_id = aws_bedrockagent_knowledge_base.kb.id
  description      = "RAG via KB"
}

# Prepare agent after any change (Bedrock build-time step)
# Terraform can't "wait" natively; we use a local-exec to call the CLI
resource "terraform_data" "prepare_agent" {
  triggers_replace = {
    prepare_hash = sha256(jsonencode({
      agent   = aws_bedrockagent_agent.agent.agent_id
      kb_link = aws_bedrockagent_agent_knowledge_base_association.agent_kb.id
    }))
  }

  provisioner "local-exec" {
    command = "aws bedrock-agent prepare-agent --agent-id ${aws_bedrockagent_agent.agent.agent_id} --region ${var.region}"
  }

  depends_on = [aws_bedrockagent_agent_knowledge_base_association.agent_kb]
}

# small sleep to allow PREPARED state to propagate
resource "time_sleep" "after_prepare" {
  create_duration = "10s"
  depends_on      = [terraform_data.prepare_agent]
}

# Create an alias that routes to the latest prepared version
resource "aws_bedrockagent_agent_alias" "alias" {
  agent_id   = aws_bedrockagent_agent.agent.agent_id
  alias_name = "${var.name_prefix}-prod"

  routing_configuration {
    agent_version = "DRAFT"  # after prepare, DRAFT becomes a concrete version; update to the new version as needed
  }

  depends_on = [time_sleep.after_prepare]
}

# ─────────────────────────────────────────────────────────────────────────────
# 5) Helpful outputs
# ─────────────────────────────────────────────────────────────────────────────
output "kb_id"            { value = aws_bedrockagent_knowledge_base.kb.id }
output "kb_role_arn"      { value = aws_iam_role.kb_role.arn }
output "agent_id"         { value = aws_bedrockagent_agent.agent.agent_id }
output "agent_alias_name" { value = aws_bedrockagent_agent_alias.alias.alias_name }
output "oss_collection_arn" { value = aws_opensearchserverless_collection.vec.arn }
