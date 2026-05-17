output "lambda_function_name" {
  value       = aws_lambda_function.trigger.function_name
  description = "Nombre de la Lambda. Para invocar manualmente: aws lambda invoke --function-name <este_valor> /tmp/out.json"
}

output "lambda_arn" {
  value       = aws_lambda_function.trigger.arn
  description = "ARN de la Lambda."
}

output "schedule_expression" {
  value       = aws_cloudwatch_event_rule.daily.schedule_expression
  description = "Cron actual (formato AWS, UTC)."
}

output "log_group" {
  value       = aws_cloudwatch_log_group.trigger.name
  description = "CloudWatch log group. Ver logs: aws logs tail <este_valor> --follow"
}
