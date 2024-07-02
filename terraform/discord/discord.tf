terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

variable "source_ip" {}
variable "joy_ip" {}
variable "do_token" {}

provider "digitalocean" {
  token = var.do_token
}

module "digitalocean_infra" {
  source   = "../digitalocean_infra"
  do_token = var.do_token
}

resource "digitalocean_droplet" "splattop_discord" {
    image = "ubuntu-22-04-x64"
    name = "splattop-discord"
    region = "nyc3"
    size = "s-1vcpu-1gb"
    ssh_keys = module.digitalocean_infra.ssh_key_ids
}

resource "digitalocean_database_firewall" "splattop_discord" {
    cluster_id = module.digitalocean_infra.database_cluster_id
    rule {
        type = "ip_addr"
        value = digitalocean_droplet.splattop_discord.ipv4_address
    }
    rule {
        type = "ip_addr"
        value = var.joy_ip
    }
}

output "bot_host_ip" {
    value = digitalocean_droplet.splattop_discord.ipv4_address
}

output "bot_host_id" {
    value = digitalocean_droplet.splattop_discord.id
}