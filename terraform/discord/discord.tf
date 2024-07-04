terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
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

variable "source_ip" {}
variable "joy_ip" {}
variable "do_token" {}
variable "database_cluster_name" {}

provider "digitalocean" {
  token = var.do_token
}

module "digitalocean_infra" {
  source   = "../digitalocean_infra"
  do_token = var.do_token
  database_cluster_name = var.database_cluster_name
}

resource "digitalocean_droplet" "splattop_discord" {
    image = "ubuntu-22-04-x64"
    name = "splattop-discord"
    region = "nyc3"
    size = "s-1vcpu-1gb"
    ssh_keys = module.digitalocean_infra.ssh_key_ids
}

output "bot_host_ip" {
    value = digitalocean_droplet.splattop_discord.ipv4_address
}

output "bot_host_id" {
    value = digitalocean_droplet.splattop_discord.id
}