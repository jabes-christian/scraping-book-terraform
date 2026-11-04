# Testes dos outputs do bootstrap (TFB-04).

mock_provider "google" {}

variables {
  project_id = "projeto-teste-123"
}

run "bucket_name_output_is_the_bucket_name" {
  command = plan

  assert {
    condition     = output.bucket_name == "projeto-teste-123-tfstate"
    error_message = "O output bucket_name deve ser o nome do bucket."
  }
}

run "backend_snippet_has_bucket_and_prefix" {
  command = plan

  assert {
    condition     = strcontains(output.backend_hcl_snippet, "bucket = \"projeto-teste-123-tfstate\"")
    error_message = "O snippet deve conter bucket = \"<nome do bucket>\"."
  }

  assert {
    condition     = strcontains(output.backend_hcl_snippet, "prefix = \"envs/prod\"")
    error_message = "O snippet deve conter prefix = \"envs/prod\"."
  }
}

run "outputs_follow_custom_bucket_name" {
  command = plan

  variables {
    bucket_name = "meu-bucket-tfstate"
  }

  assert {
    condition     = output.bucket_name == "meu-bucket-tfstate"
    error_message = "bucket_name deve refletir o nome informado."
  }

  assert {
    condition     = strcontains(output.backend_hcl_snippet, "bucket = \"meu-bucket-tfstate\"")
    error_message = "O snippet deve refletir o nome informado."
  }
}
