docker rmi -f $(docker images -a -q)
nitro-cli build-enclave --docker-dir ./ --docker-uri enclavetest/nitro-enclave-demo:latest --output-file nitro-enclave-demo.eif
nitro-cli run-enclave --cpu-count 2 --memory 2048 --eif-path nitro-enclave-demo.eif --debug-mode
nitro-cli console --enclave-id $(nitro-cli describe-enclaves | jq -r ".[0].EnclaveID")
