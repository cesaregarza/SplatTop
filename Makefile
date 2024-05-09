.PHONY: build
build:
	docker rmi fast-api-app:latest || true
	docker rmi celery-worker:latest || true
	docker rmi react-app:latest || true
	docker build -t fast-api-app:latest -f dockerfiles/dockerfile.fast-api .
	docker build -t celery-worker:latest -f dockerfiles/dockerfile.celery .
	docker build -t react-app:latest -f dockerfiles/dockerfile.react .
	kind load docker-image fast-api-app:latest
	kind load docker-image celery-worker:latest
	kind load docker-image react-app:latest

.PHONY: build-no-cache
build-no-cache:
	docker rmi fast-api-app:latest || true
	docker rmi celery-worker:latest || true
	docker rmi react-app:latest || true
	docker build --no-cache -t fast-api-app:latest -f dockerfiles/dockerfile.fast-api .
	docker build --no-cache -t celery-worker:latest -f dockerfiles/dockerfile.celery .
	docker build --no-cache -t react-app:latest -f dockerfiles/dockerfile.react .
	kind load docker-image fast-api-app:latest
	kind load docker-image celery-worker:latest
	kind load docker-image react-app:latest

.PHONY: port-forward
port-forward:
	kubectl port-forward service/fast-api-app-service 5000:80 8001:8001 & echo $$! > /tmp/fast-apiport-forward.pid
	kubectl port-forward service/react-app-service 4000:80 & echo $$! > /tmp/react-port-forward.pid
	kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8080:80 & echo $$! > /tmp/ingress-port-forward.pid
	echo "fast-api app is running at http://localhost:5000"
	echo "Websocket is running at http://localhost:8001"
	echo "React (prod) app is running at http://localhost:4000"

.PHONY: stop-port-forward
stop-port-forward:
	kill `cat /tmp/fast-apiport-forward.pid` || true
	kill `cat /tmp/react-port-forward.pid` || true
	kill `cat /tmp/ingress-port-forward.pid` || true
	rm -f /tmp/fast-apiport-forward.pid
	rm -f /tmp/react-port-forward.pid
	rm -f /tmp/ingress-port-forward.pid

.PHONY: deploy
deploy:
	kubectl apply -f k8s/secrets.yaml
	kubectl apply -f k8s/redis/redis-deployment.yaml
	kubectl apply -f k8s/redis/redis-service.yaml
	kubectl apply -f k8s/fast-api/fast-api-deployment-dev.yaml
	kubectl apply -f k8s/fast-api/fast-api-service-dev.yaml
	kubectl apply -f k8s/celery-worker/celery-worker-deployment-dev.yaml
	kubectl apply -f k8s/celery-beat/celery-beat-deployment-dev.yaml
	kubectl apply -f k8s/react/react-deployment-dev.yaml
	kubectl apply -f k8s/react/react-service-dev.yaml
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.0.0/deploy/static/provider/cloud/deploy.yaml
	sleep 20
	kubectl apply -f k8s/ingress-dev.yaml

.PHONY: undeploy
undeploy:
	kubectl delete -f k8s/secrets.yaml
	kubectl delete -f k8s/redis/redis-deployment.yaml
	kubectl delete -f k8s/redis/redis-service.yaml
	kubectl delete -f k8s/fast-api/fast-api-deployment-dev.yaml
	kubectl delete -f k8s/fast-api/fast-api-service-dev.yaml
	kubectl delete -f k8s/celery-worker/celery-worker-deployment-dev.yaml
	kubectl delete -f k8s/celery-beat/celery-beat-deployment-dev.yaml
	kubectl delete -f k8s/react/react-deployment-dev.yaml
	kubectl delete -f k8s/react/react-service-dev.yaml
	kubectl delete -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.0.0/deploy/static/provider/cloud/deploy.yaml
	kubectl delete -f k8s/ingress-dev.yaml
	make stop-port-forward

.PHONY: redeploy
redeploy: undeploy deploy

.PHONY: update
update: undeploy build deploy

.PHONY: fast-api-logs
fast-api-logs:
	kubectl logs -f `kubectl get pods -l app=fast-api-app -o jsonpath='{.items[0].metadata.name}'`

.PHONY: celery-logs
celery-logs:
	kubectl logs -f `kubectl get pods -l app=celery-worker -o jsonpath='{.items[0].metadata.name}'`

.PHONY : celery-beat-logs
celery-beat-logs:
	kubectl logs -f `kubectl get pods -l app=celery-beat -o jsonpath='{.items[0].metadata.name}'`

.PHONY: react-logs
react-logs:
	kubectl logs -f `kubectl get pods -l app=react-app -o jsonpath='{.items[0].metadata.name}'`

.PHONY: redis-logs
redis-logs:
	kubectl logs -f `kubectl get pods -l app=redis -o jsonpath='{.items[0].metadata.name}'`

.PHONY: ingress-logs
ingress-logs:
	kubectl logs -f `kubectl get pods -n ingress-nginx -l app.kubernetes.io/component=controller -o jsonpath='{.items[0].metadata.name}'` -n ingress-nginx

.PHONY: start-react-app-dev
start-react-app-dev:
	cd src/react_app && npm start