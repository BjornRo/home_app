FROM rust:alpine

WORKDIR /app

COPY . .

RUN cargo build --release

CMD ["./target/release/ntp_server"]
