# SplatTop

SplatTop is a platform showcasing the Top 500 players in Splatoon 3, along with their ranking history. This project is built using Kubernetes and consists of seven pods: a frontend (React hosted on Nginx), a backend (FastAPI hosted on Gunicorn with Uvicorn workers), a cache/message broker/pubsub (Redis), workers (Celery), a task scheduler (Celery Beat), an ingress controller (Nginx), and a cert-manager (Let's Encrypt). The deployment is managed on a Kubernetes cluster via DigitalOcean Kubernetes Service (DOKS) with continuous integration and deployment facilitated by GitHub Actions.

## Table of Contents

- [Installation](#installation)
  - [Local Development](#local-development)
  - [Secrets Configuration](#secrets-configuration)
- [Architecture](#architecture)
    - [Frontend Pod](#frontend-pod)
    - [Backend Pod](#backend-pod)
    - [Cache/Message Broker/PubSub Pod](#cachemessage-broker-pubsub-pod)
    - [Workers Pod](#workers-pod)
    - [Task Scheduler Pod](#task-scheduler-pod)
    - [Ingress Controller Pod](#ingress-controller-pod)
    - [Cert-Manager Pod (Production Only)](#cert-manager-pod-production-only)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Local Development

To set up the project for local development, please follow these steps:

1. **Clone the Repository**:
    ```sh
    git clone https://github.com/cesaregarza/SplatTop.git
    cd SplatTop
    ```

2. **Set Up Kubernetes Cluster**:
    Ensure you have [kind](https://kind.sigs.k8s.io/) installed. Use the provided `kind-config.yaml` to create a local Kubernetes cluster:
    ```sh
    kind create cluster --config k8s/kind-config.yaml
    ```

3. **Build Docker Images**:
    Use the provided `Makefile` to build the necessary Docker images located in the `dockerfiles` directory:
    ```sh
    make build
    ```

4. **Deploy to Local Cluster**:
    Deploy the core components to your local Kubernetes cluster using the development YAML files. The `-dev` commands facilitate faster iteration with hot reloading. Non `-dev` commands are more similar to production, including the use of an ingress controller, but are slower to iterate on as they require a full rebuild of the Docker images. These commands are used for testing before deploying to the production cluster and closely resemble the production environment until a live development cluster is required.
    ```sh
    make deploy-dev
    ```

5. **Access the Pods**:
    The `deploy-dev` command will start the React application on port 3000 and should open a browser window to `http://localhost:3000`. If the browser window does not open automatically, navigate to `http://localhost:3000` to view the frontend. Hot reloading is enabled, so changes to the frontend code will be reflected immediately. To access the frontend built and served by Nginx, use port 4000. The backend API is available at port 5000. Note that the ingress controller is not used in the `-dev` environment but is utilized in the pre-production environment, accessible at port 8080.


### Secrets Configuration

Currently, there are no mock values for database responses. A `secrets.yaml` file is required to run the project. Please reach out via a GitHub Issue to obtain your own `secrets.yaml`. Until mock values are created, access to the `secrets.yaml` will be granted selectively, even if it is read-only and limited.

## Architecture

### Frontend Pod
The frontend pod hosts the React application on Nginx. It serves the user interface of SplatTop, enabling users to interact with the website and view the Top 500 players and their ranking history. This pod communicates exclusively with the backend pod to fetch data and update the UI based on user actions, and it cannot access the rest of the Kubernetes cluster. While currently written in JavaScript and JSX, a migration to TypeScript and TSX is planned for the near future.

### Backend Pod
The backend pod runs a FastAPI application hosted on Gunicorn with Uvicorn workers. It handles API requests from the frontend, processes data, and communicates with the database. Port 8000 processes the API requests, while port 8001 is used for websocket connections. The backend pod is the core of the SplatTop system and is the only pod capable of communicating with every other communicable pod in the system.

### Cache/Message Broker/PubSub Pod
The Redis pod functions as a cache, message broker, and PubSub system. Celery workers use Redis as a backend to store task results and manage their task queues. The backend application also uses Redis as a cache to store frequently accessed data, reducing the load on the database and improving performance. Additionally, Redis is used as a PubSub system, allowing the Celery workers to signal to the backend that a task has been completed.

### Workers Pod
The workers pod runs Celery workers that handle asynchronous tasks such as data processing and background jobs. This ensures that the main application remains responsive by offloading time-consuming tasks to the workers. The workers receive tasks from either Redis or Celery Beat, process them, store the results in Redis, and optionally send a signal to the backend using Redis PubSub.

### Task Scheduler Pod
The task scheduler pod runs Celery Beat, which schedules periodic tasks for the Celery workers. This is used to automate recurring tasks such as data updates and maintenance jobs.

### Ingress Controller Pod
The ingress controller pod uses Nginx to manage incoming traffic to the Kubernetes cluster. It routes requests to the appropriate services based on predefined rules, ensuring that users can access the frontend and backend services. This is not used in the `-dev` environment, as the frontend and backend communicate directly with each other.

### Cert-Manager Pod (Production Only)
The cert-manager pod is responsible for managing SSL/TLS certificates using Let's Encrypt. This pod is only deployed in the production environment to ensure secure communication between users and the SplatTop website and is completely isolated from the rest of the system.

## Contributing

Contributions are welcome, but I maintain high standards for code quality and maintainability. A CONTRIBUTING.md file will be created in the future, but for now, please reach out via a GitHub Issue to discuss potential contributions. I am open to all ideas but am selective about what code is merged into the project. Feedback and suggestions are always welcome, so please do not hesitate to reach out.

## License

This project is licensed under GPL-3.0. Please refer to the [LICENSE](LICENSE) file for more information.
