terraform {
  required_version = ">= 1.16.0"

  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "3.2.4"
    }
  }
}

resource "null_resource" "check" {}
