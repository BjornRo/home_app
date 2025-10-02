import type { UserDataTokenExpiry } from "./const";

export const ACCESS_TOKEN = "access_token";
export const REFRESH_TOKEN = "refresh_token";

export const unixtime = (): number => Math.ceil(new Date().getTime() / 1000);

export const is_expired = (expiry_time: number, leeway: number = 0): boolean => expiry_time - leeway < unixtime();

export interface ClaimsCacheKey {
    claims: JWTTokenWithRawStr;
    cache_key: string;
}

export interface NewToken {
    token_type: string;
    access_token: string;
    expires_in: number;
}

export interface JWTTokenWithRawStr extends JWTToken {
    raw_token: string;
}

export interface JWTToken {
    exp: number;
    iat: number;
    sub: string;
    iss: string;
    aud: Array<string>;
}
