import jwt from "jsonwebtoken";
import fs from "fs";
import { unixtime, type JWTTokenWithRawStr } from "$lib/utils/token";

export const JWT_ALGO = "ES384";
const KEY_FILE_PATH = "src/lib/"; // TODO CHANGE TO CERTS PATH

interface APIKey {
    created: string; // iso8601
    pubkey: string; // pem format
    signature: string; // base64 encoded
}

interface APIKeys {
    refresh: APIKey;
    access: APIKey;
}

export const Keys: APIKeys = {
    refresh: JSON.parse(fs.readFileSync(KEY_FILE_PATH + "api_refresh.json", "utf-8")),
    access: JSON.parse(fs.readFileSync(KEY_FILE_PATH + "api_access.json", "utf-8")),
};

export interface JWTPayload {
    exp: number;
    iat: number;
    sub: string;
}

export interface ClaimsCacheKey {
    claims: JWTTokenWithRawStr;
    cache_key: string;
}

export interface Token {
    token_type: string;
    access_token: string;
    expires_in: number;
    refresh_token: string;
    refresh_token_expires_in: number;
}

// interface JWTHeader {
// 	alg: string;
// 	typ: string;
// }
/*
Login to get refresh/access token.
Cache with TTL=access_token_EXPIRY:
    Key = hash(access_token)
    Value = {access_token, user_data}
*/

const validate_jwt = (key: string, token: string): string | null => {
    try {
        const usr_jwt = jwt.verify(token, key, { algorithms: [JWT_ALGO] }) as string | JWTPayload;
        if (typeof usr_jwt !== "string") {
            return usr_jwt.sub;
        }
    } catch (e) {}
    return null;
};

export const validate_jwt_refresh = (token: string): string | null => validate_jwt(Keys.refresh.pubkey, token);
export const validate_jwt_access = (token: string): string | null => validate_jwt(Keys.access.pubkey, token);
export const jwt_time_diff_sec = (time: number): number => Math.ceil(time - unixtime());
