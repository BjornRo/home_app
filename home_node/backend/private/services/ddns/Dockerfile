FROM rust:alpine

WORKDIR /app

COPY . .

RUN apk update
# musl, musl-dev, musl-tools
RUN apk add --no-cache musl-dev

RUN cargo build --release

CMD ["./target/release/ddns"]
