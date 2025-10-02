#[macro_use]
extern crate lazy_static;

use local_ip_address::list_afinet_netifas;
use rustls::{ClientConfig, ClientConnection, RootCertStore, Stream};
use serde::Deserialize;
use std::{
    env::var, fs::read_to_string, io::Write, net::TcpStream, sync::Arc, thread::sleep, time,
};
use toml::from_str;
use unsafe_unwrap::UnsafeUnwrap;
use webpki_roots::TLS_SERVER_ROOTS;

#[derive(Deserialize)]
struct DDNSConfig {
    address: String, // hostname/domain/ip
    path: String,    // HTTP Path incl leading '/'
    domain: String,  // domain name
    token: String,   // access token
}

#[derive(Deserialize)]
struct Config {
    ddns: DDNSConfig, // DDNS config
}
const DEVICE: &str = "eth0";
const SLEEP_TIME_SECONDS: u64 = 600;

lazy_static! {
    static ref CFG: Config = unsafe {
        let s = &read_to_string(var("DATA_PATH").unsafe_unwrap() + "default.toml").unsafe_unwrap();
        from_str(s).unwrap()
    };
}

fn main() {
    let address: &'static str = &CFG.ddns.address;
    let base_path = &CFG
        .ddns
        .path
        .replace("{DOM}", &CFG.ddns.domain)
        .replace("{TOK}", &CFG.ddns.token);
    let root_certs = root_certificates();

    let mut last_ip = String::from("");
    loop {
        if update_ipv4(&mut last_ip) {
            let path = base_path.to_string() + &last_ip;
            if !update_address(root_certs.clone(), &address, &path) {
                last_ip.clear();
            }
        }
        sleep(time::Duration::from_secs(SLEEP_TIME_SECONDS));
    }
}

#[inline(always)]
fn update_address(certs: Arc<ClientConfig>, address: &'static str, path: &str) -> bool {
    if let Ok(mut socket) = TcpStream::connect((address, 443)) {
        let mut client = unsafe {
            ClientConnection::new(certs, address.try_into().unsafe_unwrap()).unsafe_unwrap()
        };
        let mut stream = Stream::new(&mut client, &mut socket);
        if let Ok(_) = stream.write_all(
            format!(
                "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n",
                path, address
            )
            .as_bytes(),
        ) {
            return true;
        }
    }
    false
}

#[inline(always)]
fn update_ipv4(last_ip: &mut String) -> bool {
    for (name, ip) in unsafe { list_afinet_netifas().unsafe_unwrap().iter() } {
        let _ip: String = ip.to_string();
        if name == DEVICE {
            if _ip.starts_with("192.") && &_ip != last_ip {
                *last_ip = _ip;
                return true;
            }
            break;
        }
    }
    false
}

#[inline(always)]
fn root_certificates() -> Arc<ClientConfig> {
    let mut root_store = RootCertStore::empty();
    root_store.extend(TLS_SERVER_ROOTS.iter().cloned());
    let config = ClientConfig::builder()
        .with_root_certificates(root_store)
        .with_no_client_auth();
    Arc::new(config)
}
