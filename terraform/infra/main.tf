resource "google_artifact_registry_repository" "astro_image_processing" {
  location      = var.region
  repository_id = var.artifact_registry_repository_id
  description   = "para el servicio de cloud run de modificar imagenes"
  format        = "DOCKER"
}