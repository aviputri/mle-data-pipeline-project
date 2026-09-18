# DB Setup on Terminal

```bash
docker --version
docker info
```

```bash
docker network create ny-green-taxi
```

```bash
mkdir -p db-data
```

```bash
docker run -d \
  --name ny-green-taxi-db \
  --network ny-green-taxi \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ny_green_taxi \
  -v "$(pwd)/db-data:/var/lib/postgresql/data" \
  -p 5432:5432 \
  postgres:17
```

Verify that the container is running
```bash
 docker ps --filter "name=ny-green-taxi-db"
```

Connect with psql 
```bash
docker exec -it ny-green-taxi-db psql -U postgres -d ny_green_taxi
```

```bash
\q
```