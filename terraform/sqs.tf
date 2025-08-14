resource "aws_sqs_queue" "upload_events" {
  name = "image-upload-events"
  visibility_timeout_seconds = 300
  tags = { Name = "upload-events-queue" }
} 