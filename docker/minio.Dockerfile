FROM golang:1.24-alpine AS build

ARG MINIO_RELEASE=RELEASE.2025-09-07T16-13-09Z
RUN GOBIN=/out CGO_ENABLED=0 go install "github.com/minio/minio@${MINIO_RELEASE}"

FROM alpine:3.21
RUN apk add --no-cache ca-certificates
COPY --from=build /out/minio /usr/local/bin/minio
EXPOSE 9000 9001
ENTRYPOINT ["/usr/local/bin/minio"]
