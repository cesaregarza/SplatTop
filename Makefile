KIND_CONTEXT ?= kind-kind
DEV_PORTS ?= 3000 4000 5000 8001 8080 9090
USE_HELM ?= 0
HELM_RELEASE ?= splattop
HELM_NAMESPACE ?= default
HELM_CHART ?= helm/splattop
HELM_DEV_VALUES ?= $(HELM_CHART)/values.dev.yaml
HELM_PROD_VALUES ?= $(HELM_CHART)/values.yaml
HELM_EXTRA_ARGS ?=

.PHONY: ensure-kind
ensure-kind:
	kubectl config use-context $(KIND_CONTEXT)

.PHONY: helm-template-dev
helm-template-dev: ensure-kind
	helm template $(HELM_RELEASE) $(HELM_CHART) -n $(HELM_NAMESPACE) -f $(HELM_DEV_VALUES) $(HELM_EXTRA_ARGS)

.PHONY: helm-deploy-dev
helm-deploy-dev: ensure-kind
	helm upgrade --install $(HELM_RELEASE) $(HELM_CHART) -n $(HELM_NAMESPACE) --create-namespace -f $(HELM_DEV_VALUES) --wait --atomic --history-max 5 $(HELM_EXTRA_ARGS)

.PHONY: helm-deploy-prod
helm-deploy-prod: ensure-kind
	helm upgrade --install $(HELM_RELEASE) $(HELM_CHART) -n $(HELM_NAMESPACE) --create-namespace -f $(HELM_PROD_VALUES) --wait --atomic --history-max 5 $(HELM_EXTRA_ARGS)

.PHONY: helm-uninstall
helm-uninstall: ensure-kind
	helm uninstall $(HELM_RELEASE) -n $(HELM_NAMESPACE) || true

.PHONY: build
build:
	docker rmi fast-api-app:latest || true
	docker rmi celery-worker:latest || true
	docker rmi react-app:latest || true
	docker build \
		-t fast-api-app:latest \
		-f dockerfiles/dockerfile.fast-api .
	docker build \
		-t celery-worker:latest \
		-f dockerfiles/dockerfile.celery .
	docker build \
		--build-arg REACT_APP_VERSION="1.0.0" \
		-t react-app:latest \
		-f dockerfiles/dockerfile.react .
	kind load docker-image fast-api-app:latest
	kind load docker-image celery-worker:latest
	kind load docker-image react-app:latest
	kind load docker-image splatnlp:latest

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
port-forward: ensure-kind
	$(MAKE) stop-port-forward || true
	kubectl wait --for=condition=Ready pod -l app=fast-api-app -n default --timeout=180s
	kubectl wait --for=condition=Ready pod -l app=react-app -n default --timeout=180s || true
	kubectl wait --for=condition=Ready pod -l app.kubernetes.io/component=controller -n ingress-nginx --timeout=180s
	kubectl wait --for=condition=Ready pod -l app=prometheus -n monitoring --timeout=180s
	kubectl port-forward service/fast-api-app-service 5000:80 8001:8001 & echo $$! > /tmp/fast-apiport-forward.pid
	kubectl port-forward service/react-app-service 4000:80 & echo $$! > /tmp/react-port-forward.pid
	kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8080:80 & echo $$! > /tmp/ingress-port-forward.pid
	kubectl port-forward -n monitoring service/prometheus 9090:9090 & echo $$! > /tmp/prometheus-port-forward.pid
	echo "fast-api app is running at http://localhost:5000"
	echo "Websocket is running at http://localhost:8001"
	echo "React (prod) app is running at http://localhost:4000"
	echo "Ingress is running at http://localhost:8080"
	echo "Prometheus UI is running at http://localhost:9090"

.PHONY: stop-port-forward
stop-port-forward:
	@if [ -f /tmp/fast-apiport-forward.pid ]; then kill `cat /tmp/fast-apiport-forward.pid` || true; fi
	@if [ -f /tmp/react-port-forward.pid ]; then kill `cat /tmp/react-port-forward.pid` || true; fi
	@if [ -f /tmp/ingress-port-forward.pid ]; then kill `cat /tmp/ingress-port-forward.pid` || true; fi
	@if [ -f /tmp/prometheus-port-forward.pid ]; then kill `cat /tmp/prometheus-port-forward.pid` || true; fi
	rm -f /tmp/fast-apiport-forward.pid
	rm -f /tmp/react-port-forward.pid
	rm -f /tmp/ingress-port-forward.pid
	rm -f /tmp/prometheus-port-forward.pid

.PHONY: deploy-core
deploy-core: ensure-kind
	kubectl apply -f k8s/monitoring/namespace.yaml
	kubectl apply -f k8s/monitoring/grafana/secret-dev.yaml
	kubectl apply -f k8s/monitoring/alertmanager/secret-dev.yaml
	kubectl apply -f k8s/secrets.yaml
	kubectl apply -f k8s/monitoring/prometheus/rbac.yaml
	kubectl apply -f k8s/monitoring/prometheus/configmap.yaml
	kubectl apply -f k8s/monitoring/prometheus/rules.yaml
	kubectl apply -f k8s/monitoring/prometheus/statefulset.yaml
	kubectl apply -f k8s/monitoring/prometheus/service.yaml
	kubectl apply -f k8s/monitoring/prometheus/pdb.yaml
	if kubectl get statefulset/prometheus -n monitoring >/dev/null 2>&1; then \
	  kubectl rollout restart statefulset/prometheus -n monitoring; \
	fi
	kubectl rollout status statefulset/prometheus -n monitoring --timeout=300s
	kubectl apply -f k8s/monitoring/grafana/pvc.yaml
	kubectl apply -f k8s/monitoring/grafana/configmap-datasources.yaml
	kubectl apply -f k8s/monitoring/grafana/configmap-dashboard-providers.yaml
	kubectl apply -f k8s/monitoring/grafana/dashboard-core.yaml
	kubectl apply -f k8s/monitoring/grafana/dashboard-auth-rate.yaml
	kubectl apply -f k8s/monitoring/grafana/dashboard-api-usage.yaml
	kubectl apply -f k8s/monitoring/grafana/dashboard-realtime.yaml
	kubectl apply -f k8s/monitoring/grafana/dashboard-ripple.yaml
	kubectl apply -f k8s/monitoring/grafana/dashboard-splatgpt.yaml
	kubectl apply -f k8s/monitoring/grafana/dashboard-data-pipeline.yaml
	kubectl apply -f k8s/monitoring/grafana/deployment.yaml
	kubectl apply -f k8s/monitoring/grafana/service.yaml
	kubectl apply -f k8s/monitoring/grafana/pdb.yaml
	kubectl apply -f k8s/monitoring/grafana/networkpolicy.yaml
	kubectl apply -f k8s/monitoring/prometheus/networkpolicy.yaml
	kubectl apply -f k8s/monitoring/alertmanager/deployment.yaml
	kubectl apply -f k8s/monitoring/alertmanager/service.yaml
	kubectl apply -f k8s/monitoring/alertmanager/pdb.yaml
	kubectl apply -f k8s/monitoring/alertmanager/networkpolicy.yaml
	kubectl apply -f k8s/monitoring/networkpolicy-default-deny.yaml
	if kubectl get deployment/alertmanager -n monitoring >/dev/null 2>&1; then \
	  kubectl rollout restart deployment/alertmanager -n monitoring; \
	fi
	kubectl rollout status deployment/alertmanager -n monitoring --timeout=300s
	if kubectl get deployment/grafana -n monitoring >/dev/null 2>&1; then \
	  kubectl rollout restart deployment/grafana -n monitoring; \
	fi
	kubectl rollout status deployment/grafana -n monitoring --timeout=300s
	kubectl apply -f k8s/monitoring/grafana/ingress-dev.yaml
	kubectl apply -f k8s/redis/redis-deployment.yaml
	kubectl apply -f k8s/redis/redis-service.yaml
	if [ "$(USE_HELM)" = "1" ]; then \
	  $(MAKE) helm-deploy-dev; \
	else \
	  kubectl apply -f k8s/fast-api/fast-api-deployment-dev.yaml; \
	  kubectl apply -f k8s/fast-api/fast-api-service-dev.yaml; \
	fi
	kubectl apply -f k8s/celery-worker/celery-worker-deployment-dev.yaml
	kubectl apply -f k8s/celery-beat/celery-beat-deployment-dev.yaml
	if [ "$(USE_HELM)" != "1" ]; then \
	  kubectl apply -f k8s/react/react-deployment-dev.yaml; \
	  kubectl apply -f k8s/react/react-service-dev.yaml; \
	fi
	kubectl apply -f k8s/splatgpt/splatgpt-deployment-dev.yaml
	kubectl apply -f k8s/splatgpt/splatgpt-service.yaml
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.0.0/deploy/static/provider/cloud/deploy.yaml

.PHONY: deploy
deploy: ensure-kind
	make deploy-core
	sleep 20
	kubectl apply -f k8s/ingress-dev.yaml
	kubectl port-forward -n ingress-nginx service/ingress-nginx-controller 8080:80

.PHONY: deploy-dev
deploy-dev: ensure-kind
	make deploy-core
	make port-forward
	cd src/react_app && npm start

.PHONY: _undeploy-core-base
_undeploy-core-base:
	kubectl delete -f k8s/secrets.yaml || true
	kubectl delete -f k8s/monitoring/grafana/secret-dev.yaml || true
	kubectl delete -f k8s/monitoring/grafana/ingress-dev.yaml || true
	kubectl delete -f k8s/monitoring/grafana/service.yaml || true
	kubectl delete -f k8s/monitoring/grafana/deployment.yaml || true
	kubectl delete -f k8s/monitoring/grafana/configmap-dashboard-providers.yaml || true
	kubectl delete -f k8s/monitoring/grafana/dashboard-core.yaml || true
	kubectl delete -f k8s/monitoring/grafana/dashboard-auth-rate.yaml || true
	kubectl delete -f k8s/monitoring/grafana/dashboard-api-usage.yaml || true
	kubectl delete -f k8s/monitoring/grafana/dashboard-realtime.yaml || true
	kubectl delete -f k8s/monitoring/grafana/dashboard-ripple.yaml || true
	kubectl delete -f k8s/monitoring/grafana/dashboard-splatgpt.yaml || true
	kubectl delete -f k8s/monitoring/grafana/dashboard-data-pipeline.yaml || true
	kubectl delete -f k8s/monitoring/grafana/configmap-datasources.yaml || true
	kubectl delete -f k8s/monitoring/prometheus/service.yaml || true
	kubectl delete -f k8s/monitoring/prometheus/rules.yaml || true
	kubectl delete -f k8s/monitoring/prometheus/statefulset.yaml || true
	kubectl delete -f k8s/monitoring/prometheus/pdb.yaml || true
	kubectl delete -f k8s/monitoring/prometheus/networkpolicy.yaml || true
	kubectl delete -f k8s/monitoring/prometheus/configmap.yaml || true
	kubectl delete -f k8s/monitoring/prometheus/rbac.yaml || true
	kubectl delete -f k8s/monitoring/alertmanager/networkpolicy.yaml || true
	kubectl delete -f k8s/monitoring/alertmanager/pdb.yaml || true
	kubectl delete -f k8s/monitoring/alertmanager/service.yaml || true
	kubectl delete -f k8s/monitoring/alertmanager/deployment.yaml || true
	kubectl delete -f k8s/redis/redis-deployment.yaml || true
	kubectl delete -f k8s/redis/redis-service.yaml || true
	if [ "$(USE_HELM)" = "1" ]; then \
	  $(MAKE) helm-uninstall; \
	else \
	  kubectl delete -f k8s/fast-api/fast-api-deployment-dev.yaml || true; \
	  kubectl delete -f k8s/fast-api/fast-api-service-dev.yaml || true; \
	  kubectl delete -f k8s/react/react-deployment-dev.yaml || true; \
	  kubectl delete -f k8s/react/react-service-dev.yaml || true; \
	fi
	kubectl delete -f k8s/celery-worker/celery-worker-deployment-dev.yaml || true
	kubectl delete -f k8s/celery-beat/celery-beat-deployment-dev.yaml || true
	kubectl delete -f k8s/splatgpt/splatgpt-deployment-dev.yaml || true
	kubectl delete -f k8s/splatgpt/splatgpt-service.yaml || true
	kubectl delete -f k8s/monitoring/grafana/networkpolicy.yaml || true
	kubectl delete -f k8s/monitoring/networkpolicy-default-deny.yaml || true
	kubectl delete -f k8s/monitoring/alertmanager/secret-dev.yaml || true

.PHONY: _undeploy-core-persistent
_undeploy-core-persistent:
	kubectl delete -f k8s/monitoring/grafana/pvc.yaml || true
	kubectl delete -f k8s/monitoring/namespace.yaml || true

.PHONY: undeploy-core
undeploy-core: ensure-kind _undeploy-core-base

.PHONY: undeploy-core-hard
undeploy-core-hard: ensure-kind _undeploy-core-base _undeploy-core-persistent

.PHONY: undeploy
undeploy: undeploy-core
	kubectl delete -f k8s/ingress-dev.yaml || true

.PHONY: undeploy-hard
undeploy-hard: undeploy-core-hard
	kubectl delete -f k8s/ingress-dev.yaml || true

.PHONY: undeploy-dev
undeploy-dev: undeploy-core
	$(MAKE) stop-port-forward

.PHONY: undeploy-dev-hard
undeploy-dev-hard: undeploy-core-hard
	$(MAKE) stop-port-forward

.PHONY: redeploy
redeploy: ensure-kind undeploy deploy

.PHONY: redeploy-dev
redeploy-dev: ensure-kind undeploy-dev deploy-dev

.PHONY: update
update: ensure-kind undeploy build deploy

.PHONY: update-dev
update-dev: ensure-kind undeploy-dev build deploy-dev

.PHONY: update-dev-hard
update-dev-hard: ensure-kind undeploy-dev-hard build deploy-dev

.PHONY: fast-api-logs
fast-api-logs: ensure-kind
	kubectl logs -f `kubectl get pods -l app=fast-api-app -o jsonpath='{.items[0].metadata.name}'`

.PHONY: celery-logs
celery-logs: ensure-kind
	kubectl logs -f `kubectl get pods -l app=celery-worker -o jsonpath='{.items[0].metadata.name}'`

.PHONY : celery-beat-logs
celery-beat-logs: ensure-kind
	kubectl logs -f `kubectl get pods -l app=celery-beat -o jsonpath='{.items[0].metadata.name}'`

.PHONY: react-logs
react-logs: ensure-kind
	kubectl logs -f `kubectl get pods -l app=react-app -o jsonpath='{.items[0].metadata.name}'`

.PHONY: redis-logs
redis-logs: ensure-kind
	kubectl logs -f `kubectl get pods -l app=redis -o jsonpath='{.items[0].metadata.name}'`

.PHONY: grafana-logs
grafana-logs: ensure-kind
	kubectl logs -f `kubectl get pods -n monitoring -l app=grafana -o jsonpath='{.items[0].metadata.name}'` -n monitoring

.PHONY: prometheus-logs
prometheus-logs: ensure-kind
	kubectl logs -f `kubectl get pods -n monitoring -l app=prometheus -o jsonpath='{.items[0].metadata.name}'` -n monitoring

.PHONY: splatgpt-logs
splatgpt-logs: ensure-kind
	kubectl logs -f `kubectl get pods -l app=splatnlp -o jsonpath='{.items[0].metadata.name}'`

.PHONY: ingress-logs
ingress-logs: ensure-kind
	kubectl logs -f `kubectl get pods -n ingress-nginx -l app.kubernetes.io/component=controller -o jsonpath='{.items[0].metadata.name}'` -n ingress-nginx

.PHONY: start-react-app-dev
start-react-app-dev:
	cd src/react_app && npm start

.PHONY: format
format:
	black src/ tests/
	isort src/ tests/

.PHONY: update-i18n
update-i18n:
	python scripts/i18n.py

.PHONY: load-splatgpt
load-splatgpt:
	kind load docker-image splatnlp:latest

.PHONY: test
test:
	uv run pytest

.PHONY: kill-ports
kill-ports:
	@for port in $(DEV_PORTS); do \
		pids=$$(lsof -ti tcp:$$port -sTCP:LISTEN 2>/dev/null); \
		if [ -n "$$pids" ]; then \
			echo "Force killing process on port $$port: $$pids"; \
			for pid in $$pids; do \
				kill -9 $$pid 2>/dev/null || true; \
				wait $$pid 2>/dev/null || true; \
			done; \
		else \
			echo "No process found on port $$port"; \
		fi; \
	done
