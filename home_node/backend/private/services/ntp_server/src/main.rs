use byteorder::{BigEndian, ByteOrder};
use std::net::UdpSocket;
use std::time::SystemTime;
use unsafe_unwrap::UnsafeUnwrap;

fn main() {
    let socket = unsafe { UdpSocket::bind("0.0.0.0:123").unsafe_unwrap() };
    let mut recv_buf = [0u8; 48];
    let mut send_buf = [0u8; 48];
    // Only version 2 and 3
    send_buf[1] = 1;
    send_buf[3] = 227;
    loop {
        let (n, src) = unsafe { socket.recv_from(&mut recv_buf).unsafe_unwrap() };
        s2n(&mut send_buf[16..24]);
        if n == 48 {
            let leading_byte = recv_buf[0];
            let version = leading_byte >> 3 & 7;
            if version < 4 && leading_byte & 7 == 3 {
                send_buf[0] = version << 3 | 4;
                for i in 0..8 {
                    send_buf[i + 24] = recv_buf[i + 40];
                    send_buf[i + 32] = send_buf[i + 16];
                }
                s2n(&mut send_buf[40..48]);
                unsafe {
                    socket.send_to(&send_buf, src).unsafe_unwrap();
                };
            }
        }
    }
}

fn s2n(buf: &mut [u8]) {
    // get current unixtime
    let now = unsafe {
        SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unsafe_unwrap()
    };
    let secs = (now.as_secs() + 2208988800) << 32;
    let nanos = (now.subsec_nanos() as f64 * 4.294967296) as u64;
    BigEndian::write_u64(buf, secs + nanos);
}
