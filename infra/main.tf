###############################################################################
# Obras Cerca — Infraestructura AWS para automatización del cron diario
#
# Crea:
#   - Lambda obras-cerca-trigger (Python 3.12) que POSTea al backend en EC2
#   - EventBridge rule que dispara la Lambda todos los días a las 2 AM Lima (7 UTC)
#   - IAM role mínimo para que la Lambda escriba en CloudWatch Logs
#
# NO crea:
#   - EC2 (ya existe: i-0df1bb4d5b2dd7978)
#   - Postgres (corre dentro de la EC2)
#   - Backend FastAPI (corre dentro de la EC2, configurado por aws_setup.sh)
#   - DNS records (van en el panel de Hostinger, manuales)
#
# Uso:
#   cd infra
#   cp terraform.tfvars.example terraform.tfvars   # editar con tus valores
#   terraform init
#   terraform plan
#   terraform apply
#
# Para destruir todo:
#   terraform destroy
###############################################################################

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "obras-cerca"
      ManagedBy = "terraform"
      Owner     = "anderssongodoy"
    }
  }
}

# ---------- IAM role para la Lambda ----------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "trigger" {
  name               = "obras-cerca-trigger-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.trigger.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ---------- Empaquetar el código de la Lambda ----------
data "archive_file" "trigger" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/.terraform/lambda_trigger.zip"
}

# ---------- Lambda function ----------
resource "aws_lambda_function" "trigger" {
  function_name    = "obras-cerca-trigger"
  description      = "Dispara la ingesta diaria en el backend de Obras Cerca"
  role             = aws_iam_role.trigger.arn
  filename         = data.archive_file.trigger.output_path
  source_code_hash = data.archive_file.trigger.output_base64sha256
  handler          = "index.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      BACKEND_URL    = var.backend_url
      INGESTA_TOKEN  = var.ingesta_token
    }
  }
}

# ---------- EventBridge rule (cron diario) ----------
# Sintaxis cron: minute hour day-of-month month day-of-week year
# 0 7 * * ? * = todos los días a las 07:00 UTC = 02:00 Lima
resource "aws_cloudwatch_event_rule" "daily" {
  name                = "obras-cerca-daily-ingest"
  description         = "Dispara la ingesta diaria de Obras Cerca a las 2 AM Lima"
  schedule_expression = "cron(0 7 * * ? *)"
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule = aws_cloudwatch_event_rule.daily.name
  arn  = aws_lambda_function.trigger.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.trigger.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily.arn
}

# ---------- CloudWatch log group (logs de la Lambda) ----------
# Se crea automático cuando la Lambda corre. Configuramos retención.
resource "aws_cloudwatch_log_group" "trigger" {
  name              = "/aws/lambda/obras-cerca-trigger"
  retention_in_days = 14
}
