terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
  backend "s3" {
    endpoints                   = { s3 = "https://nyc3.digitaloceanspaces.com" }
    bucket                      = "splat-top"
    key                         = "dev.tfstate"
    region                      = "us-east-1"
    skip_requesting_account_id  = true
    skip_credentials_validation = true
    skip_region_validation      = true
    skip_metadata_api_check     = true
    skip_s3_checksum            = true
  }
}

variable "source_ip" {
  type        = string
  description = "Source IP address for firewall rules"
}

variable "joy_ip" {
  type        = string
  description = "Joy's IP address for firewall rules"
}

variable "do_token" {
  type        = string
  sensitive   = true
  description = "DigitalOcean API Token"
}

variable "database_cluster_name" {
  type        = string
  description = "Name of the DigitalOcean database cluster"
}

provider "digitalocean" {
  token = var.do_token
}

module "digitalocean_infra" {
  source                = "../digitalocean_infra"
  do_token              = var.do_token
  database_cluster_name = var.database_cluster_name
}

resource "digitalocean_droplet" "splattop_discord" {
  image    = "ubuntu-22-04-x64"
  name     = "splattop-discord"
  region   = "nyc3"
  size     = "s-1vcpu-1gb"
  ssh_keys = module.digitalocean_infra.ssh_key_ids
}

output "bot_host_ip" {
  value = digitalocean_droplet.splattop_discord.ipv4_address
}

output "bot_host_id" {
  value = digitalocean_droplet.splattop_discord.id
}