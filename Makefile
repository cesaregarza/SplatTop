KIND_CONTEXT ?= kind-kind
DEV_PORTS ?= 3000 4000 5000 8001 8080 9090

.PHONY: ensure-kind
ensure-kind:
	kubectl config use-context $(KIND_CONTEXT)

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
	kubectl apply -f k8s/fast-api/fast-api-deployment-dev.yaml
	kubectl apply -f k8s/fast-api/fast-api-service-dev.yaml
	kubectl apply -f k8s/celery-worker/celery-worker-deployment-dev.yaml
	kubectl apply -f k8s/celery-beat/celery-beat-deployment-dev.yaml
	kubectl apply -f k8s/react/react-deployment-dev.yaml
	kubectl apply -f k8s/react/react-service-dev.yaml
	kubectl apply -f k8s/splatgpt/splatgpt-deployment-dev.yaml
	kubectl apply -f k8s/splatgpt/splatgpt-service.yaml
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.0.0/deploy/static/provider/cloud/deploy.yaml

.PHONY: deploy
deploy: ensure-kind
	make deploy-core
	sleep 20
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
	kubectl delete -f k8s/fast-api/fast-api-deployment-dev.yaml || true
	kubectl delete -f k8s/fast-api/fast-api-service-dev.yaml || true
	kubectl delete -f k8s/celery-worker/celery-worker-deployment-dev.yaml || true
	kubectl delete -f k8s/celery-beat/celery-beat-deployment-dev.yaml || true
	kubectl delete -f k8s/react/react-deployment-dev.yaml || true
	kubectl delete -f k8s/react/react-service-dev.yaml || true
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

.PHONY: undeploy-hard
undeploy-hard: undeploy-core-hard

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

# ==============================================================================
# Helm Commands
# ==============================================================================

HELM_CHART_PATH = helm/splattop
HELM_RELEASE_DEV = splattop-dev
HELM_RELEASE_PROD = splattop-prod
HELM_NAMESPACE_DEV = splattop-dev
HELM_NAMESPACE_PROD = splattop-prod

.PHONY: helm-install-dev
helm-install-dev:
	@echo "Installing SplatTop Helm chart (development)..."
	helm install $(HELM_RELEASE_DEV) $(HELM_CHART_PATH) \
		--create-namespace \
		--namespace $(HELM_NAMESPACE_DEV) \
		--values $(HELM_CHART_PATH)/values-local.yaml

.PHONY: helm-install-prod
helm-install-prod:
	@echo "Installing SplatTop Helm chart (production)..."
	helm install $(HELM_RELEASE_PROD) $(HELM_CHART_PATH) \
		--create-namespace \
		--namespace $(HELM_NAMESPACE_PROD) \
		--values $(HELM_CHART_PATH)/values-prod.yaml

.PHONY: helm-upgrade-dev
helm-upgrade-dev:
	@echo "Upgrading SplatTop Helm release (development)..."
	helm upgrade $(HELM_RELEASE_DEV) $(HELM_CHART_PATH) \
		--namespace $(HELM_NAMESPACE_DEV) \
		--values $(HELM_CHART_PATH)/values-local.yaml

.PHONY: helm-upgrade-prod
helm-upgrade-prod:
	@echo "Upgrading SplatTop Helm release (production)..."
	helm upgrade $(HELM_RELEASE_PROD) $(HELM_CHART_PATH) \
		--namespace $(HELM_NAMESPACE_PROD) \
		--values $(HELM_CHART_PATH)/values-prod.yaml

.PHONY: helm-uninstall-dev
helm-uninstall-dev:
	@echo "Uninstalling SplatTop Helm release (development)..."
	helm uninstall $(HELM_RELEASE_DEV) --namespace $(HELM_NAMESPACE_DEV)

.PHONY: helm-uninstall-prod
helm-uninstall-prod:
	@echo "Uninstalling SplatTop Helm release (production)..."
	helm uninstall $(HELM_RELEASE_PROD) --namespace $(HELM_NAMESPACE_PROD)

.PHONY: helm-lint
helm-lint:
	@echo "Linting Helm chart..."
	helm lint $(HELM_CHART_PATH)

.PHONY: helm-template-dev
helm-template-dev:
	@echo "Rendering Helm templates (development)..."
	helm template $(HELM_RELEASE_DEV) $(HELM_CHART_PATH) \
		--values $(HELM_CHART_PATH)/values-local.yaml

.PHONY: helm-template-prod
helm-template-prod:
	@echo "Rendering Helm templates (production)..."
	helm template $(HELM_RELEASE_PROD) $(HELM_CHART_PATH) \
		--values $(HELM_CHART_PATH)/values-prod.yaml

.PHONY: helm-dry-run-dev
helm-dry-run-dev:
	@echo "Dry-run Helm install (development)..."
	helm install $(HELM_RELEASE_DEV) $(HELM_CHART_PATH) \
		--dry-run --debug \
		--namespace $(HELM_NAMESPACE_DEV) \
		--values $(HELM_CHART_PATH)/values-local.yaml

.PHONY: helm-dry-run-prod
helm-dry-run-prod:
	@echo "Dry-run Helm install (production)..."
	helm install $(HELM_RELEASE_PROD) $(HELM_CHART_PATH) \
		--dry-run --debug \
		--namespace $(HELM_NAMESPACE_PROD) \
		--values $(HELM_CHART_PATH)/values-prod.yaml

.PHONY: helm-status-dev
helm-status-dev:
	@echo "Helm release status (development)..."
	helm status $(HELM_RELEASE_DEV) --namespace $(HELM_NAMESPACE_DEV)

.PHONY: helm-status-prod
helm-status-prod:
	@echo "Helm release status (production)..."
	helm status $(HELM_RELEASE_PROD) --namespace $(HELM_NAMESPACE_PROD)

.PHONY: helm-list
helm-list:
	@echo "Listing all Helm releases..."
	helm list --all-namespaces

# ==============================================================================
# ArgoCD Commands
# ==============================================================================

ARGOCD_NAMESPACE = argocd
ARGOCD_VERSION = stable
ARGOCD_APP_DEV = splattop-dev
ARGOCD_APP_PROD = splattop-prod

.PHONY: argocd-install
argocd-install:
	@echo "Installing ArgoCD..."
	kubectl create namespace $(ARGOCD_NAMESPACE) || true
	kubectl apply -n $(ARGOCD_NAMESPACE) -f https://raw.githubusercontent.com/argoproj/argo-cd/$(ARGOCD_VERSION)/manifests/install.yaml
	@echo "Waiting for ArgoCD to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n $(ARGOCD_NAMESPACE)
	@echo "ArgoCD installed successfully!"
	@echo "Get admin password with: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 -d"

.PHONY: argocd-uninstall
argocd-uninstall:
	@echo "Uninstalling ArgoCD..."
	kubectl delete -n $(ARGOCD_NAMESPACE) -f https://raw.githubusercontent.com/argoproj/argo-cd/$(ARGOCD_VERSION)/manifests/install.yaml || true
	kubectl delete namespace $(ARGOCD_NAMESPACE) || true

.PHONY: argocd-password
argocd-password:
	@echo "ArgoCD admin password:"
	@kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
	@echo ""

.PHONY: argocd-ui
argocd-ui:
	@echo "Port-forwarding ArgoCD UI to http://localhost:8080"
	@echo "Login with username: admin"
	@echo "Password: $$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)"
	kubectl port-forward svc/argocd-server -n $(ARGOCD_NAMESPACE) 8080:443

.PHONY: argocd-login
argocd-login:
	@echo "Logging into ArgoCD CLI..."
	@PASSWORD=$$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d); \
	kubectl port-forward svc/argocd-server -n $(ARGOCD_NAMESPACE) 8080:443 & \
	sleep 3; \
	argocd login localhost:8080 --username admin --password $$PASSWORD --insecure

.PHONY: argocd-deploy-project
argocd-deploy-project:
	@echo "Deploying ArgoCD project..."
	kubectl apply -f argocd/projects/splattop-project.yaml

.PHONY: argocd-deploy-dev
argocd-deploy-dev: argocd-deploy-project
	@echo "Deploying SplatTop application to ArgoCD (development)..."
	kubectl apply -f argocd/applications/splattop-dev.yaml

.PHONY: argocd-deploy-prod
argocd-deploy-prod: argocd-deploy-project
	@echo "Deploying SplatTop application to ArgoCD (production)..."
	kubectl apply -f argocd/applications/splattop-prod.yaml

.PHONY: argocd-deploy-all
argocd-deploy-all: argocd-deploy-project
	@echo "Deploying all SplatTop applications via ApplicationSet..."
	kubectl apply -f argocd/applications/splattop-applicationset.yaml

.PHONY: argocd-sync-dev
argocd-sync-dev:
	@echo "Syncing ArgoCD application (development)..."
	argocd app sync $(ARGOCD_APP_DEV)

.PHONY: argocd-sync-prod
argocd-sync-prod:
	@echo "Syncing ArgoCD application (production)..."
	argocd app sync $(ARGOCD_APP_PROD)

.PHONY: argocd-delete-dev
argocd-delete-dev:
	@echo "Deleting ArgoCD application (development)..."
	kubectl delete -f argocd/applications/splattop-dev.yaml || true

.PHONY: argocd-delete-prod
argocd-delete-prod:
	@echo "Deleting ArgoCD application (production)..."
	kubectl delete -f argocd/applications/splattop-prod.yaml || true

.PHONY: argocd-delete-all
argocd-delete-all:
	@echo "Deleting all ArgoCD applications..."
	kubectl delete -f argocd/applications/splattop-applicationset.yaml || true
	kubectl delete -f argocd/applications/splattop-dev.yaml || true
	kubectl delete -f argocd/applications/splattop-prod.yaml || true

.PHONY: argocd-status
argocd-status:
	@echo "ArgoCD application status:"
	@echo "==========================="
	argocd app list || echo "ArgoCD CLI not installed or not logged in"

.PHONY: argocd-status-dev
argocd-status-dev:
	@echo "ArgoCD application status (development):"
	argocd app get $(ARGOCD_APP_DEV)

.PHONY: argocd-status-prod
argocd-status-prod:
	@echo "ArgoCD application status (production):"
	argocd app get $(ARGOCD_APP_PROD)

# ==============================================================================
# Secrets Management
# ==============================================================================

.PHONY: create-secrets-dev
create-secrets-dev:
	@echo "Creating development secrets..."
	@if [ ! -f k8s/secrets.yaml ]; then \
		echo "Error: k8s/secrets.yaml not found. Copy from k8s/secrets.template and configure."; \
		exit 1; \
	fi
	kubectl create namespace $(HELM_NAMESPACE_DEV) || true
	kubectl apply -f k8s/secrets.yaml -n $(HELM_NAMESPACE_DEV)
	kubectl apply -f k8s/monitoring/grafana/secret-dev.yaml -n $(HELM_NAMESPACE_DEV) || true
	kubectl apply -f k8s/monitoring/alertmanager/secret-dev.yaml -n $(HELM_NAMESPACE_DEV) || true
	@echo "Development secrets created in namespace $(HELM_NAMESPACE_DEV)"

.PHONY: create-secrets-prod
create-secrets-prod:
	@echo "Creating production secrets..."
	@if [ ! -f k8s/secrets.yaml ]; then \
		echo "Error: k8s/secrets.yaml not found. Copy from k8s/secrets.template and configure."; \
		exit 1; \
	fi
	kubectl create namespace $(HELM_NAMESPACE_PROD) || true
	kubectl apply -f k8s/secrets.yaml -n $(HELM_NAMESPACE_PROD)
	@echo "Production secrets created in namespace $(HELM_NAMESPACE_PROD)"
	@echo "NOTE: Remember to create grafana-admin-credentials and alertmanager-config secrets for monitoring"

.PHONY: create-regcred
create-regcred:
	@echo "Creating registry credentials secret..."
	@read -p "Enter registry server (e.g., registry.digitalocean.com): " REGISTRY_SERVER; \
	read -p "Enter registry username: " REGISTRY_USER; \
	read -sp "Enter registry password: " REGISTRY_PASS; echo ""; \
	read -p "Enter namespace [default]: " NAMESPACE; \
	NAMESPACE=$${NAMESPACE:-default}; \
	kubectl create secret docker-registry regcred \
		--docker-server=$$REGISTRY_SERVER \
		--docker-username=$$REGISTRY_USER \
		--docker-password=$$REGISTRY_PASS \
		--namespace=$$NAMESPACE

# ==============================================================================
# Validation & Testing
# ==============================================================================

.PHONY: validate-helm
validate-helm:
	@echo "Validating Helm chart..."
	@helm lint $(HELM_CHART_PATH)
	@echo "Validating development configuration..."
	@helm template $(HELM_RELEASE_DEV) $(HELM_CHART_PATH) > /tmp/helm-dev-output.yaml
	@echo "Validating production configuration..."
	@helm template $(HELM_RELEASE_PROD) $(HELM_CHART_PATH) --values $(HELM_CHART_PATH)/values-prod.yaml > /tmp/helm-prod-output.yaml
	@echo "Helm validation complete!"

.PHONY: validate-k8s
validate-k8s: validate-helm
	@echo "Validating Kubernetes manifests with kubectl..."
	@kubectl apply --dry-run=client -f /tmp/helm-dev-output.yaml
	@kubectl apply --dry-run=client -f /tmp/helm-prod-output.yaml
	@echo "Kubernetes manifest validation complete!"

.PHONY: validate-argocd
validate-argocd:
	@echo "Validating ArgoCD manifests..."
	@kubectl apply --dry-run=client -f argocd/projects/splattop-project.yaml
	@kubectl apply --dry-run=client -f argocd/applications/
	@echo "ArgoCD manifest validation complete!"

.PHONY: validate-all
validate-all: validate-helm validate-k8s validate-argocd
	@echo "All validations complete!"

# ==============================================================================
# Utility Commands
# ==============================================================================

.PHONY: kubectl-dev
kubectl-dev:
	@echo "Setting kubectl context to development namespace..."
	kubectl config set-context --current --namespace=$(HELM_NAMESPACE_DEV)

.PHONY: kubectl-prod
kubectl-prod:
	@echo "Setting kubectl context to production namespace..."
	kubectl config set-context --current --namespace=$(HELM_NAMESPACE_PROD)

.PHONY: logs-dev
logs-dev:
	@echo "Streaming logs from development namespace..."
	kubectl logs -f -l app.kubernetes.io/instance=$(HELM_RELEASE_DEV) -n $(HELM_NAMESPACE_DEV) --all-containers=true

.PHONY: logs-prod
logs-prod:
	@echo "Streaming logs from production namespace..."
	kubectl logs -f -l app.kubernetes.io/instance=$(HELM_RELEASE_PROD) -n $(HELM_NAMESPACE_PROD) --all-containers=true

.PHONY: pods-dev
pods-dev:
	@echo "Listing pods in development namespace..."
	kubectl get pods -n $(HELM_NAMESPACE_DEV)

.PHONY: pods-prod
pods-prod:
	@echo "Listing pods in production namespace..."
	kubectl get pods -n $(HELM_NAMESPACE_PROD)

.PHONY: describe-pods-dev
describe-pods-dev:
	@echo "Describing pods in development namespace..."
	kubectl describe pods -n $(HELM_NAMESPACE_DEV)

.PHONY: describe-pods-prod
describe-pods-prod:
	@echo "Describing pods in production namespace..."
	kubectl describe pods -n $(HELM_NAMESPACE_PROD)

.PHONY: clean-all
clean-all:
	@echo "Cleaning up all deployments..."
	@$(MAKE) helm-uninstall-dev || true
	@$(MAKE) helm-uninstall-prod || true
	@$(MAKE) argocd-delete-all || true
	@kubectl delete namespace $(HELM_NAMESPACE_DEV) || true
	@kubectl delete namespace $(HELM_NAMESPACE_PROD) || true
	@echo "Cleanup complete!"

.PHONY: help-helm
help-helm:
	@echo "Helm Commands:"
	@echo "  make helm-install-dev        - Install Helm chart (development)"
	@echo "  make helm-install-prod       - Install Helm chart (production)"
	@echo "  make helm-upgrade-dev        - Upgrade Helm release (development)"
	@echo "  make helm-upgrade-prod       - Upgrade Helm release (production)"
	@echo "  make helm-uninstall-dev      - Uninstall Helm release (development)"
	@echo "  make helm-uninstall-prod     - Uninstall Helm release (production)"
	@echo "  make helm-lint               - Lint Helm chart"
	@echo "  make helm-template-dev       - Render Helm templates (development)"
	@echo "  make helm-template-prod      - Render Helm templates (production)"
	@echo "  make helm-dry-run-dev        - Dry-run Helm install (development)"
	@echo "  make helm-dry-run-prod       - Dry-run Helm install (production)"
	@echo "  make helm-status-dev         - Show Helm release status (development)"
	@echo "  make helm-status-prod        - Show Helm release status (production)"
	@echo "  make helm-list               - List all Helm releases"

.PHONY: help-argocd
help-argocd:
	@echo "ArgoCD Commands:"
	@echo "  make argocd-install          - Install ArgoCD"
	@echo "  make argocd-uninstall        - Uninstall ArgoCD"
	@echo "  make argocd-password         - Get ArgoCD admin password"
	@echo "  make argocd-ui               - Port-forward ArgoCD UI"
	@echo "  make argocd-login            - Login to ArgoCD CLI"
	@echo "  make argocd-deploy-project   - Deploy ArgoCD project"
	@echo "  make argocd-deploy-dev       - Deploy application (development)"
	@echo "  make argocd-deploy-prod      - Deploy application (production)"
	@echo "  make argocd-deploy-all       - Deploy all applications (ApplicationSet)"
	@echo "  make argocd-sync-dev         - Sync application (development)"
	@echo "  make argocd-sync-prod        - Sync application (production)"
	@echo "  make argocd-delete-dev       - Delete application (development)"
	@echo "  make argocd-delete-prod      - Delete application (production)"
	@echo "  make argocd-delete-all       - Delete all applications"
	@echo "  make argocd-status           - Show all ArgoCD applications"
	@echo "  make argocd-status-dev       - Show application status (development)"
	@echo "  make argocd-status-prod      - Show application status (production)"

.PHONY: help-new
help-new:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║           SplatTop - New Deployment Commands                  ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@$(MAKE) help-helm
	@echo ""
	@$(MAKE) help-argocd
	@echo ""
	@echo "Secrets Management:"
	@echo "  make create-secrets-dev      - Create development secrets"
	@echo "  make create-secrets-prod     - Create production secrets"
	@echo "  make create-regcred          - Create registry credentials"
	@echo ""
	@echo "Validation:"
	@echo "  make validate-helm           - Validate Helm chart"
	@echo "  make validate-k8s            - Validate Kubernetes manifests"
	@echo "  make validate-argocd         - Validate ArgoCD manifests"
	@echo "  make validate-all            - Run all validations"
	@echo ""
	@echo "Utilities:"
	@echo "  make kubectl-dev             - Switch kubectl to dev namespace"
	@echo "  make kubectl-prod            - Switch kubectl to prod namespace"
	@echo "  make pods-dev                - List pods (development)"
	@echo "  make pods-prod               - List pods (production)"
	@echo "  make logs-dev                - Stream logs (development)"
	@echo "  make logs-prod               - Stream logs (production)"
	@echo "  make clean-all               - Clean up all deployments"
	@echo ""
