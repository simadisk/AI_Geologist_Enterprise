# ==========================================
# Πληροφορίες για τα Data Centers
# ==========================================
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

# ==========================================
# 5. ΤΟ ΛΕΙΤΟΥΡΓΙΚΟ ΣΥΣΤΗΜΑ (Ubuntu 22.04 ARM)
# ==========================================
data "oci_core_images" "ubuntu_arm_image" {
  compartment_id           = var.tenancy_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# ==========================================
# 6. Ο SERVER (Compute Instance: 4 Cores, 24GB RAM)
# ==========================================
resource "oci_core_instance" "geologist_server" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[1].name
  compartment_id      = var.tenancy_ocid
  shape               = "VM.Standard.A1.Flex"
  display_name        = "Geologist-Server"

  shape_config {
    ocpus         = 4
    memory_in_gbs = 24
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.geologist_subnet.id
    assign_public_ip = true
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu_arm_image.images[0].id
  }

  metadata = {
    # Το δημόσιο κλειδί για να μπαίνουμε στον server
    ssh_authorized_keys = file("C:/Users/User/.oci/geologist_server_key.pub")
  }
}