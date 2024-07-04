terraform {
    required_providers {
        digitalocean = {
            source = "digitalocean/digitalocean"
            version = "~> 2.0"
        }
    }
    backend "s3" {
        endpoint                    = "nyc3.digitaloceanspaces.com"
        region                      = "us-east-1"
        bucket                      = "splat-top"
        key                         = "terraform/digitalocean_infra/terraform.tfstate"
        skip_credentials_validation = true
        skip_metadata_api_check     = true
        skip_get_ec2_platforms      = true
        skip_requesting_account_id  = true
    }
}

variable "do_token" {}

variable "database_cluster_name" {}

provider "digitalocean" {
    token = var.do_token
}

data "digitalocean_database_cluster" "sendouq_db" {
    name = var.database_cluster_name
}

data "digitalocean_ssh_key" "github_actions" {
    name = "github_actions"
}

data "digitalocean_ssh_key" "github_actions_ed25519" {
    name = "github_actions_ed25519"
}

data "digitalocean_ssh_key" "wsl" {
    name = "wsl"
}

output "database_cluster_id" {
  value = data.digitalocean_database_cluster.sendouq_db.id
}

output "ssh_key_ids" {
  value = [
    data.digitalocean_ssh_key.github_actions.id,
    data.digitalocean_ssh_key.github_actions_ed25519.id,
    data.digitalocean_ssh_key.wsl.id
  ]
}