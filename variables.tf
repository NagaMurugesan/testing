variable "region" {
  type        = string
  description = "AWS region (Bedrock supports specific regions)"
  default     = "us-east-1"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for resource names"
  default     = "rag-demo"
}

variable "docs_bucket_name" {
  type        = string
  description = "S3 bucket name to store documents"
}

variable "embedding_model_arn" {
  type        = string
  description = "ARN of embeddings model (e.g., Titan embeddings)"
  # Example:
  # default = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
}

variable "agent_model_id" {
  type        = string
  description = "Bedrock foundation model ID for the Agent (text-generation)"
  # Example:
  # default = "anthropic.claude-3-sonnet-20240229-v1:0"
}

variable "agent_instruction" {
  type        = string
  description = "System prompt for your Agent"
  default     = "You are a helpful RAG assistant. Use the knowledge base when relevant and cite the sources."
}

variable "vector_index_name" {
  type        = string
  default     = "kb-index"
}

variable "vector_field_name"  { type = string, default = "vector" }
variable "text_field_name"    { type = string, default = "text" }
variable "metadata_field_name"{ type = string, default = "metadata" }

variable "inclusion_prefixes" {
  type        = list(string)
  description = "S3 prefixes to include for the data source"
  default     = ["docs/"]
}
