.PHONY: build deploy undeploy redeploy

build:
	docker build -t flask-app:latest -f dockerfiles/dockerfile.flask .
	docker build -t celery-worker:latest -f dockerfiles/dockerfile.celery .
	kind load docker-image flask-app:latest
	kind load docker-image celery-worker:latest

port-forward:
	kubectl port-forward service/flask-app-service 5000:80

deploy:
	kubectl apply -f k8s/secrets.yaml
	kubectl apply -f k8s/redis/redis-deployment.yaml
	kubectl apply -f k8s/redis/redis-service.yaml
	kubectl apply -f k8s/flask/flask-deployment-dev.yaml
	kubectl apply -f k8s/flask/flask-service-dev.yaml
	kubectl apply -f k8s/celery-worker/celery-worker-deployment-dev.yaml
	sleep 5
	kubectl port-forward service/flask-app-service 5000:80

undeploy:
	kubectl delete -f k8s/secrets.yaml
	kubectl delete -f k8s/redis/redis-deployment.yaml
	kubectl delete -f k8s/redis/redis-service.yaml
	kubectl delete -f k8s/flask/flask-deployment-dev.yaml
	kubectl delete -f k8s/flask/flask-service-dev.yaml
	kubectl delete -f k8s/celery-worker/celery-worker-deployment-dev.yaml

redeploy: undeploy deploy

compile-sass:
	sass src/flask_app/static/scss/main.scss src/flask_app/static/css/main.css

update: undeploy build deploy

full-update: undeploy compile-sass build deploy
