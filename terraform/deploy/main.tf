resource "google_cloud_run_v2_service" "astro_image_processing" {
  name                = "astro-image-processing"
  location            = var.region
  deletion_protection = false

  # No permitir invocaciones sin autenticacion
  invoker_iam_disabled = false

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    timeout = "60s"

    containers {
      image = var.docker_image

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      volume_mounts {
        name       = "gcs-volume"
        mount_path = "/mnt/bucket"
      }
    }

    volumes {
      name = "gcs-volume"

      gcs {
        bucket    = var.gcs_bucket
        read_only = false

        mount_options = [
          "only-dir=volume-cloud-run"
        ]
      }
    }
  }
}