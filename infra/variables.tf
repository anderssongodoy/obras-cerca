variable "aws_region" {
  description = "Región AWS. us-east-1 es la default por Free Tier."
  type        = string
  default     = "us-east-1"
}

variable "backend_url" {
  description = "URL base del backend en EC2 (con HTTPS)."
  type        = string
  default     = "https://obrascerca.trinitylabs.app"
}

variable "ingesta_token" {
  description = "Token compartido entre Lambda y backend (env INGESTA_TOKEN). Generado por aws_setup.sh."
  type        = string
  sensitive   = true
}
