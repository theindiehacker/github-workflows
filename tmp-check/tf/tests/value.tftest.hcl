mock_provider "null" {}

run "value" {
  command = plan

  assert {
    condition     = output.value == 1
    error_message = "value が 1 ではありません"
  }
}
