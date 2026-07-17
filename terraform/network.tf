# ==========================================
# 1. ΤΟ ΟΙΚΟΠΕΔΟ: Virtual Cloud Network (VCN)
# ==========================================
resource "oci_core_vcn" "geologist_vcn" {
  compartment_id = var.tenancy_ocid
  cidr_block     = "10.0.0.0/16"
  display_name   = "Geologist-VCN"
  dns_label      = "geologistvcn"
}

# ==========================================
# 2. Η ΠΟΡΤΑ: Internet Gateway
# ==========================================
resource "oci_core_internet_gateway" "geologist_ig" {
  compartment_id = var.tenancy_ocid
  vcn_id         = oci_core_vcn.geologist_vcn.id
  display_name   = "Geologist-Internet-Gateway"
  enabled        = true
}

# ==========================================
# 3. Ο ΧΑΡΤΗΣ: Route Table (Δρομολόγηση στο Ίντερνετ)
# ==========================================
resource "oci_core_default_route_table" "geologist_rt" {
  manage_default_resource_id = oci_core_vcn.geologist_vcn.default_route_table_id

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.geologist_ig.id
  }
}

# ==========================================
# 4. Η ΓΕΙΤΟΝΙΑ: Subnet
# ==========================================
resource "oci_core_subnet" "geologist_subnet" {
  compartment_id    = var.tenancy_ocid
  vcn_id            = oci_core_vcn.geologist_vcn.id
  cidr_block        = "10.0.1.0/24"
  display_name      = "Geologist-Subnet"
  dns_label         = "geosubnet"
  route_table_id    = oci_core_vcn.geologist_vcn.default_route_table_id
  security_list_ids = [oci_core_vcn.geologist_vcn.default_security_list_id]
}