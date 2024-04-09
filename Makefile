.PHONY: build
build:
	docker rmi flask-app:latest || true
	docker rmi celery-worker:latest || true
	docker rmi react-app:latest || true
	docker build -t flask-app:latest -f dockerfiles/dockerfile.flask .
	docker build -t celery-worker:latest -f dockerfiles/dockerfile.celery .
	docker build -t react-app:latest -f dockerfiles/dockerfile.react .
	kind load docker-image flask-app:latest
	kind load docker-image celery-worker:latest
	kind load docker-image react-app:latest

.PHONY: build-no-cache
build-no-cache:
	docker rmi flask-app:latest || true
	docker rmi celery-worker:latest || true
	docker rmi react-app:latest || true
	docker build --no-cache -t flask-app:latest -f dockerfiles/dockerfile.flask .
	docker build --no-cache -t celery-worker:latest -f dockerfiles/dockerfile.celery .
	docker build --no-cache -t react-app:latest -f dockerfiles/dockerfile.react .
	kind load docker-image flask-app:latest
	kind load docker-image celery-worker:latest
	kind load docker-image react-app:latest

.PHONY: port-forward
port-forward:
	kubectl port-forward service/flask-app-service 5000:80 & echo $$! > /tmp/flask-port-forward.pid
	kubectl port-forward service/react-app-service 4000:80 & echo $$! > /tmp/react-port-forward.pid
	echo "Flask app is running at http://localhost:5000"
	echo "React (prod) app is running at http://localhost:4000"

.PHONY: stop-port-forward
stop-port-forward:
	kill `cat /tmp/flask-port-forward.pid` || true
	kill `cat /tmp/react-port-forward.pid` || true
	rm -f /tmp/flask-port-forward.pid
	rm -f /tmp/react-port-forward.pid

.PHONY: deploy
deploy:
	kubectl apply -f k8s/secrets.yaml
	kubectl apply -f k8s/redis/redis-deployment.yaml
	kubectl apply -f k8s/redis/redis-service.yaml
	kubectl apply -f k8s/flask/flask-deployment-dev.yaml
	kubectl apply -f k8s/flask/flask-service-dev.yaml
	kubectl apply -f k8s/celery-worker/celery-worker-deployment-dev.yaml
	kubectl apply -f k8s/celery-beat/celery-beat-deployment-dev.yaml
	kubectl apply -f k8s/react/react-deployment-dev.yaml
	kubectl apply -f k8s/react/react-service-dev.yaml
	sleep 5
	make port-forward
	echo "React (dev) app is running at http://localhost:3000"
	cd src/react_app && npm start

.PHONY: undeploy
undeploy:
	kubectl delete -f k8s/secrets.yaml
	kubectl delete -f k8s/redis/redis-deployment.yaml
	kubectl delete -f k8s/redis/redis-service.yaml
	kubectl delete -f k8s/flask/flask-deployment-dev.yaml
	kubectl delete -f k8s/flask/flask-service-dev.yaml
	kubectl delete -f k8s/celery-worker/celery-worker-deployment-dev.yaml
	kubectl delete -f k8s/celery-beat/celery-beat-deployment-dev.yaml
	kubectl delete -f k8s/react/react-deployment-dev.yaml
	kubectl delete -f k8s/react/react-service-dev.yaml
	make stop-port-forward

.PHONY: redeploy
redeploy: undeploy deploy

.PHONY: compile-sass
compile-sass:
	sass src/flask_app/static/scss/main.scss src/flask_app/static/css/main.css

.PHONY: update
update: undeploy build deploy

.PHONY: full-update
full-update: undeploy compile-sass build deploy

.PHONY: flask-logs
flask-logs:
	kubectl logs -f `kubectl get pods -l app=flask-app -o jsonpath='{.items[0].metadata.name}'`

.PHONY: celery-logs
celery-logs:
	kubectl logs -f `kubectl get pods -l app=celery-worker -o jsonpath='{.items[0].metadata.name}'`

.PHONY : celery-beat-logs
celery-beat-logs:
	kubectl logs -f `kubectl get pods -l app=celery-beat -o jsonpath='{.items[0].metadata.name}'`

.PHONY: react-logs
react-logs:
	kubectl logs -f `kubectl get pods -l app=react-app -o jsonpath='{.items[0].metadata.name}'`

.PHONY: start-react-app-dev
start-react-app-dev:
	cd src/react_app && npm start