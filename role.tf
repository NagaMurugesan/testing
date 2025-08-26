# -------------------------------
# IAM Role for Bedrock Agent
# -------------------------------
resource "aws_iam_role" "bedrock_agent_role" {
  name = "bedrock-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# -------------------------------
# IAM Policy for Bedrock Agent
# -------------------------------
resource "aws_iam_policy" "bedrock_agent_policy" {
  name        = "bedrock-agent-policy"
  description = "Permissions for Bedrock Agent to call models and access S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Allow invoking foundation models
      {
        Effect   = "Allow"
        Action   = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      # If using S3 for knowledge base / RAG
      {
        Effect   = "Allow"
        Action   = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = "*"
      },
      # Optional - allow CloudWatch logging
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "bedrock_agent_role_attach" {
  role       = aws_iam_role.bedrock_agent_role.name
  policy_arn = aws_iam_policy.bedrock_agent_policy.arn
}

# -------------------------------
# Bedrock Agent
# -------------------------------
resource "aws_bedrockagent_agent" "example" {
  agent_name              = "my-agent"
  foundation_model        = "anthropic.claude-v2"
  agent_resource_role_arn = aws_iam_role.bedrock_agent_role.arn
}
