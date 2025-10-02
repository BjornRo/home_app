#[macro_use]
extern crate lazy_static;

use local_ip_address::list_afinet_netifas;
use rustls::pki_types::ServerName;
use rustls::StreamOwned;
use rustls::{ClientConfig, ClientConnection, RootCertStore};
use serde::Deserialize;
use std::io::Write;
use std::{env::var, fs::read_to_string, net::TcpStream, sync::Arc, thread::sleep, time};
use toml::from_str;
use webpki_roots::TLS_SERVER_ROOTS;

#[derive(Deserialize)]
struct DDNSConfig {
    addr: String,        // hostname/domain/ip
    path: String,        // HTTP Path incl leading '/'
    user: String,        // Key = "{USER}"
    pwd: String,         // Key = "{PWD}"
    optional_ip: String, // Key = "{V}" \in {4, 6}
}

#[derive(Deserialize)]
struct Config {
    hostname: String, // Hostname of this device
    ddns: DDNSConfig, // DDNS config
}
const DEVICE_IPV4: &str = "eth0";
const DEVICE_IPV6: &str = "lan0";
const SLEEP_TIME_SECONDS: u64 = 600;

lazy_static! {
    static ref CFG: Config =
        from_str(&read_to_string(var("DATA_PATH").unwrap() + "default.toml").unwrap()).unwrap();
}

fn main() {
    let hosts: [String; 3] = ["", "www.", "api."].map(|p: &str| p.to_owned() + &CFG.hostname);
    let cfg = &CFG.ddns;
    let address: &'static str = &cfg.addr;
    let path = cfg
        .path
        .replace("{USER}", &cfg.user)
        .replace("{PWD}", &cfg.pwd);
    let certs = root_certificates();

    let mut last_ipv4 = String::from("");
    let mut last_ipv6 = String::from("");
    loop {
        let res_ips = get_ipv4_ipv6(&mut last_ipv4, &mut last_ipv6);
        if res_ips != 0 {
            let mut query_builder = String::new();

            if res_ips & 1 != 0 {
                query_builder.push_str(&cfg.optional_ip.replace("{V}", "4"));
                query_builder.push_str(&last_ipv4);
            }
            if res_ips & 2 != 0 {
                query_builder.push_str(&cfg.optional_ip.replace("{V}", "6"));
                query_builder.push_str(&last_ipv6);
            }
            if !update_addresses(&certs, &address, &path, hosts.iter(), &query_builder) {
                if res_ips & 1 != 0 {
                    last_ipv4.clear();
                }
                if res_ips & 2 != 0 {
                    last_ipv6.clear();
                }
            }
        }
        sleep(time::Duration::from_secs(SLEEP_TIME_SECONDS));
    }
}

#[inline(always)]
fn get_ipv4_ipv6(last_ipv4: &mut String, last_ipv6: &mut String) -> u8 {
    let mut found_ifaces = 0;
    let mut result: u8 = 0;
    for (name, ip) in list_afinet_netifas().unwrap().iter() {
        let _ip: String = ip.to_string();
        if found_ifaces & 1 == 0 && ip.is_ipv4() {
            if name != DEVICE_IPV4 {
                continue;
            };
            if !(_ip.starts_with("192") || &_ip == last_ipv4) {
                *last_ipv4 = _ip;
                result |= 1;
            }
            found_ifaces |= 1;
        } else if found_ifaces & 2 == 0 && ip.is_ipv6() && name == DEVICE_IPV6 {
            if !(_ip.starts_with("fe80") || _ip.starts_with("fd") || &_ip == last_ipv6) {
                *last_ipv6 = _ip;
                result |= 2;
            }
            found_ifaces |= 2;
        } else {
            continue;
        }

        if found_ifaces == 3 {
            break;
        }
    }
    result
}

#[inline(always)]
fn update_addresses(
    certs: &Arc<ClientConfig>,
    address: &'static str,
    path: &str,
    hosts: std::slice::Iter<'_, std::string::String>,
    query_builder: &str,
) -> bool {
    for host in hosts {
        let result: Result<(), Box<dyn std::error::Error>> = (|| {
            let request = format!(
                "GET {}{}{} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n\r\n",
                path, host, query_builder, address,
            );

            let socket = TcpStream::connect((address, 443))?;
            let server_name = ServerName::try_from(address)?;
            let client = ClientConnection::new(certs.clone(), server_name)?;

            let mut tls_stream = StreamOwned::new(client, socket);
            tls_stream.write_all(request.as_bytes())?;

            Ok(())
        })();

        if result.is_err() {
            return false;
        }
        sleep(time::Duration::from_secs(5))
    }
    true
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
