help:
	@echo "Available targets:"
	@echo "  profile-pyspy     Run py-spy and generate a flamegraph for the ingestion pipeline"
	@echo "  profile-cprofile  Run cProfile on the ingestion pipeline and open SnakeViz"
	@echo "  metrics           Start the Prometheus metrics endpoint (to be implemented)"

profile-pyspy:
	@echo "Running py-spy..."
	python -m qdrant_loader.cli.cli ingest --source-type=localfile & \
	PID=$$!; sleep 2; py-spy record -o profile.svg --pid $$PID; kill $$PID; echo "Flamegraph saved to profile.svg"

profile-cprofile:
	@echo "Running cProfile..."
	python -m qdrant_loader.cli.cli ingest --source-type=localfile --profile
	@echo "Opening SnakeViz..."
	snakeviz profile.out

metrics:
	@echo "Starting Prometheus metrics endpoint (to be implemented)"
	# TODO: Implement metrics endpoint and start it here 