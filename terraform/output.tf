output "oracle_connection_test" {
  value = data.oci_identity_availability_domains.ads.availability_domains[*].name
}

output "server_public_ip" {
  value       = oci_core_instance.geologist_server.public_ip
  description = "H Dimosia IP tou Server mas!"
}