terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "local" {
    path = "../../../artifacts/terraform/w4/terraform.tfstate"
  }
}

provider "aws" {
  region = "us-east-2"
}

variable "run_id" {
  type        = string
  description = "Unique lower-case identifier for this temporary W4 test."
  validation {
    condition     = can(regex("^[a-z0-9-]{6,24}$", var.run_id))
    error_message = "run_id must contain 6-24 lowercase letters, digits or hyphens."
  }
}

variable "source_revision" {
  type        = string
  description = "Full immutable Git commit to clone and verify."
  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.source_revision))
    error_message = "source_revision must be a 40-character lowercase Git SHA."
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "aws_ssm_parameter" "ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ssm" {
  name               = "wikipulse-thanh-w4-${var.run_id}"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ssm" {
  name = "wikipulse-thanh-w4-${var.run_id}"
  role = aws_iam_role.ssm.name
}

resource "aws_security_group" "test" {
  name        = "wikipulse-thanh-w4-${var.run_id}"
  description = "Temporary W4 test; no inbound access"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "test" {
  ami                                  = data.aws_ssm_parameter.ami.value
  instance_type                        = "m7i-flex.large"
  subnet_id                            = sort(data.aws_subnets.default.ids)[0]
  associate_public_ip_address          = true
  vpc_security_group_ids               = [aws_security_group.test.id]
  iam_instance_profile                 = aws_iam_instance_profile.ssm.name
  instance_initiated_shutdown_behavior = "terminate"
  user_data = templatefile("${path.module}/user-data.sh.tftpl", {
    source_revision = var.source_revision
    bootstrap_b64   = filebase64("${path.module}/bootstrap.sh")
    verify_b64      = filebase64("${path.module}/verify.sh")
  })
  user_data_replace_on_change = true

  metadata_options {
    http_tokens = "required"
  }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30
    delete_on_termination = true
    encrypted             = true
  }
  tags = {
    Name      = "wikipulse-thanh-w4-${var.run_id}"
    Owner     = "thanh"
    Purpose   = "temporary-w4-validation"
    ManagedBy = "terraform"
  }
}

output "instance_id" {
  value = aws_instance.test.id
}
