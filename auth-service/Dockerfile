FROM golang:1.20-alpine AS base
WORKDIR /app
COPY . .
RUN go mod tidy

FROM base AS test
RUN go test -v ./... || true

FROM base AS build
RUN CGO_ENABLED=0 GOOS=linux go build -o main .

FROM alpine:latest AS production
WORKDIR /app
COPY --from=build /app/main .
EXPOSE 8081
CMD ["./main"]
