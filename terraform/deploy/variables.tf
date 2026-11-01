variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "docker_image" {
  type = string
  default = ""
}

variable "docker_image_job" {
  type = string
  default = ""
}

variable "gcs_bucket" {
  type = string
}