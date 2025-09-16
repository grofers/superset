## How to setup DEV Env

### Prerequisites
- Docker, docker-compose, docker buildx plugin


### Build the Custom Image
```commandline
docker buildx build --load --platform linux/arm64 --target dev --output "type=docker" --tag superset:v4_prod .
```
### To do test just the frontend changes

```commandline
cd superset-frontend && npm run dev-server
```
In another cmd line
```commandline
docker-compose -f docker-compose-backend.yml up
```



