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

resource "google_cloud_run_v2_job" "astro_video_processing" {
  name     = "astro-video-processing-job"
  location = var.region

  template {
    template {
      timeout = "600s"
      max_retries = 0

      containers {
        image = var.docker_image_job

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi" #"512Mi" se murio en memoria el worker con un video de 160MB (3840x2160 22seg)
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
}