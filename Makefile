.PHONY: build run stop clean logs prod

# Build Docker image
build:
	docker build -t vinyltube-backend .

# Run with docker-compose
run:
	docker-compose up -d

# Stop services
stop:
	docker-compose down

# Clean up containers and images
clean:
	docker-compose down -v
	docker system prune -f

# View logs
logs:
	docker-compose logs -f

# Production mode with nginx
prod:
	docker-compose --profile production up -d

# Development mode
dev:
	docker-compose up vinyltube-backend

# Build and run
build-run: build run

# Enter container shell
shell:
	docker-compose exec vinyltube-backend bash

# Check health
health:
	curl -f http://localhost:8000/api/health || echo "Backend not healthy"
